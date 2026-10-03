from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
import io

from backend.app.services.report_service import report_service
from backend.app.integrations.supabase import supabase_db
from backend.app.core.logging import logger

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/exams/{exam_id}")
async def get_exam_report(exam_id: str) -> Dict[str, Any]:
    """
    Returns the comprehensive, authoritative Exam Integrity Audit Report.
    Includes exam overview, statistics, unranked candidate summary, timeline,
    alert distributions, ESP32 actuation history, and system limitations.
    """
    try:
        report = await report_service.get_exam_integrity_report(exam_id)
        # Record audit log for report generation
        await supabase_db.record_audit_event(
            actor="Invigilator",
            action="REPORT_GENERATED",
            entity_type="EXAM_REPORT",
            entity_id=exam_id,
            metadata={"format": "JSON", "scope": "EXAM"}
        )
        return report
    except Exception as e:
        logger.error(f"Error compiling exam integrity report for {exam_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate exam integrity report: {str(e)}"
        )


@router.get("/exams/{exam_id}/candidates/{student_id}")
async def get_candidate_report(exam_id: str, student_id: str) -> Dict[str, Any]:
    """
    Returns candidate-level explainable integrity report.
    Details observed events, durations, peak advisory score, contributing signals,
    invigilator reviews, and evidence frame links.
    """
    try:
        report = await report_service.get_candidate_integrity_report(exam_id, student_id)
        # Record audit log
        await supabase_db.record_audit_event(
            actor="Invigilator",
            action="REPORT_GENERATED",
            entity_type="CANDIDATE_REPORT",
            entity_id=student_id,
            metadata={"exam_id": exam_id, "format": "JSON", "scope": "CANDIDATE"}
        )
        return report
    except Exception as e:
        logger.error(f"Error compiling candidate integrity report for {student_id} in {exam_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate candidate integrity report: {str(e)}"
        )


@router.get("/exams/{exam_id}/timeline")
async def get_exam_timeline(exam_id: str) -> List[Dict[str, Any]]:
    """
    Returns the unified chronological event timeline for the exam session.
    Combines identities, behaviour events, score changes, alerts, reviews, and hardware actions.
    """
    try:
        return await report_service.build_exam_timeline(exam_id)
    except Exception as e:
        logger.error(f"Error compiling exam timeline for {exam_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate event timeline: {str(e)}"
        )


@router.get("/exams/{exam_id}/export/json")
async def export_report_json(
    exam_id: str,
    student_id: Optional[str] = Query(None, description="Optional student ID for candidate-level export")
) -> Dict[str, Any]:
    """
    Produces clean, machine-readable sanitized JSON export.
    Excludes all raw face embeddings, service credentials, and private keys.
    """
    try:
        data = await report_service.export_report_json(exam_id, student_id=student_id)
        await supabase_db.record_audit_event(
            actor="Invigilator",
            action="REPORT_GENERATED",
            entity_type="REPORT_EXPORT",
            entity_id=exam_id,
            metadata={"format": "JSON", "student_id": student_id}
        )
        return data
    except Exception as e:
        logger.error(f"Error exporting JSON report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export JSON report: {str(e)}"
        )


@router.get("/exams/{exam_id}/export/pdf")
async def export_report_pdf(
    exam_id: str,
    student_id: Optional[str] = Query(None, description="Optional student ID for candidate-level export")
):
    """
    Generates and streams the official PDF examination integrity audit report.
    Contains all 11 standardized forensic sections.
    """
    try:
        pdf_bytes = await report_service.export_report_pdf(exam_id, student_id=student_id)
        
        # Audit logging
        await supabase_db.record_audit_event(
            actor="Invigilator",
            action="REPORT_GENERATED",
            entity_type="REPORT_EXPORT",
            entity_id=exam_id,
            metadata={"format": "PDF", "student_id": student_id}
        )

        filename = f"AI-Proctor-Audit-{exam_id}"
        if student_id:
            filename += f"-{student_id[:8]}"
        filename += ".pdf"

        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        logger.error(f"Error generating PDF report for {exam_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


@router.post("/evidence/view")
async def record_evidence_viewed(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Records an audit log entry when an invigilator opens/inspects evidence for an alert.
    """
    alert_id = data.get("alert_id")
    student_id = data.get("student_id")
    viewer = data.get("viewer", "Invigilator")
    
    audit_rec = await supabase_db.record_audit_event(
        actor=viewer,
        action="EVIDENCE_VIEWED",
        entity_type="ALERT_EVIDENCE",
        entity_id=alert_id or "unknown",
        metadata={
            "student_id": student_id,
            "evidence_path": data.get("evidence_path")
        }
    )
    return {"status": "SUCCESS", "audit_id": audit_rec.get("id")}
