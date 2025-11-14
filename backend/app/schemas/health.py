"""Pydantic schemas for health check API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Health check response with system status and database connectivity."""

    status: str = Field(
        ..., description="Overall system health: healthy, degraded, unhealthy"
    )
    version: str = Field(..., description="API version string")
    database: str = Field(
        ..., description="Database connectivity: connected, disconnected"
    )
    uptime_seconds: float = Field(..., description="Process uptime in seconds")
    timestamp: datetime = Field(..., description="Health check timestamp (UTC)")

    model_config = {"from_attributes": True}
