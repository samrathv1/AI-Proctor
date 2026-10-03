from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import numpy as np
from fastapi import HTTPException, status
from backend.app.integrations.supabase import supabase_db
from backend.app.core.logging import logger


class ExamBiometricCache:
    """
    Session-level in-memory cache of enrolled student face templates
    for a specific examination. Enables O(1) vectorized dot-product matching.
    """

    def __init__(
        self,
        exam_id: str,
        session_id: Optional[str],
        student_ids: List[str],
        student_metadata: Dict[str, Dict[str, Any]],
        embedding_matrix: np.ndarray,
        model_version: str
    ):
        self.exam_id = exam_id
        self.session_id = session_id or f"ses-{exam_id}"
        self.student_ids = student_ids
        self.student_metadata = student_metadata
        self.embedding_matrix = embedding_matrix  # Shape: (N, 128), float32, normalized
        self.model_version = model_version
        self.created_at = datetime.now(timezone.utc)

    @property
    def size(self) -> int:
        return len(self.student_ids)

    def match_embedding(self, query_vec: np.ndarray) -> Tuple[Optional[str], float, Dict[str, Any]]:
        """
        Calculates vectorized cosine similarity between normalized query vector
        and all enrolled candidate templates in this exam.
        Returns:
            (best_student_id: Optional[str], best_similarity: float, metadata: Dict[str, Any])
        """
        if self.size == 0 or self.embedding_matrix.size == 0:
            return None, 0.0, {}

        # Vectorized dot products: s = M . q (shape: N,)
        scores = np.dot(self.embedding_matrix, query_vec)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        best_student_id = self.student_ids[best_idx]
        metadata = self.student_metadata.get(best_student_id, {})

        return best_student_id, best_score, metadata


class BiometricCacheManager:
    """
    Manages lifecycle of exam-specific biometric caches.
    Ensures that live camera faces are compared ONLY against candidates enrolled
    in the active examination, avoiding global database scans.
    """

    def __init__(self):
        self._caches: Dict[str, ExamBiometricCache] = {}

    async def get_or_load_cache(
        self,
        exam_id: str,
        session_id: Optional[str] = None,
        force_reload: bool = False
    ) -> ExamBiometricCache:
        if not force_reload and exam_id in self._caches:
            return self._caches[exam_id]

        logger.info(f"Loading exam-specific biometric cache for exam {exam_id}...")

        # 1. Fetch roster and enrolled face templates for this exam
        enrolled_profiles = await supabase_db.get_exam_face_profiles(exam_id)
        roster = await supabase_db.get_exam_roster(exam_id)

        # Build metadata map from roster
        metadata_map: Dict[str, Dict[str, Any]] = {}
        for cand in roster:
            metadata_map[cand["student_id"]] = {
                "name": cand.get("name", "Unknown"),
                "roll_number": cand.get("roll_number", "N/A"),
                "seat_number": cand.get("seat_number", "N/A")
            }

        # Resolve student info for any enrolled profiles not yet added to exam_students table
        for sid in enrolled_profiles:
            if sid not in metadata_map:
                student_info = await supabase_db.get_student(sid)
                if student_info:
                    metadata_map[sid] = {
                        "name": student_info.get("name", "Unknown"),
                        "roll_number": student_info.get("roll_number", "N/A"),
                        "seat_number": "N/A"
                    }

        # Validate that enrolled biometric vectors exist for this exam
        if not enrolled_profiles:
            logger.warning(f"Exam '{exam_id}' has no enrolled face biometric profiles.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"EMPTY_EXAM_ROSTER: No enrolled student face biometric profiles found for examination '{exam_id}'. "
                    "Candidates must complete biometric face enrollment before launching surveillance recognition."
                )
            )

        student_ids: List[str] = []
        vectors: List[np.ndarray] = []

        for sid, raw_bytes in enrolled_profiles.items():
            vec = np.frombuffer(raw_bytes, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            student_ids.append(sid)
            vectors.append(vec)

        embedding_matrix = np.vstack(vectors).astype(np.float32)

        cache = ExamBiometricCache(
            exam_id=exam_id,
            session_id=session_id,
            student_ids=student_ids,
            student_metadata=metadata_map,
            embedding_matrix=embedding_matrix,
            model_version="sface-onnx-v1"
        )
        self._caches[exam_id] = cache
        logger.info(f"Biometric cache initialized for exam {exam_id}: {cache.size} candidate templates mounted.")
        return cache

    def clear_cache(self, exam_id: str) -> bool:
        if exam_id in self._caches:
            del self._caches[exam_id]
            logger.info(f"Biometric cache for exam {exam_id} cleared from memory.")
            return True
        return False

    def is_cached(self, exam_id: str) -> bool:
        return exam_id in self._caches

    def get_cache(self, exam_id: str) -> Optional[ExamBiometricCache]:
        return self._caches.get(exam_id)


biometric_cache_manager = BiometricCacheManager()
