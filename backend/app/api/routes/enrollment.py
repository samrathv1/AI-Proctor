from fastapi import APIRouter, Depends
from backend.app.models.requests import FaceEnrollmentRequest
from backend.app.models.responses import FaceEnrollmentResponse
from backend.app.services.enrollment_service import enrollment_service
from backend.app.core.security import verify_api_key

router = APIRouter(prefix="/enrollment", tags=["Biometric Enrollment"])


@router.post("/face", response_model=FaceEnrollmentResponse)
async def enroll_student_face(
    request: FaceEnrollmentRequest,
    _: str = Depends(verify_api_key)
):
    """
    Contract endpoint for future face recognition enrollment.
    Validates input parameters and returns explicit NOT_IMPLEMENTED status
    without generating fabricated biometric embeddings.
    """
    return await enrollment_service.enroll_face(request)
