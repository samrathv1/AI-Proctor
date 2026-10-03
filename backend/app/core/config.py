import os
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application Settings for AI-Proctor Backend.
    Loads from environment variables and local .env file.
    """
    APP_NAME: str = "AI-Proctor Surveillance Engine"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")
    HOST: str = Field(default="0.0.0.0", alias="HOST")
    PORT: int = Field(default=8000, alias="PORT")
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")

    # Supabase credentials (Service Role is server-only)
    SUPABASE_URL: str = Field(default="", alias="SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    # API Security
    API_SECRET_KEY: str = Field(default="dev-proctor-secret-key", alias="API_SECRET_KEY")
    ESP32_API_KEY: str = Field(default="esp32-beacon-token", alias="ESP32_API_KEY")

    # Institutional Authentication Configuration (SPIT Default & Configurable Domain Support)
    INSTITUTIONAL_EMAIL_DOMAIN: str = Field(default="spit.ac.in", alias="INSTITUTIONAL_EMAIL_DOMAIN")
    ALLOWED_EMAIL_DOMAINS: str = Field(
        default="spit.ac.in,institution.edu,uni.edu",
        alias="ALLOWED_EMAIL_DOMAINS"
    )

    # Vision & AI Model Paths
    AI_MODEL_PATH: str = Field(default="backend/models/yolo11n.pt", alias="AI_MODEL_PATH")
    YOLO_MODEL_PATH: str = Field(default="backend/models/yolov8n.onnx", alias="YOLO_MODEL_PATH")
    YOLO_CONFIDENCE_THRESHOLD: float = Field(default=0.35, alias="YOLO_CONFIDENCE_THRESHOLD")
    YOLO_IOU_THRESHOLD: float = Field(default=0.45, alias="YOLO_IOU_THRESHOLD")
    YOLO_INPUT_SIZE: int = Field(default=640, alias="YOLO_INPUT_SIZE")
    FACE_DETECTOR_MODEL_PATH: str = Field(
        default="backend/models/face_detection_yunet_2023mar.onnx",
        alias="FACE_DETECTOR_MODEL_PATH"
    )
    FACE_RECOGNITION_MODEL_PATH: str = Field(
        default="backend/models/face_recognition_sface_2021dec.onnx",
        alias="FACE_RECOGNITION_MODEL_PATH"
    )
    FACE_MODEL_VERSION: str = Field(default="sface-onnx-v1", alias="FACE_MODEL_VERSION")

    # Configurable Biometric Thresholds (INITIAL DEVELOPMENT VALUES - Subject to calibration)
    FACE_MATCH_THRESHOLD: float = Field(default=0.65, alias="FACE_MATCH_THRESHOLD")
    FACE_UNCERTAIN_THRESHOLD: float = Field(default=0.45, alias="FACE_UNCERTAIN_THRESHOLD")
    MIN_FACE_SIZE: int = Field(default=60, alias="MIN_FACE_SIZE")
    MIN_QUALITY_SCORE: float = Field(default=35.0, alias="MIN_QUALITY_SCORE")

    # General Confidence Thresholds
    PERSON_DETECTION_THRESHOLD: float = Field(default=0.50, alias="PERSON_DETECTION_THRESHOLD")
    MOBILE_DETECTION_THRESHOLD: float = Field(default=0.60, alias="MOBILE_DETECTION_THRESHOLD")
    SUSPICION_ALERT_THRESHOLD: int = Field(default=75, alias="SUSPICION_ALERT_THRESHOLD")

    # Temporal & Behavioural Analysis Configuration
    HEAD_POSE_YAW_THRESHOLD: float = Field(default=20.0, alias="HEAD_POSE_YAW_THRESHOLD")
    HEAD_POSE_PITCH_THRESHOLD: float = Field(default=15.0, alias="HEAD_POSE_PITCH_THRESHOLD")
    BEHAVIOUR_WINDOW_SECONDS: int = Field(default=60, alias="BEHAVIOUR_WINDOW_SECONDS")
    HEAD_TURN_REPEAT_THRESHOLD: int = Field(default=3, alias="HEAD_TURN_REPEAT_THRESHOLD")
    LOOKING_AWAY_DURATION_THRESHOLD: float = Field(default=3.0, alias="LOOKING_AWAY_DURATION_THRESHOLD")
    FACE_ABSENCE_DURATION_THRESHOLD: float = Field(default=5.0, alias="FACE_ABSENCE_DURATION_THRESHOLD")
    PHONE_PERSISTENCE_THRESHOLD: float = Field(default=5.0, alias="PHONE_PERSISTENCE_THRESHOLD")
    ALERT_COOLDOWN_SECONDS: int = Field(default=30, alias="ALERT_COOLDOWN_SECONDS")

    # Storage buckets
    STUDENT_PHOTOS_BUCKET: str = Field(default="student-photos", alias="STUDENT_PHOTOS_BUCKET")
    ALERT_EVIDENCE_BUCKET: str = Field(default="alert-evidence", alias="ALERT_EVIDENCE_BUCKET")
    EXAM_VIDEOS_BUCKET: str = Field(default="exam-videos", alias="EXAM_VIDEOS_BUCKET")

    model_config = {
        "env_file": ("backend/.env", ".env"),
        "extra": "allow"
    }

    @property
    def is_supabase_configured(self) -> bool:
        return bool(
            self.SUPABASE_URL
            and "your-project" not in self.SUPABASE_URL
            and self.SUPABASE_SERVICE_ROLE_KEY
            and "your-supabase" not in self.SUPABASE_SERVICE_ROLE_KEY
        )


settings = Settings()
