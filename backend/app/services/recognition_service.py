import time
from typing import Optional, Any, Dict, List, Tuple
from datetime import datetime, timezone
import numpy as np

from backend.app.models.responses import FaceRecognitionResult, BoundingBox
from backend.app.services.face_engine import face_engine
from backend.app.services.biometric_cache import biometric_cache_manager
from backend.app.services.tracking_service import tracking_service
from backend.app.services.head_pose_service import head_pose_service
from backend.app.integrations.supabase import supabase_db
from backend.app.core.config import settings
from backend.app.core.logging import logger


class RecognizedFaceDetails:
    def __init__(
        self,
        face_index: int,
        tracking_id: str,
        bbox: BoundingBox,
        confidence: float,
        similarity: float,
        identity_status: str,
        student_id: Optional[str] = None,
        student_name: Optional[str] = None,
        student_roll: Optional[str] = None,
        head_pose: Optional[Dict[str, Any]] = None
    ):
        self.face_index = face_index
        self.tracking_id = tracking_id
        self.bbox = bbox
        self.confidence = confidence
        self.similarity = similarity
        self.identity_status = identity_status  # IDENTIFIED | UNCERTAIN | UNKNOWN
        self.student_id = student_id
        self.student_name = student_name
        self.student_roll = student_roll
        self.head_pose = head_pose

    def to_dict(self) -> Dict[str, Any]:
        return {
            "face_index": self.face_index,
            "tracking_id": self.tracking_id,
            "bounding_box": {
                "x": self.bbox.x,
                "y": self.bbox.y,
                "width": self.bbox.width,
                "height": self.bbox.height
            },
            "detection_confidence": round(self.confidence, 4),
            "similarity": round(self.similarity, 4),
            "identity_status": self.identity_status,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "student_roll": self.student_roll,
            "head_pose": self.head_pose
        }


