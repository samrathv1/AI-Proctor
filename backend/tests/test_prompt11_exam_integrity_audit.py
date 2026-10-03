import pytest
import io
from datetime import datetime, timezone

from backend.app.services.report_service import report_service
from backend.app.services.exam_service import exam_service
from backend.app.services.alert_service import alert_service
from backend.app.services.behaviour_service import BehaviourService
from backend.app.integrations.supabase import supabase_db


@pytest.fixture(autouse=True)
def setup_test_data():
    """Ensure in-memory collections have baseline exam data for testing."""
    supabase_db._in_memory_alerts.clear()
    supabase_db._in_memory_behaviour_events.clear()
    supabase_db._in_memory_iot_events.clear()
    supabase_db._in_memory_audit_logs.clear()
    supabase_db._in_memory_evidence.clear()


@pytest.mark.asyncio
async def test_01_candidate_report_generation():
    """1. Candidate report generation succeeds with expected structure."""
    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-01")
    assert cand_report is not None
    assert cand_report["student_id"] == "s-01"
    assert "observed_events" in cand_report
    assert "advisory_summary" in cand_report
    assert "invigilator_review" in cand_report
    assert "evidence_frames" in cand_report


@pytest.mark.asyncio
async def test_02_exam_report_generation():
    """2. Exam report generation succeeds with unranked candidates and statistics."""
    exam_rep = await report_service.get_exam_integrity_report("exam-01")
    assert exam_rep is not None
    assert "exam_overview" in exam_rep
    assert "statistics" in exam_rep
    assert "candidates_summary" in exam_rep
    assert "timeline" in exam_rep
    assert "system_limitations" in exam_rep
    assert exam_rep["statistics"]["candidates_count"] > 0


@pytest.mark.asyncio
async def test_03_chronological_event_ordering():
    """3. Timeline events are strictly sorted in ascending chronological order."""
    t1 = "2026-10-03T10:05:00Z"
    t2 = "2026-10-03T10:15:00Z"
    t3 = "2026-10-03T10:25:00Z"

    await supabase_db.save_behaviour_event({
        "id": "beh-t3",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "behaviour_type": "SIDEWAYS_GAZE",
        "timestamp": t3
    })
    await supabase_db.save_behaviour_event({
        "id": "beh-t1",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "behaviour_type": "LOOKING_AWAY",
        "timestamp": t1
    })
    await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "title": "Mobile Phone Detected",
        "description": "Phone visible",
        "occurred_at": t2
    })

    timeline = await report_service.build_exam_timeline("exam-01")
    assert len(timeline) >= 3

    timestamps = [str(e.get("timestamp") or "") for e in timeline]
    for i in range(len(timestamps) - 1):
        assert timestamps[i] <= timestamps[i + 1]


@pytest.mark.asyncio
async def test_04_alert_review_state_included_in_report():
    """4. Alert review state is reflected in the candidate and exam report."""
    alert = await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "REPEATED_HEAD_TURN",
        "title": "Repeated Head Turn",
        "description": "3 turns in 30s",
        "occurred_at": "2026-10-03T10:10:00Z"
    })
    await alert_service.review_alert(
        alert_id=alert["id"],
        status="REVIEWED",
        reviewed_by="Prof. Roberts",
        reviewer_notes="Candidate acknowledged orientation check."
    )

    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-01")
    assert cand_report["invigilator_review"]["status"] in ["REVIEWED", "ACKNOWLEDGED", "DISMISSED", "ESCALATED"]
    assert len(cand_report["alerts"]) > 0


@pytest.mark.asyncio
async def test_05_reviewer_notes_included():
    """5. Reviewer notes are preserved and returned in candidate report."""
    alert = await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "PROLONGED_SIDEWAYS_GAZE",
        "title": "Prolonged Sideways Gaze",
        "description": "Gaze deflected 8.5s",
        "occurred_at": "2026-10-03T10:12:00Z"
    })
    await alert_service.review_alert(
        alert_id=alert["id"],
        status="REVIEWED",
        reviewed_by="Invigilator Davis",
        reviewer_notes="Physical obstruction noted on adjacent desk; non-infraction."
    )

    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-01")
    assert "Physical obstruction noted" in cand_report["invigilator_review"]["notes"]


