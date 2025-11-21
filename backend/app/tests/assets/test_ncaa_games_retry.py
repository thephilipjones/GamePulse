"""
Tests for NCAA games Dagster asset retry logic and error handling.

Validates Story 2-5 acceptance criteria:
- AC1: Verify Dagster RetryPolicy configuration (max_retries=3, delay=2, backoff=exponential)
- AC2: Verify NCAA Client retry decorator (validated in test_ncaa_client_retry.py)

Additional ACs validated via alternative methods:
- AC3-AC5: NCAA client retry logic (test_ncaa_client_retry.py)
- AC6: Daemon resilience during network failure (manual test via test_network_failure.sh)
- AC7: Partial failure handling (code review + manual Dagster UI validation)
- AC8: Dagster UI retry timeline (manual verification in Dagster UI)
- AC9: Cached data retention (code review + manual Dagster UI validation)
- AC10: Structured logging with exc_info=True (code review of ncaa_games.py)

Rationale for Manual Validation (AC7, AC9):
Following Story 2-4 pattern - Dagster asset testing via manual UI materialization
preferred over async DB unit tests requiring greenlet dependency and complex
event loop management. See docs/stories/future-enhancements.md for context.
"""

import pytest

# Skip tests if Dagster can't be imported (Python 3.14 incompatibility)
try:
    from dagster import Backoff, RetryPolicy

    from app.assets.ncaa_games import ncaa_games_today

    DAGSTER_AVAILABLE = True
except (ImportError, Exception):
    DAGSTER_AVAILABLE = False
    Backoff = None  # type: ignore[assignment, misc]
    RetryPolicy = None  # type: ignore[assignment, misc]
    ncaa_games_today = None  # type: ignore[assignment]


@pytest.mark.skipif(
    not DAGSTER_AVAILABLE,
    reason="Dagster not compatible with Python 3.14+ (Pydantic type annotation issue)",
)
class TestNCAAGamesRetryPolicy:
    """Test AC1: Verify Dagster RetryPolicy configuration."""

    def test_retry_policy_configuration(self) -> None:
        """
        AC1: Verify ncaa_games_today asset has correct RetryPolicy configuration.

        Expected config (from Story 2-4):
        - max_retries: 3
        - delay: 2 seconds (initial delay)
        - backoff: Backoff.EXPONENTIAL (2s, 4s, 8s)

        Test validates:
        - Asset decorator includes retry_policy
        - RetryPolicy parameters match specification
        - Backoff strategy is exponential
        """
        # Access asset definition
        assets_def = ncaa_games_today

        # Validate retry_policy is configured
        # In Dagster 1.12+, retry_policy is stored in jobs, not assets
        # For validation, we verify the asset was created with @asset decorator
        # The actual retry_policy is defined in the ncaa_games.py file
        # We can verify it by importing and checking the decorator params

        # Access the underlying Python function's decorator metadata
        # The retry_policy is accessible via op_def
        op_def = assets_def.op

        # Validate retry_policy is configured
        assert op_def.retry_policy is not None, (
            "Asset should have retry_policy configured"
        )

        retry_policy: RetryPolicy = op_def.retry_policy

        # Validate retry policy parameters
        assert retry_policy.max_retries == 3, (
            "max_retries should be 3 (matches client layer)"
        )
        assert retry_policy.delay == 2, "Initial delay should be 2 seconds"
        assert retry_policy.backoff == Backoff.EXPONENTIAL, (
            "Backoff strategy should be EXPONENTIAL"
        )

        # Exponential backoff formula: delay * (backoff ** attempt)
        # Attempt 1: 2s, Attempt 2: 4s, Attempt 3: 8s
        # This matches the NCAA client retry timing (2s, 4s, 8s)

    def test_asset_metadata_includes_retry_info(self) -> None:
        """
        AC1: Verify asset metadata exposes retry configuration for observability.

        Dagster UI should display retry policy in asset details.
        Test validates asset definition includes required metadata.
        """
        assets_def = ncaa_games_today

        # Get asset spec
        asset_spec = list(assets_def.specs)[0]

        # Validate asset metadata
        assert asset_spec.key.path == ["ncaa_games_today"], (
            "Asset key should be ncaa_games_today"
        )
        assert asset_spec.group_name == "sports_data", (
            "Asset should be in sports_data group"
        )

        # Validate retry policy is accessible for Dagster UI
        assert assets_def.op.retry_policy is not None, (
            "RetryPolicy should be exposed for Dagster UI"
        )
