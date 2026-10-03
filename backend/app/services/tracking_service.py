from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timezone
import numpy as np
from backend.app.models.responses import TrackingResult
from backend.app.core.logging import logger


def calculate_iou(boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
    """Calculates Intersection over Union between two (x, y, w, h) boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    unionArea = float(boxAArea + boxBArea - interArea)

    if unionArea <= 0:
        return 0.0
    return interArea / unionArea


class Tracklet:
    """Internal state representation for an actively tracked candidate."""
    def __init__(self, tracking_id: str, camera_id: str, box: Tuple[int, int, int, int], initial_status: str = "UNKNOWN"):
        now = datetime.now(timezone.utc)
        self.tracking_id = tracking_id
        self.camera_id = camera_id
        self.box = box
        self.student_id: Optional[str] = None
        self.student_name: Optional[str] = None
        self.confidence: float = 0.80
        self.similarity: float = 0.0
        self.status: str = initial_status  # UNKNOWN | UNCERTAIN | IDENTIFIED | TEMPORARILY_NOT_VISIBLE | LOST
        self.first_seen: datetime = now
        self.last_seen: datetime = now
        self.frames_tracked: int = 1
        self.frames_missing: int = 0

    def to_response(self) -> TrackingResult:
        return TrackingResult(
            tracking_id=self.tracking_id,
            camera_id=self.camera_id,
            student_id=self.student_id,
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            confidence=self.confidence,
            status=self.status
        )


class TrackingService:
    """
    Candidate Multi-Object Tracking Service.
    Maintains spatial tracklets across frames and governs identity state transitions:
    UNKNOWN -> UNCERTAIN -> IDENTIFIED -> TEMPORARILY_NOT_VISIBLE -> LOST.
    Ensures tracking_id is strictly separated from student_id.
    """

    def __init__(self):
        self._tracks: Dict[str, Dict[str, Tracklet]] = {}  # camera_id -> tracking_id -> Tracklet
        self._track_counters: Dict[str, int] = {}
        self._timeout_seconds: float = 15.0

    def _next_tracking_id(self, camera_id: str) -> str:
        count = self._track_counters.get(camera_id, 0) + 1
        self._track_counters[camera_id] = count
        return f"trk-{camera_id}-{count:03d}"

    async def update_tracks_for_frame(
        self,
        camera_id: str,
        detected_faces: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, Optional[str]]]:
        """
        Associates detected face boxes in current frame with active tracklets on camera_id.
        Returns:
            List of (face_index, tracking_id, identity_status)
        """
        now = datetime.now(timezone.utc)
        if camera_id not in self._tracks:
            self._tracks[camera_id] = {}

        camera_tracks = self._tracks[camera_id]
        matched_track_ids = set()
        associations: List[Tuple[int, str, str]] = []

        # 1. Match each detected face box to active tracklet via IoU
        for i, det in enumerate(detected_faces):
            box = det["box"]
            best_track_id = None
            best_iou = 0.0

            for tid, track in camera_tracks.items():
                if tid in matched_track_ids or track.status == "LOST":
                    continue
                iou = calculate_iou(box, track.box)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = tid

            # If IoU overlap is sufficient, associate with existing tracklet
            if best_track_id and best_iou >= 0.25:
                track = camera_tracks[best_track_id]
                track.box = box
                track.last_seen = now
                track.frames_tracked += 1
                track.frames_missing = 0
                track.confidence = det.get("confidence", 0.90)
                matched_track_ids.add(best_track_id)
                associations.append((i, best_track_id, track.status))
            else:
                # Allocate new tracklet
                new_tid = self._next_tracking_id(camera_id)
                new_track = Tracklet(new_tid, camera_id, box, initial_status="UNKNOWN")
                new_track.confidence = det.get("confidence", 0.90)
                camera_tracks[new_tid] = new_track
                matched_track_ids.add(new_tid)
                associations.append((i, new_tid, new_track.status))

        # 2. Update unobserved tracks: Transition to TEMPORARILY_NOT_VISIBLE or LOST
        for tid, track in list(camera_tracks.items()):
            if tid not in matched_track_ids:
                track.frames_missing += 1
                elapsed_sec = (now - track.last_seen).total_seconds()
                if elapsed_sec > self._timeout_seconds:
                    track.status = "LOST"
                else:
                    if track.status == "IDENTIFIED":
                        track.status = "TEMPORARILY_NOT_VISIBLE"

        return associations

    async def update_track_identity(
        self,
        camera_id: str,
        tracking_id: str,
        identity_status: str,
        student_id: Optional[str] = None,
        student_name: Optional[str] = None,
        similarity: float = 0.0
    ) -> Tracklet:
        """
        Updates biometric identity state for an active tracklet.
        """
        if camera_id not in self._tracks or tracking_id not in self._tracks[camera_id]:
            track = Tracklet(tracking_id, camera_id, (0, 0, 100, 100), initial_status=identity_status)
            if camera_id not in self._tracks:
                self._tracks[camera_id] = {}
            self._tracks[camera_id][tracking_id] = track
        else:
            track = self._tracks[camera_id][tracking_id]

        track.similarity = similarity
        track.last_seen = datetime.now(timezone.utc)

        # State Machine Transitions
        if identity_status == "IDENTIFIED":
            track.status = "IDENTIFIED"
            track.student_id = student_id
            track.student_name = student_name
        elif identity_status == "UNCERTAIN":
            if track.status != "IDENTIFIED":
                track.status = "UNCERTAIN"
                track.student_id = student_id
                track.student_name = student_name
        elif identity_status == "UNKNOWN":
            if track.status != "IDENTIFIED":
                track.status = "UNKNOWN"
                track.student_id = None
                track.student_name = None

        return track

    async def update_track(
        self,
        tracking_id: str,
        camera_id: str,
        student_id: Optional[str] = None,
        confidence: float = 0.90,
        status: str = "IDENTIFIED"
    ) -> TrackingResult:
        """Legacy compatibility wrapper."""
        track = await self.update_track_identity(
            camera_id=camera_id,
            tracking_id=tracking_id,
            identity_status=status,
            student_id=student_id,
            similarity=confidence
        )
        return track.to_response()

    async def get_track(self, tracking_id: str, camera_id: Optional[str] = None) -> Optional[TrackingResult]:
        if camera_id and camera_id in self._tracks:
            track = self._tracks[camera_id].get(tracking_id)
            return track.to_response() if track else None
        
        for cam_tracks in self._tracks.values():
            if tracking_id in cam_tracks:
                return cam_tracks[tracking_id].to_response()
        return None

    async def mark_temporarily_hidden(self, tracking_id: str, camera_id: Optional[str] = None) -> Optional[TrackingResult]:
        for cam, cam_tracks in self._tracks.items():
            if camera_id and cam != camera_id:
                continue
            if tracking_id in cam_tracks:
                cam_tracks[tracking_id].status = "TEMPORARILY_NOT_VISIBLE"
                return cam_tracks[tracking_id].to_response()
        return None

    def get_active_tracks(self, camera_id: str) -> List[Tracklet]:
        if camera_id in self._tracks:
            return [t for t in self._tracks[camera_id].values() if t.status != "LOST"]
        return []


tracking_service = TrackingService()
