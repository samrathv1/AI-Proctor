import pytest
import time
from datetime import datetime, timezone, timedelta
import numpy as np

from backend.app.services.head_pose_service import head_pose_service, HeadPoseResult
from backend.app.services.temporal_service import temporal_service, TemporalBehaviourService
from backend.app.services.behaviour_service import behaviour_service
from backend.app.services.suspicion_service import suspicion_service
from backend.app.models.responses import BehaviourEvent
from backend.app.core.config import settings


@pytest.fixture(autouse=True)
def reset_temporal_state():
    """Ensure clean temporal state between test cases."""
    temporal_service.clear()
    yield
    temporal_service.clear()


# ==============================================================================
# HEAD POSE ESTIMATION TESTS
# ==============================================================================

def test_head_pose_frontal_estimation():
    """Verify solvePnP computes near-zero Euler angles for frontal synthetic landmarks."""
    # Canonical frontal landmarks: (left_eye, right_eye, nose, left_mouth, right_mouth)
    landmarks = [
        (280.0, 200.0),  # left eye
        (360.0, 200.0),  # right eye
        (320.0, 250.0),  # nose tip
        (290.0, 310.0),  # mouth left
        (350.0, 310.0)   # mouth right
    ]
    res = head_pose_service.estimate_pose_from_landmarks(landmarks, frame_width=640, frame_height=480)
    assert isinstance(res, HeadPoseResult)
    assert res.posture == "FRONTAL"
    assert not res.is_looking_away
    assert abs(res.yaw) < 20.0
    assert abs(res.pitch) < 25.0
    d = res.to_dict()
    assert "yaw" in d and "pitch" in d and "roll" in d


def test_head_pose_turn_left():
    """Verify solvePnP detects head turn left when nose shifts left relative to eyes."""
    # Left turn shifts nose towards left eye and narrows left side
    landmarks = [
        (260.0, 200.0),  # left eye
        (330.0, 200.0),  # right eye
        (265.0, 250.0),  # nose tip shifted far left
        (265.0, 310.0),  # mouth left
        (315.0, 310.0)   # mouth right
    ]
    res = head_pose_service.estimate_pose_from_landmarks(landmarks, frame_width=640, frame_height=480)
    assert res.yaw < -settings.HEAD_POSE_YAW_THRESHOLD
    assert res.posture == "HEAD_TURN_LEFT"
    assert res.is_looking_away is True


def test_head_pose_turn_right():
    """Verify solvePnP detects head turn right when nose shifts right relative to eyes."""
    landmarks = [
        (310.0, 200.0),  # left eye
        (380.0, 200.0),  # right eye
        (375.0, 250.0),  # nose tip shifted far right
        (325.0, 310.0),  # mouth left
        (375.0, 310.0)   # mouth right
    ]
    res = head_pose_service.estimate_pose_from_landmarks(landmarks, frame_width=640, frame_height=480)
    assert res.yaw > settings.HEAD_POSE_YAW_THRESHOLD
    assert res.posture == "HEAD_TURN_RIGHT"
    assert res.is_looking_away is True


def test_head_pose_looking_down():
    """Verify solvePnP detects looking down when nose shifts down towards mouth."""
    landmarks = [
        (280.0, 200.0),  # left eye
        (360.0, 200.0),  # right eye
        (320.0, 280.0),  # nose shifted down
        (290.0, 330.0),  # mouth left
        (350.0, 330.0)   # mouth right
    ]
    res = head_pose_service.estimate_pose_from_landmarks(landmarks, frame_width=640, frame_height=480)
    assert res.posture in ["LOOKING_DOWN", "LOOKING_AWAY"]
    assert res.is_looking_away is True
    assert res.pitch > settings.HEAD_POSE_PITCH_THRESHOLD


# ==============================================================================
# SPECIFICATION STEP 17: 15 REALISTIC TEMPORAL TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_case_01_single_head_turn_no_significant_alert():
    """Test 1: One isolated head turn does not produce a significant or high-severity alert."""
    ev = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="HEAD_TURN_LEFT",
        confidence=0.85,
        duration_seconds=0.5
    )
    suspicion = suspicion_service.calculate_suspicion([ev])
    # Weight of single head turn is 5, confidence 0.85 => 4 pts
    assert suspicion.score < settings.SUSPICION_ALERT_THRESHOLD
    assert suspicion.severity == "LOW"
    assert suspicion.requires_alert is False


