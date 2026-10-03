import base64
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from backend.app.models.requests import (
    StudentRegisterRequest,
    StudentLoginRequest,
    FaceEnrollmentRequest,
)
from backend.app.models.responses import (
    StudentResponse,
    StudentFaceProfileStatus,
    StudentLoginResponse,
    FaceEnrollmentResponse,
    ExamRosterStudentResponse,
)
from backend.app.services.student_service import student_service
from backend.app.services.enrollment_service import enrollment_service
from backend.app.core.security import verify_api_key

router = APIRouter(prefix="/students", tags=["Students"])


# ==============================================================================
# 1. STUDENT REGISTRATION & LOGIN
# ==============================================================================

@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def register_student(
    request: StudentRegisterRequest,
    _: str = Depends(verify_api_key)
):
    """
    Registers a new student account in the official registry.
    Assigns candidate to the examination cohort and initiates enrollment lifecycle.
    """
    return await student_service.register_student(request)


@router.post("/login", response_model=StudentLoginResponse)
async def login_student(
    request: StudentLoginRequest,
    _: str = Depends(verify_api_key)
):
    """
    Authenticates a student by roll number, student ID, or institutional email.
    Returns authenticated database identity and checks if biometric face profile exists.
    """
    return await student_service.login_student(request.identifier)


# ==============================================================================
# 2. STUDENT LOOKUP & EXAM ROSTER
# ==============================================================================

@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Look up student identity by ID.
    Enforces privacy by never returning facial vector embeddings.
    """
    student = await student_service.get_student(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found"
        )
    return student


@router.get("/exam/{exam_id}", response_model=List[ExamRosterStudentResponse])
async def get_exam_roster(
    exam_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Retrieve candidate roster and seat allocations for an examination.
    """
    roster = await student_service.get_exam_students(exam_id)
    if not roster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No roster found for examination '{exam_id}'"
        )
    return roster


# ==============================================================================
# 3. BIOMETRIC FACE ENROLLMENT STATUS & ACTIONS
# ==============================================================================

@router.get("/{student_id}/face/status", response_model=StudentFaceProfileStatus)
@router.get("/{student_id}/face-status", response_model=StudentFaceProfileStatus)
async def get_face_enrollment_status(
    student_id: str,
    _: str = Depends(verify_api_key)
):
    """
    Check if a candidate has completed biometric face enrollment.
    Returns status: ENROLLED | PENDING | REJECTED, without raw vector embeddings.
    """
    profile_status = await student_service.get_student_face_profile_status(student_id)
    if not profile_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student '{student_id}' not found in registry"
        )
    return profile_status


@router.post("/{student_id}/face/enroll", response_model=FaceEnrollmentResponse)
async def enroll_student_face_base64(
    student_id: str,
    request: FaceEnrollmentRequest,
    _: str = Depends(verify_api_key)
):
    """
    Option B: Real-time webcam / Base64 frame face enrollment.
    Validates single face, checks minimum dimensions and quality, and generates 128-D embedding.
    """
    # Enforce path student_id
    request.student_id = student_id
    return await enrollment_service.enroll_face(request)


@router.post("/{student_id}/face/enroll/upload", response_model=FaceEnrollmentResponse)
async def enroll_student_face_upload(
    student_id: str,
    file: UploadFile = File(..., description="Uploaded student passport / portrait photograph"),
    notes: Optional[str] = Form(None),
    _: str = Depends(verify_api_key)
):
    """
    Option A: Photo Upload face enrollment.
    Accepts image file (JPEG, PNG, WebP), checks file size, validates exactly ONE face via YuNet,
    and extracts 128-D SFace embedding.
    """
    # Validate MIME type
    valid_content_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if file.content_type not in valid_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Must be JPEG, PNG, or WebP."
        )

    # Read bytes and check size (maximum 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 10MB."
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # Encode to Base64 and delegate to production enrollment service
    b64_img = base64.b64encode(contents).decode("utf-8")
    req = FaceEnrollmentRequest(
        student_id=student_id,
        image_base64=b64_img,
        notes=notes or f"Uploaded photo: {file.filename}"
    )
    return await enrollment_service.enroll_face(req)

