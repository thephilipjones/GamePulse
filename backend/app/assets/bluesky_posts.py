"""
Dagster asset for Bluesky post extraction with multi-hashtag support (Epic 4).

Asset: extract_bluesky_posts
- Fetches posts from configured hashtags (CollegeBasketball, MarchMadness, NCAAM)
- Implements incremental extraction via cursor (MAX(fetched_at))
- Stores dual format: parsed columns + complete raw_json JSONB
- Idempotent via ON CONFLICT DO NOTHING on PK (post_uri)
- Deduplicates posts across hashtags (same post can have multiple hashtags)
- Respects 5000 points/hour rate limit via BlueskyClient
- Auto-runs every 5 minutes via schedule

Schedule: extract_bluesky_posts_schedule
- Cron: */5 * * * * (every 5 minutes)
- Timezone: America/New_York
- Auto-start on daemon init
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from dagster import (
    AssetExecutionContext,
    Backoff,
    DefaultScheduleStatus,
    RetryPolicy,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.social import RawBlueskyPost
from app.resources.database import DatabaseResource
from app.services.bluesky_client import BlueskyClient

logger = structlog.get_logger()


@asset(
    name="extract_bluesky_posts",
    description="Multi-hashtag Bluesky post extraction with incremental cursor and dual storage (parsed + raw JSON)",
    group_name="social_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def extract_bluesky_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Extract Bluesky posts from configured hashtags with incremental extraction.

    Features:
    - Multi-hashtag: Fetches from all hashtags in BLUESKY_HASHTAGS env var
    - Incremental: Uses MAX(fetched_at) cursor across all hashtags
    - Deduplication: Same post can appear under multiple hashtags - deduped by post_uri
    - Dual storage: Parsed columns + complete raw_json JSONB
    - Idempotent: ON CONFLICT DO NOTHING on PK (post_uri)
    - Rate limited: Token bucket 5000 points/hour (handled by BlueskyClient)
    - Credential validation: Raises ValueError if credentials missing

    Returns:
        Metadata dict with keys:
        - posts_extracted: Total posts from Bluesky API (before deduplication)
        - posts_inserted: Total new posts inserted to DB (after deduplication)
        - hashtags_searched: Number of hashtags searched
    """
    # Step 0: Validate credentials
    if not settings.BLUESKY_HANDLE or not settings.BLUESKY_APP_PASSWORD:
        raise ValueError(
            "BLUESKY_HANDLE and BLUESKY_APP_PASSWORD must be configured. "
            "Get app password from: Bluesky Settings → Privacy and Security → App Passwords"
        )

    context.log.info(
        "extract_bluesky_posts_started",
        extra={
            "handle": settings.BLUESKY_HANDLE,
            "hashtags": settings.BLUESKY_HASHTAGS,
        },
    )

    # Parse hashtags from comma-separated env var
    hashtags = [h.strip() for h in settings.BLUESKY_HASHTAGS.split(",") if h.strip()]

    if not hashtags:
        context.log.warning("No hashtags configured in BLUESKY_HASHTAGS")
        return {
            "posts_extracted": 0,
            "posts_inserted": 0,
            "hashtags_searched": 0,
        }

    async with database.get_session() as session:
        # Step 1: Get incremental cursor (last fetched time across ALL posts)
        cursor = await _get_cursor(session, context)

        # Step 2: Fetch posts from all hashtags with deduplication
        async with BlueskyClient() as bluesky:
            try:
                # fetch_all_hashtags handles deduplication by post_uri
                posts = await bluesky.fetch_all_hashtags(
                    hashtags=hashtags,
                    limit=100,  # Per hashtag
                    since=cursor,  # Incremental extraction
                )

                posts_extracted = len(posts)

                if posts_extracted == 0:
                    context.log.info("no_posts_extracted")
                    return {
                        "posts_extracted": 0,
                        "posts_inserted": 0,
                        "hashtags_searched": len(hashtags),
                    }

                # Step 3: Transform and insert posts
                posts_inserted = await _insert_posts(
                    session,
                    posts,
                )

                context.log.info(
                    "extract_bluesky_posts_completed",
                    extra={
                        "posts_extracted": posts_extracted,
                        "posts_inserted": posts_inserted,
                        "hashtags_searched": len(hashtags),
                    },
                )

                return {
                    "posts_extracted": posts_extracted,
                    "posts_inserted": posts_inserted,
                    "hashtags_searched": len(hashtags),
                }

            except Exception as e:
                context.log.error(
                    "extract_bluesky_posts_failed",
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise


async def _get_cursor(
    session: AsyncSession,
    context: AssetExecutionContext,
) -> datetime | None:
    """
    Get incremental extraction cursor.

    Returns MAX(fetched_at) across all Bluesky posts, or None if no posts exist.
    """
    stmt = (
        select(RawBlueskyPost.fetched_at)  # type: ignore[call-overload]
        .order_by(RawBlueskyPost.fetched_at.desc())  # type: ignore[attr-defined]
        .limit(1)
    )
    result = await session.execute(stmt)
    cursor = result.scalar_one_or_none()

    if cursor:
        context.log.debug(
            "incremental_cursor_found",
            extra={"cursor": cursor.isoformat()},
        )
    else:
        context.log.debug(
            "incremental_cursor_none",
            extra={"info": "First extraction - no cursor found"},
        )

    return cursor


async def _insert_posts(
    session: AsyncSession,
    posts: list[dict[str, Any]],
) -> int:
    """
    Transform Bluesky API response to RawBlueskyPost and insert with idempotency.

    Args:
        posts: List of post dicts from BlueskyClient (already deduplicated by URI)

    Returns:
        Number of posts inserted (ON CONFLICT skips count as 0)
    """
    now = datetime.now(timezone.utc)
    posts_inserted = 0

    for post in posts:
        # Parse created_at from ISO format
        created_at_str = post["record"]["createdAt"]
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

        # Build RawBlueskyPost data dict for insert
        raw_post: dict[str, Any] = {
            "post_uri": post["uri"],
            "post_cid": post["cid"],
            "created_at": created_at,
            "fetched_at": now,
            # Author information
            "author_did": post["author"]["did"],
            "author_handle": post["author"].get("handle"),
            # Post content
            "post_text": post["record"].get("text"),
            # Complete raw JSON (dual storage for future ML)
            "raw_json": post["raw_data"],  # Full post data from SDK
            # Game matching fields (default values for Story 4-4)
            "matched_to_game": False,
            "match_confidence": None,
            "processed_at": None,
        }

        # Upsert with ON CONFLICT DO NOTHING (idempotency on composite PK)
        stmt = insert(RawBlueskyPost).values(raw_post)
        stmt = stmt.on_conflict_do_nothing(index_elements=["post_uri", "created_at"])

        result = await session.execute(stmt)

        # PostgreSQL returns rowcount=0 for ON CONFLICT DO NOTHING skips
        if result.rowcount > 0:  # type: ignore[attr-defined]
            posts_inserted += 1

    await session.commit()

    return posts_inserted


# Dagster job and schedule definitions

bluesky_posts_job = define_asset_job(
    name="materialize_bluesky_posts",
    selection="extract_bluesky_posts",
    description="Manually materialize Bluesky posts asset",
)

bluesky_posts_schedule = ScheduleDefinition(
    name="extract_bluesky_posts_schedule",
    job=bluesky_posts_job,
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    description="Extract Bluesky posts every 5 minutes from all configured hashtags",
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start on daemon init
)
