import pytest
import os
import asyncio
import time
from datetime import datetime, timezone
import numpy as np
import cv2

from backend.app.services.video_source import (
    FramePacket,
    BoundedFrameBuffer,
    WebcamSource,
    IPCameraSource,
    RecordedVideoSource
)
from backend.app.services.common_pipeline_service import common_frame_pipeline
from backend.app.services.camera_manager import camera_stream_manager
from backend.app.workers.video_worker import video_worker
from backend.app.models.requests import VideoProcessRequest


# ==============================================================================
# 1. BOUNDED BUFFER & BACKPRESSURE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_bounded_buffer_latest_frame_wins():
    """Verify that buffer keeps capacity=1, dropping older frames when overwhelmed."""
    buffer = BoundedFrameBuffer(capacity=1)
    img = np.zeros((100, 100, 3), dtype=np.uint8)

    # Ingest 10 frames rapidly without consumer reading
    for i in range(10):
        pkt = FramePacket(frame=img, source_id="cam-01", source_type="WEBCAM", frame_number=i)
        await buffer.put(pkt)

    stats = buffer.get_stats()
    assert stats["frames_captured"] == 10
    assert stats["frames_dropped"] == 9
    assert stats["queue_depth"] == 1

    # Reading should return the latest frame (frame_number=9)
    latest = await buffer.get_latest()
    assert latest is not None
    assert latest.frame_number == 9

    # Second read should be empty (cleared)
    second = await buffer.get_latest()
    assert second is None


# ==============================================================================
# 2. WEBCAM SOURCE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_webcam_source_client_push_mode():
    """Verify WebcamSource accepts client browser frames and enforces bounded queue."""
    webcam = WebcamSource(source_id="webcam-test", device_index=None)
    connected = await webcam.connect()
    assert connected is True
    assert webcam.get_status() == "ONLINE"

    img = np.zeros((480, 640, 3), dtype=np.uint8)
    dropped = await webcam.ingest_client_frame(img, metadata={"client": "browser"})
    assert dropped is False

    frame_pkt = await webcam.read_frame()
    assert frame_pkt is not None
    assert frame_pkt.source_type == "WEBCAM"
    assert frame_pkt.resolution == (640, 480)
    assert frame_pkt.metadata.get("client") == "browser"

    await webcam.disconnect()
    assert webcam.get_status() == "OFFLINE"


# ==============================================================================
# 3. RECORDED VIDEO SOURCE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_recorded_video_source_real_mp4():
    """Verify RecordedVideoSource opens and reads valid MP4 video."""
    video_path = os.path.join("backend", "models", "test_exam_video.mp4")
    assert os.path.exists(video_path)

    rec_source = RecordedVideoSource(source_id="rec-test", file_path=video_path)
    connected = await rec_source.connect()
    assert connected is True
    assert rec_source.get_status() == "ONLINE"
    assert rec_source.total_frames == 15
    assert rec_source.fps == 10.0
    assert rec_source.duration_seconds == 1.5

    # Read all frames
    count = 0
    while True:
        pkt = await rec_source.read_frame()
        if pkt is None:
            break
        count += 1
        assert pkt.source_type == "RECORDED_VIDEO"
        assert pkt.frame_number == count

    assert count == 15
    assert rec_source.progress_percentage == 100.0
    assert rec_source.get_status() == "COMPLETED"

    await rec_source.disconnect()
    assert rec_source.get_status() == "OFFLINE"


@pytest.mark.asyncio
async def test_recorded_video_missing_file_error():
    """Verify error handling when video file does not exist."""
    rec_source = RecordedVideoSource(source_id="rec-bad", file_path="nonexistent_video_path.mp4")
    connected = await rec_source.connect()
    assert connected is False
    assert rec_source.get_status() == "ERROR"
    assert "not found" in rec_source.error_message.lower()


# ==============================================================================
# 4. IP CAMERA RTSP ADAPTER TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_ip_camera_adapter_failed_socket_handling():
    """Verify IPCameraSource handles inaccessible RTSP socket gracefully without crash."""
    # Connecting to invalid RTSP endpoint
    ip_source = IPCameraSource(
        source_id="cctv-front",
        rtsp_url="rtsp://127.0.0.1:8554/nonexistent_stream",
        reconnect_attempts=1,
        base_backoff_seconds=0.1
    )
    connected = await ip_source.connect()
    # Should report failed connection cleanly
    assert connected is False
    assert ip_source.get_status() == "ERROR"
    assert ip_source.error_message is not None

    meta = ip_source.get_metadata()
    assert meta["source_id"] == "cctv-front"
    assert meta["status"] == "ERROR"

    await ip_source.disconnect()
    assert ip_source.get_status() == "OFFLINE"


# ==============================================================================
# 5. COMMON AI FRAME PIPELINE UNIFIED PROCESSING
# ==============================================================================