@pytest.mark.asyncio
async def test_case_02_repeated_head_turns_increases_advisory_score():
    """Test 2: Repeated head turns in rolling window emit REPEATED_HEAD_TURNS event and escalate score."""
    subject_id = "trk-cam-01-001"
    
    # Simulate 3 sequential head turns in rolling window
    for _ in range(3):
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=True)
        temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=False)

    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-01",
        camera_id="cam-01"
    )
    assert any(ev.behaviour_type in ["REPEATED_HEAD_TURNS", "REPEATED_HEAD_TURN"] for ev in agg)
    repeat_ev = next(ev for ev in agg if ev.behaviour_type in ["REPEATED_HEAD_TURNS", "REPEATED_HEAD_TURN"])
    assert repeat_ev.metadata["count_in_window"] >= 3

    suspicion = suspicion_service.calculate_suspicion([repeat_ev])
    assert suspicion.score >= 12  # Base weight 15 * conf
    assert any("REPEATED_HEAD_TURN" in c for c in suspicion.contributing_events)


@pytest.mark.asyncio
async def test_case_03_brief_face_disappearance_no_major_alert():
    """Test 3: Brief face absence (< 5s) does not trigger FACE_NOT_VISIBLE event or alert."""
    subject_id = "trk-cam-01-002"
    # Simulate brief 1.5s disappearance
    temporal_service.update_observation_state(subject_id, "FACE_NOT_VISIBLE", is_active=True)
    # Below threshold:
    dur = temporal_service.get_active_duration(subject_id, "FACE_NOT_VISIBLE")
    assert dur < settings.FACE_ABSENCE_DURATION_THRESHOLD

    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-01",
        camera_id="cam-01"
    )
    assert not any(ev.behaviour_type == "FACE_NOT_VISIBLE" for ev in agg)


@pytest.mark.asyncio
async def test_case_04_long_face_disappearance_observable_event():
    """Test 4: Extended face absence (>= 5s and >= 20s) produces observable event and escalation bonus."""
    subject_id = "trk-cam-01-003"
    obs_active, _ = temporal_service.update_observation_state(subject_id, "FACE_NOT_VISIBLE", is_active=True)
    # Artificially age the observation to 22.0 seconds
    temporal_service._active_states[subject_id]["FACE_NOT_VISIBLE"].started_at = datetime.now(timezone.utc) - timedelta(seconds=22)
    temporal_service._active_states[subject_id]["FACE_NOT_VISIBLE"].last_seen_at = datetime.now(timezone.utc)

    dur = temporal_service.get_active_duration(subject_id, "FACE_NOT_VISIBLE")
    assert dur >= 20.0

    agg = await behaviour_service.check_temporal_aggregations(
        subject_id=subject_id,
        exam_session_id="sess-01",
        camera_id="cam-01"
    )
    absent_ev = next((ev for ev in agg if ev.behaviour_type == "FACE_NOT_VISIBLE"), None)
    assert absent_ev is not None
    assert absent_ev.duration_seconds >= 20.0

    suspicion = suspicion_service.calculate_suspicion([absent_ev])
    factor = next(f for f in suspicion.contributing_factors if f["type"] == "FACE_NOT_VISIBLE")
    assert factor["duration_bonus"] == 15  # Escalation bonus for > 20s absence
    assert factor["total_weight"] == 25     # 10 base + 15 bonus


@pytest.mark.asyncio
async def test_case_05_phone_detected_1_second():
    """Test 5: Phone detected for 1 second produces a base phone event without duration bonus."""
    ev = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.90,
        duration_seconds=1.0,
        is_continuous=False
    )
    suspicion = suspicion_service.calculate_suspicion([ev])
    factor = next(f for f in suspicion.contributing_factors if f["type"] == "MOBILE_PHONE_DETECTED")
    assert factor["base_weight"] == 45
    assert factor["duration_bonus"] == 0
    assert suspicion.score == int(45 * 0.90)  # 40


@pytest.mark.asyncio
async def test_case_06_phone_persistent_20_seconds():
    """Test 6: Phone persistent for 20 seconds receives duration escalation bonus."""
    ev = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.90,
        duration_seconds=20.0,
        is_continuous=True
    )
    suspicion = suspicion_service.calculate_suspicion([ev])
    factor = next(f for f in suspicion.contributing_factors if f["type"] == "MOBILE_PHONE_DETECTED")
    assert factor["base_weight"] == 45
    assert factor["duration_bonus"] > 10  # Escalation bonus
    assert suspicion.score > 45           # Score scaled above base single frame


