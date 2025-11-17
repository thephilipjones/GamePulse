"""
Dagster asset for sentiment analysis of social media posts (Story 4-5).

Asset: calculate_sentiment
- Applies VADER sentiment analysis to social posts
- Resolves game_key using GameMatcher service
- Inserts sentiment-enriched posts into fact_social_sentiment
- Processes incrementally (LEFT JOIN to find unprocessed posts)
- Batch size: 2500 posts per run (optimized for t4g.small)
- Trigger: Auto-materializes when transform_social_posts completes (eager policy)
- Freshness SLA: Maximum 45 minutes from extract to sentiment complete (Story 4-7)

Transform Logic:
- Uses VADER sentiment analyzer for compound + component scores
- Only processes posts with matched_to_game = TRUE
- Denormalizes key fields (platform, post_text, created_at, engagement_score)
- Skips posts that cannot be matched to a game
"""

import structlog
from dagster import (
    AssetExecutionContext,
    AutoMaterializePolicy,
    Backoff,
    FreshnessPolicy,
    RetryPolicy,
    asset,
)
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import FactSocialSentiment, StgSocialPost
from app.resources.database import DatabaseResource
from app.services.game_matcher import GameMatcher
from app.services.sentiment_analyzer import analyze_sentiment

logger = structlog.get_logger()

# Batch size for incremental processing (optimized for t4g.small)
BATCH_SIZE = 2500


@asset(
    name="calculate_sentiment",
    description="VADER sentiment analysis for social posts with game resolution",
    group_name="social_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
    # Auto-materialize: Trigger when transform_social_posts completes
    auto_materialize_policy=AutoMaterializePolicy.eager(),
    # Freshness SLA: Maximum 45 minutes from extract to sentiment complete
    freshness_policy=FreshnessPolicy(maximum_lag_minutes=45),
    # Dependency: Runs after social post transformation completes
    deps=["transform_social_posts"],
)
async def calculate_sentiment(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Calculate sentiment scores for social posts and insert to fact_social_sentiment.

    Features:
    - VADER sentiment analysis (compound + component scores)
    - GameMatcher resolution for game_key foreign key
    - Incremental processing (LEFT JOIN to find unprocessed posts)
    - Batch processing (2500 posts per run)
    - Only processes posts with matched_to_game = TRUE

    Returns:
        Metadata dict with keys:
        - posts_analyzed: Posts with sentiment scores calculated
        - posts_matched_to_games: Posts successfully linked to game_key
        - posts_skipped: Posts without valid game_key (no matching game found)
    """
    context.log.info("calculate_sentiment_started")

    posts_analyzed = 0
    posts_matched_to_games = 0
    posts_skipped = 0

    async with database.get_session() as session:
        # Step 1: Find unprocessed social posts
        # LEFT JOIN to find posts not yet in fact_social_sentiment
        unprocessed_posts = await _find_unprocessed_posts(session)

        if not unprocessed_posts:
            context.log.info("no_unprocessed_posts")
            return {
                "posts_analyzed": 0,
                "posts_matched_to_games": 0,
                "posts_skipped": 0,
            }

        context.log.info(
            f"found_unprocessed_posts count={len(unprocessed_posts)} batch_size={BATCH_SIZE}"
        )

        # Step 2: Initialize GameMatcher once for batch (loads teams cache)
        matcher = GameMatcher(session)
        await matcher.initialize()

        # Step 3: Process each post (sentiment + game matching)
        for post in unprocessed_posts:
            # Apply VADER sentiment analysis
            sentiment_scores = analyze_sentiment(post.post_text)
            posts_analyzed += 1

            # Resolve game_key using matched_teams + post date
            game_key = None
            if post.matched_teams:
                game_key = await matcher.resolve_game_key(
                    team_ids=post.matched_teams,
                    post_date=post.created_at,
                )

            # Skip posts without valid game_key
            if not game_key:
                posts_skipped += 1
                context.log.debug(
                    "post_skipped_no_game_key",
                    extra={
                        "social_post_key": post.social_post_key,
                        "matched_teams": post.matched_teams,
                        "post_date": str(post.created_at.date()),
                    },
                )
                continue

            # Calculate date_key from post created_at (YYYYMMDD format)
            date_key = int(post.created_at.strftime("%Y%m%d"))

            # Build FactSocialSentiment record
            sentiment_record = {
                "game_key": game_key,
                "date_key": date_key,
                "social_post_key": post.social_post_key,
                # VADER sentiment scores
                "sentiment_compound": sentiment_scores["compound"],
                "sentiment_positive": sentiment_scores["positive"],
                "sentiment_negative": sentiment_scores["negative"],
                "sentiment_neutral": sentiment_scores["neutral"],
                # Denormalized fields for Epic 5 queries
                "platform": post.platform,
                "post_text": post.post_text,
                "created_at": post.created_at,
                "engagement_score": post.engagement_score,
                # analyzed_at has DEFAULT NOW() in database
            }

            # Upsert to fact_social_sentiment (idempotent on social_post_key unique constraint)
            stmt = insert(FactSocialSentiment).values(sentiment_record)
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_sentiment_social_post_key"
            )

            result = await session.execute(stmt)

            if result.rowcount > 0:  # type: ignore[attr-defined]
                posts_matched_to_games += 1

        # Commit all inserts
        await session.commit()

    context.log.info(
        "calculate_sentiment_completed",
        extra={
            "posts_analyzed": posts_analyzed,
            "posts_matched_to_games": posts_matched_to_games,
            "posts_skipped": posts_skipped,
        },
    )

    return {
        "posts_analyzed": posts_analyzed,
        "posts_matched_to_games": posts_matched_to_games,
        "posts_skipped": posts_skipped,
    }


async def _find_unprocessed_posts(
    session: AsyncSession,
) -> list[StgSocialPost]:
    """
    Find social posts that haven't been sentiment-analyzed yet.

    Query Logic:
    - LEFT JOIN stg_social_posts to fact_social_sentiment
    - WHERE fact_social_sentiment.sentiment_key IS NULL (not yet processed)
    - AND stg_social_posts.matched_to_game = TRUE (only posts matched to teams)
    - ORDER BY stg_social_posts.created_at ASC (oldest first)
    - LIMIT 2500

    Returns:
        List of unprocessed StgSocialPost records
    """
    join_condition = (
        StgSocialPost.social_post_key == FactSocialSentiment.social_post_key
    ) & (StgSocialPost.created_at == FactSocialSentiment.created_at)
    stmt = (
        select(StgSocialPost)
        .outerjoin(FactSocialSentiment, join_condition)  # type: ignore[arg-type]
        .where(FactSocialSentiment.sentiment_key.is_(None))  # type: ignore[union-attr]
        .where(StgSocialPost.matched_to_game == True)  # type: ignore[arg-type] # noqa: E712
        .order_by(StgSocialPost.created_at)  # type: ignore[arg-type]
        .limit(BATCH_SIZE)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
