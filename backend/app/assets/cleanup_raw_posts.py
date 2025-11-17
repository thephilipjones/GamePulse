"""
Dagster asset for cleaning up old unmatched raw social posts (Story 4-7).

Asset: cleanup_unmatched_raw_posts
- Deletes old posts that were never matched to games
- Runs daily at 2 AM ET (low activity period)
- Retention: 7 days for unmatched posts (vs 90 days for matched via TimescaleDB policy)
- Estimated savings: ~200 MB over 90 days

Cleanup Logic:
- DELETE FROM raw_reddit_posts WHERE created_at < NOW() - 7 days AND matched_to_game = FALSE
- DELETE FROM raw_bluesky_posts WHERE created_at < NOW() - 7 days AND matched_to_game = FALSE

Rationale:
- Unmatched posts have no value for sentiment analysis (can't link to games)
- 7-day retention allows for debugging/manual review if needed
- Matched posts retained for 90 days via TimescaleDB compression policy
"""

from datetime import datetime, timedelta, timezone

import structlog
from dagster import (
    Backoff,
    DefaultScheduleStatus,
    MaterializeResult,
    RetryPolicy,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from sqlalchemy import delete

from app.models.reddit import RawRedditPost
from app.models.social import RawBlueskyPost, StgSocialPost
from app.resources.database import DatabaseResource

logger = structlog.get_logger()

# Retention period for unmatched posts (7 days)
UNMATCHED_RETENTION_DAYS = 7


@asset(
    name="cleanup_unmatched_raw_posts",
    description="Delete old unmatched posts from raw tables (7-day retention)",
    group_name="social_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def cleanup_unmatched_raw_posts(
    context,  # type: ignore[no-untyped-def]
    database: DatabaseResource,
) -> MaterializeResult:  # type: ignore[type-arg]
    """
    Clean up old unmatched posts from raw tables (AC5).

    Deletes posts that:
    1. Were created more than 7 days ago
    2. Were NOT matched to any game (checked via stg_social_posts.matched_to_game)

    This saves storage while preserving matched posts for sentiment analysis.

    Returns:
        MaterializeResult with deletion counts
    """
    context.log.info("cleanup_unmatched_raw_posts_started")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=UNMATCHED_RETENTION_DAYS)
    reddit_deleted = 0
    bluesky_deleted = 0

    async with database.get_session() as session:
        # Step 1: Find Reddit post IDs to delete
        # Strategy: Delete from raw_reddit_posts if NOT EXISTS in stg_social_posts with matched_to_game=TRUE
        reddit_ids_to_delete = await _find_unmatched_reddit_posts(session, cutoff_date)

        if reddit_ids_to_delete:
            # Delete matching raw_reddit_posts records
            stmt_delete = delete(RawRedditPost).where(
                RawRedditPost.post_id.in_(reddit_ids_to_delete)  # type: ignore[attr-defined]
            )
            result = await session.execute(stmt_delete)
            reddit_deleted = result.rowcount or 0  # type: ignore[attr-defined]
            context.log.info(f"deleted_old_reddit_posts count={reddit_deleted}")

        # Step 2: Find Bluesky post URIs to delete
        bluesky_uris_to_delete = await _find_unmatched_bluesky_posts(
            session, cutoff_date
        )

        if bluesky_uris_to_delete:
            # Delete matching raw_bluesky_posts records
            stmt_delete = delete(RawBlueskyPost).where(
                RawBlueskyPost.post_uri.in_(bluesky_uris_to_delete)  # type: ignore[attr-defined]
            )
            result = await session.execute(stmt_delete)
            bluesky_deleted = result.rowcount or 0  # type: ignore[attr-defined]
            context.log.info(f"deleted_old_bluesky_posts count={bluesky_deleted}")

        # Commit deletions
        await session.commit()

    total_deleted = reddit_deleted + bluesky_deleted

    context.log.info(
        "cleanup_unmatched_raw_posts_completed",
        extra={
            "reddit_posts_deleted": reddit_deleted,
            "bluesky_posts_deleted": bluesky_deleted,
            "total_posts_deleted": total_deleted,
            "cutoff_date": cutoff_date.isoformat(),
        },
    )

    return MaterializeResult(
        metadata={
            "reddit_posts_deleted": reddit_deleted,
            "bluesky_posts_deleted": bluesky_deleted,
            "total_posts_deleted": total_deleted,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": UNMATCHED_RETENTION_DAYS,
        }
    )


