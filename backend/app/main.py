import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.api.api import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Autonomous Computer Vision & AI Examination Surveillance Engine for AI-Proctor. "
        "Provides backend interfaces for face enrollment, multi-camera processing, "
        "detection contracts, tracking, suspicion scoring, alerts, and ESP32 telemetry."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cross-Origin Resource Sharing (CORS) for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    """
    Structured logging and telemetry middleware.
    Tracks Request ID, endpoint path, and processing latency.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(process_time_ms)

    # Log request metrics
    extra = {
        "request_id": request_id,
        "endpoint": request.url.path,
        "processing_time_ms": process_time_ms,
    }
    logger.info(
        f"{request.method} {request.url.path} returned {response.status_code} in {process_time_ms}ms",
        extra=extra,
    )

    return response


# Mount All API Routes
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
