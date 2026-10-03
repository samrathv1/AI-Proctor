import base64
import time
import os
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
import cv2

from backend.app.core.config import settings
from backend.app.core.logging import logger


class FaceEngine:
    """
    Biometric Face Processing Engine.
    Handles image decoding, face detection with landmark extraction,
    quality score metrics, face alignment, and deep feature embedding generation.
    """

    def __init__(self):
        self._detector: Optional[cv2.FaceDetectorYN] = None
        self._recognizer: Optional[cv2.FaceRecognizerSF] = None
        self._haar_cascade: Optional[cv2.CascadeClassifier] = None
        self._initialized = False
        self._init_models()

    def _init_models(self):
        detector_path = os.path.abspath(settings.FACE_DETECTOR_MODEL_PATH)
        recognizer_path = os.path.abspath(settings.FACE_RECOGNITION_MODEL_PATH)

        # 1. Initialize FaceDetectorYN (YuNet ONNX)
        if os.path.exists(detector_path):
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    detector_path,
                    "",
                    (320, 320),
                    score_threshold=0.45,
                    nms_threshold=0.30,
                    top_k=5000
                )
                logger.info(f"YuNet Face Detector initialized from {detector_path}")
            except Exception as e:
                logger.error(f"Failed to load YuNet detector: {str(e)}")
                self._detector = None

        # 2. Fallback: Haar Cascade frontal face detector
        haar_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if os.path.exists(haar_path):
            try:
                self._haar_cascade = cv2.CascadeClassifier(haar_path)
            except Exception as e:
                logger.error(f"Failed to load Haar cascade: {str(e)}")

        # 3. Initialize FaceRecognizerSF (SFace / ArcFace compatible ONNX)
        if os.path.exists(recognizer_path):
            try:
                self._recognizer = cv2.FaceRecognizerSF.create(recognizer_path, "")
                logger.info(f"Face Recognizer initialized from {recognizer_path}")
            except Exception as e:
                logger.error(f"Failed to load Face Recognizer: {str(e)}")
                self._recognizer = None

        self._initialized = (self._detector is not None or self._haar_cascade is not None) and self._recognizer is not None

    @property
    def is_ready(self) -> bool:
        return self._initialized

    # =========================================================================
    # IMAGE DECODING & NORMALIZATION
    # =========================================================================

    def decode_image(self, image_data: Any) -> np.ndarray:
        """
        Decodes image input from base64 string, data URL prefix, or raw bytes
        into an OpenCV BGR numpy array.
        """
        if isinstance(image_data, str):
            # Strip data URL prefix if present (e.g. 'data:image/jpeg;base64,...')
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(image_data)
            except Exception as e:
                raise ValueError(f"Failed to base64-decode image: {str(e)}")
        elif isinstance(image_data, bytes):
            raw_bytes = image_data
        elif isinstance(image_data, np.ndarray):
            return image_data
        else:
            raise ValueError(f"Unsupported image input type: {type(image_data)}")

        np_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("OpenCV failed to decode image buffer into valid pixels.")
        return img

    # =========================================================================
    # FACE DETECTION
    # =========================================================================

    def detect_faces(self, img_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects faces and 5 facial landmarks in image.
        Returns list of detection dictionaries.
        """
        h, w = img_bgr.shape[:2]
        detections = []

        if self._detector is not None:
            # Set input size dynamically to match incoming image resolution
            self._detector.setInputSize((w, h))
            _, faces = self._detector.detect(img_bgr)
            if faces is not None and len(faces) > 0:
                for face in faces:
                    x, y, box_w, box_h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    confidence = float(face[14])
                    if box_w < settings.MIN_FACE_SIZE or box_h < settings.MIN_FACE_SIZE:
                        continue
                    detections.append({
                        "box": (x, y, box_w, box_h),
                        "confidence": confidence,
                        "landmarks": face[4:14].copy(),
                        "raw": face.copy(),
                        "engine": "yunet"
                    })
                return detections

        # Fallback to Haar Cascade if YuNet is unmounted or returns no face
        if self._haar_cascade is not None:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            faces = self._haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(settings.MIN_FACE_SIZE, settings.MIN_FACE_SIZE)
            )
            for (x, y, box_w, box_h) in faces:
                detections.append({
                    "box": (x, y, box_w, box_h),
                    "confidence": 0.85,
                    "landmarks": None,
                    "raw": np.array([x, y, box_w, box_h, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.85]),
                    "engine": "haar"
                })

        return detections

    # =========================================================================
    # QUALITY METRICS
    # =========================================================================

    def calculate_quality_score(self, img_bgr: np.ndarray, box: Tuple[int, int, int, int], confidence: float) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates a 0-100 quality score based on:
        - Face resolution & dimensions
        - Sharpness via Laplacian variance
        - Illumination balance
        - Contrast dispersion
        - Detector confidence
        """
        h_img, w_img = img_bgr.shape[:2]
        x, y, w, h = box
        
        # Clamp coordinates to image boundaries
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_img, x + w)
        y2 = min(h_img, y + h)

        face_roi = img_bgr[y1:y2, x1:x2]
        if face_roi.size == 0:
            return 0.0, {"error": "Empty face region"}

        gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        # 1. Size Metric (w >= 100 is ideal, 60 is minimum)
        area = w * h
        size_score = min(100.0, (area / 14400.0) * 100.0)  # 120x120 = 14400

        # 2. Blur / Sharpness Metric (Laplacian variance)
        lap_var = float(cv2.Laplacian(gray_roi, cv2.CV_64F).var())
        # > 100 is sharp, < 30 is blurry
        blur_score = min(100.0, (lap_var / 120.0) * 100.0)

        # 3. Illumination Metric (Mean luminance optimal between 80 and 180)
        mean_lum = float(np.mean(gray_roi))
        if 80 <= mean_lum <= 180:
            lum_score = 100.0
        elif mean_lum < 80:
            lum_score = max(0.0, (mean_lum / 80.0) * 100.0)
        else:
            lum_score = max(0.0, 100.0 - ((mean_lum - 180.0) / 75.0) * 100.0)

        # 4. Contrast Metric (Standard deviation of pixel intensities)
        std_lum = float(np.std(gray_roi))
        contrast_score = min(100.0, (std_lum / 45.0) * 100.0)

        # 5. Composite Weighted Score
        # 30% Size, 30% Sharpness, 20% Illumination, 10% Contrast, 10% Confidence
        overall_score = (
            0.30 * size_score +
            0.30 * blur_score +
            0.20 * lum_score +
            0.10 * contrast_score +
            0.10 * (confidence * 100.0)
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 2)

        details = {
            "overall_score": overall_score,
            "face_width": w,
            "face_height": h,
            "blur_metric": round(lap_var, 2),
            "mean_luminance": round(mean_lum, 2),
            "contrast_std": round(std_lum, 2),
            "detector_confidence": round(confidence, 2)
        }

        return overall_score, details

    # =========================================================================
    # EMBEDDING EXTRACTION & NORMALIZATION
    # =========================================================================

    def extract_embedding(self, img_bgr: np.ndarray, detection: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Aligns, crops face, and generates L2-normalized deep feature embedding.
        Returns:
            (normalized_vector: np.ndarray [shape (128,)], aligned_face: np.ndarray)
        """
        if self._recognizer is None:
            raise RuntimeError("Face Recognizer model is not loaded.")

        raw = detection["raw"]
        
        # SFace affine crop & alignment using 5 landmarks
        if detection.get("engine") == "yunet":
            aligned = self._recognizer.alignCrop(img_bgr, raw)
        else:
            x, y, w, h = detection["box"]
            h_img, w_img = img_bgr.shape[:2]
            crop = img_bgr[max(0, y):min(h_img, y + h), max(0, x):min(w_img, x + w)]
            aligned = cv2.resize(crop, (112, 112))

        # Extract deep feature vector
        feature = self._recognizer.feature(aligned).flatten()

        # L2-Normalization: ||v|| = 1.0
        norm = np.linalg.norm(feature)
        if norm > 1e-6:
            normalized_feature = feature / norm
        else:
            normalized_feature = feature

        return normalized_feature.astype(np.float32), aligned

    # =========================================================================
    # COSINE SIMILARITY
    # =========================================================================

    @staticmethod
    def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
        """
        Computes cosine similarity between two normalized vectors:
        sim(u, v) = (u . v) / (||u|| * ||v||)
        """
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))


face_engine = FaceEngine()
