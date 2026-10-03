from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.models.responses import BehaviourEvent, SuspicionScoreResult
from backend.app.core.config import settings
from backend.app.core.logging import logger

EVENT_WEIGHTS = {
    "MOBILE_PHONE_DETECTED": 45,
    "UNKNOWN_PERSON": 50,
    "MULTIPLE_PERSONS": 40,
    "UNAUTHORIZED_MATERIAL": 35,
    "DESK_PEEKING": 25,
    "PERSON_INTERACTION": 25,
    "PROLONGED_SIDEWAYS_GAZE": 20,
    "SUSPICIOUS_MOVEMENT_PATTERN": 20,
    "REPEATED_HEAD_TURNS": 15,
    "REPEATED_HEAD_TURN": 15,
    "HEAD_TURN": 15,
    "LOOKING_AWAY": 10,
    "POSSIBLE_TALKING": 10,
    "FACE_NOT_VISIBLE": 10,
    "SIDEWAYS_GAZE": 5,
    "HEAD_TURN_LEFT": 5,
    "HEAD_TURN_RIGHT": 5,
    "LOOKING_DOWN": 5,
    "PERSON_DETECTED": 0,
}


class SuspicionEngineService:
    """
    Temporal Algorithmic Suspicion Scoring Engine.
    Calculates explainable statistical anomaly indices from a stream of observable events.
    
    PRESERVES STRICT DISTINCTION:
    An observed event is factual (e.g. mobile detected on desk for 12 seconds).
    A suspicion score is an advisory ranking for invigilators, NOT proof of intent.
    Provides complete transparency into contributing factors and evidence timeline.
    """

    def calculate_suspicion(
        self,
        events: List[BehaviourEvent],
        timeline: Optional[List[Dict[str, Any]]] = None
    ) -> SuspicionScoreResult:
        if not events:
            return SuspicionScoreResult(
                score=0,
                severity="LOW",
                contributing_events=[],
                contributing_factors=[],
                evidence_timeline=timeline or [],
                recommended_action="NONE",
                requires_alert=False
            )

        raw_score = 0
        contributing_strings: List[str] = []
        contributing_factors: List[Dict[str, Any]] = []

        # Deduplication tracking to prevent double-counting across the same frame
        seen_types = set()

        for ev in events:
            # Prevent double-counting the identical infraction type within the same evaluation frame
            if ev.behaviour_type in seen_types and ev.behaviour_type != "PERSON_DETECTED":
                continue
            seen_types.add(ev.behaviour_type)

            base_weight = EVENT_WEIGHTS.get(ev.behaviour_type, 10)
            
            # Duration-based escalation bonus
            duration_bonus = 0
            dur_sec = ev.duration_seconds or 0.0

            if ev.behaviour_type == "MOBILE_PHONE_DETECTED" and dur_sec >= settings.PHONE_PERSISTENCE_THRESHOLD:
                # Persistent phone on desk adds escalation weight
                duration_bonus = min(20, int(dur_sec * 0.8))
            elif ev.behaviour_type == "FACE_NOT_VISIBLE" and dur_sec >= 20.0:
                # Extended candidate absence from frame
                duration_bonus = 15
            elif ev.behaviour_type in ["LOOKING_AWAY", "SIDEWAYS_GAZE"] and dur_sec >= 10.0:
                duration_bonus = 10
            elif ev.behaviour_type == "PROLONGED_SIDEWAYS_GAZE" and dur_sec >= 8.0:
                duration_bonus = 10
            elif ev.behaviour_type == "PERSON_INTERACTION" and dur_sec >= 6.0:
                duration_bonus = 10
            elif ev.behaviour_type == "DESK_PEEKING" and dur_sec >= 5.0:
                duration_bonus = 10

            total_weight = base_weight + duration_bonus
            contribution = int(total_weight * ev.confidence)
            raw_score += contribution

            contributing_strings.append(f"{ev.behaviour_type} (conf={ev.confidence:.2f})")
            contributing_factors.append({
                "type": ev.behaviour_type,
                "base_weight": base_weight,
                "duration_bonus": duration_bonus,
                "total_weight": total_weight,
                "confidence": round(ev.confidence, 2),
                "duration_seconds": round(dur_sec, 2) if dur_sec else None,
                "contribution": contribution
            })

        capped_score = min(raw_score, 100)

        # Configurable Escalation Hierarchy
        if capped_score >= 85:
            severity = "CRITICAL"
            recommended_action = "TRIGGER_IOT_ALARM"
        elif capped_score >= 70:
            severity = "HIGH"
            recommended_action = "REVIEW_EVIDENCE"
        elif capped_score >= 40:
            severity = "MEDIUM"
            recommended_action = "MONITOR"
        else:
            severity = "LOW"
            recommended_action = "NONE"

        requires_alert = capped_score >= settings.SUSPICION_ALERT_THRESHOLD

        logger.info(
            f"Suspicion score calculated: {capped_score}/100, severity={severity}, "
            f"requires_alert={requires_alert}"
        )

        return SuspicionScoreResult(
            score=capped_score,
            severity=severity,
            contributing_events=contributing_strings,
            contributing_factors=contributing_factors,
            evidence_timeline=timeline or [],
            recommended_action=recommended_action,
            requires_alert=requires_alert
        )


suspicion_service = SuspicionEngineService()
