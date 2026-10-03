import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import numpy as np

from backend.app.services.video_source import VideoSource, WebcamSource, IPCameraSource, FramePacket
from backend.app.services.common_pipeline_service import common_frame_pipeline
from backend.app.core.logging import logger


class CameraStreamManager:
    """
    Central Video Stream & Ingestion Manager.
    
    RESPONSIBILITIES:
    1. Manages VideoSource instances across cameras (Webcam, IP Camera/CCTV, Recorded Video).
    2. Runs background non-blocking AI ingestion workers for connected RTSP streams.
    3. Enforces Latest-Frame-Wins backpressure policy to eliminate stale latency.
    4. Provides complete stream telemetry (FPS, dropped frames, buffer depth, connection status).
    5. Clean session lifecycle management (releases all camera resources on stop).
    """
    def __init__(self):
        # camera_id -> VideoSource
        self._sources: Dict[str, VideoSource] = {}
        # camera_id -> asyncio.Task
        self._ai_worker_tasks: Dict[str, asyncio.Task] = {}
        # camera_id -> latest AI frame result
        self._latest_ai_results: Dict[str, Dict[str, Any]] = {}
        self._running_flags: Dict[str, bool] = {}

    def get_source(self, camera_id: str) -> Optional[VideoSource]:
        return self._sources.get(camera_id)

    def register_source(self, camera_id: str, source: VideoSource):
        self._sources[camera_id] = source

    async def get_or_create_webcam_source(self, camera_id: str = "cam-webcam") -> WebcamSource:
        if camera_id not in self._sources or not isinstance(self._sources[camera_id], WebcamSource):
            src = WebcamSource(source_id=camera_id)
            await src.connect()
            self._sources[camera_id] = src
        return self._sources[camera_id]  # type: ignore

    async def start_ip_stream(
        self,
        camera_id: str,
        rtsp_url: str,
        exam_session_id: str,
        exam_id: str
    ) -> bool:
        """
        Mounts and starts continuous RTSP IP Camera stream with latest-frame-wins backpressure.
        Credentials stay strictly backend-only.
        """
        # Stop existing stream if running
        await self.stop_camera_stream(camera_id)

        source = IPCameraSource(source_id=camera_id, rtsp_url=rtsp_url)
        connected = await source.connect()
        self._sources[camera_id] = source
        if not connected:
            logger.warning(f"Could not connect to IP Camera '{camera_id}'")
            return False

        self._running_flags[camera_id] = True
        # Launch background AI worker for this camera
        task = asyncio.create_task(
            self._ip_ai_consumer_loop(camera_id, source, exam_session_id, exam_id)
        )
        self._ai_worker_tasks[camera_id] = task
        logger.info(f"Background AI stream worker launched for IP Camera '{camera_id}'.")
        return True

    async def _ip_ai_consumer_loop(
        self,
        camera_id: str,
        source: IPCameraSource,
        exam_session_id: str,
        exam_id: str
    ):
        """
        Pulls latest frames from the bounded dropping queue and processes via Common AI Pipeline.
        Guarantees AI runs at actual processing throughput without queuing delay.
        """
        logger.info(f"AI consumer loop active for camera '{camera_id}'")
        while self._running_flags.get(camera_id, False):
            try:
                # Pull latest frame from the 1-capacity buffer
                packet = await source.read_frame()
                if packet is not None:
                    # Execute common AI frame pipeline
                    ai_result = await common_frame_pipeline.process_frame(
                        frame_packet=packet,
                        exam_session_id=exam_session_id,
                        exam_id=exam_id
                    )
                    self._latest_ai_results[camera_id] = ai_result
                else:
                    # No new frame in buffer; sleep briefly
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in IP AI consumer loop for '{camera_id}': {str(e)}")
                await asyncio.sleep(0.1)

    async def stop_camera_stream(self, camera_id: str) -> bool:
        """Stops background ingestion and releases resources for a camera."""
        self._running_flags[camera_id] = False
        task = self._ai_worker_tasks.pop(camera_id, None)
        if task and not task.done():
            task.cancel()

        source = self._sources.get(camera_id)
        if source:
            await source.disconnect()

        logger.info(f"Camera stream stopped for '{camera_id}'.")
        return True

    def get_latest_ai_result(self, camera_id: str) -> Optional[Dict[str, Any]]:
        return self._latest_ai_results.get(camera_id)

    def get_stream_telemetry(self, camera_id: str) -> Dict[str, Any]:
        source = self._sources.get(camera_id)
        if not source:
            return {
                "camera_id": camera_id,
                "status": "OFFLINE",
                "connected": False,
                "buffer_stats": {
                    "frames_captured": 0,
                    "frames_processed": 0,
                    "frames_dropped": 0,
                    "queue_depth": 0,
                    "capture_fps": 0.0,
                    "processing_fps": 0.0,
                }
            }
        return {
            "camera_id": camera_id,
            "status": source.status,
            "connected": source.status == "ONLINE",
            "last_seen_at": source.last_seen_at.isoformat() if source.last_seen_at else None,
            "error_message": source.error_message,
            "buffer_stats": source.buffer.get_stats()
        }

    async def shutdown_all(self):
        """Clean shutdown across all active camera streams (Session lifecycle)."""
        logger.info("Shutting down all active camera streams...")
        for cid in list(self._sources.keys()):
            await self.stop_camera_stream(cid)
        self._sources.clear()
        self._latest_ai_results.clear()
        self._running_flags.clear()


camera_stream_manager = CameraStreamManager()
