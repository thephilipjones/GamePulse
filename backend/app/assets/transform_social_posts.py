"""
Dagster asset for unified social media post transformation (Story 4-4).

Asset: transform_social_posts
- Transforms raw Reddit and Bluesky posts into unified stg_social_posts table
- Calculates platform-specific engagement scores
- Matches posts to NCAA teams using GameMatcher service (Story 4-5 prerequisite)
- Processes incrementally (WHERE processed_at IS NULL)
- Batch size: 2500 posts per run (optimized for t4g.small)
- Trigger: Auto-materializes when EITHER extract_reddit_posts OR extract_bluesky_posts completes (eager policy)
- Freshness SLA: Maximum 30 minutes from extract to transform complete (Story 4-7)

Transform Logic:
- Reddit: score + num_comments → engagement_score
- Bluesky: likeCount + replyCount → engagement_score
- Normalizes post text: Reddit (title + selftext), Bluesky (post_text)
- Team matching: Identifies team mentions in post text, stores team IDs for game resolution
- Maintains game matching metadata (matched_to_game, match_confidence, matched_teams)
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from dagster import (
    AssetExecutionContext,
    AutoMaterializePolicy,
    Backoff,
    FreshnessPolicy,
    RetryPolicy,
    asset,
)
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reddit import RawRedditPost
from app.models.social import RawBlueskyPost, StgSocialPost
from app.resources.database import DatabaseResource
from app.services.engagement import (
    calculate_bluesky_engagement,
    calculate_reddit_engagement,
)
from app.services.game_matcher import GameMatcher

logger = structlog.get_logger()

# Batch size for incremental processing (optimized for t4g.small)
BATCH_SIZE = 2500


@asset(
    name="transform_social_posts",
    description="Unified transform layer for Reddit and Bluesky posts with engagement scoring",
    group_name="social_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
    # Auto-materialize: Trigger when either Reddit or Bluesky extract completes
    auto_materialize_policy=AutoMaterializePolicy.eager(),
    # Freshness SLA: Maximum 30 minutes from extract to transform complete
    freshness_policy=FreshnessPolicy(maximum_lag_minutes=30),  # type: ignore[call-arg]
    # Dependencies: Runs after either Reddit or Bluesky extract completes
    deps=["extract_reddit_posts", "extract_bluesky_posts"],
)
async def transform_social_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Transform raw social posts into unified stg_social_posts table.

    Features:
    - Platform-agnostic schema with platform discriminator
    - Engagement scoring for prioritization (Reddit: score + comments, Bluesky: likes + replies)
    - Incremental processing (WHERE processed_at IS NULL)
    - Batch processing (2500 posts per run)
    - Marks source posts as processed after successful transform

    Returns:
        Metadata dict with keys:
        - reddit_posts_transformed: Posts from raw_reddit_posts
        - bluesky_posts_transformed: Posts from raw_bluesky_posts
        - total_posts_transformed: Total posts inserted to stg_social_posts
    """
    context.log.info("transform_social_posts_started")

    reddit_transformed = 0
    bluesky_transformed = 0

    async with database.get_session() as session:
        # Step 1: Transform Reddit posts
        reddit_transformed = await _transform_reddit_posts(session, context)

        # Step 2: Transform Bluesky posts
        bluesky_transformed = await _transform_bluesky_posts(session, context)

    total_transformed = reddit_transformed + bluesky_transformed

    context.log.info(
        "transform_social_posts_completed",
        extra={
            "reddit_posts_transformed": reddit_transformed,
            "bluesky_posts_transformed": bluesky_transformed,
            "total_posts_transformed": total_transformed,
        },
    )

    return {
        "reddit_posts_transformed": reddit_transformed,
        "bluesky_posts_transformed": bluesky_transformed,
        "total_posts_transformed": total_transformed,
    }


