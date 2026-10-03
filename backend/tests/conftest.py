import os
import sys
from pathlib import Path

# Add project root to sys.path so 'backend' package is resolvable
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from starlette.testclient import TestClient

# Ensure test configuration environment
os.environ["API_SECRET_KEY"] = "test-secret-key"
os.environ["ESP32_API_KEY"] = "test-esp32-key"

from backend.app.main import app
from backend.app.core.config import settings

settings.API_SECRET_KEY = "test-secret-key"
settings.ESP32_API_KEY = "test-esp32-key"


@pytest.fixture
def client():
    """Synchronous test client for FastAPI routes."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers for authorized invigilator/admin API calls."""
    return {"X-API-Key": "test-secret-key"}


@pytest.fixture
def esp32_headers():
    """Headers for authorized ESP32 hardware calls."""
    return {"X-ESP32-Key": "test-esp32-key"}


@pytest.fixture(autouse=True)
def cleanup_test_students():
    """Ensures ephemeral test students from test runs do not conflict."""
    test_rolls = ["CS-2026-088", "CS-2026-077", "CS-2026-055", "CS-2026-095"]
    from backend.app.integrations.supabase import supabase_db
    for k in list(supabase_db._in_memory_students.keys()):
        if supabase_db._in_memory_students[k].get("roll_number") in test_rolls:
            del supabase_db._in_memory_students[k]
    if supabase_db._client:
        try:
            for r in test_rolls:
                supabase_db._client.table("students").delete().eq("roll_number", r).execute()
        except Exception:
            pass
    yield
    for k in list(supabase_db._in_memory_students.keys()):
        if supabase_db._in_memory_students[k].get("roll_number") in test_rolls:
            del supabase_db._in_memory_students[k]
    if supabase_db._client:
        try:
            for r in test_rolls:
                supabase_db._client.table("students").delete().eq("roll_number", r).execute()
        except Exception:
            pass
