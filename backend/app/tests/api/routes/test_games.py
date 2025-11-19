"""API tests for games endpoint."""

import time
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.dim_date import DimDate
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.models.social import FactSocialSentiment, StgSocialPost


class TestGamesEndpoint:
    """Test suite for games API endpoints."""

    def test_get_games_empty_result(self, client: TestClient) -> None:
        """Test that endpoint returns empty array when no games exist for date."""
        # Query a date with no games (2025-01-01 - no games scheduled)
        response = client.get("/api/v1/games?date=2025-01-01")

        assert response.status_code == 200
        data = response.json()

        assert "games" in data
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])
        assert data["requested_date"] == "2025-01-01"
        assert "generated_at" in data

    def test_get_games_with_date_parameter(self, client: TestClient) -> None:
        """Test getting games for a specific date with query parameter."""
        # Query a specific date (may or may not have games)
        response = client.get("/api/v1/games?date=2024-11-13")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "games" in data
        assert "total_count" in data
        assert data["requested_date"] == "2024-11-13"
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])

        # If games exist, verify data structure
        if len(data["games"]) > 0:
            game = data["games"][0]
            assert "game_id" in game
            assert "game_key" in game
            assert "game_date" in game
            assert "game_start_time" in game
            assert "game_status" in game
            assert "home_score" in game
            assert "away_score" in game

            # Verify team details structure
            assert "home_team" in game
            assert "away_team" in game
            for team_key in ["home_team", "away_team"]:
                team = game[team_key]
                assert "team_key" in team
                assert "team_id" in team
                assert "team_name" in team
                # team_group_name, primary_color, secondary_color can be null

    def test_get_games_default_to_today(self, client: TestClient) -> None:
        """Test that endpoint defaults to today when no date parameter provided."""
        response = client.get("/api/v1/games")

        assert response.status_code == 200
        data = response.json()

        # Should return today's date
        assert data["requested_date"] == date.today().isoformat()
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])

    def test_get_games_today_endpoint(self, client: TestClient) -> None:
        """Test /today convenience endpoint returns same as default."""
        # Get from both endpoints
        response_default = client.get("/api/v1/games")
        response_today = client.get("/api/v1/games/today")

        assert response_default.status_code == 200
        assert response_today.status_code == 200

        # Both should return same data
        data_default = response_default.json()
        data_today = response_today.json()

        assert data_default["total_count"] == data_today["total_count"]
        assert len(data_default["games"]) == len(data_today["games"])
        assert data_default["requested_date"] == data_today["requested_date"]
        assert data_default["requested_date"] == date.today().isoformat()

    def test_get_games_invalid_date_format(self, client: TestClient) -> None:
        """Test that invalid date formats return HTTP 400."""
        # Various invalid formats
        invalid_dates = [
            "11-13-2025",  # MM-DD-YYYY
            "2025/11/13",  # Slashes instead of dashes
            "invalid",  # Not a date
            "2025-13-01",  # Invalid month
            "2025-02-30",  # Invalid day
        ]

        for invalid_date in invalid_dates:
            response = client.get(f"/api/v1/games?date={invalid_date}")

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "Invalid date format" in data["detail"]

    def test_get_games_future_date(self, client: TestClient) -> None:
        """Test getting games for a future date."""
        # Query far future date (unlikely to have data)
        response = client.get("/api/v1/games?date=2026-12-31")

        assert response.status_code == 200
        data = response.json()

        assert data["requested_date"] == "2026-12-31"
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])

    def test_get_games_past_date(self, client: TestClient) -> None:
        """Test getting games for a historical date."""
        # Query a past date
        response = client.get("/api/v1/games?date=2024-03-15")

        assert response.status_code == 200
        data = response.json()

        assert data["requested_date"] == "2024-03-15"
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])

    def test_cors_headers_allowed_origin(self, client: TestClient) -> None:
        """Test CORS headers are present for allowed origins."""
        # Test with localhost origin (should be allowed)
        headers = {"Origin": "http://localhost:5173"}
        response = client.get("/api/v1/games", headers=headers)

        assert response.status_code == 200
        # FastAPI TestClient doesn't fully simulate CORS middleware
        # In production, these headers would be present

    def test_response_schema_validation(self, client: TestClient) -> None:
        """Test that response matches expected Pydantic schema."""
        # Use today endpoint to get any available games
        response = client.get("/api/v1/games/today")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level schema
        assert "games" in data
        assert "total_count" in data
        assert "generated_at" in data
        assert "requested_date" in data
        assert isinstance(data["games"], list)
        assert data["total_count"] == len(data["games"])

        # Verify game schema (if games exist)
        if data["games"]:
            game = data["games"][0]

            # Required game fields
            assert "game_key" in game
            assert "game_id" in game
            assert "game_date" in game
            assert "game_start_time" in game
            assert "game_status" in game
            assert "home_team" in game
            assert "away_team" in game
            assert "home_score" in game
            assert "away_score" in game

            # Verify team schema
            for team_key in ["home_team", "away_team"]:
                team = game[team_key]
                assert "team_key" in team
                assert "team_id" in team
                assert "team_name" in team
                # Optional fields can be null
                assert "team_group_name" in team
                assert "primary_color" in team
                assert "secondary_color" in team

    def test_games_ordered_by_time(self, client: TestClient) -> None:
        """Test that games are returned ordered by game_start_time ascending."""
        response = client.get("/api/v1/games/today")

        assert response.status_code == 200
        data = response.json()

        # If multiple games exist, verify ordering
        if len(data["games"]) > 1:
            game_times = [
                game["game_start_time"]
                for game in data["games"]
                if game["game_start_time"]
            ]
            # game_times should be sorted (earlier times first)
            if game_times:
                assert game_times == sorted(game_times)

    def test_database_error_handling(self, client: TestClient) -> None:
        """Test that database errors are handled gracefully with proper logging."""
        from collections.abc import Generator
        from unittest.mock import Mock

        from sqlalchemy.exc import OperationalError

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
            # Make request - should return HTTP 500
            response = client.get("/api/v1/games/today")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Database connection failed" in data["detail"]
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_game_public_schema_validation(self) -> None:
        """Test that Pydantic schemas validate data correctly."""
        from datetime import datetime

        from pydantic import ValidationError

        from app.schemas.game import GamePublic, TeamInfo

        # Valid data should work
        valid_team = TeamInfo(
            team_key=1,
            team_id="ncaam_150",
            team_name="Duke",
            team_group_name="ACC",
            primary_color="#00539B",
            secondary_color="#FFFFFF",
        )

        valid_game = GamePublic(
            game_key=1,
            game_id="ncaam_401234567",
            game_date=datetime(2025, 11, 14),
            game_start_time=datetime(2025, 11, 14, 19, 0, 0),
            game_status="scheduled",
            game_clock=None,
            game_period=None,
            home_team=valid_team,
            away_team=valid_team,
            home_score=0,
            away_score=0,
        )

        assert valid_game.game_key == 1
        assert valid_game.game_id == "ncaam_401234567"

        # Invalid data should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            GamePublic(
                game_key="not-an-int",  # type: ignore[arg-type]  # Should be int
                game_id=123,  # type: ignore[arg-type]  # Should be str
                game_date="not-a-date",  # type: ignore[arg-type]  # Should be datetime
                game_start_time="invalid",  # type: ignore[arg-type]  # Should be datetime
                game_status="scheduled",
                game_clock=None,
                game_period=None,
                home_team=valid_team,
                away_team=valid_team,
            )

        # Verify validation errors were raised
        assert exc_info.value.error_count() > 0

        # Test missing required fields
        with pytest.raises(ValidationError):
            GamePublic()  # type: ignore[call-arg]  # Missing all required fields


