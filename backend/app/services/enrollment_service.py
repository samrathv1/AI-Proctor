import time
from typing import Optional
from fastapi import HTTPException, status
from backend.app.models.requests import FaceEnrollmentRequest
from backend.app.models.responses import FaceEnrollmentResponse
from backend.app.services.face_engine import face_engine
from backend.app.integrations.supabase import supabase_db
from backend.app.core.config import settings
from backend.app.core.logging import logger


class EnrollmentService:
    """
    Production Biometric Face Enrollment Pipeline.
    Extracts, verifies, and securely stores deep facial recognition embeddings.
    """

    async def enroll_face(self, request: FaceEnrollmentRequest) -> FaceEnrollmentResponse:
        t_start = time.perf_counter()

        # 1. Validate student exists in primary registry
        student = await supabase_db.get_student(request.student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student ID '{request.student_id}' does not exist in student registry",
            )

        # 2. Validate image payload presence
        if not request.image_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="INVALID_IMAGE: No image data provided for face enrollment",
            )

        # 3. Decode image with OpenCV
        try:
            img = face_engine.decode_image(request.image_base64)
        except Exception as e:
            logger.warning(f"Image decode failed for student {request.student_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"INVALID_IMAGE: Failed to decode image payload. {str(e)}",
            )

        # 4. Face Detection (YuNet ONNX / Haar Cascade fallback)
        faces = face_engine.detect_faces(img)
        if len(faces) == 0:
            await supabase_db.record_audit_event(
                actor="system",
                action="FACE_ENROLLMENT_FAILED",
                entity_type="student_face_profile",
                entity_id=request.student_id,
                metadata={"reason": "NO_FACE"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NO_FACE: No human face detected in provided image. Please face the camera directly in good lighting.",
            )
        elif len(faces) > 1:
            await supabase_db.record_audit_event(
                actor="system",
                action="FACE_ENROLLMENT_FAILED",
                entity_type="student_face_profile",
                entity_id=request.student_id,
                metadata={"reason": "MULTIPLE_FACES", "count": len(faces)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MULTIPLE_FACES: Multiple faces detected ({len(faces)}). Exactly one candidate face must be in frame.",
            )

        # 5. Extract and Validate Target Face
        face = faces[0]
        x, y, w, h = face["box"]
        if w < settings.MIN_FACE_SIZE or h < settings.MIN_FACE_SIZE:
            await supabase_db.record_audit_event(
                actor="system",
                action="FACE_ENROLLMENT_FAILED",
                entity_type="student_face_profile",
                entity_id=request.student_id,
                metadata={"reason": "FACE_TOO_SMALL", "dimensions": f"{w}x{h}"}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FACE_TOO_SMALL: Detected face is too small ({w}x{h} px). Minimum required size is {settings.MIN_FACE_SIZE}x{settings.MIN_FACE_SIZE} px.",
            )

        # 6. Quality Metrics Calculation
        quality_score, details = face_engine.calculate_quality_score(img, face["box"], face["confidence"])
        if quality_score < settings.MIN_QUALITY_SCORE:
            await supabase_db.record_audit_event(
                actor="system",
                action="FACE_ENROLLMENT_FAILED",
                entity_type="student_face_profile",
                entity_id=request.student_id,
                metadata={"reason": "LOW_QUALITY", "quality_score": quality_score}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LOW_QUALITY: Image quality too low ({quality_score:.1f}/100). Please improve lighting and reduce motion blur.",
            )

        # 7. Alignment & Deep Feature Vector Extraction (L2-Normalized)
        try:
            embedding, aligned_face = face_engine.extract_embedding(img, face)
        except Exception as e:
            logger.error(f"Feature extraction failed for student {request.student_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Biometric feature extractor failed during embedding generation.",
            )

        embedding_bytes = embedding.tobytes()

        # 8. Persist to Secure Biometric Storage (student_face_profiles)
        success, is_reenrollment = await supabase_db.save_student_face_profile(
            student_id=request.student_id,
            embedding_bytes=embedding_bytes,
            model_version=settings.FACE_MODEL_VERSION,
            quality_score=quality_score
        )

        # 8b. Invalidate exam biometric cache so live surveillance immediately mounts the new candidate template
        try:
            from backend.app.services.biometric_cache import biometric_cache_manager
            biometric_cache_manager.clear_cache("exam-01")
        except Exception as e:
            logger.debug(f"Biometric cache refresh advisory: {e}")


        # 9. Audit Event Registration
        action_name = "FACE_REENROLLED" if is_reenrollment else "FACE_ENROLLMENT_VERIFIED"
        await supabase_db.record_audit_event(
            actor="invigilator",
            action=action_name,
            entity_type="student_face_profile",
            entity_id=request.student_id,
            metadata={
                "quality_score": quality_score,
                "model_version": settings.FACE_MODEL_VERSION,
                "face_dimensions": f"{w}x{h}",
                "blur_metric": details.get("blur_metric"),
                "is_reenrollment": is_reenrollment
            }
        )

        t_elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(
            f"Face enrollment completed for student {request.student_id} "
            f"in {t_elapsed_ms}ms with quality score {quality_score} ({settings.FACE_MODEL_VERSION})."
        )

        # 10. Return Safe Metadata Response (STRICTLY NO RAW BIOMETRIC VECTORS)
        return FaceEnrollmentResponse(
            student_id=request.student_id,
            status="VERIFIED",
            message="Face biometric profile successfully enrolled and verified.",
            quality_score=quality_score,
            model_version=settings.FACE_MODEL_VERSION,
        )


enrollment_service = EnrollmentService()
