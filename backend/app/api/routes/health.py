from fastapi import APIRouter
from datetime import datetime, timezone
from backend.app.models.responses import HealthResponse, DependencyStatus
from backend.app.core.config import settings
from backend.app.integrations.supabase import supabase_db

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """
    Health check endpoint reporting backend service status and external dependencies.
    """
    supabase_status = "connected" if supabase_db.is_connected else "fallback_mode"
    ai_engine_status = "contract_ready_pending_model_mount"
    worker_status = "ready"

    return HealthResponse(
        status="ok",
        service="ai-proctor-backend",
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION,
        dependencies=DependencyStatus(
            supabase=supabase_status,
            ai_engine=ai_engine_status,
            worker_queue=worker_status
        )
    )
