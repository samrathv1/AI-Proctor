from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import deque

from backend.app.core.config import settings
from backend.app.core.logging import logger


class ActiveObservation:
    """Represents an active, continuous behavioral observation over time."""
    def __init__(self, event_type: str, confidence: float, metadata: Optional[Dict[str, Any]] = None):
        now = datetime.now(timezone.utc)
        self.event_type = event_type
        self.confidence = confidence
        self.started_at = now
        self.last_seen_at = now
        self.metadata = metadata or {}

    @property
    def duration_seconds(self) -> float:
        return (self.last_seen_at - self.started_at).total_seconds()

    def update(self, confidence: float, metadata: Optional[Dict[str, Any]] = None):
        self.last_seen_at = datetime.now(timezone.utc)
        self.confidence = max(self.confidence, confidence)
        if metadata:
            self.metadata.update(metadata)


class HistoricalEvent:
    """Archived behavioral observation in rolling time window."""
    def __init__(
        self,
        event_type: str,
        confidence: float,
        started_at: datetime,
        ended_at: datetime,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.event_type = event_type
        self.confidence = confidence
        self.started_at = started_at
        self.ended_at = ended_at
        self.duration_seconds = duration_seconds
        self.metadata = metadata or {}


class TemporalBehaviourService:
    """
    Temporal Behavioral Aggregation, Frequency Analysis, and Multi-Signal Fusion Engine.
    
    CRITICAL ARCHITECTURAL SAFEGUARDS:
    1. Duration Tracking: Distinguishes momentary glances from persistent infractions.
    2. Double Counting Prevention: Continuous events have duration; they are NOT multiplied frame-by-frame.
    3. Alert Cooldown: Prevents database and realtime flooding for ongoing infractions.
    4. Explainable Evidence Timeline: Preserves ordered chronological proof for invigilator review.
    """

    def __init__(self):
        # subject_id -> { event_type -> ActiveObservation }
        self._active_states: Dict[str, Dict[str, ActiveObservation]] = {}
        # subject_id -> deque[HistoricalEvent]
        self._event_history: Dict[str, deque] = {}
        # (subject_id, alert_type) -> { "last_alert_at": datetime, "severity": str, "alert_id": str }
        self._alert_cooldowns: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def update_observation_state(
        self,
        subject_id: str,
        event_type: str,
        is_active: bool,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float]:
        """
        Updates ongoing observation state for a candidate track/student.
        Returns:
            (is_continuous: bool, duration_seconds: float)
        """
        if subject_id not in self._active_states:
            self._active_states[subject_id] = {}
        if subject_id not in self._event_history:
            self._event_history[subject_id] = deque(maxlen=200)

        subject_active = self._active_states[subject_id]
        now = datetime.now(timezone.utc)

        if is_active:
            if event_type in subject_active:
                obs = subject_active[event_type]
                obs.update(confidence, metadata)
                return True, obs.duration_seconds
            else:
                # Fresh observation starts
                obs = ActiveObservation(event_type, confidence, metadata)
                subject_active[event_type] = obs
                logger.debug(f"TEMPORAL: Started observation '{event_type}' for {subject_id}")
                return False, 0.0
        else:
            # Observation concluded
            if event_type in subject_active:
                obs = subject_active.pop(event_type)
                hist = HistoricalEvent(
                    event_type=obs.event_type,
                    confidence=obs.confidence,
                    started_at=obs.started_at,
                    ended_at=now,
                    duration_seconds=obs.duration_seconds,
                    metadata=obs.metadata
                )
                self._event_history[subject_id].append(hist)
                logger.debug(
                    f"TEMPORAL: Concluded '{event_type}' for {subject_id} (duration={obs.duration_seconds:.2f}s)"
                )
                return False, obs.duration_seconds
            return False, 0.0

    def get_active_duration(self, subject_id: str, event_type: str) -> float:
        """Returns the current continuous duration in seconds of an active observation."""
        obs = self._active_states.get(subject_id, {}).get(event_type)
        if obs:
            return obs.duration_seconds
        return 0.0

    def get_event_frequency_in_window(
        self,
        subject_id: str,
        event_type: str,
        window_seconds: float = 60.0
    ) -> int:
        """
        Counts occurrences of an event type within a rolling time window.
        Includes both archived completed events and active continuous observations.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)
        count = 0

        # Check historical archive
        history = self._event_history.get(subject_id, deque())
        for ev in history:
            if ev.event_type == event_type and ev.ended_at >= cutoff:
                count += 1

        # Check active state
        if event_type in self._active_states.get(subject_id, {}):
            count += 1

        return count

    def can_trigger_alert(
        self,
        subject_id: str,
        alert_type: str,
        cooldown_seconds: float = 30.0
    ) -> bool:
        """
        Checks whether an alert cooldown window has passed to prevent duplicate spam.
        """
        key = (subject_id, alert_type)
        record = self._alert_cooldowns.get(key)
        if not record:
            return True

        elapsed = (datetime.now(timezone.utc) - record["last_alert_at"]).total_seconds()
        return elapsed >= cooldown_seconds

    def record_alert_dispatched(
        self,
        subject_id: str,
        alert_type: str,
        severity: str,
        alert_id: Optional[str] = None
    ):
        """Records an alert dispatch timestamp for cooldown tracking."""
        key = (subject_id, alert_type)
        self._alert_cooldowns[key] = {
            "last_alert_at": datetime.now(timezone.utc),
            "severity": severity,
            "alert_id": alert_id
        }

    def get_evidence_timeline(self, subject_id: str, max_items: int = 15) -> List[Dict[str, Any]]:
        """
        Assembles an ordered, chronological evidence timeline for invigilator review.
        """
        timeline: List[Dict[str, Any]] = []

        # 1. Historical completed events
        history = self._event_history.get(subject_id, deque())
        for ev in history:
            timeline.append({
                "event_type": ev.event_type,
                "timestamp": ev.started_at.isoformat(),
                "duration_seconds": round(ev.duration_seconds, 2),
                "confidence": round(ev.confidence, 2),
                "is_active": False,
                "metadata": ev.metadata
            })

        # 2. Currently active observations
        active_map = self._active_states.get(subject_id, {})
        for ev_type, obs in active_map.items():
            timeline.append({
                "event_type": obs.event_type,
                "timestamp": obs.started_at.isoformat(),
                "duration_seconds": round(obs.duration_seconds, 2),
                "confidence": round(obs.confidence, 2),
                "is_active": True,
                "metadata": obs.metadata
            })

        # Sort chronologically by timestamp
        timeline.sort(key=lambda x: x["timestamp"])
        return timeline[-max_items:]

    def clear(self):
        """Clears all in-memory states (used in test teardown)."""
        self._active_states.clear()
        self._event_history.clear()
        self._alert_cooldowns.clear()


temporal_service = TemporalBehaviourService()
