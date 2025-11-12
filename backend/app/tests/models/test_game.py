"""
Unit tests for Game SQLModel.

Tests model instantiation, serialization, defaults, and field validation
without database interaction.
"""

from datetime import datetime, timezone

from app.models.game import Game


class TestGameModel:
    """Unit tests for Game model creation and validation."""

    def test_create_game_instance_valid_data(self) -> None:
        """Test creating a Game instance with all required fields."""
        game_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=game_date,
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
            home_score=75,
            away_score=72,
            game_status="final",
            venue="Cameron Indoor Stadium",
        )

        assert game.game_id == "ncaam_401234567"
        assert game.sport == "ncaam"
        assert game.game_date == game_date
        assert game.home_team_id == "ncaam_duke"
        assert game.away_team_id == "ncaam_unc"
        assert game.home_score == 75
        assert game.away_score == 72
        assert game.game_status == "final"
        assert game.venue == "Cameron Indoor Stadium"

    def test_game_model_serialization(self) -> None:
        """Test Game works as Pydantic schema for JSON serialization."""
        game_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=game_date,
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
        )

        # Test Pydantic model_dump() for JSON serialization
        game_dict = game.model_dump()

        assert isinstance(game_dict, dict)
        assert game_dict["game_id"] == "ncaam_401234567"
        assert game_dict["sport"] == "ncaam"
        assert game_dict["home_team_id"] == "ncaam_duke"
        assert game_dict["away_team_id"] == "ncaam_unc"
        assert game_dict["home_score"] == 0  # Default value
        assert game_dict["away_score"] == 0  # Default value

        # Test SQLModel dual nature (ORM + Pydantic)
        assert hasattr(game, "model_dump")
        assert hasattr(game, "__tablename__")

    def test_game_timestamps_auto_generated(self) -> None:
        """Test created_at and updated_at auto-populated with UTC datetime."""
        before_creation = datetime.utcnow()
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
        )
        after_creation = datetime.utcnow()

        # Verify timestamps are auto-populated
        assert game.created_at is not None
        assert game.updated_at is not None

        # Verify timestamps are within reasonable time window
        assert before_creation <= game.created_at <= after_creation
        assert before_creation <= game.updated_at <= after_creation

        # Note: Current implementation uses datetime.utcnow() which returns naive datetimes
        # Future enhancement: Migrate to timezone-aware datetimes using datetime.now(timezone.utc)

    def test_game_default_values(self) -> None:
        """Test Game model default values for scores, sport, and game_type."""
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
        )

        # Test default score values
        assert game.home_score == 0
        assert game.away_score == 0

        # Test default game_type
        assert game.game_type == "regular_season"

        # Test optional fields default to None
        assert game.game_status is None
        assert game.game_clock is None
        assert game.game_start_time is None
        assert game.game_end_time is None
        assert game.venue is None
        assert game.rivalry_factor is None
        assert game.broadcast_network is None
        assert game.attendance is None

    def test_game_field_types(self) -> None:
        """Test field type validation for str | None, int, and datetime fields."""
        # Test valid game with all required fields
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
        )

        # Test str | None fields accept None
        game.game_status = None
        game.venue = None
        game.broadcast_network = None
        assert game.game_status is None
        assert game.venue is None
        assert game.broadcast_network is None

        # Test str | None fields accept strings
        game.game_status = "scheduled"
        game.venue = "Cameron Indoor Stadium"
        game.broadcast_network = "ESPN"
        assert game.game_status == "scheduled"
        assert game.venue == "Cameron Indoor Stadium"
        assert game.broadcast_network == "ESPN"

        # Test int fields accept valid integers
        game.home_score = 75
        game.away_score = 72
        assert game.home_score == 75
        assert game.away_score == 72
        assert isinstance(game.home_score, int)
        assert isinstance(game.away_score, int)

        # Test datetime fields properly typed
        assert isinstance(game.game_date, datetime)
        assert isinstance(game.created_at, datetime)
        assert isinstance(game.updated_at, datetime)

    def test_game_rivalry_factor_optional(self) -> None:
        """Test rivalry_factor field accepts float or None."""
        game = Game(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_id="ncaam_duke",
            away_team_id="ncaam_unc",
        )

        # Default should be None
        assert game.rivalry_factor is None

        # Should accept float values
        game.rivalry_factor = 0.95
        assert game.rivalry_factor == 0.95

        # Should accept None
        game.rivalry_factor = None
        assert game.rivalry_factor is None