class FaceRecognitionService:
    """
    Real-Time Face Recognition & Student Identity Matching Service.
    Compares detected camera faces strictly against the active examination's
    biometric cache, integrating tracking and identity state transitions.
    """

    def __init__(self):
        # Track persistent meaningful events to avoid database flooding
        self._persisted_identities: Dict[str, str] = {}  # tracking_id -> last_persisted_status

    async def recognize_face(
        self,
        frame_data: Optional[Any],
        exam_id: str,
        expected_student_id: Optional[str] = None,
        camera_id: str = "cam-01"
    ) -> FaceRecognitionResult:
        """
        Single-face contract matching method.
        """
        multi_result = await self.recognize_frame_faces(
            frame_data=frame_data,
            exam_id=exam_id,
            camera_id=camera_id
        )

        faces = multi_result.get("recognized_faces", [])
        if len(faces) == 0:
            return FaceRecognitionResult(
                status="NO_FACE",
                student_id=None,
                confidence=0.0,
                bounding_box=None
            )
        elif len(faces) > 1:
            first = faces[0]
            return FaceRecognitionResult(
                status="MULTIPLE_FACES",
                student_id=first.get("student_id"),
                confidence=first.get("similarity", 0.0),
                bounding_box=BoundingBox(**first["bounding_box"])
            )

        target = faces[0]
        return FaceRecognitionResult(
            status=target["identity_status"],
            student_id=target.get("student_id"),
            confidence=target.get("similarity", 0.0),
            bounding_box=BoundingBox(**target["bounding_box"])
        )

    async def recognize_frame_faces(
        self,
        frame_data: Optional[Any],
        exam_id: str,
        camera_id: str = "cam-01",
        exam_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified Multi-Person Live Frame Face Recognition Pipeline:
        1. Decode frame
        2. Detect all faces via YuNet
        3. Match every detected face independently against exam cache
        4. Associate with tracking service tracklets
        5. Filter & persist meaningful events (no frame-by-frame spam)
        """
        t0 = time.perf_counter()
        session_id = exam_session_id or f"ses-{exam_id}"

        if frame_data is None or (isinstance(frame_data, (str, list, bytes)) and len(frame_data) == 0):
            return {
                "status": "NO_FACE",
                "faces_detected_count": 0,
                "recognized_faces": [],
                "active_tracks": []
            }

        # 1. Decode Frame
        try:
            img = face_engine.decode_image(frame_data)
        except Exception as e:
            logger.warning(f"Frame decode error: {str(e)}")
            return {
                "status": "NO_FACE",
                "faces_detected_count": 0,
                "recognized_faces": [],
                "active_tracks": []
            }

        h_img, w_img = img.shape[:2]

        # 2. Detect Faces
        detections = face_engine.detect_faces(img)
        if len(detections) == 0:
            # Update tracking for missing faces (transition to TEMPORARILY_NOT_VISIBLE)
            await tracking_service.update_tracks_for_frame(camera_id, [])
            return {
                "status": "NO_FACE",
                "faces_detected_count": 0,
                "recognized_faces": [],
                "active_tracks": [t.to_response() for t in tracking_service.get_active_tracks(camera_id)]
            }

        # 3. Associate with Spatial Tracklets
        track_associations = await tracking_service.update_tracks_for_frame(camera_id, detections)

        # 4. Load Exam-Specific Biometric Cache
        cache = None
        try:
            cache = await biometric_cache_manager.get_or_load_cache(exam_id, session_id)
        except Exception as e:
            logger.warning(f"Biometric cache unavailable for exam '{exam_id}': {str(e)}")

        recognized_items: List[Dict[str, Any]] = []

        # 5. Process EVERY detected face independently
        for i, det in enumerate(detections):
            # Resolve associated tracking_id
            tracking_id = next((t[1] for t in track_associations if t[0] == i), f"trk-{camera_id}-{i:03d}")
            
            box = det["box"]
            x, y, w, h = box
            rel_box = BoundingBox(
                x=round(max(0, x) / w_img, 3),
                y=round(max(0, y) / h_img, 3),
                width=round(min(w, w_img) / w_img, 3),
                height=round(min(h, h_img) / h_img, 3)
            )

            # Feature Extraction (128-d L2-Normalized)
            try:
                query_vec, _ = face_engine.extract_embedding(img, det)
            except Exception as e:
                logger.error(f"Embedding extraction failed for face {i}: {str(e)}")
                continue

            # Vectorized Cosine Matching against Exam Cache
            if cache is None:
                identity_status = "UNKNOWN"
                matched_sid = None
                conf_norm = 0.0
                student_name = None
                student_roll = None
            else:
                best_student_id, similarity, student_meta = cache.match_embedding(query_vec)
                conf_norm = round(max(0.0, min(1.0, similarity)), 4)

                # Determine Identity Status using Configurable Development Thresholds
                if conf_norm >= settings.FACE_MATCH_THRESHOLD:
                    identity_status = "IDENTIFIED"
                    matched_sid = best_student_id
                    student_name = student_meta.get("name")
                    student_roll = student_meta.get("roll_number")
                elif conf_norm >= settings.FACE_UNCERTAIN_THRESHOLD:
                    identity_status = "UNCERTAIN"
                    matched_sid = best_student_id
                    student_name = student_meta.get("name")
                    student_roll = student_meta.get("roll_number")
                else:
                    identity_status = "UNKNOWN"
                    matched_sid = None
                    student_name = None
                    student_roll = None

            # Update Tracking Service State Machine
            await tracking_service.update_track_identity(
                camera_id=camera_id,
                tracking_id=tracking_id,
                identity_status=identity_status,
                student_id=matched_sid,
                student_name=student_name,
                similarity=conf_norm
            )

            # Head Pose Estimation via 3D PnP Anthropometric Facial Model
            head_pose_dict = None
            raw_lm = det.get("landmarks")
            if raw_lm is not None:
                try:
                    hp_res = head_pose_service.estimate_pose_from_landmarks(
                        landmarks=raw_lm,
                        frame_width=w_img,
                        frame_height=h_img
                    )
                    head_pose_dict = hp_res.to_dict()
                except Exception as e:
                    logger.debug(f"Head pose estimation failed for face {i}: {str(e)}")

            face_obj = RecognizedFaceDetails(
                face_index=i,
                tracking_id=tracking_id,
                bbox=rel_box,
                confidence=det["confidence"],
                similarity=conf_norm,
                identity_status=identity_status,
                student_id=matched_sid,
                student_name=student_name,
                student_roll=student_roll,
                head_pose=head_pose_dict
            )
            recognized_items.append(face_obj.to_dict())

            # 6. Selective Persistence of Meaningful Events (NO FRAME-BY-FRAME DB FLOODING)
            last_status = self._persisted_identities.get(tracking_id)
            if last_status != identity_status:
                self._persisted_identities[tracking_id] = identity_status
                # Store meaningful detection record
                await self._persist_meaningful_event(
                    exam_session_id=session_id,
                    camera_id=camera_id,
                    student_id=matched_sid,
                    tracking_id=tracking_id,
                    identity_status=identity_status,
                    confidence=int(conf_norm * 100),
                    rel_box=rel_box
                )

        t_total_ms = round((time.perf_counter() - t0) * 1000, 2)
        overall_status = "MULTIPLE_FACES" if len(recognized_items) > 1 else (recognized_items[0]["identity_status"] if recognized_items else "NO_FACE")

        return {
            "status": overall_status,
            "camera_id": camera_id,
            "exam_id": exam_id,
            "exam_session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "faces_detected_count": len(recognized_items),
            "recognized_faces": recognized_items,
            "active_tracks": [t.to_response() for t in tracking_service.get_active_tracks(camera_id)],
            "processing_time_ms": t_total_ms,
            "model_version": settings.FACE_MODEL_VERSION
        }

    async def _persist_meaningful_event(
        self,
        exam_session_id: str,
        camera_id: str,
        student_id: Optional[str],
        tracking_id: str,
        identity_status: str,
        confidence: int,
        rel_box: BoundingBox
    ):
        """Persists meaningful identity events to Supabase detections and student_tracking."""
        event_type = f"FACE_{identity_status}"
        logger.info(
            f"MEANINGFUL EVENT: {event_type} on {camera_id} for {student_id or 'UNKNOWN'} (trk={tracking_id}, conf={confidence}%)"
        )
        # 1. Update student_tracking table in Supabase
        if supabase_db._client:
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                supabase_db._client.table("student_tracking").upsert({
                    "exam_session_id": exam_session_id,
                    "camera_id": camera_id,
                    "student_id": student_id,
                    "tracking_reference": tracking_id,
                    "confidence": confidence,
                    "status": identity_status,
                    "last_seen_at": now_iso
                }, on_conflict="tracking_reference").execute()
            except Exception as e:
                logger.error(f"Error persisting student tracking record: {str(e)}")


recognition_service = FaceRecognitionService()