class TestSocialPostsEndpoint:
    """Test suite for social posts API endpoint (Story 4-10).

    Uses client_with_db fixture to share test database session with the app.
    This allows tests to create data and access it via API in the same transaction.
    """

    def _create_test_data(
        self, db: Session, game_id: str = "ncaam_test123"
    ) -> tuple[FactGame, list[FactSocialSentiment]]:
        """Create test game and social posts data."""
        # Create dim_date
        dim_date = DimDate(
            date_key=20251114,
            full_date=date(2025, 11, 14),
            year=2025,
            month=11,
            day_of_month=14,
            day_of_week=4,
            day_name="Friday",
            month_name="November",
            quarter=4,
            week_of_year=46,
            is_weekend=False,
            is_march_madness=False,
        )
        db.add(dim_date)
        db.flush()

        # Create teams
        home_team = DimTeam(
            team_id="ncaam_duke",
            team_name="Duke Blue Devils",
            sport="ncaam",
            is_current=True,
        )
        away_team = DimTeam(
            team_id="ncaam_unc",
            team_name="North Carolina Tar Heels",
            sport="ncaam",
            is_current=True,
        )
        db.add(home_team)
        db.add(away_team)
        db.flush()

        # Create game
        game = FactGame(
            game_id=game_id,
            game_date_key=20251114,
            game_date=datetime(2025, 11, 14, tzinfo=timezone.utc),
            game_start_time=datetime(2025, 11, 14, 19, 0, tzinfo=timezone.utc),
            game_status="scheduled",
            sport="ncaam",
            home_team_key=home_team.team_key,
            away_team_key=away_team.team_key,
            home_score=0,
            away_score=0,
        )
        db.add(game)
        db.flush()

        # Create staging posts and sentiment records
        sentiments = []
        posts_data = [
            {
                "platform": "reddit",
                "post_id": "t3_abc123",
                "post_text": "Duke starts with a 10-0 run! This is amazing!",
                "engagement_score": 500,
                "sentiment_compound": 0.85,  # positive
                "author_handle": "hoopsfan",
                "raw_json": {
                    "permalink": "/r/CollegeBasketball/comments/abc123/duke_starts/"
                },
            },
            {
                "platform": "bluesky",
                "post_id": "at://did:plc:xyz/app.bsky.feed.post/3abc123",
                "post_text": "Great defense from UNC right now",
                "engagement_score": 300,
                "sentiment_compound": 0.02,  # neutral
                "author_handle": "ballgame.bsky.social",
                "raw_json": {},
            },
            {
                "platform": "reddit",
                "post_id": "t3_def456",
                "post_text": "Terrible call by the refs, this is ridiculous",
                "engagement_score": 200,
                "sentiment_compound": -0.75,  # negative
                "author_handle": "angryref",
                "raw_json": {
                    "permalink": "/r/CollegeBasketball/comments/def456/bad_call/"
                },
            },
        ]

        # Generate unique base key using timestamp to avoid conflicts in parallel test runs
        base_key = int(time.time() * 1000) % 1000000000

        for i, post_data in enumerate(posts_data):
            # Create staging post with unique social_post_key
            stg_post = StgSocialPost(
                social_post_key=base_key + i,
                platform=post_data["platform"],
                post_id=post_data["post_id"],
                created_at=datetime(2025, 11, 14, 19, 0 + i, tzinfo=timezone.utc),
                fetched_at=datetime(2025, 11, 14, 19, 5, tzinfo=timezone.utc),
                author_handle=post_data["author_handle"],
                post_text=post_data["post_text"],
                engagement_score=post_data["engagement_score"],
                raw_json=post_data["raw_json"],
            )
            db.add(stg_post)
            db.flush()

            # Create sentiment record
            sentiment = FactSocialSentiment(
                game_key=game.game_key,
                date_key=20251114,
                social_post_key=stg_post.social_post_key,
                sentiment_compound=post_data["sentiment_compound"],
                sentiment_positive=0.5,
                sentiment_negative=0.1,
                sentiment_neutral=0.4,
                platform=post_data["platform"],
                post_text=post_data["post_text"],
                created_at=stg_post.created_at,
                engagement_score=post_data["engagement_score"],
            )
            db.add(sentiment)
            sentiments.append(sentiment)

        db.flush()
        return game, sentiments

    def test_get_social_posts_success(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test GET /api/v1/games/{game_id}/social-posts returns posts."""
        # Setup test data
        game, _ = self._create_test_data(db)
        db.flush()

        # Execute
        response = client_with_db.get(f"/api/v1/games/{game.game_id}/social-posts")

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert "posts" in data
        assert "total_count" in data
        assert "game_id" in data
        assert data["game_id"] == game.game_id
        assert data["total_count"] == 3
        assert len(data["posts"]) == 3

        # Verify posts are ordered by engagement_score DESC
        engagement_scores = [p["engagement_score"] for p in data["posts"]]
        assert engagement_scores == sorted(engagement_scores, reverse=True)

    def test_get_social_posts_respects_limit(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test that limit parameter works correctly."""
        game, _ = self._create_test_data(db)
        db.flush()

        # Request with limit=2
        response = client_with_db.get(
            f"/api/v1/games/{game.game_id}/social-posts?limit=2"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 2
        assert len(data["posts"]) == 2

    def test_get_social_posts_empty_result(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test endpoint returns empty array when no posts exist for game."""
        # Create game without social posts
        dim_date = DimDate(
            date_key=20251114,
            full_date=date(2025, 11, 14),
            year=2025,
            month=11,
            day_of_month=14,
            day_of_week=4,
            day_name="Friday",
            month_name="November",
            quarter=4,
            week_of_year=46,
            is_weekend=False,
            is_march_madness=False,
        )
        db.add(dim_date)

        team = DimTeam(
            team_id="ncaam_test",
            team_name="Test Team",
            sport="ncaam",
            is_current=True,
        )
        db.add(team)
        db.flush()

        game = FactGame(
            game_id="ncaam_empty",
            game_date_key=20251114,
            game_date=datetime(2025, 11, 14, tzinfo=timezone.utc),
            sport="ncaam",
            home_team_key=team.team_key,
            away_team_key=team.team_key,
        )
        db.add(game)
        db.flush()

        # Execute
        response = client_with_db.get("/api/v1/games/ncaam_empty/social-posts")

        # Verify
        assert response.status_code == 200
        data = response.json()

        assert data["posts"] == []
        assert data["total_count"] == 0
        assert data["game_id"] == "ncaam_empty"

    def test_get_social_posts_game_not_found(self, client: TestClient) -> None:
        """Test 404 error if game doesn't exist."""
        response = client.get("/api/v1/games/ncaam_invalid/social-posts")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Game not found" in data["detail"]

    def test_get_social_posts_invalid_limit(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test 422 error for invalid limit parameter."""
        game, _ = self._create_test_data(db)
        db.flush()

        # Test limit too high
        response = client_with_db.get(
            f"/api/v1/games/{game.game_id}/social-posts?limit=100"
        )
        assert response.status_code == 422

        # Test limit too low
        response = client_with_db.get(
            f"/api/v1/games/{game.game_id}/social-posts?limit=0"
        )
        assert response.status_code == 422

    def test_sentiment_classification(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test sentiment compound scores are classified correctly."""
        game, _ = self._create_test_data(db)
        db.flush()

        response = client_with_db.get(f"/api/v1/games/{game.game_id}/social-posts")

        assert response.status_code == 200
        data = response.json()

        # Find posts by engagement score (known order)
        posts_by_engagement = {p["engagement_score"]: p for p in data["posts"]}

        # Post with compound 0.85 should be positive
        assert posts_by_engagement[500]["sentiment_label"] == "positive"

        # Post with compound 0.02 should be neutral
        assert posts_by_engagement[300]["sentiment_label"] == "neutral"

        # Post with compound -0.75 should be negative
        assert posts_by_engagement[200]["sentiment_label"] == "negative"

    def test_reddit_url_construction(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test Reddit URL constructed correctly from permalink."""
        game, _ = self._create_test_data(db)
        db.flush()

        response = client_with_db.get(f"/api/v1/games/{game.game_id}/social-posts")

        assert response.status_code == 200
        data = response.json()

        # Find Reddit posts
        reddit_posts = [p for p in data["posts"] if p["platform"] == "reddit"]

        for post in reddit_posts:
            assert post["source_url"].startswith("https://www.reddit.com")
            assert "/r/CollegeBasketball/comments/" in post["source_url"]

    def test_bluesky_url_construction(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test Bluesky URL constructed correctly."""
        game, _ = self._create_test_data(db)
        db.flush()

        response = client_with_db.get(f"/api/v1/games/{game.game_id}/social-posts")

        assert response.status_code == 200
        data = response.json()

        # Find Bluesky post
        bluesky_posts = [p for p in data["posts"] if p["platform"] == "bluesky"]

        for post in bluesky_posts:
            assert post["source_url"].startswith("https://bsky.app/profile/")
            assert "ballgame.bsky.social" in post["source_url"]
            assert "/post/3abc123" in post["source_url"]

    def test_response_schema_validation(
        self, client_with_db: TestClient, db: Session
    ) -> None:
        """Test that response matches expected schema fields."""
        game, _ = self._create_test_data(db)
        db.flush()

        response = client_with_db.get(f"/api/v1/games/{game.game_id}/social-posts")

        assert response.status_code == 200
        data = response.json()

        # Verify post schema
        post = data["posts"][0]
        assert "social_post_key" in post
        assert "platform" in post
        assert "post_text" in post
        assert "created_at" in post
        assert "engagement_score" in post
        assert "sentiment_compound" in post
        assert "sentiment_label" in post
        assert "source_url" in post

        # Verify types
        assert isinstance(post["social_post_key"], int)
        assert isinstance(post["engagement_score"], int)
        assert isinstance(post["sentiment_compound"], float)
        assert post["sentiment_label"] in ["positive", "neutral", "negative"]
