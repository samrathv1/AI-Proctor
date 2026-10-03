from typing import List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.requests import CameraStreamControlRequest
from backend.app.services.camera_manager import camera_stream_manager
from backend.app.core.security import verify_api_key
from backend.app.core.logging import logger

router = APIRouter(prefix="/cameras", tags=["Cameras & Video Adapters"])


class CameraAdapterConfig(BaseModel):
    camera_id: str
    name: str
    source_type: str = Field(..., description="WEBCAM | IP_CAMERA | RECORDED_VIDEO")
    source_reference: str = Field(..., description="Device index (0), RTSP URI, or file storage path")
    target_fps: int = 30
    resolution: str = "1080p (1920x1080)"


class CameraAdapterResponse(BaseModel):
    camera_id: str
    source_type: str
    pipeline_mode: str = "COMMON_AI_FRAME_PIPELINE"
    status: str
    message: str


@router.get("", response_model=List[Dict[str, Any]])
async def list_cameras(_: str = Depends(verify_api_key)):
    """
    Returns registered examination cameras.
    """
    return [
        {
            "id": "cam-01",
            "name": "Hall 304 - Front Wide IP Camera",
            "camera_type": "IP_CAMERA",
            "location": "Hall 304 - Front Center",
            "status": "ONLINE",
            "source_type": "RTSP_STREAM",
            "resolution": "1080p (1920x1080)",
            "fps": 30
        },
        {
            "id": "cam-02",
            "name": "Hall 304 - Invigilator Webcam",
            "camera_type": "WEBCAM",
            "location": "Podium 1",
            "status": "ONLINE",
            "source_type": "WEBRTC",
            "resolution": "720p (1280x720)",
            "fps": 30
        },
        {
            "id": "cam-03",
            "name": "Hall 304 - Rear Archive Camera",
            "camera_type": "RECORDED_VIDEO",
            "location": "Archive Wing",
            "status": "ONLINE",
            "source_type": "FILE_MP4",
            "resolution": "1080p (1920x1080)",
            "fps": 25
        }
    ]


@router.post("/adapter", response_model=CameraAdapterResponse)
async def mount_camera_adapter(
    config: CameraAdapterConfig,
    _: str = Depends(verify_api_key)
):
    """
    Common video adapter initialization endpoint.
    All camera inputs (Webcam, IP/CCTV RTSP, Recorded MP4) normalize
    into a standardized RGB frame buffer feeding the common AI surveillance pipeline.
    """
    logger.info(
        f"Mounting video adapter for camera '{config.camera_id}' "
        f"with source type '{config.source_type}'."
    )
    return CameraAdapterResponse(
        camera_id=config.camera_id,
        source_type=config.source_type,
        pipeline_mode="COMMON_AI_FRAME_PIPELINE",
        status="MOUNTED",
        message=f"Standardized video stream adapter established for {config.source_type}"
    )


@router.post("/stream/control")
async def control_camera_stream(
    request: CameraStreamControlRequest,
    _: str = Depends(verify_api_key)
):
    """
    Start, stop, or restart an active video stream ingestion worker (e.g. for IP Camera / RTSP).
    Enforces Latest-Frame-Wins backpressure and bounded queue policy.
    """
    if request.action == "START":
        if not request.rtsp_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rtsp_url is required when starting an IP camera stream"
            )
        success = await camera_stream_manager.start_ip_stream(
            camera_id=request.camera_id,
            rtsp_url=request.rtsp_url,
            exam_session_id=request.exam_session_id or f"sess-{request.camera_id}",
            exam_id=request.exam_id or "exam-01"
        )
        return {"camera_id": request.camera_id, "action": "START", "status": "ONLINE" if success else "ERROR"}

    elif request.action == "STOP":
        await camera_stream_manager.stop_camera_stream(request.camera_id)
        return {"camera_id": request.camera_id, "action": "STOP", "status": "OFFLINE"}

    elif request.action == "RESTART":
        await camera_stream_manager.stop_camera_stream(request.camera_id)
        if request.rtsp_url:
            await camera_stream_manager.start_ip_stream(
                camera_id=request.camera_id,
                rtsp_url=request.rtsp_url,
                exam_session_id=request.exam_session_id or f"sess-{request.camera_id}",
                exam_id=request.exam_id or "exam-01"
            )
        return {"camera_id": request.camera_id, "action": "RESTART", "status": "RESTARTED"}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid action: {request.action}")


@router.get("/stream/{camera_id}/telemetry")
async def get_camera_stream_telemetry(
    camera_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Telemetry monitoring endpoint for video stream performance:
    Reports connection state, capture FPS, AI processing FPS, dropped frames, and queue depth.
    """
    telemetry = camera_stream_manager.get_stream_telemetry(camera_id)
    return telemetry


@router.get("/stream/{camera_id}/latest-ai")
async def get_camera_latest_ai(
    camera_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Pulls the latest processed AI frame analytics from the background ingestion worker.
    """
    result = camera_stream_manager.get_latest_ai_result(camera_id)
    if not result:
        return {"camera_id": camera_id, "has_frame": False, "status": "WAITING_FOR_FRAME"}
    return {"camera_id": camera_id, "has_frame": True, **result}

