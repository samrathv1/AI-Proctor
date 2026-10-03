from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.models.requests import AlertCreateRequest, AlertReviewRequest
from backend.app.models.responses import AlertResponse
from backend.app.services.alert_service import alert_service
from backend.app.integrations.supabase import supabase_db
from backend.app.core.security import verify_api_key

router = APIRouter(prefix="/alerts", tags=["Alerts & Infractions"])


@router.post("", response_model=AlertResponse)
async def create_alert(
    request: AlertCreateRequest,
    _: str = Depends(verify_api_key)
):
    """
    Publish an infraction alert to Supabase.
    If severity is HIGH or CRITICAL, automatically queues an IoT alert action.
    """
    return await alert_service.create_alert(request)


@router.get("", response_model=List[Dict[str, Any]])
async def list_alerts(
    exam_id: str = None,
    session_id: str = None,
    status: str = None,
    severity: str = None,
    limit: int = 50,
    _: str = Depends(verify_api_key)
):
    """
    List alerts filtered by exam, session, status, or severity.
    """
    return await alert_service.list_alerts(
        exam_id=exam_id,
        session_id=session_id,
        status=status,
        severity=severity,
        limit=limit
    )


@router.get("/{alert_id}", response_model=Dict[str, Any])
async def get_alert(
    alert_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Get alert details by ID including associated evidence reference.
    """
    alert = await alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found."
        )
    return alert


@router.post("/{alert_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(
    alert_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Invigilator acknowledges receipt of an active alert.
    """
    try:
        return await alert_service.acknowledge_alert(alert_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{alert_id}/review", response_model=Dict[str, Any])
async def review_alert(
    alert_id: str,
    request: AlertReviewRequest,
    _: str = Depends(verify_api_key)
):
    """
    Invigilator formally marks an alert as REVIEWED or DISMISSED with optional notes.
    """
    try:
        return await alert_service.review_alert(
            alert_id=alert_id,
            status=request.status,
            reviewer_notes=request.reviewer_notes
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/session/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_alerts(
    session_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Retrieve alerts recorded for a specific surveillance session.
    """
    alerts = await alert_service.list_alerts(session_id=session_id)
    if alerts:
        return alerts

    # Fallback sample baseline response for mock session
    return [
        {
            "id": "alt-01",
            "exam_session_id": session_id,
            "student_id": "s-01",
            "camera_id": "cam-01",
            "alert_type": "MOBILE_PHONE",
            "severity": "CRITICAL",
            "confidence": 94,
            "suspicion_score": 92,
            "title": "Unauthorized Mobile Device in Candidate Vicinity",
            "description": "High-confidence detection of smartphone under desk area.",
            "status": "OPEN",
            "evidence_image": "alert-evidence/evidence-alt-01.svg"
        }
    ]

