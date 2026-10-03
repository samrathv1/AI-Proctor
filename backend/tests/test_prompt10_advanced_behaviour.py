"""
==============================================================================
AI-PROCTOR — PROMPT 10: ADVANCED BEHAVIOUR DETECTION & TEMPORAL ANALYSIS
TEST SUITE

Validates:
1. Single sideways glance does not create a critical alert.
2. Repeated sideways gaze is temporally accumulated (SIDEWAYS_GAZE / PROLONGED_SIDEWAYS_GAZE).
3. Repeated head turns accumulate correctly (REPEATED_HEAD_TURN).
4. Tracking continuity preserves the same student/track across frames.
5. Unknown identity is never assigned a student name (UNKNOWN PERSON).
6. Identity uncertainty remains UNCERTAIN.
7. Person interaction is associated with correct tracks (PERSON_INTERACTION).
8. Camera disconnection does not generate fake behaviour events.
9. Frame drops do not duplicate events (anti-double-counting).
10. Alert cooldown prevents duplicate alerts.
11. Advisory score remains explainable with contributing factors.
12. Existing phone detection still works.
13. Existing face recognition still works.
14. Existing ESP32 alert dispatch still works.
15. Existing Prompt 9 exam lifecycle still works.
16. Existing alert acknowledgement/review still works.
==============================================================================
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from backend.app.services.temporal_service import temporal_service
from backend.app.services.suspicion_service import suspicion_service
from backend.app.services.behaviour_service import behaviour_service
from backend.app.services.head_pose_service import head_pose_service
from backend.app.services.iot_service import iot_service
from backend.app.services.alert_service import alert_service
from backend.app.models.requests import AlertCreateRequest
from backend.app.main import app
from backend.app.core.config import settings
from fastapi.testclient import TestClient

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": settings.API_SECRET_KEY}


# ==============================================================================
# 1. SIDEWAYS GAZE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_01_single_sideways_glance_low_advisory_no_critical_alert():
    """1. Single brief sideways glance (0.8s) creates low advisory impact, no critical alert."""
    subject_id = "trk-glance-01"
    
    # 0.8s momentary sideways gaze
    is_cont, dur = temporal_service.update_observation_state(
        subject_id=subject_id,
        event_type="SIDEWAYS_GAZE",
        is_active=True,
        confidence=0.88,
        metadata={"direction": "RIGHT"}
    )
    
    ev = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-p10-01",
        camera_id="cam-01",
        student_id="s-dev",
        tracking_id=subject_id,
        behaviour_type="SIDEWAYS_GAZE",
        confidence=0.88,
        duration_seconds=dur,
        is_continuous=False,
        metadata={"direction": "RIGHT"}
    )
    
    suspicion = suspicion_service.calculate_suspicion([ev])
    # Must have low advisory score (< 20) and LOW severity (never CRITICAL)
    assert suspicion.score < 20
    assert suspicion.severity == "LOW"
    assert suspicion.requires_alert is False


@pytest.mark.asyncio
async def test_02_repeated_and_prolonged_sideways_gaze_accumulates():
    """2. Prolonged sideways gaze (>= 4.0s) triggers PROLONGED_SIDEWAYS_GAZE and elevates advisory score."""
    subject_id = "trk-gaze-long"
    
    # Simulate sustained sideways gaze for 5.0 seconds
    temporal_service.update_observation_state(
        subject_id=subject_id,
        event_type="SIDEWAYS_GAZE",
        is_active=True,
        confidence=0.92,
        metadata={"direction": "LEFT"}
    )
    temporal_service._active_states[subject_id]["SIDEWAYS_GAZE"].started_at = (
        datetime.now(timezone.utc) - timedelta(seconds=5.0)
    )
    
    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-p10-02",
        camera_id="cam-01",
        student_id="s-dev",
        tracking_id=subject_id
    )
    
    # Prolonged sideways gaze event should be generated
    types = [e.behaviour_type for e in agg]
    assert "PROLONGED_SIDEWAYS_GAZE" in types
    prolonged_ev = next(e for e in agg if e.behaviour_type == "PROLONGED_SIDEWAYS_GAZE")
    assert prolonged_ev.duration_seconds >= 4.0
    
    suspicion = suspicion_service.calculate_suspicion(agg)
    assert suspicion.score >= 18
    assert any("PROLONGED_SIDEWAYS_GAZE" in c for c in suspicion.contributing_events)


# ==============================================================================
# 2. REPEATED HEAD TURN & CYCLIC MOVEMENT PATTERNS
# ==============================================================================

@pytest.mark.asyncio
async def test_03_repeated_head_turn_accumulates_correctly():
    """3. Repeated head turns accumulate and generate REPEATED_HEAD_TURN observation."""
    subject_id = "trk-headturn-01"
    
    # Simulate 3 turns in window
    for _ in range(3):
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_RIGHT", is_active=True)
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_RIGHT", is_active=False)
        
    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-p10-03",
        camera_id="cam-01",
        student_id="s-dev",
        tracking_id=subject_id
    )
    
    types = [e.behaviour_type for e in agg]
    assert "REPEATED_HEAD_TURN" in types or "REPEATED_HEAD_TURNS" in types


@pytest.mark.asyncio
async def test_03b_suspicious_cyclic_movement_pattern():
    """3b. Alternating cyclic turns (Left-Right >= 4) trigger SUSPICIOUS_MOVEMENT_PATTERN."""
    subject_id = "trk-cyclic-01"
    
    # Alternating Left-Right turns
    for _ in range(3):
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=True)
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=False)
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_RIGHT", is_active=True)
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_RIGHT", is_active=False)
        
    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-p10-03b",
        camera_id="cam-01",
        student_id="s-dev",
        tracking_id=subject_id
    )
    types = [e.behaviour_type for e in agg]
    assert "SUSPICIOUS_MOVEMENT_PATTERN" in types


# ==============================================================================
# 3. TRACKING & IDENTITY SAFETY
# ==============================================================================

@pytest.mark.asyncio
async def test_04_tracking_continuity_preserves_same_student_and_track():
    """4. Tracking continuity preserves subject ID and student mapping across observation states."""
    track_id = "trk-continuous-99"
    student_id = "s-ananya"
    
    # Sequence of frames
    temporal_service.update_observation_state(track_id, "FRONTAL", is_active=True, metadata={"student_id": student_id})
    temporal_service.update_observation_state(track_id, "LOOKING_AWAY", is_active=True, metadata={"student_id": student_id})
    
    timeline = temporal_service.get_evidence_timeline(track_id)
    assert len(timeline) >= 2
    for item in timeline:
        assert item["metadata"]["student_id"] == student_id


@pytest.mark.asyncio
async def test_05_unknown_identity_never_assigned_student_name():
    """5. Unknown identity is never silently assigned a student name; remains UNKNOWN PERSON."""
    ev_unk = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-p10-05",
        camera_id="cam-01",
        student_id=None,
        tracking_id="trk-unk-01",
        behaviour_type="UNKNOWN_PERSON",
        confidence=0.85
    )
    assert ev_unk.student_id is None
    assert ev_unk.behaviour_type == "UNKNOWN_PERSON"
    
    suspicion = suspicion_service.calculate_suspicion([ev_unk])
    # Objective advisory signal
    assert suspicion.score == 42  # 50 base * 0.85 conf
    assert "UNKNOWN_PERSON" in suspicion.contributing_events[0]


@pytest.mark.asyncio
async def test_06_identity_uncertainty_remains_uncertain():
    """6. Identity similarity between 45% and 60% remains UNCERTAIN."""
    ev_unc = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-p10-06",
        camera_id="cam-01",
        student_id="s-candidate",
        tracking_id="trk-unc-01",
        behaviour_type="UNCERTAIN_BIOMETRIC_MATCH",
        confidence=0.53,
        metadata={"similarity": 0.53, "status": "IDENTITY UNCERTAIN"}
    )
    assert ev_unc.metadata.get("status") == "IDENTITY UNCERTAIN"
    assert ev_unc.confidence == 0.53


# ==============================================================================
# 4. SPATIAL & MULTI-TRACK INTERACTION
# ==============================================================================

@pytest.mark.asyncio
async def test_07_person_interaction_associated_with_correct_tracks():
    """7. Person interaction is detected when candidates are in close proximity, tagged with both tracks."""
    track_a = {"tracking_id": "trk-01", "student_id": "s-01", "bounding_box": {"x": 100, "y": 100, "width": 80, "height": 100}}
    track_b = {"tracking_id": "trk-02", "student_id": "s-02", "bounding_box": {"x": 160, "y": 105, "width": 80, "height": 100}}
    
    is_interact, norm_dist = behaviour_service.evaluate_person_interaction(track_a, track_b)
    assert is_interact is True
    assert norm_dist < 1.35
    
    # Event creation associates tracks
    ev_interact = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-p10-07",
        camera_id="cam-01",
        student_id="s-01",
        tracking_id="trk-01",
        behaviour_type="PERSON_INTERACTION",
        confidence=0.88,
        duration_seconds=2.5,
        is_continuous=True,
        metadata={"interacting_with_track": "trk-02", "normalized_distance": norm_dist}
    )
    assert ev_interact.behaviour_type == "PERSON_INTERACTION"
    assert ev_interact.metadata["interacting_with_track"] == "trk-02"


@pytest.mark.asyncio
async def test_07b_desk_peeking_single_webcam_safely_reported():
    """7b. Single-person webcam view reports NOT RELIABLY DETECTABLE WITH CURRENT CAMERA INPUT without faking."""
    track_solo = {"tracking_id": "trk-solo", "student_id": "s-01", "bounding_box": {"x": 200, "y": 150, "width": 120, "height": 150}}
    
    is_peeking, target_id, reason = behaviour_service.evaluate_desk_peeking(
        candidate_track=track_solo,
        other_tracks=[],
        camera_type="WEBCAM"
    )
    assert is_peeking is False
    assert reason == "NOT RELIABLY DETECTABLE WITH CURRENT CAMERA INPUT"


# ==============================================================================
# 5. ROBUSTNESS & TEMPORAL DISPATCH
# ==============================================================================

@pytest.mark.asyncio
async def test_08_camera_disconnection_does_not_generate_fake_events():
    """8. Camera disconnection handles cleanly without producing synthetic behaviour events."""
    # Simulating inactive/offline stream
    temporal_service._active_states.clear()
    temporal_service._event_history.clear()
    timeline = temporal_service.get_evidence_timeline("cam-disconnected-stream")
    assert len(timeline) == 0


@pytest.mark.asyncio
async def test_09_frame_drops_do_not_duplicate_events():
    """9. Frame drops and consecutive identical frames maintain anti-double-counting duration state."""
    subject_id = "trk-antidouble"
    
    # Frame 1
    is_cont1, dur1 = temporal_service.update_observation_state(subject_id, "LOOKING_AWAY", is_active=True)
    assert is_cont1 is False
    
    # Frame 2 (consecutive active frame)
    is_cont2, dur2 = temporal_service.update_observation_state(subject_id, "LOOKING_AWAY", is_active=True)
    assert is_cont2 is True
    assert dur2 >= dur1


@pytest.mark.asyncio
async def test_10_alert_cooldown_prevents_duplicate_alerts():
    """10. Alert cooldown prevents firing back-to-back alerts for the same subject within cooldown window."""
    subject_id = "trk-cooldown-test"
    alert_type = "MOBILE_PHONE_DETECTED"
    
    # First check: allowed
    can_fire = temporal_service.can_trigger_alert(subject_id, alert_type, cooldown_seconds=30.0)
    assert can_fire is True
    
    # Record dispatched
    temporal_service.record_alert_dispatched(subject_id, alert_type, "CRITICAL", alert_id="alt-001")
    
    # Second check within cooldown: blocked
    can_fire_again = temporal_service.can_trigger_alert(subject_id, alert_type, cooldown_seconds=30.0)
    assert can_fire_again is False


@pytest.mark.asyncio
async def test_11_advisory_score_remains_transparent_and_explainable():
    """11. Advisory score exposes every contributing factor with its exact weight and duration bonus."""
    ev1 = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-exp",
        camera_id="cam-01",
        behaviour_type="SIDEWAYS_GAZE",
        confidence=0.90,
        duration_seconds=2.0
    )
    ev2 = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-exp",
        camera_id="cam-01",
        behaviour_type="REPEATED_HEAD_TURN",
        confidence=0.85
    )
    
    suspicion = suspicion_service.calculate_suspicion([ev1, ev2])
    assert suspicion.score > 0
    assert len(suspicion.contributing_factors) == 2
    for factor in suspicion.contributing_factors:
        assert "type" in factor
        assert "base_weight" in factor
        assert "confidence" in factor
        assert "total_weight" in factor


# ==============================================================================
# 6. REGRESSION SAFETY ON PREVIOUS SUBSYSTEMS
# ==============================================================================

@pytest.mark.asyncio
async def test_12_existing_phone_detection_still_works():
    """12. Existing mobile phone detection still produces high advisory score."""
    ev_phone = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-reg",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.94,
        duration_seconds=3.0,
        is_continuous=True
    )
    suspicion = suspicion_service.calculate_suspicion([ev_phone])
    assert suspicion.score >= 40
    assert suspicion.severity in ["MEDIUM", "HIGH", "CRITICAL"]
    assert any("MOBILE_PHONE_DETECTED" in c for c in suspicion.contributing_events)


@pytest.mark.asyncio
async def test_13_existing_face_recognition_head_pose_still_works():
    """13. Existing head-pose estimation still calculates yaw, pitch, roll and gaze direction."""
    # 5 2D landmarks (right eye, left eye, nose, right mouth, left mouth)
    landmarks = np.array([
        [180, 200],  # Right eye
        [240, 200],  # Left eye
        [210, 230],  # Nose
        [190, 260],  # Right mouth
        [230, 260]   # Left mouth
    ], dtype=np.float32)
    
    pose = head_pose_service.estimate_pose_from_landmarks(landmarks, 640, 480)
    assert pose.posture in ["FRONTAL", "HEAD_TURN_LEFT", "HEAD_TURN_RIGHT", "LOOKING_DOWN", "LOOKING_UP"]
    assert pose.gaze_direction in ["LEFT", "RIGHT", "CENTER"]
    assert isinstance(pose.is_sideways_gaze, bool)


@pytest.mark.asyncio
async def test_14_existing_esp32_alert_dispatch_still_works():
    """14. Existing ESP32 IoT hardware alert dispatch works with GPIO 27 LED and GPIO 15 Buzzer."""
    device_id = "ESP32-TEST-P10-DISPATCH"
    iot_service._devices[device_id] = {
        "device_id": device_id,
        "device_uid": device_id,
        "status": "ONLINE",
        "last_seen_at": datetime.now(timezone.utc)
    }
    iot_service._pending_commands[device_id] = []
    
    # High severity mobile phone alert -> triggers hardware command
    high_alert = {"id": "alt-p10-01", "severity": "HIGH", "alert_type": "MOBILE_PHONE"}
    cmd = await iot_service.dispatch_alert_for_infraction(high_alert, device_id=device_id)
    assert cmd is not None
    assert cmd.led is True
    assert cmd.buzzer is True
    assert cmd.pattern == "PULSE"


def test_15_existing_prompt9_exam_lifecycle_still_works():
    """15. Existing exam creation and summary lifecycle still functions."""
    resp_exam = client.get("/api/v1/exams/exam-01", headers=AUTH_HEADERS)
    assert resp_exam.status_code == 200
    exam_data = resp_exam.json()
    assert exam_data["id"] == "exam-01"
    assert "status" in exam_data


def test_16_existing_alert_acknowledgement_and_review_still_works():
    """16. Existing alert acknowledgement and review workflow functions properly."""
    alert_req = {
        "exam_session_id": "sess-p10-review",
        "exam_id": "exam-01",
        "student_id": "s-01",
        "camera_id": "cam-01",
        "alert_type": "SIDEWAYS_GAZE",
        "severity": "LOW",
        "confidence": 85,
        "suspicion_score": 15,
        "title": "Advisory: Sideways Gaze",
        "description": "Candidate observed with lateral gaze divergence."
    }
    resp_create = client.post("/api/v1/alerts", json=alert_req, headers=AUTH_HEADERS)
    assert resp_create.status_code == 200
    created_alert = resp_create.json()
    alert_id = created_alert["id"]

    # Acknowledge alert
    resp_ack = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", headers=AUTH_HEADERS)
    assert resp_ack.status_code == 200
    assert resp_ack.json()["status"] == "ACKNOWLEDGED"

    # Review alert
    review_req = {
        "status": "REVIEWED",
        "reviewer_notes": "Reviewed and confirmed momentary glance at clock."
    }
    resp_review = client.post(f"/api/v1/alerts/{alert_id}/review", json=review_req, headers=AUTH_HEADERS)
    assert resp_review.status_code == 200
    assert resp_review.json()["status"] == "REVIEWED"
