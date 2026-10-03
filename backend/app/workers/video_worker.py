import asyncio
import uuid
import time
import os
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from backend.app.models.requests import VideoProcessRequest
from backend.app.models.responses import VideoProcessJobResponse
from backend.app.services.video_source import RecordedVideoSource, FramePacket
from backend.app.services.common_pipeline_service import common_frame_pipeline
from backend.app.services.biometric_cache import biometric_cache_manager
from backend.app.services.tracking_service import tracking_service
from backend.app.integrations.supabase import supabase_db
from backend.app.core.logging import logger
from backend.app.core.config import settings


class VideoProcessingWorker:
    """
    Asynchronous Examination Recorded Video Processing Worker.
    
    CAPABILITIES:
    1. Loads exam candidates' biometric cache for face recognition.
    2. Uses RecordedVideoSource to decode real MP4/AVI examination footage.
    3. Feeds extracted frames sequentially through the COMMON AI FRAME PIPELINE.
    4. Computes true video duration, frames processed, processing throughput (FPS),
       estimated remaining time, and progress percentage.
    5. Detects observable events and generates advisory alerts.
    6. Supports invigilator-authorized manual identity mapping with audit logging.
    """

    def __init__(self):
        # job_id -> VideoProcessJobResponse
        self._jobs: Dict[str, VideoProcessJobResponse] = {}
        # job_id -> asyncio.Task
        self._tasks: Dict[str, asyncio.Task] = {}
        # job_id -> RecordedVideoSource
        self._sources: Dict[str, RecordedVideoSource] = {}

    async def enqueue_video_job(self, request: VideoProcessRequest) -> VideoProcessJobResponse:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        job = VideoProcessJobResponse(
            job_id=job_id,
            exam_id=request.exam_id,
            video_reference=request.video_reference,
            status="QUEUED",
            progress_percentage=0.0,
            frames_processed=0,
            total_frames_estimate=0,
            duration_seconds=0.0,
            processing_fps=0.0,
            estimated_remaining_seconds=None,
            events_detected_count=0,
            alerts_generated_count=0,
            error_message=None,
            manual_mappings={},
            created_at=now,
            completed_at=None,
        )
        self._jobs[job_id] = job
        logger.info(f"Recorded video job '{job_id}' enqueued for exam '{request.exam_id}': {request.video_reference}")

        # Dispatch async worker task without blocking HTTP response
        task = asyncio.create_task(self._execute_video_job(job_id, request))
        self._tasks[job_id] = task
        return job

    async def _execute_video_job(self, job_id: str, request: VideoProcessRequest):
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = "PROCESSING"
        logger.info(f"Worker started asynchronous processing for video job '{job_id}'")

        file_path = request.video_reference
        # If relative or storage path, check if it exists locally
        if not os.path.exists(file_path):
            # Check models directory or scratch directory for test videos
            candidates = [
                os.path.join("backend", "models", file_path),
                os.path.join("scratch", file_path),
                file_path
            ]
            for c in candidates:
                if os.path.exists(c):
                    file_path = c
                    break

        # 1. Initialize Recorded Video Source
        source = RecordedVideoSource(source_id=f"rec-{job_id}", file_path=file_path)
        self._sources[job_id] = source
        connected = await source.connect()
        if not connected:
            job.status = "FAILED"
            job.error_message = source.error_message or f"Could not access video file at {file_path}"
            logger.error(f"Job '{job_id}' failed to connect to video source: {job.error_message}")
            return

        job.total_frames_estimate = source.total_frames
        job.duration_seconds = source.duration_seconds

        # 2. Preload Exam Biometric Cache (Enrolled Face Templates)
        try:
            await biometric_cache_manager.get_or_load_cache(request.exam_id)
        except Exception as e:
            logger.warning(f"Could not load biometric cache for exam '{request.exam_id}': {str(e)}")

        start_time = time.perf_counter()
        frames_processed = 0
        events_count = 0
        alerts_count = 0
        exam_session_id = f"sess-rec-{job_id}"
        camera_id = request.camera_id or "cam-recorded"

        try:
            # Step size for sampling: if video is high frame rate, sample to match AI throughput (~4 FPS)
            # or process every frame for short test clips
            sample_interval = 1 if source.total_frames < 30 else max(1, int(source.fps / 4.0))

            while True:
                packet = await source.read_frame()
                if packet is None:
                    # End of video reached
                    break

                # Sample frames based on interval
                if source.current_frame_index % sample_interval != 0:
                    continue

                # Execute COMMON AI FRAME PIPELINE
                result = await common_frame_pipeline.process_frame(
                    frame_packet=packet,
                    exam_session_id=exam_session_id,
                    exam_id=request.exam_id
                )

                frames_processed += 1
                ev_list = result.get("observable_events", [])
                events_count += len(ev_list)

                suspicion = result.get("suspicion_index", {})
                if suspicion.get("requires_alert"):
                    alerts_count += 1

                # Update Progress Telemetry
                elapsed = max(0.001, time.perf_counter() - start_time)
                current_fps = round(frames_processed / elapsed, 2)
                progress = round((source.current_frame_index / max(1, source.total_frames)) * 100.0, 1)

                remaining_frames = max(0, (source.total_frames - source.current_frame_index) / sample_interval)
                rem_sec = round(remaining_frames / max(0.1, current_fps), 1) if current_fps > 0 else 0.0

                job.frames_processed = source.current_frame_index
                job.progress_percentage = min(100.0, progress)
                job.processing_fps = current_fps
                job.estimated_remaining_seconds = rem_sec
                job.events_detected_count = events_count
                job.alerts_generated_count = alerts_count

                # Yield control to event loop to keep FastAPI responsive
                await asyncio.sleep(0.001)

            # Successfully completed
            job.status = "COMPLETED"
            job.progress_percentage = 100.0
            job.frames_processed = source.total_frames
            job.completed_at = datetime.now(timezone.utc)
            total_duration = time.perf_counter() - start_time
            logger.info(
                f"Video job '{job_id}' completed successfully in {total_duration:.2f}s "
                f"({frames_processed} frames analyzed, {events_count} events, {alerts_count} alerts)."
            )

        except asyncio.CancelledError:
            job.status = "CANCELLED"
            job.error_message = "Job cancelled by user request"
            logger.info(f"Video job '{job_id}' was cancelled.")
        except Exception as e:
            job.status = "FAILED"
            job.error_message = str(e)
            logger.error(f"Error during video processing job '{job_id}': {str(e)}")
        finally:
            await source.disconnect()

    def get_job_status(self, job_id: str) -> Optional[VideoProcessJobResponse]:
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job or job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return False
        task = self._tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        job.status = "CANCELLED"
        job.completed_at = datetime.now(timezone.utc)
        return True

    async def manual_identity_mapping(
        self,
        job_id: str,
        tracking_id: str,
        student_id: str,
        invigilator_id: str = "invigilator-01",
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Preserves manual identity mapping capability for offline recorded examination reviews.
        Overwrites track identity and records non-repudiable audit event.
        """
        job = self._jobs.get(job_id)
        camera_id = "cam-recorded"

        # Update Tracking Service State Machine
        await tracking_service.update_track_identity(
            camera_id=camera_id,
            tracking_id=tracking_id,
            identity_status="IDENTIFIED",
            student_id=student_id,
            student_name=f"Student {student_id}",
            similarity=1.0  # Manual authorization confidence
        )

        # Record Non-Repudiable Audit Event
        audit = await supabase_db.record_audit_event(
            actor=invigilator_id,
            action="MANUAL_IDENTITY_MAPPING",
            entity_type="STUDENT_TRACK",
            entity_id=tracking_id,
            metadata={
                "job_id": job_id,
                "mapped_student_id": student_id,
                "notes": notes or "Manual override by invigilator during recorded video review"
            }
        )

        if job:
            job.manual_mappings[tracking_id] = student_id

        logger.info(
            f"AUDIT OVERRIDE: Tracking '{tracking_id}' manually mapped to student '{student_id}' "
            f"by '{invigilator_id}'."
        )
        return {
            "status": "MAPPED",
            "job_id": job_id,
            "tracking_id": tracking_id,
            "student_id": student_id,
            "audit_id": audit["id"],
            "timestamp": audit["timestamp"]
        }


video_worker = VideoProcessingWorker()
