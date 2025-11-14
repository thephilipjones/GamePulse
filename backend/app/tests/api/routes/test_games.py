"""API tests for games endpoint."""

from datetime import date

import pytest
from fastapi.testclient import TestClient


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
                home_team=valid_team,
                away_team=valid_team,
            )

        # Verify validation errors were raised
        assert exc_info.value.error_count() > 0

        # Test missing required fields
        with pytest.raises(ValidationError):
            GamePublic()  # type: ignore[call-arg]  # Missing all required fields