async def _find_unmatched_reddit_posts(session, cutoff_date: datetime) -> list[str]:  # type: ignore[no-untyped-def]
    """
    Find Reddit post IDs that are old and unmatched.

    Returns IDs from raw_reddit_posts where:
    - created_at < cutoff_date (older than 7 days)
    - NOT EXISTS in stg_social_posts with matched_to_game=TRUE
    """
    from sqlalchemy import select

    # Subquery: Check if post exists in stg_social_posts with matched_to_game=TRUE
    matched_subquery = (
        select(1)  # type: ignore[call-overload]
        .select_from(StgSocialPost)
        .where(StgSocialPost.platform == "reddit")  # type: ignore[arg-type]
        .where(StgSocialPost.post_id == RawRedditPost.post_id)  # type: ignore[arg-type]
        .where(StgSocialPost.matched_to_game == True)  # noqa: E712  # type: ignore[arg-type]
        .exists()
    )

    # Main query: Find unmatched old posts
    stmt = (
        select(RawRedditPost.post_id)  # type: ignore[call-overload]
        .where(RawRedditPost.post_created_at < cutoff_date)  # type: ignore[arg-type]
        .where(~matched_subquery)  # NOT EXISTS
    )

    result = await session.execute(stmt)
    return [row[0] for row in result.fetchall()]


async def _find_unmatched_bluesky_posts(session, cutoff_date: datetime) -> list[str]:  # type: ignore[no-untyped-def]
    """
    Find Bluesky post URIs that are old and unmatched.

    Returns URIs from raw_bluesky_posts where:
    - created_at < cutoff_date (older than 7 days)
    - NOT EXISTS in stg_social_posts with matched_to_game=TRUE
    """
    from sqlalchemy import select

    # Subquery: Check if post exists in stg_social_posts with matched_to_game=TRUE
    matched_subquery = (
        select(1)  # type: ignore[call-overload]
        .select_from(StgSocialPost)
        .where(StgSocialPost.platform == "bluesky")  # type: ignore[arg-type]
        .where(StgSocialPost.post_id == RawBlueskyPost.post_uri)  # type: ignore[arg-type]
        .where(StgSocialPost.matched_to_game == True)  # noqa: E712  # type: ignore[arg-type]
        .exists()
    )

    # Main query: Find unmatched old posts
    stmt = (
        select(RawBlueskyPost.post_uri)  # type: ignore[call-overload]
        .where(RawBlueskyPost.created_at < cutoff_date)  # type: ignore[arg-type]
        .where(~matched_subquery)  # NOT EXISTS
    )

    result = await session.execute(stmt)
    return [row[0] for row in result.fetchall()]


# Define cleanup job for manual materialization
cleanup_unmatched_posts_job = define_asset_job(
    name="cleanup_unmatched_posts_job",
    selection="cleanup_unmatched_raw_posts",
    description="Delete old unmatched posts from raw tables",
)

# Define cleanup schedule: Daily at 2 AM ET (low activity period)
cleanup_unmatched_posts_schedule = ScheduleDefinition(
    name="cleanup_unmatched_posts_schedule",
    job=cleanup_unmatched_posts_job,
    cron_schedule="0 2 * * *",  # Daily at 2 AM
    description="Clean up old unmatched posts daily (7-day retention)",
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start for continuous cleanup
)
