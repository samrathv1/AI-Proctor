from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from backend.app.models.responses import BehaviourEvent
from backend.app.services.temporal_service import temporal_service
from backend.app.core.config import settings
from backend.app.core.logging import logger


class BehaviourService:
    """
    Candidate observable behaviour event analyzer with temporal duration integration.
    CRITICAL ARCHITECTURAL PRINCIPLE:
    This service records OBSERVABLE physical movements and detections.
    It does NOT make subjective or legal claims about candidate intent (i.e. 'cheating').
    """

    async def create_behaviour_event(
        self,
        exam_session_id: str,
        camera_id: str,
        behaviour_type: str,
        confidence: float,
        student_id: Optional[str] = None,
        tracking_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        is_continuous: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BehaviourEvent:
        """
        Creates and registers an observable behavioral event.
        """
        subject_key = student_id or tracking_id or f"anon-{camera_id}"
        meta = dict(metadata or {})

        # If duration_seconds is provided or resolved from temporal service
        active_dur = duration_seconds
        if active_dur is None and subject_key:
            active_dur = temporal_service.get_active_duration(subject_key, behaviour_type)

        dur_ms = duration_ms if duration_ms is not None else (int(active_dur * 1000) if active_dur else None)

        event = BehaviourEvent(
            event_id=f"beh-{uuid.uuid4().hex[:8]}",
            exam_session_id=exam_session_id,
            camera_id=camera_id,
            student_id=student_id,
            tracking_id=tracking_id,
            behaviour_type=behaviour_type,
            confidence=round(confidence, 4),
            timestamp=datetime.now(timezone.utc),
            duration_ms=dur_ms,
            duration_seconds=round(active_dur, 2) if active_dur is not None else None,
            is_continuous=is_continuous,
            metadata=meta
        )

        logger.info(
            f"Observable event recorded: {behaviour_type} (conf={confidence:.2f}, dur={active_dur or 0:.1f}s) "
            f"for {subject_key} in session {exam_session_id}, camera {camera_id}"
        )

        try:
            from backend.app.integrations.supabase import supabase_db
            await supabase_db.save_behaviour_event({
                "id": event.event_id,
                "exam_session_id": exam_session_id,
                "camera_id": camera_id,
                "student_id": student_id,
                "tracking_id": tracking_id,
                "behaviour_type": behaviour_type,
                "confidence": confidence,
                "duration_ms": dur_ms,
                "metadata": meta,
                "timestamp": event.timestamp.isoformat()
            })
        except Exception as e:
            logger.debug(f"Failed to persist behaviour event: {e}")

        return event

    async def check_temporal_aggregations(
        self,
        subject_id: str,
        exam_session_id: str,
        camera_id: str,
        student_id: Optional[str] = None,
        tracking_id: Optional[str] = None
    ) -> List[BehaviourEvent]:
        """
        Evaluates temporal rolling-window frequency and duration escalation rules.
        Generates aggregated events (e.g. REPEATED_HEAD_TURNS) when thresholds are crossed.
        """
        aggregated_events: List[BehaviourEvent] = []

        # 1. Frequency of Head Turns in Rolling Window
        left_turns = temporal_service.get_event_frequency_in_window(
            subject_id, "HEAD_TURN_LEFT", settings.BEHAVIOUR_WINDOW_SECONDS
        )
        right_turns = temporal_service.get_event_frequency_in_window(
            subject_id, "HEAD_TURN_RIGHT", settings.BEHAVIOUR_WINDOW_SECONDS
        )
        total_head_turns = left_turns + right_turns

        if total_head_turns >= settings.HEAD_TURN_REPEAT_THRESHOLD:
            ev_repeat = await self.create_behaviour_event(
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                student_id=student_id,
                tracking_id=tracking_id,
                behaviour_type="REPEATED_HEAD_TURN",
                confidence=min(1.0, 0.70 + (total_head_turns * 0.05)),
                metadata={
                    "count_in_window": total_head_turns,
                    "window_seconds": settings.BEHAVIOUR_WINDOW_SECONDS,
                    "left_turns": left_turns,
                    "right_turns": right_turns
                }
            )
            aggregated_events.append(ev_repeat)

            # Rapid alternating movement pattern detection (oscillating back and forth)
            if left_turns >= 2 and right_turns >= 2 and total_head_turns >= 4:
                ev_pattern = await self.create_behaviour_event(
                    exam_session_id=exam_session_id,
                    camera_id=camera_id,
                    student_id=student_id,
                    tracking_id=tracking_id,
                    behaviour_type="SUSPICIOUS_MOVEMENT_PATTERN",
                    confidence=min(1.0, 0.75 + (total_head_turns * 0.04)),
                    metadata={
                        "pattern_type": "ALTERNATING_HEAD_TURNS",
                        "oscillations_count": total_head_turns,
                        "window_seconds": settings.BEHAVIOUR_WINDOW_SECONDS,
                        "description": "Cyclic repetitive lateral head movements between neighboring areas"
                    }
                )
                aggregated_events.append(ev_pattern)

        # 2. Sideways Gaze & Prolonged Sideways Gaze
        sideways_dur = temporal_service.get_active_duration(subject_id, "SIDEWAYS_GAZE")
        sideways_freq = temporal_service.get_event_frequency_in_window(
            subject_id, "SIDEWAYS_GAZE", settings.BEHAVIOUR_WINDOW_SECONDS
        )
        if sideways_dur >= 4.0 or sideways_freq >= 3:
            ev_prolonged_gaze = await self.create_behaviour_event(
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                student_id=student_id,
                tracking_id=tracking_id,
                behaviour_type="PROLONGED_SIDEWAYS_GAZE",
                confidence=min(1.0, 0.75 + (max(sideways_dur, float(sideways_freq)) * 0.03)),
                duration_seconds=sideways_dur if sideways_dur > 0 else float(sideways_freq),
                is_continuous=sideways_dur >= 4.0,
                metadata={
                    "continuous_duration_seconds": round(sideways_dur, 2),
                    "occurrences_in_window": sideways_freq,
                    "window_seconds": settings.BEHAVIOUR_WINDOW_SECONDS
                }
            )
            aggregated_events.append(ev_prolonged_gaze)

        # 3. Persistent Looking Away
        looking_away_dur = temporal_service.get_active_duration(subject_id, "LOOKING_AWAY")
        if looking_away_dur >= settings.LOOKING_AWAY_DURATION_THRESHOLD:
            ev_away = await self.create_behaviour_event(
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                student_id=student_id,
                tracking_id=tracking_id,
                behaviour_type="LOOKING_AWAY",
                confidence=min(1.0, 0.75 + (looking_away_dur * 0.02)),
                duration_seconds=looking_away_dur,
                is_continuous=True,
                metadata={"continuous_duration_seconds": round(looking_away_dur, 2)}
            )
            aggregated_events.append(ev_away)

        # 4. Persistent Face Absence
        absence_dur = temporal_service.get_active_duration(subject_id, "FACE_NOT_VISIBLE")
        if absence_dur >= settings.FACE_ABSENCE_DURATION_THRESHOLD:
            ev_absent = await self.create_behaviour_event(
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                student_id=student_id,
                tracking_id=tracking_id,
                behaviour_type="FACE_NOT_VISIBLE",
                confidence=min(1.0, 0.80 + (absence_dur * 0.01)),
                duration_seconds=absence_dur,
                is_continuous=True,
                metadata={"continuous_duration_seconds": round(absence_dur, 2)}
            )
            aggregated_events.append(ev_absent)

        return aggregated_events

    def evaluate_desk_peeking(
        self,
        candidate_track: Dict[str, Any],
        other_tracks: List[Dict[str, Any]],
        camera_type: str = "WEBCAM"
    ) -> Tuple[bool, Optional[str], str]:
        """
        Evaluates potential desk peeking / leaning toward another student's desk.
        Uses person/face bounding boxes and lateral proximity.
        
        SAFETY SAFEGUARD:
        If camera geometry does not support spatial desk coverage (e.g. single-student laptop webcam),
        DOES NOT invent detections. Strictly returns:
        'NOT RELIABLY DETECTABLE WITH CURRENT CAMERA INPUT'.
        """
        if camera_type == "WEBCAM" and len(other_tracks) == 0:
            return False, None, "NOT RELIABLY DETECTABLE WITH CURRENT CAMERA INPUT"

        if not other_tracks:
            return False, None, "NO_ADJACENT_CANDIDATES"

        cand_box = candidate_track.get("bounding_box")
        if not cand_box:
            return False, None, "MISSING_BOUNDING_BOX"

        cx = cand_box.get("x", 0) + (cand_box.get("width", 0) / 2.0)
        cw = cand_box.get("width", 100)

        # Check proximity and lateral shift toward any other track
        for other in other_tracks:
            if other.get("tracking_id") == candidate_track.get("tracking_id"):
                continue
            obox = other.get("bounding_box")
            if not obox:
                continue

            ox = obox.get("x", 0) + (obox.get("width", 0) / 2.0)
            lateral_dist = abs(cx - ox)

            # If lateral distance is unusually close (< 1.4 * width) with candidate turned toward other
            if lateral_dist < 1.4 * cw:
                return True, other.get("tracking_id"), "DESK_PEEKING"

        return False, None, "NORMAL_DESK_BOUNDS"

    def evaluate_person_interaction(
        self,
        track_a: Dict[str, Any],
        track_b: Dict[str, Any]
    ) -> Tuple[bool, float]:
        """
        Evaluates persistent close interaction between two tracked candidates.
        Returns: (is_interacting: bool, center_distance_normalized: float)
        """
        box_a = track_a.get("bounding_box")
        box_b = track_b.get("bounding_box")
        if not box_a or not box_b:
            return False, 999.0

        cax = box_a.get("x", 0) + (box_a.get("width", 0) / 2.0)
        cay = box_a.get("y", 0) + (box_a.get("height", 0) / 2.0)
        cbx = box_b.get("x", 0) + (box_b.get("width", 0) / 2.0)
        cby = box_b.get("y", 0) + (box_b.get("height", 0) / 2.0)

        dist = ((cax - cbx) ** 2 + (cay - cby) ** 2) ** 0.5
        avg_w = (box_a.get("width", 100) + box_b.get("width", 100)) / 2.0
        normalized_dist = dist / max(avg_w, 1.0)

        # Close physical interaction zone (< 1.35 normalized width)
        is_interacting = normalized_dist < 1.35
        return is_interacting, round(normalized_dist, 2)


behaviour_service = BehaviourService()
