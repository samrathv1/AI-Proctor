import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import numpy as np

from backend.app.services.video_source import FramePacket
from backend.app.services.recognition_service import recognition_service
from backend.app.services.detection_service import detection_service
from backend.app.services.tracking_service import tracking_service
from backend.app.services.behaviour_service import behaviour_service
from backend.app.services.suspicion_service import suspicion_service
from backend.app.services.temporal_service import temporal_service
from backend.app.services.alert_service import alert_service
from backend.app.models.requests import AlertCreateRequest
from backend.app.core.config import settings
from backend.app.core.logging import logger


class CommonFramePipelineService:
    """
    Centralized Common AI Surveillance Frame Pipeline.
    
    ARCHITECTURAL MANDATE:
    All three video ingestion modalities (Laptop Webcam, IP/CCTV RTSP, Recorded Examination Video)
    must feed into this SAME processing pipeline.
    
    NO SEPARATE AI IMPLEMENTATIONS ARE PERMITTED PER SOURCE.
    """

    async def process_frame(
        self,
        frame_packet: FramePacket,
        exam_session_id: str,
        exam_id: str
    ) -> Dict[str, Any]:
        t_start = time.perf_counter()
        camera_id = frame_packet.source_id
        img = frame_packet.frame

        # 1. Face Pipeline: Real Face Detection, 5-point alignment, SFace extraction,
        #    exam cache matching, spatial tracking, and head-pose estimation
        recog_result = await recognition_service.recognize_frame_faces(
            frame_data=img,
            exam_id=exam_id,
            camera_id=camera_id,
            exam_session_id=exam_session_id
        )

        recognized_faces = recog_result.get("recognized_faces", [])
        active_tracks = recog_result.get("active_tracks", [])

        # 2. Object Pipeline: Real YOLOv8 Object Detection (Phones, Laptops, Books)
        detection_result = await detection_service.detect_frame(
            frame_data=img,
            camera_id=camera_id,
            exam_session_id=exam_session_id
        )

        # 3. Track Correlation: Correlate Detected Objects with Active Student Tracks
        internal_tracks = tracking_service.get_active_tracks(camera_id)
        correlated_detections = detection_service.correlate_objects_with_tracks(
            detections=detection_result.detections,
            active_tracks=internal_tracks,
            camera_id=camera_id
        )

        # 4. Extract Observable Behaviour Events (Objective Physical Observations Only)
        observable_events = []

        # A) Multi-person presence tracking over time
        camera_subject = f"camera-{camera_id}"
        if len(recognized_faces) > 1:
            is_cont, dur = temporal_service.update_observation_state(
                subject_id=camera_subject,
                event_type="MULTIPLE_PERSONS",
                is_active=True,
                confidence=0.95,
                metadata={"faces_count": len(recognized_faces)}
            )
            ev_multi = await behaviour_service.create_behaviour_event(
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                behaviour_type="MULTIPLE_PERSONS",
                confidence=0.95,
                duration_seconds=dur,
                is_continuous=is_cont,
                metadata={"faces_count": len(recognized_faces), "duration_seconds": round(dur, 2)}
            )
            observable_events.append(ev_multi)
        else:
            temporal_service.update_observation_state(
                subject_id=camera_subject,
                event_type="MULTIPLE_PERSONS",
                is_active=False
            )

        # B) Head Pose Movements, Looking Away & Identity Analysis
        for face in recognized_faces:
            tracking_id = face["tracking_id"]
            head_pose = face.get("head_pose")

            # Head-Pose Temporal Analysis
            if head_pose:
                posture = head_pose.get("posture", "FRONTAL")
                is_looking_away = head_pose.get("is_looking_away", False)
                hp_conf = head_pose.get("confidence", 0.9)

                if posture in ["HEAD_TURN_LEFT", "HEAD_TURN_RIGHT", "LOOKING_DOWN", "LOOKING_UP"]:
                    is_cont, dur = temporal_service.update_observation_state(
                        subject_id=tracking_id,
                        event_type=posture,
                        is_active=True,
                        confidence=hp_conf,
                        metadata={"student_id": face.get("student_id"), "head_pose": head_pose}
                    )
                    ev_hp = await behaviour_service.create_behaviour_event(
                        exam_session_id=exam_session_id,
                        camera_id=camera_id,
                        student_id=face.get("student_id"),
                        tracking_id=tracking_id,
                        behaviour_type=posture,
                        confidence=hp_conf,
                        duration_seconds=dur,
                        is_continuous=is_cont,
                        metadata={"head_pose": head_pose, "duration_seconds": round(dur, 2)}
                    )
                    observable_events.append(ev_hp)
                else:
                    # Returned to FRONTAL; close any active turn observations
                    for turn_type in ["HEAD_TURN_LEFT", "HEAD_TURN_RIGHT", "LOOKING_DOWN", "LOOKING_UP"]:
                        temporal_service.update_observation_state(
                            subject_id=tracking_id,
                            event_type=turn_type,
                            is_active=False
                        )

                # Sideways gaze tracking
                if head_pose.get("is_sideways_gaze", False):
                    is_cont, dur = temporal_service.update_observation_state(
                        subject_id=tracking_id,
                        event_type="SIDEWAYS_GAZE",
                        is_active=True,
                        confidence=hp_conf,
                        metadata={
                            "gaze_direction": head_pose.get("gaze_direction", "CENTER"),
                            "student_id": face.get("student_id")
                        }
                    )
                    ev_sg = await behaviour_service.create_behaviour_event(
                        exam_session_id=exam_session_id,
                        camera_id=camera_id,
                        student_id=face.get("student_id"),
                        tracking_id=tracking_id,
                        behaviour_type="SIDEWAYS_GAZE",
                        confidence=hp_conf,
                        duration_seconds=dur,
                        is_continuous=is_cont,
                        metadata={
                            "gaze_direction": head_pose.get("gaze_direction", "CENTER"),
                            "duration_seconds": round(dur, 2)
                        }
                    )
                    observable_events.append(ev_sg)
                else:
                    temporal_service.update_observation_state(
                        subject_id=tracking_id,
                        event_type="SIDEWAYS_GAZE",
                        is_active=False
                    )

                # Looking away continuous duration tracking
                temporal_service.update_observation_state(
                    subject_id=tracking_id,
                    event_type="LOOKING_AWAY",
                    is_active=is_looking_away,
                    confidence=hp_conf
                )

            # Identity Observation
            if face["identity_status"] == "UNKNOWN":
                ev_unk = await behaviour_service.create_behaviour_event(
                    exam_session_id=exam_session_id,
                    camera_id=camera_id,
                    behaviour_type="UNKNOWN_PERSON",
                    confidence=round(1.0 - face["similarity"], 2),
                    tracking_id=face["tracking_id"]
                )
                observable_events.append(ev_unk)
            elif face["identity_status"] == "IDENTIFIED":
                ev_ident = await behaviour_service.create_behaviour_event(
                    exam_session_id=exam_session_id,
                    camera_id=camera_id,
                    student_id=face["student_id"],
                    behaviour_type="PERSON_DETECTED",
                    confidence=face["similarity"],
                    tracking_id=face["tracking_id"]
                )
                observable_events.append(ev_ident)

        # C) Face Absence Tracking (Distinguish momentary glance from extended absence)
        for track in internal_tracks:
            if track.status == "TEMPORARILY_NOT_VISIBLE":
                is_cont, dur = temporal_service.update_observation_state(
                    subject_id=track.tracking_id,
                    event_type="FACE_NOT_VISIBLE",
                    is_active=True,
                    confidence=0.85,
                    metadata={"student_id": track.student_id}
                )
                if dur >= settings.FACE_ABSENCE_DURATION_THRESHOLD:
                    ev_absent = await behaviour_service.create_behaviour_event(
                        exam_session_id=exam_session_id,
                        camera_id=camera_id,
                        student_id=track.student_id,
                        tracking_id=track.tracking_id,
                        behaviour_type="FACE_NOT_VISIBLE",
                        confidence=0.85,
                        duration_seconds=dur,
                        is_continuous=is_cont,
                        metadata={"absence_duration_seconds": round(dur, 2)}
                    )
                    observable_events.append(ev_absent)
            else:
                temporal_service.update_observation_state(
                    subject_id=track.tracking_id,
                    event_type="FACE_NOT_VISIBLE",
                    is_active=False
                )

        # D) Observable Object Events with Continuous Duration Tracking
        for det in correlated_detections:
            subject_key = det.metadata.get("correlated_tracking_id") or camera_subject
            if det.detection_type == "MOBILE_PHONE":
                is_cont, dur = temporal_service.update_observation_state(
                    subject_id=subject_key,
                    event_type="MOBILE_PHONE_DETECTED",
                    is_active=True,
                    confidence=det.confidence,
                    metadata={"correlated_student_id": det.metadata.get("correlated_student_id")}
                )
                ev_phone = await behaviour_service.create_behaviour_event(
                    exam_session_id=exam_session_id,
                    camera_id=camera_id,
                    student_id=det.metadata.get("correlated_student_id"),
                    tracking_id=det.metadata.get("correlated_tracking_id"),
                    behaviour_type="MOBILE_PHONE_DETECTED",
                    confidence=det.confidence,
                    duration_seconds=dur,
                    is_continuous=is_cont,
                    metadata={
                        "bounding_box": det.bounding_box.model_dump(),
                        "spatial_relation": det.metadata.get("spatial_relation", "UNKNOWN"),
                        "correlated_student_name": det.metadata.get("correlated_student_name"),
                        "duration_seconds": round(dur, 2)
                    }
                )
                observable_events.append(ev_phone)
            elif det.detection_type in ["LAPTOP", "UNAUTHORIZED_OBJECT"]:
                is_cont, dur = temporal_service.update_observation_state(
                    subject_id=subject_key,
                    event_type="UNAUTHORIZED_MATERIAL",
                    is_active=True,
                    confidence=det.confidence
                )
                ev_unauth = await behaviour_service.create_behaviour_event(
                    exam_session_id=exam_session_id,
                    camera_id=camera_id,
                    student_id=det.metadata.get("correlated_student_id"),
                    tracking_id=det.metadata.get("correlated_tracking_id"),
                    behaviour_type="UNAUTHORIZED_MATERIAL",
                    confidence=det.confidence,
                    duration_seconds=dur,
                    is_continuous=is_cont,
                    metadata={
                        "object_label": det.metadata.get("label", "unauthorized_object"),
                        "bounding_box": det.bounding_box.model_dump(),
                        "spatial_relation": det.metadata.get("spatial_relation", "UNKNOWN"),
                        "duration_seconds": round(dur, 2)
                    }
                )
                observable_events.append(ev_unauth)

        # E) Multi-Track Spatial Interactions (Person Interaction & Desk Peeking)
        all_tracks_dict = [t.model_dump() for t in active_tracks]
        if len(all_tracks_dict) >= 2:
            for i in range(len(all_tracks_dict)):
                track_i = all_tracks_dict[i]
                tid_i = track_i.get("tracking_id")
                # Desk peeking check
                is_peeking, target_tid, peek_reason = behaviour_service.evaluate_desk_peeking(
                    candidate_track=track_i,
                    other_tracks=all_tracks_dict,
                    camera_type=frame_packet.source_type or "WEBCAM"
                )
                if is_peeking and tid_i:
                    is_cont, dur = temporal_service.update_observation_state(
                        subject_id=tid_i,
                        event_type="DESK_PEEKING",
                        is_active=True,
                        confidence=0.85,
                        metadata={"target_track_id": target_tid}
                    )
                    if dur >= 1.0:
                        ev_peek = await behaviour_service.create_behaviour_event(
                            exam_session_id=exam_session_id,
                            camera_id=camera_id,
                            student_id=track_i.get("student_id"),
                            tracking_id=tid_i,
                            behaviour_type="DESK_PEEKING",
                            confidence=0.85,
                            duration_seconds=dur,
                            is_continuous=is_cont,
                            metadata={"target_track_id": target_tid, "duration_seconds": round(dur, 2)}
                        )
                        observable_events.append(ev_peek)
                elif tid_i:
                    temporal_service.update_observation_state(
                        subject_id=tid_i,
                        event_type="DESK_PEEKING",
                        is_active=False
                    )

                # Pairwise candidate interaction
                for j in range(i + 1, len(all_tracks_dict)):
                    track_j = all_tracks_dict[j]
                    tid_j = track_j.get("tracking_id")
                    if not tid_i or not tid_j:
                        continue
                    is_interact, norm_dist = behaviour_service.evaluate_person_interaction(track_i, track_j)
                    pair_key = f"{min(str(tid_i), str(tid_j))}_{max(str(tid_i), str(tid_j))}"
                    if is_interact:
                        is_cont, dur = temporal_service.update_observation_state(
                            subject_id=pair_key,
                            event_type="PERSON_INTERACTION",
                            is_active=True,
                            confidence=0.88,
                            metadata={"track_a": tid_i, "track_b": tid_j, "distance": norm_dist}
                        )
                        if dur >= 1.5:
                            ev_interact = await behaviour_service.create_behaviour_event(
                                exam_session_id=exam_session_id,
                                camera_id=camera_id,
                                student_id=track_i.get("student_id") or track_j.get("student_id"),
                                tracking_id=tid_i,
                                behaviour_type="PERSON_INTERACTION",
                                confidence=0.88,
                                duration_seconds=dur,
                                is_continuous=is_cont,
                                metadata={
                                    "interacting_with_track": tid_j,
                                    "interacting_with_student": track_j.get("student_id"),
                                    "normalized_distance": norm_dist,
                                    "duration_seconds": round(dur, 2)
                                }
                            )
                            observable_events.append(ev_interact)
                    else:
                        temporal_service.update_observation_state(
                            subject_id=pair_key,
                            event_type="PERSON_INTERACTION",
                            is_active=False
                        )

        # F) Temporal Aggregation Layer (Rolling Window & Frequency Analysis)
        for face in recognized_faces:
            agg_events = await behaviour_service.check_temporal_aggregations(
                subject_id=face["tracking_id"],
                exam_session_id=exam_session_id,
                camera_id=camera_id,
                student_id=face.get("student_id"),
                tracking_id=face["tracking_id"]
            )
            observable_events.extend(agg_events)

        # 5. Multi-Signal Evidence Timeline & Advisory Suspicion Score
        primary_subject = (
            recognized_faces[0]["tracking_id"]
            if recognized_faces
            else (internal_tracks[0].tracking_id if internal_tracks else camera_subject)
        )
        timeline = temporal_service.get_evidence_timeline(primary_subject)
        suspicion = suspicion_service.calculate_suspicion(observable_events, timeline=timeline)

        # 6. Cooldown-Protected Alert Dispatch (No Database Flooding)
        if suspicion.requires_alert and exam_session_id:
            top_factor = (
                suspicion.contributing_factors[0]["type"]
                if suspicion.contributing_factors
                else "SUSPICIOUS_BEHAVIOUR"
            )
            if temporal_service.can_trigger_alert(primary_subject, top_factor, cooldown_seconds=settings.ALERT_COOLDOWN_SECONDS):
                student_target = recognized_faces[0].get("student_id") if recognized_faces else None
                try:
                    alert_req = AlertCreateRequest(
                        exam_session_id=exam_session_id,
                        exam_id=exam_id,
                        student_id=student_target,
                        camera_id=camera_id,
                        alert_type=top_factor,
                        severity=suspicion.severity,
                        confidence=int((suspicion.contributing_factors[0].get("confidence", 0.85)) * 100) if suspicion.contributing_factors else 85,
                        suspicion_score=suspicion.score,
                        title=f"Advisory Observation: {top_factor.replace('_', ' ').title()}",
                        description=f"Automated advisory score {suspicion.score}/100. Factors: {', '.join(suspicion.contributing_events)}",
                        evidence_storage_path=None
                    )
                    alert_resp = await alert_service.create_alert(alert_req)
                    temporal_service.record_alert_dispatched(
                        subject_id=primary_subject,
                        alert_type=top_factor,
                        severity=suspicion.severity,
                        alert_id=alert_resp.id
                    )
                except Exception as e:
                    logger.warning(f"Temporal alert dispatch skipped or failed: {str(e)}")

        total_latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        return {
            "source_id": frame_packet.source_id,
            "source_type": frame_packet.source_type,
            "camera_id": camera_id,
            "exam_id": exam_id,
            "exam_session_id": exam_session_id,
            "timestamp": frame_packet.timestamp,
            "frame_number": frame_packet.frame_number,
            "resolution": frame_packet.resolution,
            "faces_detected_count": len(recognized_faces),
            "status": recog_result.get("status", "NO_FACE"),
            "detection_summary": {
                "faces_detected_count": len(recognized_faces),
                "objects_detected_count": len(correlated_detections),
                "status": recog_result.get("status", "NO_FACE")
            },
            "recognized_faces": recognized_faces,
            "detected_objects": [d.model_dump() for d in correlated_detections],
            "tracking": active_tracks,
            "active_tracks": active_tracks,
            "observable_behaviour": [ev.model_dump() for ev in observable_events],
            "observable_events": [ev.model_dump() for ev in observable_events],
            "suspicion_index": suspicion.model_dump(),
            "processing_time_ms": total_latency_ms,
            "metadata": frame_packet.metadata
        }


common_frame_pipeline = CommonFramePipelineService()
