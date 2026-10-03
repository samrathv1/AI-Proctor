from typing import Optional, Dict, Any
from datetime import datetime, timezone
from backend.app.models.requests import AlertCreateRequest
from backend.app.models.responses import AlertResponse
from backend.app.integrations.supabase import supabase_db
from backend.app.core.logging import logger


class AlertService:
    """
    Central alert dispatch and persistence service.
    Receives analyzed infractions, registers them in Supabase PostgreSQL,
    and initiates downstream alerts / IoT triggers as determined by policy.
    """

    async def create_alert(self, request: AlertCreateRequest) -> AlertResponse:
        logger.info(
            f"Creating alert for session {request.exam_session_id}, type {request.alert_type}, "
            f"severity {request.severity}."
        )

        alert_payload = {
            "exam_session_id": request.exam_session_id,
            "exam_id": request.exam_id,
            "student_id": request.student_id,
            "camera_id": request.camera_id,
            "alert_type": request.alert_type,
            "severity": request.severity,
            "confidence": request.confidence,
            "suspicion_score": request.suspicion_score,
            "title": request.title,
            "description": request.description,
            "evidence_storage_path": request.evidence_storage_path,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }

        created = await supabase_db.insert_alert(alert_payload)

        # Downstream action policy: High / Critical alerts dispatch to physical ESP32
        try:
            from backend.app.services.iot_service import iot_service
            await iot_service.dispatch_alert_for_infraction(created)
        except Exception as iot_err:
            logger.warning(f"Non-fatal error dispatching alert {created.get('id')} to IoT hardware: {iot_err}")

        return AlertResponse(
            id=created["id"],
            exam_session_id=created.get("exam_session_id"),
            exam_id=created["exam_id"],
            student_id=created.get("student_id"),
            camera_id=created.get("camera_id"),
            alert_type=created["alert_type"],
            severity=created["severity"],
            confidence=created["confidence"],
            suspicion_score=created.get("suspicion_score", 80),
            title=created["title"],
            description=created["description"],
            occurred_at=datetime.fromisoformat(created["occurred_at"].replace("Z", "+00:00")),
            status=created.get("status", "OPEN"),
            evidence_storage_path=request.evidence_storage_path,
        )

    async def list_alerts(
        self,
        exam_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        return await supabase_db.list_alerts(
            exam_id=exam_id,
            session_id=session_id,
            status=status,
            severity=severity,
            limit=limit
        )

    async def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return await supabase_db.get_alert(alert_id)

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: Optional[str] = None) -> Dict[str, Any]:
        logger.info(f"Acknowledging alert {alert_id} by {acknowledged_by or 'invigilator'}")
        updated = await supabase_db.update_alert_status(
            alert_id=alert_id,
            status="ACKNOWLEDGED",
            reviewed_by=acknowledged_by
        )
        if not updated:
            raise ValueError(f"Alert {alert_id} not found")
        await supabase_db.record_audit_event(
            actor=acknowledged_by or "invigilator",
            action="ALERT_ACKNOWLEDGED",
            entity_type="alert",
            entity_id=alert_id,
            metadata={"status": "ACKNOWLEDGED"}
        )
        return updated

    async def review_alert(
        self,
        alert_id: str,
        status: str = "REVIEWED",
        reviewer_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        # Normalize status
        normalized_status = status.upper()
        if normalized_status in ["CONFIRMED", "VALIDATED"]:
            normalized_status = "REVIEWED"
        elif normalized_status not in ["ACKNOWLEDGED", "REVIEWED", "DISMISSED", "ESCALATED"]:
            normalized_status = "REVIEWED"

        logger.info(f"Reviewing alert {alert_id} as {normalized_status} by {reviewed_by or 'invigilator'}")
        updated = await supabase_db.update_alert_status(
            alert_id=alert_id,
            status=normalized_status,
            reviewed_by=reviewed_by,
            reviewer_notes=reviewer_notes
        )
        if not updated:
            raise ValueError(f"Alert {alert_id} not found")
        
        audit_action = (
            "ALERT_DISMISSED" if normalized_status == "DISMISSED"
            else ("ALERT_ESCALATED" if normalized_status == "ESCALATED" else "ALERT_REVIEWED")
        )
        await supabase_db.record_audit_event(
            actor=reviewed_by or "invigilator",
            action=audit_action,
            entity_type="alert",
            entity_id=alert_id,
            metadata={"status": normalized_status, "reviewer_notes": reviewer_notes}
        )
        return updated


alert_service = AlertService()