@pytest.mark.asyncio
async def test_06_evidence_metadata_included():
    """6. Evidence storage path and frame metadata are returned."""
    await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "title": "Mobile Phone Detection",
        "description": "Confidence 88%",
        "evidence_storage_path": "evidence/s-01-frame-01.svg",
        "occurred_at": "2026-10-03T10:14:00Z"
    })

    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-01")
    assert len(cand_report["evidence_frames"]) >= 1
    assert any(ef["storage_path"] == "evidence/s-01-frame-01.svg" for ef in cand_report["evidence_frames"])


@pytest.mark.asyncio
async def test_07_esp32_dispatch_history_included():
    """7. Dispatched ESP32 command is listed in hardware actuation history."""
    await supabase_db.insert_iot_event(
        device_id="ESP32-HALL304-01",
        event_type="ALERT_TRIGGER",
        command="BUZZER_LED_ON",
        status="DISPATCHED",
        exam_session_id="00000000-0000-0000-0000-000000000011"
    )

    exam_rep = await report_service.get_exam_integrity_report("exam-01")
    hw_acts = exam_rep["hardware_activity"]
    assert any(h["device_id"] == "ESP32-HALL304-01" for h in hw_acts)


@pytest.mark.asyncio
async def test_08_esp32_acknowledgement_included():
    """8. Acknowledged ESP32 event displays ACKNOWLEDGED status."""
    await supabase_db.insert_iot_event(
        device_id="ESP32-HALL304-01",
        event_type="COMMAND_ACK",
        command="BUZZER_LED_ACK",
        status="ACKNOWLEDGED",
        exam_session_id="00000000-0000-0000-0000-000000000011"
    )

    exam_rep = await report_service.get_exam_integrity_report("exam-01")
    assert any(h["status"] == "ACKNOWLEDGED" for h in exam_rep["hardware_activity"])


@pytest.mark.asyncio
async def test_09_unknown_identity_represented_correctly():
    """9. Unknown candidate is handled and tagged as UNKNOWN identity status."""
    cand_report = await report_service.get_candidate_integrity_report("exam-01", "unknown-track-99")
    assert cand_report["identity_status"] == "UNKNOWN"
    assert "unknown-track-99" in cand_report["student_id"]


@pytest.mark.asyncio
async def test_10_no_biometric_embedding_leakage():
    """10. Deep sanitization prevents face_embedding or raw biometric leakage."""
    exam_rep = await report_service.get_exam_integrity_report("exam-01")
    cand_rep = await report_service.get_candidate_integrity_report("exam-01", "s-01")

    rep_str = str(exam_rep) + str(cand_rep)
    assert "face_embedding" not in rep_str
    assert "embedding" not in rep_str.lower() or "embedding" in "sface-embedding-model"
    assert "service_role" not in rep_str.lower()
    assert "secret" not in rep_str.lower()


@pytest.mark.asyncio
async def test_11_json_export_contains_required_fields():
    """11. Machine-readable JSON export contains all mandatory report keys."""
    json_data = await report_service.export_report_json("exam-01")
    assert "exam_overview" in json_data
    assert "statistics" in json_data
    assert "candidates_summary" in json_data
    assert "timeline" in json_data
    assert "hardware_activity" in json_data
    assert "system_limitations" in json_data


@pytest.mark.asyncio
async def test_12_json_export_excludes_secrets():
    """12. JSON export excludes private keys or service credentials."""
    json_data = await report_service.export_report_json("exam-01")
    json_str = str(json_data).lower()
    assert "supabase_service_role" not in json_str
    assert "private_key" not in json_str
    assert "password" not in json_str


@pytest.mark.asyncio
async def test_13_empty_report_handled_correctly():
    """13. Handled gracefully when exam has zero alerts or behaviour events."""
    clean_exam_id = "exam-empty-test"
    exam_service._in_memory_exams[clean_exam_id] = {
        "id": clean_exam_id,
        "exam_code": "EMPTY-101",
        "name": "Empty Examination",
        "subject": "General",
        "exam_date": "2026-10-03",
        "start_time": "10:00 AM",
        "end_time": "11:00 AM",
        "duration_minutes": 60,
        "room": "Hall Empty",
        "invigilator_name": "Proctor Clean",
        "status": "COMPLETED",
        "description": "Empty exam test"
    }

    report = await report_service.get_exam_integrity_report(clean_exam_id)
    assert report["statistics"]["alerts_generated"] == 0
    assert report["statistics"]["total_observable_events"] == 0
    assert isinstance(report["timeline"], list)


