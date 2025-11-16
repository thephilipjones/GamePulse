"""
Integration tests for calculate_sentiment Dagster asset (Story 4-5).

Tests sentiment analysis asset with test database fixtures.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assets.social_sentiment import calculate_sentiment
from app.models.dim_date import DimDate
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.models.social import FactSocialSentiment, StgSocialPost


@pytest.mark.integration
@pytest.mark.asyncio
class TestCalculateSentiment:
    """Test calculate_sentiment asset."""

    async def test_process_matched_posts(
        self,
        session: AsyncSession,
        test_context: any,
    ) -> None:
        """Test processing posts that match to games."""
        # Setup: Create test teams
        team1 = DimTeam(
            team_id="ncaam_duke",
            sport="ncaam",
            team_name="Duke",
            conference_id="acc",
        )
        team2 = DimTeam(
            team_id="ncaam_unc",
            sport="ncaam",
            team_name="North Carolina",
            conference_id="acc",
        )
        session.add_all([team1, team2])

        # Create test game
        game_date = datetime.now(timezone.utc) - timedelta(days=1)
        date_key = int(game_date.strftime("%Y%m%d"))

        dim_date = DimDate(
            date_key=date_key,
            date_actual=game_date.date(),
            day_of_week=game_date.weekday(),
            month_name=game_date.strftime("%B"),
            year=game_date.year,
        )
        session.add(dim_date)

        game = FactGame(
            game_id="ncaam_game_1",
            game_date=game_date,
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
            home_score=85,
            away_score=80,
            status="Final",
        )
        session.add(game)
        await session.flush()

        # Create test social post with team mentions
        post = StgSocialPost(
            platform="reddit",
            post_id="test_post_1",
            created_at=game_date + timedelta(hours=2),  # After game
            fetched_at=datetime.now(timezone.utc),
            author_handle="test_user",
            post_text="Duke crushed UNC! Amazing game!",
            engagement_score=100.0,
            matched_to_game=True,
            matched_teams=["ncaam_duke", "ncaam_unc"],
            match_confidence=0.95,
            raw_json={},
        )
        session.add(post)
        await session.commit()

        # Execute asset
        from app.resources.database import DatabaseResource

        database = DatabaseResource()
        result = await calculate_sentiment(test_context, database)

        # Verify results
        assert result["posts_analyzed"] == 1
        assert result["posts_matched_to_games"] == 1
        assert result["posts_skipped"] == 0

        # Verify sentiment record created
        stmt = select(FactSocialSentiment)
        db_result = await session.execute(stmt)
        sentiment_records = list(db_result.scalars().all())

        assert len(sentiment_records) == 1
        sentiment = sentiment_records[0]

        # Verify FK relationships
        assert sentiment.game_key == game.game_key
        assert sentiment.date_key == date_key
        assert sentiment.social_post_key == post.social_post_key

        # Verify sentiment scores (positive text should have positive compound)
        assert sentiment.sentiment_compound > 0.05  # Positive sentiment
        assert sentiment.sentiment_positive > sentiment.sentiment_negative

        # Verify denormalized fields
        assert sentiment.platform == "reddit"
        assert sentiment.post_text == "Duke crushed UNC! Amazing game!"
        assert sentiment.created_at == post.created_at
        assert sentiment.engagement_score == 100.0

    async def test_skip_posts_without_game_match(
        self,
        session: AsyncSession,
        test_context: any,
    ) -> None:
        """Test posts without valid game_key are skipped."""
        # Create post with matched_teams but no corresponding game
        post = StgSocialPost(
            platform="reddit",
            post_id="test_post_nomatch",
            created_at=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
            author_handle="test_user",
            post_text="Some random sports talk",
            engagement_score=50.0,
            matched_to_game=True,
            matched_teams=["ncaam_nonexistent"],  # No game for these teams
            match_confidence=0.5,
            raw_json={},
        )
        session.add(post)
        await session.commit()

        # Execute asset
        from app.resources.database import DatabaseResource

        database = DatabaseResource()
        result = await calculate_sentiment(test_context, database)

        # Verify post was skipped
        assert result["posts_analyzed"] == 1
        assert result["posts_matched_to_games"] == 0
        assert result["posts_skipped"] == 1

        # Verify no sentiment record created
        stmt = select(FactSocialSentiment)
        db_result = await session.execute(stmt)
        sentiment_records = list(db_result.scalars().all())
        assert len(sentiment_records) == 0

    async def test_no_unprocessed_posts(
        self,
        session: AsyncSession,
        test_context: any,
    ) -> None:
        """Test asset handles no unprocessed posts gracefully."""
        # Execute asset with empty database
        from app.resources.database import DatabaseResource

        database = DatabaseResource()
        result = await calculate_sentiment(test_context, database)

        # Verify zero counts
        assert result["posts_analyzed"] == 0
        assert result["posts_matched_to_games"] == 0
        assert result["posts_skipped"] == 0

    async def test_idempotency(
        self,
        session: AsyncSession,
        test_context: any,
    ) -> None:
        """Test asset is idempotent (running twice doesn't duplicate records)."""
        # Setup: Create minimal test data
        team = DimTeam(
            team_id="ncaam_duke",
            sport="ncaam",
            team_name="Duke",
            conference_id="acc",
        )
        session.add(team)

        game_date = datetime.now(timezone.utc) - timedelta(days=1)
        date_key = int(game_date.strftime("%Y%m%d"))

        dim_date = DimDate(
            date_key=date_key,
            date_actual=game_date.date(),
            day_of_week=game_date.weekday(),
            month_name=game_date.strftime("%B"),
            year=game_date.year,
        )
        session.add(dim_date)

        game = FactGame(
            game_id="ncaam_game_idem",
            game_date=game_date,
            home_team_id="ncaam_duke",
            away_team_id="ncaam_duke",
            home_score=75,
            away_score=70,
            status="Final",
        )
        session.add(game)
        await session.flush()

        post = StgSocialPost(
            platform="reddit",
            post_id="test_post_idem",
            created_at=game_date + timedelta(hours=1),
            fetched_at=datetime.now(timezone.utc),
            author_handle="test_user",
            post_text="Great game!",
            engagement_score=75.0,
            matched_to_game=True,
            matched_teams=["ncaam_duke"],
            match_confidence=0.9,
            raw_json={},
        )
        session.add(post)
        await session.commit()

        # Execute asset twice
        from app.resources.database import DatabaseResource

        database = DatabaseResource()

        result1 = await calculate_sentiment(test_context, database)
        assert result1["posts_analyzed"] == 1
        assert result1["posts_matched_to_games"] == 1

        result2 = await calculate_sentiment(test_context, database)
        assert result2["posts_analyzed"] == 0  # No unprocessed posts left

        # Verify only one sentiment record exists
        stmt = select(FactSocialSentiment)
        db_result = await session.execute(stmt)
        sentiment_records = list(db_result.scalars().all())
        assert len(sentiment_records) == 1
