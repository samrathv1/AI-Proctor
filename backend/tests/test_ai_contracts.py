import pytest
from backend.app.services.recognition_service import recognition_service
from backend.app.services.detection_service import detection_service
from backend.app.services.tracking_service import tracking_service
from backend.app.services.behaviour_service import behaviour_service
from backend.app.services.suspicion_service import suspicion_service


from backend.tests.test_face_enrollment_pipeline import generate_single_face, encode_image_base64


@pytest.mark.asyncio
async def test_face_recognition_contract_no_fake_match():
    # Empty frame produces NO_FACE
    res_empty = await recognition_service.recognize_face(None, "exam-01")
    assert res_empty.status == "NO_FACE"
    assert res_empty.student_id is None

    # Unenrolled face produces UNKNOWN, never an invented identity
    face_img = generate_single_face()
    b64 = encode_image_base64(face_img)
    res_frame = await recognition_service.recognize_face(b64, "exam-unenrolled")
    assert res_frame.status == "UNKNOWN"
    assert res_frame.student_id is None


@pytest.mark.asyncio
async def test_detection_contract_format():
    res = await detection_service.detect_frame(
        frame_data="sample_frame_bytes",
        camera_id="cam-01",
        exam_session_id="ses-01"
    )
    assert res.camera_id == "cam-01"
    assert res.exam_session_id == "ses-01"
    assert len(res.detections) > 0
    det = res.detections[0]
    assert det.detection_type == "PERSON"
    assert det.bounding_box.width > 0
    assert det.confidence > 0.5


@pytest.mark.asyncio
async def test_tracking_contract_state_lifecycle():
    track = await tracking_service.update_track(
        tracking_id="trk-99",
        camera_id="cam-01",
        status="IDENTIFIED"
    )
    assert track.tracking_id == "trk-99"
    assert track.status == "IDENTIFIED"

    # Verify transition to TEMPORARILY_NOT_VISIBLE
    updated = await tracking_service.mark_temporarily_hidden("trk-99")
    assert updated.status == "TEMPORARILY_NOT_VISIBLE"


@pytest.mark.asyncio
async def test_behaviour_event_contract_no_cheating_label():
    event = await behaviour_service.create_behaviour_event(
        exam_session_id="ses-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.92,
        student_id="s-01"
    )
    assert event.behaviour_type == "MOBILE_PHONE_DETECTED"
    # STRICT REQUIREMENT: Does not label observable event as "cheating"
    assert "cheating" not in event.behaviour_type.lower()
    assert event.confidence == 0.92


def test_suspicion_scoring_contract():
    # Empty events
    res_empty = suspicion_service.calculate_suspicion([])
    assert res_empty.score == 0
    assert res_empty.severity == "LOW"
    assert res_empty.requires_alert is False

    # Event with mobile detection
    from backend.app.models.responses import BehaviourEvent
    from datetime import datetime, timezone
    mobile_event = BehaviourEvent(
        event_id="beh-test-01",
        exam_session_id="ses-01",
        camera_id="cam-01",
        student_id="s-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.90,
        timestamp=datetime.now(timezone.utc)
    )
    res_mobile = suspicion_service.calculate_suspicion([mobile_event])
    assert res_mobile.score > 0
    assert isinstance(res_mobile.contributing_events, list)
    assert "RECOMMENDED" in res_mobile.recommended_action or res_mobile.recommended_action in ["NONE", "MONITOR", "REVIEW_EVIDENCE", "TRIGGER_IOT_ALARM"]


def test_frame_analysis_endpoint(client, auth_headers):
    payload = {
        "camera_id": "cam-01",
        "exam_session_id": "ses-01",
        "exam_id": "exam-01",
        "frame_base64": "dummy-frame-bytes"
    }
    response = client.post("/api/v1/monitoring/frame", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["camera_id"] == "cam-01"
    assert "detection_summary" in data
    assert "tracking" in data
    assert "observable_behaviour" in data
    assert "suspicion_index" in data


def test_video_worker_job_lifecycle(client, auth_headers):
    payload = {
        "exam_id": "exam-01",
        "video_reference": "exam-videos/hall-304-session-1.mp4",
        "camera_id": "cam-recorded"
    }
    response = client.post("/api/v1/video/process", json=payload, headers=auth_headers)
    assert response.status_code == 200
    job = response.json()
    assert "job_id" in job
    assert job["status"] in ["QUEUED", "PROCESSING", "COMPLETED"]

    # Poll status
    job_id = job["job_id"]
    status_resp = client.get(f"/api/v1/video/jobs/{job_id}", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == job_id