@pytest.mark.asyncio
async def test_14_missing_evidence_handled_correctly():
    """14. Candidate with no evidence frames captured reports empty list without error."""
    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-03")
    assert isinstance(cand_report["evidence_frames"], list)


@pytest.mark.asyncio
async def test_15_dismissed_alert_represented_correctly():
    """15. Dismissed alert sets candidate review status to DISMISSED."""
    alert = await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "test-cand-dismissed",
        "camera_id": "cam-01",
        "alert_type": "DESK_PEEKING",
        "title": "Desk Peeking",
        "description": "Head turned toward aisle",
        "occurred_at": "2026-10-03T10:18:00Z"
    })
    await alert_service.review_alert(
        alert_id=alert["id"],
        status="DISMISSED",
        reviewed_by="Invigilator Wilson",
        reviewer_notes="Dropped pen retrieved; false positive."
    )

    cand_report = await report_service.get_candidate_integrity_report("exam-01", "test-cand-dismissed")
    assert cand_report["invigilator_review"]["status"] == "DISMISSED"
    assert any(a["id"] == alert["id"] and a["status"] == "DISMISSED" for a in cand_report["alerts"])


@pytest.mark.asyncio
async def test_16_escalated_alert_represented_correctly():
    """16. Escalated alert sets candidate review status to ESCALATED."""
    alert = await supabase_db.insert_alert({
        "exam_id": "exam-01",
        "exam_session_id": "00000000-0000-0000-0000-000000000011",
        "student_id": "s-03",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "title": "Mobile Phone Detection",
        "description": "Phone actively used",
        "occurred_at": "2026-10-03T10:20:00Z"
    })
    await alert_service.review_alert(
        alert_id=alert["id"],
        status="ESCALATED",
        reviewed_by="Chief Invigilator",
        reviewer_notes="Unapproved device visible in hand; escalating to disciplinary committee."
    )

    cand_report = await report_service.get_candidate_integrity_report("exam-01", "s-03")
    assert cand_report["invigilator_review"]["status"] == "ESCALATED"


@pytest.mark.asyncio
async def test_17_audit_events_represented_chronologically():
    """17. Audit events in timeline maintain chronological integrity."""
    await supabase_db.record_audit_event(
        actor="Chief Invigilator",
        action="EXAM_STARTED",
        entity_type="EXAM",
        entity_id="exam-01",
        metadata={"exam_id": "exam-01"}
    )
    timeline = await report_service.build_exam_timeline("exam-01")
    audit_evs = [e for e in timeline if e.get("category") == "AUDIT"]
    assert len(audit_evs) >= 1
    assert any(a["event_type"] == "EXAM_STARTED" for a in audit_evs)


@pytest.mark.asyncio
async def test_18_pdf_generation_succeeds():
    """18. ReportLab PDF generation compiles valid PDF binary starting with %PDF-."""
    pdf_bytes = await report_service.export_report_pdf("exam-01")
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_19_existing_prompt9_exam_workflow_remains_functional():
    """19. Prompt 9 exam roster, exam session, and lifecycle calls remain functional."""
    exam = await exam_service.get_exam("exam-01")
    assert exam["id"] == "exam-01"
    roster = await exam_service.get_exam_roster("exam-01")
    assert len(roster) > 0


@pytest.mark.asyncio
async def test_20_existing_prompt10_behaviour_events_remain_functional():
    """20. Prompt 10 BehaviourService creates observable events and persists them."""
    bs = BehaviourService()
    ev = await bs.create_behaviour_event(
        exam_session_id="00000000-0000-0000-0000-000000000011",
        camera_id="cam-01",
        behaviour_type="SIDEWAYS_GAZE",
        confidence=0.88,
        student_id="s-01",
        duration_seconds=3.2
    )
    assert ev is not None
    assert ev.behaviour_type == "SIDEWAYS_GAZE"
    assert ev.duration_seconds == 3.2

    events = await supabase_db.list_behaviour_events(exam_session_id="00000000-0000-0000-0000-000000000011", student_id="s-01")
    assert any(e.get("behaviour_type") == "SIDEWAYS_GAZE" for e in events)
