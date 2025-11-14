"""API routes for health check."""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlmodel import select

from app.api.deps import SessionDep
from app.schemas.health import HealthCheckResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Store application start time for uptime calculation
APP_START_TIME = time.time()


@router.get("", response_model=HealthCheckResponse)
async def get_health(
    session: SessionDep,
    request_id: str | None = Query(None, alias="X-Request-ID", include_in_schema=False),
) -> HealthCheckResponse:
    """
    System health check endpoint.

    Validates database connectivity and returns system status.
    Used by GitHub Actions smoke test and future monitoring.

    Returns:
        HealthCheckResponse: System health status with database connectivity

    Raises:
        HTTPException: 503 if database unreachable
    """
    start_time = time.time()

    try:
        # Simple database connectivity check
        result = session.exec(select(1)).one()
        database_status = "connected" if result == 1 else "disconnected"
        overall_status = "healthy" if database_status == "connected" else "unhealthy"

        uptime = time.time() - APP_START_TIME
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        logger.info(
            "health_check_completed",
            extra={
                "endpoint": "/api/v1/health",
                "status": overall_status,
                "database": database_status,
                "response_time_ms": response_time,
                "request_id": request_id or "unknown",
            },
        )

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            database=database_status,
            uptime_seconds=uptime,
            timestamp=datetime.now(timezone.utc),
        )

    except (OperationalError, DatabaseError) as e:
        uptime = time.time() - APP_START_TIME
        response_time = (time.time() - start_time) * 1000

        logger.error(
            "health_check_failed",
            exc_info=True,
            extra={
                "endpoint": "/api/v1/health",
                "database_status": "disconnected",
                "response_time_ms": response_time,
                "error": str(e),
                "request_id": request_id or "unknown",
            },
        )

        raise HTTPException(
            status_code=503,
            detail="Service unavailable - database connection failed",
        ) from e
