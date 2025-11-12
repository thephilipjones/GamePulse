"""
Unit tests for DimTeam SQLModel.

Tests model instantiation, serialization, defaults, and field validation
without database interaction.
"""

from datetime import datetime, timezone

from app.models.dim_team import DimTeam

# Python 3.10 compatibility
UTC = timezone.utc


class TestDimTeamModel:
    """Unit tests for DimTeam model creation and validation."""

    def test_create_dim_team_instance_valid_data(self):
        """Test creating a DimTeam instance with all required fields."""
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
            team_abbr="DUKE",
            team_group_id="ncaam_acc",
            team_group_name="Atlantic Coast Conference",
            primary_color="#003087",
            secondary_color="#FFFFFF",
            aliases=["Duke", "Blue Devils", "Duke Blue Devils"],
        )

        # Verify natural key and core attributes
        assert team.team_id == "ncaam_150"
        assert team.sport == "ncaam"
        assert team.team_name == "Duke"
        assert team.team_abbr == "DUKE"

        # Verify flattened team_group fields
        assert team.team_group_id == "ncaam_acc"
        assert team.team_group_name == "Atlantic Coast Conference"

        # Verify UI metadata
        assert team.primary_color == "#003087"
        assert team.secondary_color == "#FFFFFF"
        assert team.aliases == ["Duke", "Blue Devils", "Duke Blue Devils"]

    def test_dim_team_model_serialization(self):
        """Test DimTeam works as Pydantic schema for JSON serialization."""
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
            team_group_id="ncaam_acc",
            team_group_name="Atlantic Coast Conference",
        )

        # Test Pydantic model_dump() for JSON serialization
        team_dict = team.model_dump()

        assert isinstance(team_dict, dict)
        assert team_dict["team_id"] == "ncaam_150"
        assert team_dict["sport"] == "ncaam"
        assert team_dict["team_name"] == "Duke"
        assert team_dict["team_group_id"] == "ncaam_acc"
        assert team_dict["team_group_name"] == "Atlantic Coast Conference"

        # Test SQLModel dual nature (ORM + Pydantic)
        assert hasattr(team, "model_dump")
        assert hasattr(team, "__tablename__")
        assert team.__tablename__ == "dim_team"

    def test_dim_team_timestamps_auto_generated(self):
        """Test created_at and updated_at auto-populated with UTC datetime."""
        before_creation = datetime.now(UTC)
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
        )
        after_creation = datetime.now(UTC)

        # Verify timestamps are auto-populated
        assert team.created_at is not None
        assert team.updated_at is not None

        # Verify timestamps are within reasonable time window
        assert before_creation <= team.created_at <= after_creation
        assert before_creation <= team.updated_at <= after_creation

    def test_dim_team_scd_type2_defaults(self):
        """Test SCD Type 2 fields have correct default values."""
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
        )

        # SCD Type 2 fields should have defaults
        assert team.is_current is True
        assert team.valid_from is not None
        assert team.valid_to is None  # NULL = current version

        # valid_from should be recent (within last second)
        now = datetime.now(UTC)
        time_diff = (now - team.valid_from).total_seconds()
        assert time_diff < 1.0  # Should be very recent

    def test_dim_team_default_values(self):
        """Test DimTeam model default values for optional fields."""
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
        )

        # Test optional fields default to None
        assert team.team_abbr is None
        assert team.team_group_id is None
        assert team.team_group_name is None
        assert team.primary_color is None
        assert team.secondary_color is None

        # Test aliases defaults to empty list
        assert team.aliases == []

    def test_dim_team_field_types(self):
        """Test field type validation for dimensional attributes."""
        # Test valid team with all required fields
        team = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
        )

        # Test str | None fields accept None
        team.team_abbr = None
        team.team_group_id = None
        team.team_group_name = None
        team.primary_color = None
        team.secondary_color = None
        assert team.team_abbr is None
        assert team.team_group_id is None
        assert team.team_group_name is None
        assert team.primary_color is None
        assert team.secondary_color is None

        # Test str | None fields accept strings
        team.team_abbr = "DUKE"
        team.team_group_id = "ncaam_acc"
        team.team_group_name = "Atlantic Coast Conference"
        team.primary_color = "#003087"
        team.secondary_color = "#FFFFFF"
        assert team.team_abbr == "DUKE"
        assert team.team_group_id == "ncaam_acc"
        assert team.team_group_name == "Atlantic Coast Conference"
        assert team.primary_color == "#003087"
        assert team.secondary_color == "#FFFFFF"

        # Test list[str] field accepts list
        team.aliases = ["Duke", "Blue Devils"]
        assert team.aliases == ["Duke", "Blue Devils"]
        assert isinstance(team.aliases, list)

        # Test datetime fields properly typed
        assert isinstance(team.created_at, datetime)
        assert isinstance(team.updated_at, datetime)
        assert isinstance(team.valid_from, datetime)

        # Test bool field
        assert isinstance(team.is_current, bool)

    def test_dim_team_scd_type2_versioning_scenario(self):
        """Test SCD Type 2 field usage for tracking historical changes (conference realignment)."""
        # Create initial version (Texas in Big 12)
        team_v1 = DimTeam(
            team_key=42,  # Manually set for testing (DB would auto-generate)
            team_id="ncaam_251",
            sport="ncaam",
            team_name="Texas",
            team_group_id="ncaam_b12",
            team_group_name="Big 12",
            is_current=False,  # Historical version
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
            valid_to=datetime(2024, 7, 1, tzinfo=UTC),  # Superseded
        )

        # Create new version (Texas moves to SEC)
        team_v2 = DimTeam(
            team_key=143,  # Different surrogate key for new version
            team_id="ncaam_251",  # Same natural key
            sport="ncaam",
            team_name="Texas",
            team_group_id="ncaam_sec",
            team_group_name="Southeastern Conference",
            is_current=True,  # Current version
            valid_from=datetime(2024, 7, 1, tzinfo=UTC),
            valid_to=None,  # NULL = still current
        )

        # Verify historical version
        assert team_v1.team_key == 42
        assert team_v1.team_id == "ncaam_251"
        assert team_v1.team_group_name == "Big 12"
        assert team_v1.is_current is False
        assert team_v1.valid_to is not None

        # Verify current version
        assert team_v2.team_key == 143  # Different surrogate key!
        assert team_v2.team_id == "ncaam_251"  # Same natural key
        assert team_v2.team_group_name == "Southeastern Conference"
        assert team_v2.is_current is True
        assert team_v2.valid_to is None

    def test_dim_team_surrogate_key_placeholder(self):
        """Test team_key surrogate key field exists (auto-generated in DB)."""
        # Note: team_key is auto-generated by database SERIAL
        # Unit tests can't test auto-generation without DB interaction
        # This test verifies the field exists and can be set manually for mocking
        team = DimTeam(
            team_key=1,  # Manually set for testing (DB would auto-generate)
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
        )

        assert team.team_key == 1
        assert isinstance(team.team_key, int)

    def test_dim_team_espn_team_id_field(self):
        """Test espn_team_id field for ESPN API integration."""
        # Test with espn_team_id
        team_with_espn_id = DimTeam(
            team_id="ncaam_150",
            sport="ncaam",
            team_name="Duke",
            espn_team_id="150",
        )

        assert team_with_espn_id.espn_team_id == "150"
        assert isinstance(team_with_espn_id.espn_team_id, str)

        # Test without espn_team_id (defaults to None)
        team_without_espn_id = DimTeam(
            team_id="ncaam_manual_team",
            sport="ncaam",
            team_name="Manual Team",
        )

        assert team_without_espn_id.espn_team_id is None

        # Test espn_team_id can be set after creation
        team_without_espn_id.espn_team_id = "999"
        assert team_without_espn_id.espn_team_id == "999"
