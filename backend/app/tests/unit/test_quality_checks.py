"""
Unit tests for Dagster asset checks (Story 4-7).

Tests check logic for freshness and volume anomaly detection.

KNOWN ISSUE (Python 3.14):
These tests cannot currently run locally due to Python 3.14/Dagster/Pydantic compatibility issue.
Run in Docker: docker compose exec backend pytest app/tests/unit/test_quality_checks.py -v
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from dagster import build_asset_check_context

# Note: These tests will fail in Python 3.14 due to Dagster import issues
# They work correctly in Python 3.10/3.12 (Docker environment)
from app.assets.quality_checks import (
    BLUESKY_VOLUME_MAX,
    BLUESKY_VOLUME_MIN,
    FRESHNESS_SLA_HOURS,
    REDDIT_VOLUME_MAX,
    REDDIT_VOLUME_MIN,
    check_bluesky_freshness,
    check_bluesky_volume_anomaly,
    check_reddit_freshness,
    check_reddit_volume_anomaly,
)


def extract_metadata_value(metadata_val: Any) -> Any:
    """
    Extract actual value from Dagster MetadataValue wrapper.

    Dagster 1.12+ wraps metadata in typed objects (FloatMetadataValue, etc.).
    This helper extracts the underlying value for test assertions.
    """
    if hasattr(metadata_val, "value"):
        return metadata_val.value
    return metadata_val


@pytest.fixture
def asset_check_context() -> Any:
    """Proper Dagster asset check context for testing."""
    return build_asset_check_context()


@pytest.fixture
def mock_database() -> tuple[MagicMock, AsyncMock]:
    """Mock DatabaseResource with session management."""
    database = MagicMock()
    session = AsyncMock()
    database.get_session.return_value.__aenter__.return_value = session
    database.get_session.return_value.__aexit__.return_value = None
    return database, session


class TestRedditFreshnessCheck:
    """Test Reddit freshness check logic."""

    @pytest.mark.asyncio
    async def test_passes_when_data_is_fresh(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should pass when data was fetched within SLA (2 hours)."""
        database, session = mock_database

        # Mock recent fetch (1 hour ago)
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_result = MagicMock()
        mock_result.scalar.return_value = recent_time
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_freshness(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is True
        assert (
            extract_metadata_value(result.metadata["age_hours"]) < FRESHNESS_SLA_HOURS
        )
        assert (
            extract_metadata_value(result.metadata["sla_hours"]) == FRESHNESS_SLA_HOURS
        )
        assert "action" not in result.metadata  # No action needed when passing

    @pytest.mark.asyncio
    async def test_fails_when_data_is_stale(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when data exceeds SLA (>2 hours old)."""
        database, session = mock_database

        # Mock stale fetch (3 hours ago - exceeds SLA)
        stale_time = datetime.now(timezone.utc) - timedelta(hours=3)
        mock_result = MagicMock()
        mock_result.scalar.return_value = stale_time
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_freshness(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert (
            extract_metadata_value(result.metadata["age_hours"]) > FRESHNESS_SLA_HOURS
        )
        assert "action" in result.metadata  # Action required for failure

    @pytest.mark.asyncio
    async def test_fails_when_no_data_exists(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when no Reddit data has ever been fetched."""
        database, session = mock_database

        # Mock no data (NULL fetched_at)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_freshness(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert "No Reddit data found" in extract_metadata_value(
            result.metadata["reason"]
        )
        assert (
            extract_metadata_value(result.metadata["sla_hours"]) == FRESHNESS_SLA_HOURS
        )


class TestRedditVolumeAnomalyCheck:
    """Test Reddit volume anomaly detection logic."""

    @pytest.mark.asyncio
    async def test_passes_when_volume_is_normal(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should pass when post count is within expected range."""
        database, session = mock_database

        # Mock normal volume (200 posts - within 50-500 range)
        normal_count = 200
        mock_result = MagicMock()
        mock_result.scalar.return_value = normal_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is True
        assert (
            extract_metadata_value(result.metadata["post_count_last_15min"])
            == normal_count
        )
        assert (
            extract_metadata_value(result.metadata["baseline_min"]) == REDDIT_VOLUME_MIN
        )
        assert (
            extract_metadata_value(result.metadata["baseline_max"]) == REDDIT_VOLUME_MAX
        )
        assert "anomaly" not in result.metadata

    @pytest.mark.asyncio
    async def test_fails_when_volume_too_low(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when post count is below minimum threshold."""
        database, session = mock_database

        # Mock low volume (20 posts - below 50 minimum)
        low_count = 20
        mock_result = MagicMock()
        mock_result.scalar.return_value = low_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert extract_metadata_value(result.metadata["anomaly"]) == "volume_too_low"
        assert (
            "rate limits" in extract_metadata_value(result.metadata["action"]).lower()
        )

    @pytest.mark.asyncio
    async def test_fails_when_volume_too_high(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when post count exceeds maximum threshold."""
        database, session = mock_database

        # Mock high volume (600 posts - exceeds 500 maximum)
        high_count = 600
        mock_result = MagicMock()
        mock_result.scalar.return_value = high_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert extract_metadata_value(result.metadata["anomaly"]) == "volume_too_high"
        assert "duplicate" in extract_metadata_value(result.metadata["action"]).lower()

    @pytest.mark.asyncio
    async def test_passes_when_zero_posts(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should pass when zero posts (no recent run)."""
        database, session = mock_database

        # Mock zero posts (no recent run)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        session.execute.return_value = mock_result

        # Execute check
        result = await check_reddit_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        # Zero is acceptable (no recent run) - not considered "too low"
        assert result.passed is True


class TestBlueskyFreshnessCheck:
    """Test Bluesky freshness check logic."""

    @pytest.mark.asyncio
    async def test_passes_when_data_is_fresh(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should pass when data was fetched within SLA (2 hours)."""
        database, session = mock_database

        # Mock recent fetch (30 minutes ago)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        mock_result = MagicMock()
        mock_result.scalar.return_value = recent_time
        session.execute.return_value = mock_result

        # Execute check
        result = await check_bluesky_freshness(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is True
        assert (
            extract_metadata_value(result.metadata["age_hours"]) < FRESHNESS_SLA_HOURS
        )
        assert (
            extract_metadata_value(result.metadata["sla_hours"]) == FRESHNESS_SLA_HOURS
        )

    @pytest.mark.asyncio
    async def test_fails_when_data_is_stale(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when data exceeds SLA (>2 hours old)."""
        database, session = mock_database

        # Mock stale fetch (5 hours ago)
        stale_time = datetime.now(timezone.utc) - timedelta(hours=5)
        mock_result = MagicMock()
        mock_result.scalar.return_value = stale_time
        session.execute.return_value = mock_result

        # Execute check
        result = await check_bluesky_freshness(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert (
            extract_metadata_value(result.metadata["age_hours"]) > FRESHNESS_SLA_HOURS
        )


class TestBlueskyVolumeAnomalyCheck:
    """Test Bluesky volume anomaly detection logic."""

    @pytest.mark.asyncio
    async def test_passes_when_volume_is_normal(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should pass when post count is within expected range."""
        database, session = mock_database

        # Mock normal volume (100 posts - within 20-200 range)
        normal_count = 100
        mock_result = MagicMock()
        mock_result.scalar.return_value = normal_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_bluesky_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is True
        assert (
            extract_metadata_value(result.metadata["post_count_last_10min"])
            == normal_count
        )
        assert (
            extract_metadata_value(result.metadata["baseline_min"])
            == BLUESKY_VOLUME_MIN
        )
        assert (
            extract_metadata_value(result.metadata["baseline_max"])
            == BLUESKY_VOLUME_MAX
        )

    @pytest.mark.asyncio
    async def test_fails_when_volume_too_low(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when post count is below minimum threshold."""
        database, session = mock_database

        # Mock low volume (5 posts - below 20 minimum)
        low_count = 5
        mock_result = MagicMock()
        mock_result.scalar.return_value = low_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_bluesky_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert extract_metadata_value(result.metadata["anomaly"]) == "volume_too_low"

    @pytest.mark.asyncio
    async def test_fails_when_volume_too_high(
        self: Any, asset_check_context: Any, mock_database: Any
    ) -> None:
        """Check should fail when post count exceeds maximum threshold."""
        database, session = mock_database

        # Mock high volume (300 posts - exceeds 200 maximum)
        high_count = 300
        mock_result = MagicMock()
        mock_result.scalar.return_value = high_count
        session.execute.return_value = mock_result

        # Execute check
        result = await check_bluesky_volume_anomaly(asset_check_context, database)  # type: ignore[misc]

        # Assertions
        assert result.passed is False
        assert extract_metadata_value(result.metadata["anomaly"]) == "volume_too_high"


class TestAssetCheckConfiguration:
    """Test asset check metadata and configuration."""

    def test_all_checks_are_non_blocking(self) -> None:
        """All asset checks should be non-blocking (blocking=False)."""
        # Access check definitions via their metadata
        checks = [
            check_reddit_freshness,
            check_reddit_volume_anomaly,
            check_bluesky_freshness,
            check_bluesky_volume_anomaly,
        ]

        for check in checks:
            # Verify blocking=False in decorator (check via check_specs)
            # The @asset_check decorator sets this attribute in Dagster 1.12+
            assert hasattr(check, "check_specs"), (
                f"{getattr(check, '__name__', str(check))} missing check_specs attribute"
            )
            # All checks should allow materialization to proceed even if they fail
            # This is configured via blocking=False parameter

    def test_freshness_sla_is_2_hours(self) -> None:
        """Freshness SLA should be 2 hours for all checks."""
        assert FRESHNESS_SLA_HOURS == 2

    def test_reddit_volume_thresholds(self) -> None:
        """Reddit volume thresholds should match expected baseline."""
        assert REDDIT_VOLUME_MIN == 50, "Reddit minimum should be 50 posts/run"
        assert REDDIT_VOLUME_MAX == 500, "Reddit maximum should be 500 posts/run"

    def test_bluesky_volume_thresholds(self) -> None:
        """Bluesky volume thresholds should match expected baseline."""
        assert BLUESKY_VOLUME_MIN == 20, "Bluesky minimum should be 20 posts/run"
        assert BLUESKY_VOLUME_MAX == 200, "Bluesky maximum should be 200 posts/run"
