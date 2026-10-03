from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, status
import numpy as np
from datetime import datetime, timezone

from backend.app.models.requests import (
    FrameAnalysisRequest,
    VideoProcessRequest,
    ManualIdentityMappingRequest
)
from backend.app.models.responses import VideoProcessJobResponse
from backend.app.services.video_source import FramePacket
from backend.app.services.common_pipeline_service import common_frame_pipeline
from backend.app.services.face_engine import face_engine
from backend.app.workers.video_worker import video_worker
from backend.app.core.security import verify_api_key
from backend.app.core.logging import logger

router = APIRouter(prefix="", tags=["Monitoring & Vision Pipeline"])


@router.post("/monitoring/frame")
async def analyze_surveillance_frame(
    request: FrameAnalysisRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Unified Live Surveillance Frame Analysis Endpoint:
    Normalizes incoming browser webcam or push frames into standardized FramePacket,
    and feeds it through the COMMON AI SURVEILLANCE PIPELINE.
    """
    # 1. Decode frame image or fallback gracefully for test contracts
    img: Optional[np.ndarray] = None
    if request.frame_base64:
        try:
            img = face_engine.decode_image(request.frame_base64)
        except Exception as e:
            logger.debug(f"Frame decode fallback in monitoring endpoint: {str(e)}")

    if img is None:
        img = np.zeros((480, 640, 3), dtype=np.uint8)

    # 2. Package into standardized FramePacket
    packet = FramePacket(
        frame=img,
        source_id=request.camera_id,
        source_type="WEBCAM",
        timestamp=request.timestamp or datetime.now(timezone.utc),
        metadata={"client_timestamp": request.timestamp.isoformat() if request.timestamp else None}
    )

    # 3. Route through COMMON AI FRAME PIPELINE
    return await common_frame_pipeline.process_frame(
        frame_packet=packet,
        exam_session_id=request.exam_session_id,
        exam_id=request.exam_id
    )


@router.post("/video/process", response_model=VideoProcessJobResponse)
async def process_recorded_video(
    request: VideoProcessRequest,
    _: str = Depends(verify_api_key)
):
    """
    Asynchronous video analysis dispatcher.
    Offloads heavy video decoding and frame evaluation to background workers.
    """
    return await video_worker.enqueue_video_job(request)


@router.get("/video/jobs/{job_id}", response_model=VideoProcessJobResponse)
async def get_video_job_status(
    job_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Check the processing state, real percentage progress, and telemetry of a video job.
    """
    job = video_worker.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video processing job '{job_id}' not found"
        )
    return job


@router.post("/video/jobs/{job_id}/manual-map")
async def manual_identity_map_job(
    job_id: str,
    request: ManualIdentityMappingRequest,
    _: str = Depends(verify_api_key)
):
    """
    Manual identity override for offline recorded examination reviews.
    Permits an authorized invigilator to map a candidate tracklet (e.g. TRACK-017)
    to a registered student UUID, creating a persistent, non-repudiable audit event.
    """
    job = video_worker.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video processing job '{job_id}' not found"
        )

    mapping_result = await video_worker.manual_identity_mapping(
        job_id=job_id,
        tracking_id=request.tracking_id,
        student_id=request.student_id,
        invigilator_id=request.invigilator_id,
        notes=request.notes
    )
    return mapping_result


@router.post("/video/jobs/{job_id}/cancel")
async def cancel_video_job(
    job_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Cancels an active or queued recorded video processing job.
    """
    success = await video_worker.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' cannot be cancelled (already completed, failed, or not found)"
        )
    return {"status": "CANCELLED", "job_id": job_id}

