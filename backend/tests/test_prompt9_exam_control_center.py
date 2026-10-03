import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.API_SECRET_KEY}


def test_spit_institutional_email_authentication_validation():
    """
    Prompt 9 Requirement 2:
    SPIT institutional email authentication validation.
    Must accept @spit.ac.in emails and reject unapproved domains.
    """
    # 1. Reject non-institutional email
    unauthorized_payload = {
        "name": "External Student",
        "roll_number": "EXT-2026-999",
        "email": "external.user@gmail.com",
        "class_name": "CS-2026",
        "department": "Computer Science & Engineering"
    }
    resp_rejected = client.post(
        "/api/v1/students/register",
        json=unauthorized_payload,
        headers=AUTH_HEADERS
    )
    assert resp_rejected.status_code == 400
    assert "institutional email" in resp_rejected.json()["detail"].lower()

    # 2. Accept SPIT institutional email
    import time
    uid = int(time.time()) % 100000
    spit_payload = {
        "name": "SPIT Scholar",
        "roll_number": f"SPIT-2026-{uid}",
        "email": f"scholar.{uid}@spit.ac.in",
        "class_name": "CS-2026",
        "department": "Computer Science & Engineering"
    }
    resp_accepted = client.post(
        "/api/v1/students/register",
        json=spit_payload,
        headers=AUTH_HEADERS
    )
    assert resp_accepted.status_code == 201
    data = resp_accepted.json()
    assert data["email"] == spit_payload["email"]
    assert data["roll_number"] == spit_payload["roll_number"]


def test_exam_lifecycle_roster_and_summary():
    """
    Prompt 9 Requirements 3, 4, 5, 8, 16, 17:
    - Exam Creation
    - Roster inspection and seat/camera assignment
    - Start Exam (biometric cache loading, transition to LIVE)
    - End Exam (safe hardware reset, transition to ENDED)
    - Exam Summary (objective facts, no defamatory conclusions)
    """
    # 1. Fetch existing exam
    resp_exam = client.get("/api/v1/exams/exam-01", headers=AUTH_HEADERS)
    assert resp_exam.status_code == 200
    exam_data = resp_exam.json()
    assert exam_data["id"] == "exam-01"

    # 2. Inspect exam roster
    resp_roster = client.get("/api/v1/exams/exam-01/roster", headers=AUTH_HEADERS)
    assert resp_roster.status_code == 200
    roster = resp_roster.json()
    assert len(roster) >= 3
    # Check that seat and camera are associated
    first_candidate = roster[0]
    assert "seat_number" in first_candidate
    assert "camera_id" in first_candidate
    assert "enrollment_status" in first_candidate

    # 3. Start Exam endpoint
    resp_start = client.post("/api/v1/exams/exam-01/start", headers=AUTH_HEADERS)
    assert resp_start.status_code == 200
    start_data = resp_start.json()
    assert start_data["status"] == "LIVE"
    assert "started_at" in start_data

    # 4. End Exam endpoint
    resp_end = client.post("/api/v1/exams/exam-01/end", headers=AUTH_HEADERS)
    assert resp_end.status_code == 200
    end_data = resp_end.json()
    assert end_data["status"] == "ENDED"
    assert "ended_at" in end_data

    # 5. Fetch Exam Summary
    resp_summary = client.get("/api/v1/exams/exam-01/summary", headers=AUTH_HEADERS)
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert summary["exam_id"] == "exam-01"
    assert summary["reporting_standard"] == "OBJECTIVE_OBSERVABLE_FACTS_ONLY"
    assert "total_students_enrolled" in summary
    assert "alerts_count" in summary
    assert "hardware_alerts_dispatched" in summary
    # Verify no defamatory labels
    assert "cheaters" not in summary
    assert "cheater_count" not in summary


def test_alert_center_acknowledge_and_review():
    """
    Prompt 9 Requirement 14:
    Invigilator alert center actions:
    - View alert
    - Acknowledge alert
    - Review alert with notes
    """
    # 1. Create a test alert
    alert_req = {
        "exam_session_id": "session-test-p9",
        "exam_id": "exam-01",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "MOBILE_PHONE",
        "severity": "HIGH",
        "confidence": 92,
        "suspicion_score": 88,
        "title": "Mobile Device In Desk Area",
        "description": "Continuous mobile screen emission under desk."
    }
    resp_create = client.post("/api/v1/alerts", json=alert_req, headers=AUTH_HEADERS)
    assert resp_create.status_code == 200
    created_alert = resp_create.json()
    alert_id = created_alert["id"]

    # 2. Acknowledge alert
    resp_ack = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=AUTH_HEADERS)
    assert resp_ack.status_code == 200
    ack_data = resp_ack.json()
    assert ack_data["status"] == "ACKNOWLEDGED"

    # 3. Review alert
    review_req = {
        "status": "REVIEWED",
        "reviewer_notes": "Invigilator verified candidate desk. Phone confiscated."
    }
    resp_review = client.post(f"/api/v1/alerts/{alert_id}/review", json=review_req, headers=AUTH_HEADERS)
    assert resp_review.status_code == 200
    rev_data = resp_review.json()
    assert rev_data["status"] == "REVIEWED"
    assert rev_data["reviewer_notes"] == "Invigilator verified candidate desk. Phone confiscated."