@pytest.mark.asyncio
async def test_case_07_phone_plus_repeated_head_movement():
    """Test 7: Combined signals (phone + repeated head turns) fuse into high advisory suspicion."""
    ev_phone = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.90,
        duration_seconds=5.0
    )
    ev_turns = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="REPEATED_HEAD_TURNS",
        confidence=0.85
    )
    suspicion = suspicion_service.calculate_suspicion([ev_phone, ev_turns])
    assert suspicion.score >= 50
    assert len(suspicion.contributing_factors) == 2
    types = [f["type"] for f in suspicion.contributing_factors]
    assert "MOBILE_PHONE_DETECTED" in types and "REPEATED_HEAD_TURNS" in types


@pytest.mark.asyncio
async def test_case_08_unknown_person_alone():
    """Test 8: Unknown person alone generates review signal (MEDIUM severity, score ~50)."""
    ev_unk = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="UNKNOWN_PERSON",
        confidence=1.0
    )
    suspicion = suspicion_service.calculate_suspicion([ev_unk])
    assert suspicion.score == 50
    assert suspicion.severity == "MEDIUM"
    assert suspicion.recommended_action == "MONITOR"


@pytest.mark.asyncio
async def test_case_09_unknown_person_plus_phone():
    """Test 9: Unknown person + phone fuses to CRITICAL escalation score (> 85)."""
    ev_unk = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="UNKNOWN_PERSON",
        confidence=1.0
    )
    ev_phone = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.95,
        duration_seconds=6.0
    )
    suspicion = suspicion_service.calculate_suspicion([ev_unk, ev_phone])
    assert suspicion.score >= 85
    assert suspicion.severity == "CRITICAL"
    assert suspicion.recommended_action == "TRIGGER_IOT_ALARM"


@pytest.mark.asyncio
async def test_case_10_multiple_persons_briefly_observable_event():
    """Test 10: Multiple persons observed briefly is an objective event, NOT automatic cheating."""
    ev = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MULTIPLE_PERSONS",
        confidence=0.95,
        duration_seconds=1.0,
        metadata={"faces_count": 2}
    )
    suspicion = suspicion_service.calculate_suspicion([ev])
    # Base weight is 40 * 0.95 = 38
    assert suspicion.score <= 40
    assert suspicion.severity in ["LOW", "MEDIUM"]
    # Verify description is objective
    assert "cheating" not in str(suspicion).lower()


@pytest.mark.asyncio
async def test_case_11_multiple_persons_persistently():
    """Test 11: Multiple persons persisting across frames maintains ongoing continuous duration."""
    subject_id = "camera-cam-01"
    temporal_service.update_observation_state(subject_id, "MULTIPLE_PERSONS", is_active=True)
    # Simulate time lapse of 15 seconds
    temporal_service._active_states[subject_id]["MULTIPLE_PERSONS"].started_at = datetime.now(timezone.utc) - timedelta(seconds=15)
    temporal_service._active_states[subject_id]["MULTIPLE_PERSONS"].last_seen_at = datetime.now(timezone.utc)

    dur = temporal_service.get_active_duration(subject_id, "MULTIPLE_PERSONS")
    assert dur >= 15.0


def test_case_12_same_event_across_many_frames_no_double_counting():
    """Test 12: Evaluating multiple events of same type in same frame does not multiply score."""
    # 5 identical MOBILE_PHONE events in same frame
    events = [
        BehaviourEvent(
            event_id=f"ev-{i}",
            exam_session_id="sess-01",
            camera_id="cam-01",
            student_id="stu-01",
            tracking_id="trk-01",
            behaviour_type="MOBILE_PHONE_DETECTED",
            confidence=0.90,
            duration_seconds=5.0,
            is_continuous=True,
            timestamp=datetime.now(timezone.utc)
        )
        for i in range(5)
    ]
    suspicion = suspicion_service.calculate_suspicion(events)
    # Without deduplication, 5 * 45 = 225 (capped to 100).
    # With deduplication, counted ONCE: base 45 + duration bonus 4 = 49 * 0.9 = 44
    assert suspicion.score < 50
    assert len(suspicion.contributing_factors) == 1


