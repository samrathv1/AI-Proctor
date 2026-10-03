import logging
import sys
import json
import time
from typing import Any, Dict
from datetime import datetime, timezone

SENSITIVE_KEYS = {
    "password", "token", "secret", "face_embedding", "embedding",
    "service_role_key", "api_key", "authorization", "key"
}


def sanitize_data(data: Any) -> Any:
    """Recursively redacts sensitive keys from logs (embeddings, passwords, tokens)."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_data(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for observability."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured context attributes if present
        for attr in ["request_id", "endpoint", "processing_time_ms", "exam_session_id", "camera_id", "worker_state"]:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(sanitize_data(log_entry))


def setup_logger(name: str = "ai_proctor", log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        
    return logger


logger = setup_logger()
