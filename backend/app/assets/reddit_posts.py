"""
Dagster asset for Reddit post extraction with multi-subreddit support (Epic 4).

Asset: extract_reddit_posts
- Fetches posts from all active subreddits (CollegeBasketball, CFB, sports)
- Implements incremental extraction via cursor (MAX(fetched_at) per subreddit)
- Stores dual format: parsed columns + complete raw_json JSONB
- Idempotent via ON CONFLICT DO NOTHING
- Respects 10 QPM rate limit via RedditClient token bucket
- Auto-runs every 10 minutes via schedule

Schedule: extract_reddit_posts_schedule
- Cron: */10 * * * * (every 10 minutes)
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
from app.models.reddit import DimSubreddit, RawRedditPost
from app.resources.database import DatabaseResource
from app.services.reddit_client import RedditClient

logger = structlog.get_logger()


@asset(
    name="extract_reddit_posts",
    description="Multi-subreddit Reddit post extraction with incremental cursor and dual storage (parsed + raw JSON)",
    group_name="social_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def extract_reddit_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, Any]:
    """
    Extract Reddit posts from all active subreddits with incremental extraction.

    Features:
    - Multi-subreddit: Fetches from all active subreddits in dim_subreddit
    - Incremental: Uses MAX(fetched_at) cursor per subreddit
    - Dual storage: Parsed columns + complete raw_json JSONB
    - Idempotent: ON CONFLICT DO NOTHING on composite PK (post_id, fetched_at)
    - Rate limited: Token bucket 10 QPM (handled by RedditClient)
    - Toggleable: Respects REDDIT_POLLING_ENABLED env var

    Returns:
        Metadata dict with keys:
        - subreddits_fetched: Number of active subreddits polled
        - total_posts_fetched: Total posts from Reddit API
        - total_posts_inserted: Total new posts inserted to DB
        - posts_by_subreddit: Dict mapping subreddit -> insert count
        - cursor_times: Dict mapping subreddit -> last fetched_at
    """
    # Check if polling is enabled
    if not settings.REDDIT_POLLING_ENABLED:
        context.log.info("Reddit polling disabled via REDDIT_POLLING_ENABLED=false")
        return {
            "subreddits_fetched": 0,
            "total_posts_fetched": 0,
            "total_posts_inserted": 0,
            "posts_by_subreddit": {},
            "cursor_times": {},
        }

    context.log.info("extract_reddit_posts_started polling_enabled=True")

    total_posts_fetched = 0
    total_posts_inserted = 0
    posts_by_subreddit: dict[str, int] = {}
    cursor_times: dict[str, str] = {}

    async with database.get_session() as session:
        # Step 1: Query active subreddits
        active_subreddits = await _get_active_subreddits(session)

        if not active_subreddits:
            context.log.warning("No active subreddits found in dim_subreddit")
            return {
                "subreddits_fetched": 0,
                "total_posts_fetched": 0,
                "total_posts_inserted": 0,
                "posts_by_subreddit": {},
                "cursor_times": {},
            }

        context.log.info(
            f"active_subreddits_loaded count={len(active_subreddits)} "
            f"subreddits={[s.subreddit_name for s in active_subreddits]}"
        )

        # Step 2: Fetch posts from each subreddit
        async with RedditClient() as reddit:
            for subreddit in active_subreddits:
                try:
                    # Get incremental cursor (last fetched time for this subreddit)
                    cursor = await _get_cursor_for_subreddit(
                        session, subreddit.subreddit_name, context
                    )

                    # Fetch posts from Reddit API
                    response = await reddit.fetch_posts(
                        subreddit=subreddit.subreddit_name,
                        limit=100,
                    )

                    # Extract posts from Reddit API response
                    children = response.get("data", {}).get("children", [])
                    posts_fetched = len(children)
                    total_posts_fetched += posts_fetched

                    if posts_fetched == 0:
                        context.log.info(
                            f"no_posts_fetched subreddit={subreddit.subreddit_name}"
                        )
                        posts_by_subreddit[subreddit.subreddit_name] = 0
                        continue

                    # Step 3: Transform and insert posts
                    posts_inserted = await _insert_posts(
                        session,
                        children,
                        subreddit.subreddit_name,
                        cursor,
                        context,
                    )

                    total_posts_inserted += posts_inserted
                    posts_by_subreddit[subreddit.subreddit_name] = posts_inserted

                    # Store cursor time for metadata
                    cursor_times[subreddit.subreddit_name] = (
                        cursor.isoformat() if cursor else "null"
                    )

                    context.log.info(
                        f"subreddit_extraction_completed subreddit={subreddit.subreddit_name} "
                        f"posts_fetched={posts_fetched} posts_inserted={posts_inserted}"
                    )

                except Exception as e:
                    context.log.error(
                        f"subreddit_extraction_failed subreddit={subreddit.subreddit_name} "
                        f"error={str(e)} error_type={type(e).__name__}"
                    )
                    # Continue to next subreddit instead of failing entire asset
                    posts_by_subreddit[subreddit.subreddit_name] = 0
                    continue

    context.log.info(
        f"extract_reddit_posts_completed subreddits_fetched={len(active_subreddits)} "
        f"total_posts_fetched={total_posts_fetched} total_posts_inserted={total_posts_inserted}"
    )

    return {
        "subreddits_fetched": len(active_subreddits),
        "total_posts_fetched": total_posts_fetched,
        "total_posts_inserted": total_posts_inserted,
        "posts_by_subreddit": posts_by_subreddit,
        "cursor_times": cursor_times,
    }


async def _get_active_subreddits(
    session: AsyncSession,
) -> list[DimSubreddit]:
    """Query all active subreddits from dim_subreddit."""
    stmt = select(DimSubreddit).where(DimSubreddit.is_active)  # type: ignore[arg-type]
    result = await session.execute(stmt)
    subreddits = list(result.scalars().all())
    return subreddits


async def _get_cursor_for_subreddit(
    session: AsyncSession,
    subreddit_name: str,
    context: AssetExecutionContext,
) -> datetime | None:
    """
    Get incremental extraction cursor for a subreddit.

    Returns MAX(fetched_at) for posts from this subreddit, or None if no posts exist.
    """
    stmt = (
        select(RawRedditPost.fetched_at)  # type: ignore[call-overload]
        .where(RawRedditPost.subreddit == subreddit_name)
        .order_by(RawRedditPost.fetched_at.desc())  # type: ignore[attr-defined]
        .limit(1)
    )
    result = await session.execute(stmt)
    cursor = result.scalar_one_or_none()

    if cursor:
        context.log.debug(
            f"incremental_cursor_found subreddit={subreddit_name} cursor={cursor.isoformat()}"
        )
    else:
        context.log.debug(
            f"incremental_cursor_none subreddit={subreddit_name} "
            f"message='First extraction for this subreddit'"
        )

    return cursor


async def _insert_posts(
    session: AsyncSession,
    children: list[dict[str, Any]],
    subreddit_name: str,
    cursor: datetime | None,
    context: AssetExecutionContext,
) -> int:
    """
    Transform Reddit API response to RawRedditPost and insert with idempotency.

    Args:
        children: Reddit API response data.children array
        subreddit_name: Subreddit name for FK reference
        cursor: Last fetched_at timestamp for filtering
        context: Dagster execution context for logging

    Returns:
        Number of posts inserted (ON CONFLICT skips count as 0)
    """
    now = datetime.now(timezone.utc)
    posts_inserted = 0

    for child in children:
        # Extract post data from Reddit API response structure
        post_data = child.get("data", {})

        # Parse Reddit created_utc (Unix timestamp) to datetime
        created_utc = post_data.get("created_utc")
        if not created_utc:
            context.log.warning(
                f"post_missing_created_utc post_id={post_data.get('id')}"
            )
            continue

        post_created_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)

        # Skip posts older than cursor (already processed)
        if cursor and post_created_at <= cursor:
            continue

        # Build RawRedditPost data dict for insert
        raw_post: dict[str, Any] = {
            "post_id": post_data.get("id"),
            "fetched_at": now,
            "subreddit": subreddit_name,
            "post_created_at": post_created_at,
            # Parsed metadata columns
            "author": post_data.get("author"),
            "title": post_data.get("title"),
            "selftext": post_data.get("selftext"),
            "score": post_data.get("score"),
            "num_comments": post_data.get("num_comments"),
            "upvote_ratio": post_data.get("upvote_ratio"),
            "permalink": post_data.get("permalink"),
            "flair_text": post_data.get("link_flair_text"),
            "post_type": _determine_post_type(post_data),
            # Complete raw JSON (dual storage for future ML)
            "raw_json": post_data,
            # Game matching fields (default values for Story 4-4)
            "matched_to_game": False,
            "match_confidence": None,
            "processed_at": None,
        }

        # Upsert with ON CONFLICT DO NOTHING (idempotency on composite PK)
        stmt = insert(RawRedditPost).values(raw_post)
        stmt = stmt.on_conflict_do_nothing(index_elements=["post_id", "fetched_at"])

        result = await session.execute(stmt)

        # PostgreSQL returns rowcount=0 for ON CONFLICT DO NOTHING skips
        if result.rowcount > 0:  # type: ignore[attr-defined]
            posts_inserted += 1

    await session.commit()

    return posts_inserted


def _determine_post_type(post_data: dict[str, Any]) -> str | None:
    """
    Determine Reddit post type from API response.

    Types: "link", "self", "image", "video"
    """
    if post_data.get("is_self"):
        return "self"
    elif post_data.get("post_hint") == "image":
        return "image"
    elif post_data.get("is_video"):
        return "video"
    elif post_data.get("url"):
        return "link"
    return None


# Dagster job and schedule definitions

reddit_posts_job = define_asset_job(
    name="materialize_reddit_posts",
    selection="extract_reddit_posts",
    description="Manually materialize Reddit posts asset",
)

reddit_posts_schedule = ScheduleDefinition(
    name="extract_reddit_posts_schedule",
    job=reddit_posts_job,
    cron_schedule="*/10 * * * *",  # Every 10 minutes
    description="Extract Reddit posts every 10 minutes from all active subreddits",
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start on daemon init
)