def test_case_13_alert_cooldown_prevents_duplicate_spam():
    """Test 13: Alert cooldown suppresses duplicate alerts within cooldown window."""
    subject_id = "trk-cam-01-005"
    alert_type = "MOBILE_PHONE_DETECTED"

    # Initially alert can trigger
    assert temporal_service.can_trigger_alert(subject_id, alert_type, cooldown_seconds=30.0) is True

    # Dispatch alert
    temporal_service.record_alert_dispatched(subject_id, alert_type, severity="HIGH", alert_id="alt-001")

    # Immediately after, should be suppressed
    assert temporal_service.can_trigger_alert(subject_id, alert_type, cooldown_seconds=30.0) is False

    # Simulate 31 seconds elapsed
    temporal_service._alert_cooldowns[(subject_id, alert_type)]["last_alert_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=31)
    )
    assert temporal_service.can_trigger_alert(subject_id, alert_type, cooldown_seconds=30.0) is True


def test_case_14_evidence_timeline_chronological_ordering():
    """Test 14: Evidence timeline preserves chronological ordering and metadata."""
    subject_id = "trk-cam-01-006"
    now = datetime.now(timezone.utc)

    # 1. Historical completed event
    temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=True)
    temporal_service._active_states[subject_id]["HEAD_TURN_LEFT"].started_at = now - timedelta(seconds=30)
    temporal_service.update_observation_state(subject_id, "HEAD_TURN_LEFT", is_active=False)

    # 2. Currently active observation
    temporal_service.update_observation_state(subject_id, "MOBILE_PHONE_DETECTED", is_active=True)
    temporal_service._active_states[subject_id]["MOBILE_PHONE_DETECTED"].started_at = now - timedelta(seconds=10)

    timeline = temporal_service.get_evidence_timeline(subject_id)
    assert len(timeline) >= 2
    # Verify chronological ordering
    assert timeline[0]["event_type"] == "HEAD_TURN_LEFT"
    assert timeline[0]["is_active"] is False
    assert timeline[1]["event_type"] == "MOBILE_PHONE_DETECTED"
    assert timeline[1]["is_active"] is True


@pytest.mark.asyncio
async def test_case_15_score_explanation_transparency():
    """Test 15: Score result contains completely transparent contributing factors and no cheating claims."""
    ev_phone = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="MOBILE_PHONE_DETECTED",
        confidence=0.90,
        duration_seconds=12.0
    )
    ev_away = await behaviour_service.create_behaviour_event(
        exam_session_id="sess-01",
        camera_id="cam-01",
        behaviour_type="LOOKING_AWAY",
        confidence=0.80,
        duration_seconds=11.0
    )
    suspicion = suspicion_service.calculate_suspicion([ev_phone, ev_away])
    
    assert suspicion.score > 0
    assert len(suspicion.contributing_factors) == 2
    for factor in suspicion.contributing_factors:
        assert "base_weight" in factor
        assert "duration_bonus" in factor
        assert "total_weight" in factor
        assert "contribution" in factor
        assert factor["contribution"] > 0

    # Strict compliance: Output must never declare definitive cheating
    score_str = str(suspicion.model_dump()).lower()
    assert "cheating" not in score_str
    assert "fraud" not in score_str


# ==============================================================================
# PERFORMANCE BENCHMARK TESTS
# ==============================================================================

def test_head_pose_performance_benchmark():
    """Empirical latency measurement of solvePnP head pose estimation on CPU."""
    landmarks = [
        (280.0, 200.0), (360.0, 200.0), (320.0, 250.0),
        (290.0, 310.0), (350.0, 310.0)
    ]
    # Warmup
    for _ in range(10):
        head_pose_service.estimate_pose_from_landmarks(landmarks, 640, 480)

    start = time.perf_counter()
    iterations = 200
    for _ in range(iterations):
        head_pose_service.estimate_pose_from_landmarks(landmarks, 640, 480)
    elapsed = time.perf_counter() - start

    avg_latency_ms = (elapsed / iterations) * 1000.0
    print(f"\n[BENCHMARK] Head Pose solvePnP latency: {avg_latency_ms:.3f} ms / face")
    # Must be under 2.0 ms on CPU
    assert avg_latency_ms < 2.0
