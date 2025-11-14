"""API tests for health check endpoint."""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import DatabaseError, OperationalError


class TestHealthEndpoint:
    """Test suite for health check API endpoints."""

    def test_health_endpoint_healthy(self, client: TestClient) -> None:
        """Test health endpoint returns healthy status with connected database."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "version" in data
        assert "database" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data

        # Verify field values
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] > 0
        assert isinstance(data["timestamp"], str)  # ISO format datetime string

    def test_health_endpoint_unhealthy(self, client: TestClient) -> None:
        """Test health endpoint returns unhealthy status when database fails."""
        # Create a mock session that raises OperationalError on exec
        mock_session = Mock()
        mock_session.exec.side_effect = OperationalError(
            "connection failed", params=None, orig=Exception("DB down")
        )

        # Override the get_db dependency
        from app.api.deps import get_db
        from app.main import app

        def mock_get_db() -> Generator[Mock, None, None]:
            yield mock_session

        app.dependency_overrides[get_db] = mock_get_db

        try:
            # Make request - should return HTTP 503
            response = client.get("/api/v1/health")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "Service unavailable - database connection failed" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_health_endpoint_database_error(self, client: TestClient) -> None:
        """Test health endpoint handles DatabaseError correctly."""
        # Create a mock session that raises DatabaseError on exec
        mock_session = Mock()
        mock_session.exec.side_effect = DatabaseError(
            "database error", params=None, orig=Exception("DB error")
        )

        # Override the get_db dependency
        from app.api.deps import get_db
        from app.main import app

        def mock_get_db() -> Generator[Mock, None, None]:
            yield mock_session

        app.dependency_overrides[get_db] = mock_get_db

        try:
            # Make request - should return HTTP 503
            response = client.get("/api/v1/health")

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert "Service unavailable - database connection failed" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_health_endpoint_logging(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test health endpoint emits structured logs on success."""
        import logging

        # Set log level to capture INFO logs
        caplog.set_level(logging.INFO)

        response = client.get("/api/v1/health")

        assert response.status_code == 200

        # Verify structured log was emitted
        assert len(caplog.records) > 0

        # Find health_check_completed log record
        health_logs = [
            record
            for record in caplog.records
            if "health_check_completed" in record.message
        ]
        assert len(health_logs) > 0

        log_record = health_logs[0]
        assert log_record.levelname == "INFO"

        # Verify structured log context fields
        assert hasattr(log_record, "endpoint")
        assert log_record.endpoint == "/api/v1/health"
        assert hasattr(log_record, "status")
        assert log_record.status == "healthy"
        assert hasattr(log_record, "database")
        assert log_record.database == "connected"
        assert hasattr(log_record, "response_time_ms")
        assert isinstance(log_record.response_time_ms, (int, float))

    def test_health_endpoint_error_logging(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test health endpoint emits error logs with exc_info on database failure."""
        import logging

        # Set log level to capture ERROR logs
        caplog.set_level(logging.ERROR)

        # Create a mock session that raises OperationalError on exec
        mock_session = Mock()
        mock_session.exec.side_effect = OperationalError(
            "connection failed", params=None, orig=Exception("DB down")
        )

        # Override the get_db dependency
        from app.api.deps import get_db
        from app.main import app

        def mock_get_db() -> Generator[Mock, None, None]:
            yield mock_session

        app.dependency_overrides[get_db] = mock_get_db

        try:
            response = client.get("/api/v1/health")

            assert response.status_code == 503

            # Verify error log was emitted
            assert len(caplog.records) > 0

            # Find health_check_failed log record
            error_logs = [
                record
                for record in caplog.records
                if "health_check_failed" in record.message
            ]
            assert len(error_logs) > 0

            log_record = error_logs[0]
            assert log_record.levelname == "ERROR"

            # Verify structured log context fields
            assert hasattr(log_record, "endpoint")
            assert log_record.endpoint == "/api/v1/health"
            assert hasattr(log_record, "database_status")
            assert log_record.database_status == "disconnected"
            assert hasattr(log_record, "error")
            assert hasattr(log_record, "response_time_ms")

            # Verify exc_info is present (full stack trace)
            assert log_record.exc_info is not None
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_health_check_response_schema_validation(self) -> None:
        """Test that HealthCheckResponse Pydantic schema validates data correctly."""
        from app.schemas.health import HealthCheckResponse

        # Valid data should work
        valid_response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            database="connected",
            uptime_seconds=3600.5,
            timestamp=datetime(2025, 11, 14, 18, 45, 0),
        )

        assert valid_response.status == "healthy"
        assert valid_response.version == "1.0.0"
        assert valid_response.database == "connected"
        assert valid_response.uptime_seconds == 3600.5

        # Invalid data should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckResponse(
                status=123,  # type: ignore[arg-type]  # Should be str
                version=True,  # type: ignore[arg-type]  # Should be str
                database=None,  # type: ignore[arg-type]  # Should be str
                uptime_seconds="not-a-float",  # type: ignore[arg-type]  # Should be float
                timestamp="not-a-date",  # type: ignore[arg-type]  # Should be datetime
            )

        # Verify validation errors were raised
        assert exc_info.value.error_count() > 0

        # Test missing required fields
        with pytest.raises(ValidationError):
            HealthCheckResponse()  # type: ignore[call-arg]  # Missing all required fields

    def test_health_endpoint_uptime_increases(self, client: TestClient) -> None:
        """Test that uptime_seconds increases between requests."""
        import time

        # First request
        response1 = client.get("/api/v1/health")
        assert response1.status_code == 200
        data1 = response1.json()
        uptime1 = data1["uptime_seconds"]

        # Wait a bit
        time.sleep(0.1)

        # Second request
        response2 = client.get("/api/v1/health")
        assert response2.status_code == 200
        data2 = response2.json()
        uptime2 = data2["uptime_seconds"]

        # Uptime should have increased
        assert uptime2 > uptime1

    def test_health_endpoint_response_schema(self, client: TestClient) -> None:
        """Test that response matches expected Pydantic schema structure."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "status",
            "version",
            "database",
            "uptime_seconds",
            "timestamp",
        ]
        for field in required_fields:
            assert field in data

        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["database"], str)
        assert isinstance(data["uptime_seconds"], (int, float))
        assert isinstance(data["timestamp"], str)

        # Verify status field contains valid value
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

        # Verify database field contains valid value
        assert data["database"] in ["connected", "disconnected"]
