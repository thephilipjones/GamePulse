"""
Unit tests for FactGame SQLModel.

Tests model instantiation, serialization, defaults, and field validation
without database interaction.
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.models.fact_game import FactGame

# Python 3.10 compatibility
UTC = timezone.utc


class TestFactGameModel:
    """Unit tests for FactGame model creation and validation."""

    def test_create_fact_game_instance_valid_data(self):
        """Test creating a FactGame instance with required fields and surrogate key FKs."""
        game_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=game_date,
            home_team_key=1,  # Surrogate key FK to dim_team
            away_team_key=2,  # Surrogate key FK to dim_team
            home_score=75,
            away_score=72,
            game_status="final",
            venue="Cameron Indoor Stadium",
        )

        # Verify natural key and dimensions
        assert game.game_id == "ncaam_401234567"
        assert game.sport == "ncaam"
        assert game.game_date == game_date
        assert game.home_team_key == 1
        assert game.away_team_key == 2

        # Verify measures
        assert game.home_score == 75
        assert game.away_score == 72

        # Verify degenerate dimensions
        assert game.game_status == "final"
        assert game.venue == "Cameron Indoor Stadium"

    def test_fact_game_model_serialization(self):
        """Test FactGame works as Pydantic schema for JSON serialization."""
        game_date = datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc)
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=game_date,
            home_team_key=1,
            away_team_key=2,
        )

        # Test Pydantic model_dump() for JSON serialization
        game_dict = game.model_dump()

        assert isinstance(game_dict, dict)
        assert game_dict["game_id"] == "ncaam_401234567"
        assert game_dict["sport"] == "ncaam"
        assert game_dict["home_team_key"] == 1
        assert game_dict["away_team_key"] == 2
        assert game_dict["home_score"] == 0  # Default value
        assert game_dict["away_score"] == 0  # Default value

        # Test SQLModel dual nature (ORM + Pydantic)
        assert hasattr(game, "model_dump")
        assert hasattr(game, "__tablename__")
        assert game.__tablename__ == "fact_game"

    def test_fact_game_timestamps_auto_generated(self):
        """Test created_at and updated_at auto-populated with UTC datetime."""
        before_creation = datetime.now(UTC)
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_key=1,
            away_team_key=2,
        )
        after_creation = datetime.now(UTC)

        # Verify timestamps are auto-populated
        assert game.created_at is not None
        assert game.updated_at is not None

        # Verify timestamps are within reasonable time window
        assert before_creation <= game.created_at <= after_creation
        assert before_creation <= game.updated_at <= after_creation

    def test_fact_game_default_values(self):
        """Test FactGame model default values for scores, game_type, and optional FKs."""
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_key=1,
            away_team_key=2,
        )

        # Test default score values
        assert game.home_score == 0
        assert game.away_score == 0

        # Test default game_type
        assert game.game_type == "regular_season"

        # Test optional dimension FK defaults to None
        assert game.game_date_key is None

        # Test optional fields default to None
        assert game.game_status is None
        assert game.game_clock is None
        assert game.game_start_time is None
        assert game.game_end_time is None
        assert game.venue is None
        assert game.rivalry_factor is None
        assert game.broadcast_network is None
        assert game.attendance is None

    def test_fact_game_field_types(self):
        """Test field type validation for dimensional FKs and measures."""
        # Test valid game with all required fields
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_key=1,
            away_team_key=2,
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

        # Test int measures accept valid integers
        game.home_score = 75
        game.away_score = 72
        assert game.home_score == 75
        assert game.away_score == 72
        assert isinstance(game.home_score, int)
        assert isinstance(game.away_score, int)

        # Test int | None FK accepts None
        game.game_date_key = None
        assert game.game_date_key is None

        # Test int | None FK accepts integers
        game.game_date_key = 20240315
        assert game.game_date_key == 20240315

        # Test datetime fields properly typed
        assert isinstance(game.game_date, datetime)
        assert isinstance(game.created_at, datetime)
        assert isinstance(game.updated_at, datetime)

    def test_fact_game_rivalry_factor_decimal(self):
        """Test rivalry_factor field accepts Decimal or None."""
        game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_key=1,
            away_team_key=2,
        )

        # Default should be None
        assert game.rivalry_factor is None

        # Should accept Decimal values
        game.rivalry_factor = Decimal("1.50")
        assert game.rivalry_factor == Decimal("1.50")

        # Should accept None
        game.rivalry_factor = None
        assert game.rivalry_factor is None

    def test_fact_game_surrogate_key_placeholder(self):
        """Test game_key surrogate key field exists (auto-generated in DB)."""
        # Note: game_key is auto-generated by database BIGSERIAL
        # Unit tests can't test auto-generation without DB interaction
        # This test verifies the field exists and can be set manually for mocking
        game = FactGame(
            game_key=12345,  # Manually set for testing (DB would auto-generate)
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2024, 3, 15, 19, 0, 0, tzinfo=timezone.utc),
            home_team_key=1,
            away_team_key=2,
        )

        assert game.game_key == 12345
        assert isinstance(game.game_key, int)