@pytest.mark.asyncio
async def test_common_frame_pipeline_with_various_sources():
    """
    Verify that FramePackets from WEBCAM, IP_CAMERA, and RECORDED_VIDEO
    all process seamlessly through the EXACT SAME common frame pipeline.
    """
    img = cv2.imread("backend/models/test_exam_phone.jpg")
    if img is None:
        img = np.zeros((480, 640, 3), dtype=np.uint8)

    sources = ["WEBCAM", "IP_CAMERA", "RECORDED_VIDEO"]
    for src_type in sources:
        packet = FramePacket(
            frame=img,
            source_id=f"test-{src_type.lower()}",
            source_type=src_type,
            timestamp=datetime.now(timezone.utc),
            frame_number=1,
            metadata={"source_test": True}
        )

        result = await common_frame_pipeline.process_frame(
            frame_packet=packet,
            exam_session_id="sess-common-test",
            exam_id="exam-01"
        )

        assert result["source_type"] == src_type
        assert "recognized_faces" in result
        assert "detected_objects" in result
        assert "suspicion_index" in result
        assert "observable_events" in result
        assert result["processing_time_ms"] > 0.0


# ==============================================================================
# 6. RECORDED VIDEO BACKGROUND WORKER & JOB LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_recorded_video_worker_full_lifecycle():
    """Verify real video processing job execution, progress updates, and completion."""
    video_path = os.path.join("backend", "models", "test_exam_video.mp4")

    req = VideoProcessRequest(
        exam_id="exam-01",
        video_reference=video_path,
        camera_id="cam-recorded-test"
    )

    job_resp = await video_worker.enqueue_video_job(req)
    assert job_resp.job_id is not None
    assert job_resp.status == "QUEUED"

    # Poll status until complete (short 15 frame video takes < 4 seconds)
    for _ in range(40):
        await asyncio.sleep(0.1)
        current = video_worker.get_job_status(job_resp.job_id)
        if current and current.status in ["COMPLETED", "FAILED"]:
            break

    final_job = video_worker.get_job_status(job_resp.job_id)
    assert final_job is not None
    assert final_job.status == "COMPLETED"
    assert final_job.progress_percentage == 100.0
    assert final_job.frames_processed == 15
    assert final_job.duration_seconds == 1.5
    assert final_job.processing_fps > 0.0
    assert final_job.completed_at is not None


@pytest.mark.asyncio
async def test_recorded_video_manual_identity_mapping():
    """Verify invigilator can manually map a tracking ID to a student with audit trail."""
    video_path = os.path.join("backend", "models", "test_exam_video.mp4")
    req = VideoProcessRequest(
        exam_id="exam-01",
        video_reference=video_path,
        camera_id="cam-recorded-test"
    )
    job = await video_worker.enqueue_video_job(req)

    # Perform manual mapping
    mapping = await video_worker.manual_identity_mapping(
        job_id=job.job_id,
        tracking_id="trk-cam-01-017",
        student_id="s-01",
        invigilator_id="invigilator-chief",
        notes="Confirmed student seat matches B4-12"
    )

    assert mapping["status"] == "MAPPED"
    assert mapping["tracking_id"] == "trk-cam-01-017"
    assert mapping["student_id"] == "s-01"
    assert "audit_id" in mapping

    # Verify reflected in job
    current_job = video_worker.get_job_status(job.job_id)
    assert current_job.manual_mappings.get("trk-cam-01-017") == "s-01"


@pytest.mark.asyncio
async def test_recorded_video_cancel_job():
    """Verify job cancellation."""
    video_path = os.path.join("backend", "models", "test_exam_video.mp4")
    req = VideoProcessRequest(
        exam_id="exam-01",
        video_reference=video_path,
        camera_id="cam-cancel-test"
    )
    job = await video_worker.enqueue_video_job(req)
    cancelled = await video_worker.cancel_job(job.job_id)
    assert cancelled is True
    status = video_worker.get_job_status(job.job_id)
    assert status.status == "CANCELLED"


# ==============================================================================
# 7. CAMERA STREAM MANAGER & SESSION LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_camera_stream_manager_telemetry_and_lifecycle():
    """Verify camera stream manager telemetry reporting and clean session shutdown."""
    webcam = await camera_stream_manager.get_or_create_webcam_source("cam-live-webcam")
    assert webcam.status == "ONLINE"

    # Telemetry check
    telemetry = camera_stream_manager.get_stream_telemetry("cam-live-webcam")
    assert telemetry["camera_id"] == "cam-live-webcam"
    assert telemetry["connected"] is True
    assert "buffer_stats" in telemetry

    # Clean shutdown of all camera streams
    await camera_stream_manager.shutdown_all()
    assert camera_stream_manager.get_source("cam-live-webcam") is None
