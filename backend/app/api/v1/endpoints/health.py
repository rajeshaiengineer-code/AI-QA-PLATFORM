"""
Health Check Endpoints

Provides health check and readiness endpoints for monitoring.
"""

from datetime import datetime
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ============================================================
# Response Schemas
# ============================================================

class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "AI QA Platform",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        }
    )

    status: str
    service: str
    version: str
    timestamp: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "service": "AI QA Platform",
                "version": "1.0.0",
                "environment": "development",
                "timestamp": "2024-01-15T10:30:00Z",
                "checks": {
                    "database": {"status": "healthy", "latency_ms": 5.2},
                },
            }
        }
    )

    status: str
    service: str
    version: str
    environment: str
    timestamp: str
    checks: Dict[str, Any]


# ============================================================
# Endpoints
# ============================================================

@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Basic health check endpoint. Returns service status.",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns HTTP 200 if the service is running.
    Does not check dependencies.
    """
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get(
    "/ready",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Detailed readiness check. Validates database connectivity.",
    responses={
        503: {
            "description": "Service unavailable - one or more dependencies are unhealthy",
        }
    },
)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> Union[DetailedHealthResponse, JSONResponse]:
    """
    Detailed readiness check endpoint.

    Validates critical dependencies:
    - Database connectivity (SELECT 1 + latency)

    Returns HTTP 503 if the database (or any check) is unhealthy.
    """
    checks: Dict[str, Any] = {}
    overall_status = "healthy"

    db_check = await check_database(db)
    checks["database"] = db_check
    if db_check["status"] != "healthy":
        overall_status = "unhealthy"

    payload = DetailedHealthResponse(
        status=overall_status,
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow().isoformat() + "Z",
        checks=checks,
    )

    if overall_status != "healthy":
        logger.warning(
            "Readiness check failed",
            extra_fields={"checks": checks},
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )

    return payload


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Simple liveness probe. Returns 200 if process is alive.",
)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness probe endpoint.

    Returns HTTP 200 as long as the process is running.
    Used by Kubernetes/container orchestrators.
    """
    return {"status": "alive"}


# ============================================================
# Helper Functions
# ============================================================

async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check database connectivity and measure latency."""
    import time

    try:
        start = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }
