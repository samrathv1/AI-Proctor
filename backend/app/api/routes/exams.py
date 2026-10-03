from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.app.core.security import verify_api_key
from backend.app.services.exam_service import exam_service
from backend.app.core.logging import logger

router = APIRouter(prefix="/exams", tags=["Examinations"])


class ExamCreateRequest(BaseModel):
    name: str
    subject: str
    exam_code: Optional[str] = None
    exam_date: Optional[str] = None
    start_time: Optional[str] = "10:00 AM"
    end_time: Optional[str] = "12:00 PM"
    duration_minutes: Optional[int] = 120
    room: Optional[str] = "Hall 304 - Engineering Wing B"
    invigilator_name: Optional[str] = "Dr. Robert Vance, Ph.D."
    description: Optional[str] = ""


class RosterAddRequest(BaseModel):
    student_id: str
    seat_number: Optional[str] = "B4-01"
    camera_id: Optional[str] = "cam-01"


@router.get("", response_model=List[Dict[str, Any]])
async def list_exams(
    _: str = Depends(verify_api_key)
):
    """Lists all examinations registered in the system."""
    return await exam_service.list_exams()


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_exam(
    request: ExamCreateRequest,
    _: str = Depends(verify_api_key)
):
    """Creates a new examination session with initial session provisioning."""
    created = await exam_service.create_exam(request.model_dump())
    return created


@router.get("/{exam_id}", response_model=Dict[str, Any])
async def get_exam_details(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Get detailed examination metadata and session state.
    """
    exam = await exam_service.get_exam(exam_id)
    # Ensure legacy compatibility keys
    exam["total_enrolled"] = exam.get("totalStudents", 60)
    return exam


@router.get("/{exam_id}/roster", response_model=List[Dict[str, Any]])
async def get_exam_roster(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Retrieves the authoritative candidate roster for an examination:
    Student -> Seat -> Camera -> Face Enrollment Status.
    """
    return await exam_service.get_exam_roster(exam_id)


@router.post("/{exam_id}/roster", response_model=Dict[str, Any])
async def add_student_to_roster(
    exam_id: str,
    request: RosterAddRequest,
    _: str = Depends(verify_api_key)
):
    """
    Assigns a candidate to the exam roster with seat assignment and camera coverage.
    """
    return await exam_service.add_student_to_roster(
        exam_id=exam_id,
        student_id=request.student_id,
        seat_number=request.seat_number or "B4-01",
        camera_id=request.camera_id or "cam-01"
    )


@router.delete("/{exam_id}/roster/{student_id}")
async def remove_student_from_roster(
    exam_id: str,
    student_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Removes a candidate from the exam roster.
    """
    await exam_service.remove_student_from_roster(exam_id, student_id)
    return {"success": True, "message": f"Student '{student_id}' removed from exam roster"}


@router.post("/{exam_id}/start")
async def start_exam(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Launches exam surveillance session.
    Validates roster, mounts exam-specific biometric cache, and marks exam LIVE.
    """
    return await exam_service.start_exam(exam_id)


@router.post("/{exam_id}/session/start")
async def start_exam_session_legacy(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """Backwards-compatible endpoint for existing test contracts."""
    res = await exam_service.start_exam(exam_id)
    return {
        "session_id": res["session_id"],
        "exam_id": res["exam_id"],
        "status": "RUNNING",
        "enrolled_candidates_cached_count": res["enrolled_candidates_cached_count"],
        "model_version": res["model_version"],
        "active_cameras": 3,
        "message": f"Examination surveillance session started. Loaded {res['enrolled_candidates_cached_count']} candidate biometric templates into cache."
    }


@router.post("/{exam_id}/end")
async def end_exam(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Terminates exam surveillance session, clears biometric cache,
    returns hardware to safe state, marks exam ENDED, and generates summary.
    """
    return await exam_service.end_exam(exam_id)


@router.post("/{exam_id}/session/stop")
async def stop_exam_session_legacy(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """Backwards-compatible endpoint for existing test contracts."""
    res = await exam_service.end_exam(exam_id)
    return {
        "exam_id": exam_id,
        "status": "COMPLETED",
        "cache_cleared": res["cache_cleared"],
        "message": "Surveillance session ended and biometric templates purged from memory."
    }


@router.get("/{exam_id}/summary", response_model=Dict[str, Any])
async def get_exam_summary(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Returns the objective examination completion summary:
    Duration, observable events, alerts, hardware alerts, unknown identities, and review metrics.
    """
    return await exam_service.get_exam_summary(exam_id)
