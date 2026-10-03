from fastapi import APIRouter
from backend.app.api.routes import (
    health,
    students,
    enrollment,
    exams,
    cameras,
    monitoring,
    alerts,
    iot,
    reports,
)

api_router = APIRouter()

# Health probe mounted at root level as well
api_router.include_router(health.router)

# Versioned API Endpoints (/api/v1/...)
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(students.router)
v1_router.include_router(enrollment.router)
v1_router.include_router(exams.router)
v1_router.include_router(cameras.router)
v1_router.include_router(monitoring.router)
v1_router.include_router(alerts.router)
v1_router.include_router(iot.router)
v1_router.include_router(reports.router)

api_router.include_router(v1_router)
