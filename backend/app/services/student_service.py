from typing import Optional, List
from fastapi import HTTPException, status
from backend.app.models.requests import StudentRegisterRequest, StudentLoginRequest
from backend.app.models.responses import (
    StudentResponse,
    StudentFaceProfileStatus,
    StudentLoginResponse,
    ExamRosterStudentResponse,
)
from backend.app.integrations.supabase import supabase_db
from backend.app.core.config import settings
from backend.app.core.logging import logger


class StudentService:
    """
    Student and examination roster service.
    CRITICAL SECURITY REQUIREMENT:
    Raw biometric face embeddings are strictly omitted from all client responses.
    """

    async def register_student(self, request: StudentRegisterRequest) -> StudentResponse:
        """Registers a new student account in the official registry."""
        email_clean = request.email.strip().lower()
        allowed_domains = [d.strip().lower() for d in settings.ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
        domain_match = any(email_clean.endswith(f"@{d}") or email_clean.endswith(f".{d}") for d in allowed_domains)
        if not domain_match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_INSTITUTIONAL_EMAIL: Registration requires an official institutional email ({settings.INSTITUTIONAL_EMAIL_DOMAIN})."
            )

        existing = await supabase_db.get_student_by_identifier(request.roll_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with roll number '{request.roll_number}' is already registered."
            )
        existing_email = await supabase_db.get_student_by_identifier(request.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with email '{request.email}' is already registered."
            )

        data = await supabase_db.create_student(request.model_dump())
        logger.info(f"Registered new student {data['name']} ({data['roll_number']}, ID={data['id']})")
        return StudentResponse(
            id=data["id"],
            student_code=data["student_code"],
            name=data["name"],
            roll_number=data["roll_number"],
            email=data["email"],
            class_name=data.get("class_name"),
            department=data.get("department"),
            profile_photo_path=data.get("profile_photo_path"),
            status=data.get("status", "ACTIVE"),
        )

    async def login_student(self, identifier: str) -> StudentLoginResponse:
        """
        Authenticates a student by roll number, student ID, or institutional email.
        Returns the student's database identity and current biometric face enrollment state.
        """
        data = await supabase_db.get_student_by_identifier(identifier)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No registered student found matching '{identifier}'."
            )

        student_resp = StudentResponse(
            id=data["id"],
            student_code=data["student_code"],
            name=data["name"],
            roll_number=data["roll_number"],
            email=data["email"],
            class_name=data.get("class_name"),
            department=data.get("department"),
            profile_photo_path=data.get("profile_photo_path"),
            status=data.get("status", "ACTIVE"),
        )

        face_status = await supabase_db.get_face_profile_status(data["id"])
        is_enrolled = face_status is not None and face_status.get("enrollment_status") == "ENROLLED"
        enrollment_status = face_status.get("enrollment_status", "PENDING") if face_status else "PENDING"

        return StudentLoginResponse(
            success=True,
            student=student_resp,
            face_enrolled=is_enrolled,
            enrollment_status=enrollment_status,
            message="Student authentication successful."
        )

    async def get_student(self, student_id: str) -> Optional[StudentResponse]:
        data = await supabase_db.get_student(student_id)
        if not data:
            return None
        return StudentResponse(
            id=data["id"],
            student_code=data["student_code"],
            name=data["name"],
            roll_number=data["roll_number"],
            email=data["email"],
            class_name=data.get("class_name"),
            department=data.get("department"),
            profile_photo_path=data.get("profile_photo_path"),
            status=data.get("status", "ACTIVE"),
        )

    async def get_student_by_identifier(self, identifier: str) -> Optional[StudentResponse]:
        data = await supabase_db.get_student_by_identifier(identifier)
        if not data:
            return None
        return StudentResponse(
            id=data["id"],
            student_code=data["student_code"],
            name=data["name"],
            roll_number=data["roll_number"],
            email=data["email"],
            class_name=data.get("class_name"),
            department=data.get("department"),
            profile_photo_path=data.get("profile_photo_path"),
            status=data.get("status", "ACTIVE"),
        )

    async def get_exam_students(self, exam_id: str) -> List[ExamRosterStudentResponse]:
        roster_data = await supabase_db.get_exam_roster(exam_id)
        return [
            ExamRosterStudentResponse(
                student_id=item["student_id"],
                name=item["name"],
                roll_number=item["roll_number"],
                seat_number=item["seat_number"],
                attendance_status=item["attendance_status"],
                face_verified=item["face_verified"],
                risk_score=item["risk_score"],
            )
            for item in roster_data
        ]

    async def get_student_face_profile_status(self, student_id: str) -> Optional[StudentFaceProfileStatus]:
        status_data = await supabase_db.get_face_profile_status(student_id)
        if not status_data:
            return None
        return StudentFaceProfileStatus(
            student_id=status_data["student_id"],
            enrollment_status=status_data["enrollment_status"],
            model_version=status_data.get("model_version"),
            quality_score=status_data.get("quality_score"),
            has_embedding=status_data.get("has_embedding", False),
        )


student_service = StudentService()