async def _transform_reddit_posts(
    session: AsyncSession,
    context: AssetExecutionContext,
) -> int:
    """
    Transform Reddit posts from raw_reddit_posts to stg_social_posts.

    Business Logic:
    - Engagement: score + num_comments
    - Post text: title + selftext (concatenated)
    - Filters: WHERE processed_at IS NULL LIMIT 2500

    Returns:
        Number of posts transformed
    """
    # Fetch unprocessed Reddit posts
    stmt = (
        select(RawRedditPost)
        .where(RawRedditPost.processed_at.is_(None))  # type: ignore[union-attr]
        .limit(BATCH_SIZE)
    )
    result = await session.execute(stmt)
    reddit_posts = list(result.scalars().all())

    if not reddit_posts:
        context.log.info("no_unprocessed_reddit_posts")
        return 0

    context.log.info(
        f"transforming_reddit_posts count={len(reddit_posts)} batch_size={BATCH_SIZE}"
    )

    posts_transformed = 0
    now = datetime.now(timezone.utc)

    # Initialize GameMatcher once for batch (loads teams cache)
    matcher = GameMatcher(session)
    await matcher.initialize()

    for post in reddit_posts:
        # Calculate engagement score
        engagement_score = calculate_reddit_engagement(post.score, post.num_comments)

        # Normalize post text (Reddit: title + selftext)
        post_text = ""
        if post.title:
            post_text += post.title
        if post.selftext:
            if post_text:
                post_text += "\n\n"  # Separate title and body
            post_text += post.selftext

        # Match post to teams (Story 4-5 prerequisite)
        matched_teams: list[str] | None = None
        matched_to_game = False
        match_confidence = None

        if post_text:
            match_result = matcher.match_post_to_teams(post_text)
            if match_result.matched_teams:
                matched_teams = match_result.matched_teams
                matched_to_game = True
                match_confidence = match_result.match_confidence

        # Build StgSocialPost data dict
        stg_post: dict[str, Any] = {
            "platform": "reddit",
            "post_id": post.post_id,
            "created_at": post.post_created_at,
            "fetched_at": post.fetched_at,
            "author_handle": post.author,
            "post_text": post_text if post_text else None,
            "engagement_score": engagement_score,
            "matched_to_game": matched_to_game,
            "match_confidence": match_confidence,
            "matched_teams": matched_teams,
            "processed_at": post.processed_at,
            "raw_json": post.raw_json,
        }

        # Upsert to stg_social_posts (idempotent on composite PK)
        stmt_insert = insert(StgSocialPost).values(stg_post)
        stmt_insert = stmt_insert.on_conflict_do_nothing(
            index_elements=["platform", "post_id", "created_at"]
        )

        result_insert = await session.execute(stmt_insert)

        # Mark source post as processed
        if result_insert.rowcount > 0:  # type: ignore[attr-defined]
            posts_transformed += 1

            # Update raw_reddit_posts.processed_at
            stmt_update = (
                update(RawRedditPost)
                .where(RawRedditPost.post_id == post.post_id)  # type: ignore[arg-type]
                .where(RawRedditPost.fetched_at == post.fetched_at)  # type: ignore[arg-type]
                .values(processed_at=now)
            )
            await session.execute(stmt_update)

    await session.commit()

    context.log.info(
        f"reddit_posts_transformed count={posts_transformed} out_of={len(reddit_posts)}"
    )

    return posts_transformed


async def _transform_bluesky_posts(
    session: AsyncSession,
    context: AssetExecutionContext,
) -> int:
    """
    Transform Bluesky posts from raw_bluesky_posts to stg_social_posts.

    Business Logic:
    - Engagement: likeCount + replyCount (from raw_json)
    - Post text: post_text field
    - Filters: WHERE processed_at IS NULL LIMIT 2500

    Returns:
        Number of posts transformed
    """
    # Fetch unprocessed Bluesky posts
    stmt = (
        select(RawBlueskyPost)
        .where(RawBlueskyPost.processed_at.is_(None))  # type: ignore[union-attr]
        .limit(BATCH_SIZE)
    )
    result = await session.execute(stmt)
    bluesky_posts = list(result.scalars().all())

    if not bluesky_posts:
        context.log.info("no_unprocessed_bluesky_posts")
        return 0

    context.log.info(
        f"transforming_bluesky_posts count={len(bluesky_posts)} batch_size={BATCH_SIZE}"
    )

    posts_transformed = 0
    now = datetime.now(timezone.utc)

    # Initialize GameMatcher once for batch (loads teams cache)
    matcher = GameMatcher(session)
    await matcher.initialize()

    for post in bluesky_posts:
        # Calculate engagement score from raw_json
        engagement_score = calculate_bluesky_engagement(post.raw_json)

        # Match post to teams (Story 4-5 prerequisite)
        matched_teams: list[str] | None = None
        matched_to_game = False
        match_confidence = None

        if post.post_text:
            match_result = matcher.match_post_to_teams(post.post_text)
            if match_result.matched_teams:
                matched_teams = match_result.matched_teams
                matched_to_game = True
                match_confidence = match_result.match_confidence

        # Build StgSocialPost data dict
        stg_post: dict[str, Any] = {
            "platform": "bluesky",
            "post_id": post.post_uri,
            "created_at": post.created_at,
            "fetched_at": post.fetched_at,
            "author_handle": post.author_handle,
            "post_text": post.post_text,
            "engagement_score": engagement_score,
            "matched_to_game": matched_to_game,
            "match_confidence": match_confidence,
            "matched_teams": matched_teams,
            "processed_at": post.processed_at,
            "raw_json": post.raw_json,
        }

        # Upsert to stg_social_posts (idempotent on composite PK)
        stmt_insert = insert(StgSocialPost).values(stg_post)
        stmt_insert = stmt_insert.on_conflict_do_nothing(
            index_elements=["platform", "post_id", "created_at"]
        )

        result_insert = await session.execute(stmt_insert)

        # Mark source post as processed
        if result_insert.rowcount > 0:  # type: ignore[attr-defined]
            posts_transformed += 1

            # Update raw_bluesky_posts.processed_at
            stmt_update = (
                update(RawBlueskyPost)
                .where(RawBlueskyPost.post_uri == post.post_uri)  # type: ignore[arg-type]
                .where(RawBlueskyPost.created_at == post.created_at)  # type: ignore[arg-type]
                .values(processed_at=now)
            )
            await session.execute(stmt_update)

    await session.commit()

    context.log.info(
        f"bluesky_posts_transformed count={posts_transformed} out_of={len(bluesky_posts)}"
    )

    return posts_transformed
