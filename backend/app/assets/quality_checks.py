"""
Dagster asset checks for data quality monitoring (Story 4-7).

Implements non-blocking asset checks for:
- Freshness: Ensures data is recent (SLA: 2 hours)
- Volume anomaly: Detects unusual post counts (baseline thresholds)

All checks are non-blocking (blocking=False) to allow asset materialization even if checks fail.
This provides observability without stopping the pipeline.

Asset Checks:
1. check_reddit_freshness - Ensures Reddit posts fetched within 2 hours
2. check_reddit_volume_anomaly - Detects abnormal Reddit post volume
3. check_bluesky_freshness - Ensures Bluesky posts fetched within 2 hours
4. check_bluesky_volume_anomaly - Detects abnormal Bluesky post volume
"""

from datetime import datetime, timedelta, timezone

import structlog
from dagster import AssetCheckExecutionContext, AssetCheckResult, asset_check
from sqlalchemy import func, select

from app.models.reddit import RawRedditPost
from app.models.social import RawBlueskyPost
from app.resources.database import DatabaseResource

logger = structlog.get_logger()

# Freshness SLA: Maximum age before considered stale (2 hours)
FRESHNESS_SLA_HOURS = 2

# Volume anomaly thresholds (based on observed patterns)
REDDIT_VOLUME_MIN = 50  # Minimum expected posts per run
REDDIT_VOLUME_MAX = 500  # Maximum expected posts per run (anomaly if exceeded)
BLUESKY_VOLUME_MIN = 20  # Minimum expected posts per run
BLUESKY_VOLUME_MAX = 200  # Maximum expected posts per run


@asset_check(
    asset="extract_reddit_posts",
    blocking=False,  # Non-blocking: Asset materializes even if check fails
    description="Ensures Reddit posts were fetched within the last 2 hours (freshness SLA)",
)
async def check_reddit_freshness(
    _context: AssetCheckExecutionContext,
    database: DatabaseResource,
) -> AssetCheckResult:
    """
    Check Reddit data freshness (AC9).

    SLA: Data should be fetched within last 2 hours.
    Failure indicates: Extract schedule not running or failing silently.
    """
    async with database.get_session() as session:
        # Query most recent fetched_at timestamp
        stmt = select(func.max(RawRedditPost.fetched_at))
        result = await session.execute(stmt)
        last_fetch = result.scalar()

        if not last_fetch:
            # No data ever fetched - fail check
            return AssetCheckResult(
                passed=False,
                metadata={
                    "reason": "No Reddit data found in database",
                    "sla_hours": FRESHNESS_SLA_HOURS,
                    "action": "Verify extract_reddit_posts is running",
                },
            )

        # Calculate age in hours
        now = datetime.now(timezone.utc)
        age = now - last_fetch
        age_hours = age.total_seconds() / 3600

        passed = age_hours < FRESHNESS_SLA_HOURS

        metadata = {
            "last_fetch_utc": last_fetch.isoformat(),
            "age_hours": round(age_hours, 2),
            "sla_hours": FRESHNESS_SLA_HOURS,
        }

        if not passed:
            metadata["action"] = "Check extract_reddit_posts schedule and logs"

        return AssetCheckResult(passed=passed, metadata=metadata)


@asset_check(
    asset="extract_reddit_posts",
    blocking=False,
    description="Detects abnormal Reddit post volume (baseline: 50-500 posts per run)",
)
async def check_reddit_volume_anomaly(
    _context: AssetCheckExecutionContext,
    database: DatabaseResource,
) -> AssetCheckResult:
    """
    Check Reddit volume for anomalies (AC9).

    Baseline: 50-500 posts per run (based on observed patterns).
    Anomalies indicate: API issues, rate limiting, or data quality problems.
    """
    async with database.get_session() as session:
        # Count posts fetched in last run (last 15 minutes)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        stmt = select(func.count(RawRedditPost.post_id)).where(
            RawRedditPost.fetched_at >= cutoff_time
        )
        result = await session.execute(stmt)
        recent_count = result.scalar() or 0

        # Check if volume is within expected range
        is_too_low = recent_count > 0 and recent_count < REDDIT_VOLUME_MIN
        is_too_high = recent_count > REDDIT_VOLUME_MAX

        passed = not (is_too_low or is_too_high)

        metadata = {
            "post_count_last_15min": recent_count,
            "baseline_min": REDDIT_VOLUME_MIN,
            "baseline_max": REDDIT_VOLUME_MAX,
        }

        if is_too_low:
            metadata["anomaly"] = "volume_too_low"
            metadata["action"] = "Check Reddit API rate limits or subreddit activity"
        elif is_too_high:
            metadata["anomaly"] = "volume_too_high"
            metadata["action"] = "Check for duplicate posts or bot activity"

        return AssetCheckResult(passed=passed, metadata=metadata)


@asset_check(
    asset="extract_bluesky_posts",
    blocking=False,
    description="Ensures Bluesky posts were fetched within the last 2 hours (freshness SLA)",
)
async def check_bluesky_freshness(
    _context: AssetCheckExecutionContext,
    database: DatabaseResource,
) -> AssetCheckResult:
    """
    Check Bluesky data freshness (AC9).

    SLA: Data should be fetched within last 2 hours.
    Failure indicates: Extract schedule not running or failing silently.
    """
    async with database.get_session() as session:
        # Query most recent fetched_at timestamp
        stmt = select(func.max(RawBlueskyPost.fetched_at))
        result = await session.execute(stmt)
        last_fetch = result.scalar()

        if not last_fetch:
            # No data ever fetched - fail check
            return AssetCheckResult(
                passed=False,
                metadata={
                    "reason": "No Bluesky data found in database",
                    "sla_hours": FRESHNESS_SLA_HOURS,
                    "action": "Verify extract_bluesky_posts is running",
                },
            )

        # Calculate age in hours
        now = datetime.now(timezone.utc)
        age = now - last_fetch
        age_hours = age.total_seconds() / 3600

        passed = age_hours < FRESHNESS_SLA_HOURS

        metadata = {
            "last_fetch_utc": last_fetch.isoformat(),
            "age_hours": round(age_hours, 2),
            "sla_hours": FRESHNESS_SLA_HOURS,
        }

        if not passed:
            metadata["action"] = "Check extract_bluesky_posts schedule and logs"

        return AssetCheckResult(passed=passed, metadata=metadata)


@asset_check(
    asset="extract_bluesky_posts",
    blocking=False,
    description="Detects abnormal Bluesky post volume (baseline: 20-200 posts per run)",
)
async def check_bluesky_volume_anomaly(
    _context: AssetCheckExecutionContext,
    database: DatabaseResource,
) -> AssetCheckResult:
    """
    Check Bluesky volume for anomalies (AC9).

    Baseline: 20-200 posts per run (based on observed patterns).
    Anomalies indicate: API issues, rate limiting, or data quality problems.
    """
    async with database.get_session() as session:
        # Count posts fetched in last run (last 10 minutes)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        stmt = select(func.count(RawBlueskyPost.post_uri)).where(
            RawBlueskyPost.fetched_at >= cutoff_time
        )
        result = await session.execute(stmt)
        recent_count = result.scalar() or 0

        # Check if volume is within expected range
        is_too_low = recent_count > 0 and recent_count < BLUESKY_VOLUME_MIN
        is_too_high = recent_count > BLUESKY_VOLUME_MAX

        passed = not (is_too_low or is_too_high)

        metadata = {
            "post_count_last_10min": recent_count,
            "baseline_min": BLUESKY_VOLUME_MIN,
            "baseline_max": BLUESKY_VOLUME_MAX,
        }

        if is_too_low:
            metadata["anomaly"] = "volume_too_low"
            metadata["action"] = "Check Bluesky API status or feed activity"
        elif is_too_high:
            metadata["anomaly"] = "volume_too_high"
            metadata["action"] = "Check for duplicate posts or spam"

        return AssetCheckResult(passed=passed, metadata=metadata)
