"""
Unit tests for TeamEnricher service.

Tests team data enrichment with colors and aliases from external sources.
Validates idempotency, fuzzy matching, and programmatic alias generation.
"""

from datetime import timezone
from unittest.mock import Mock, patch

import pytest
from sqlmodel import Session, select

from app.models.dim_team import DimTeam
from app.services.team_enricher import EnrichmentReport, TeamEnricher

# Python 3.10 compatibility
UTC = timezone.utc


@pytest.fixture
def mock_colors_dataset() -> list[dict[str, object]]:
    """
    Mock NCAA team colors dataset (GitHub format).

    Returns:
        List of team dictionaries with name, colors, and slug
    """
    return [
        {
            "name": "Duke Blue Devils",
            "colors": ["#003087", "#FFFFFF"],
            "slug": "duke_blue_devils",
        },
        {
            "name": "North Carolina Tar Heels",
            "colors": ["#7BAFD4", "#FFFFFF"],
            "slug": "north_carolina_tar_heels",
        },
        {
            "name": "Kansas Jayhawks",
            "colors": ["#0051BA", "#E8000D"],
            "slug": "kansas_jayhawks",
        },
        {
            "name": "Kentucky Wildcats",
            "colors": ["#0033A0", "#FFFFFF"],
            "slug": "kentucky_wildcats",
        },
        {
            "name": "Villanova Wildcats",
            "colors": ["#00205B", "#FFFFFF"],
            "slug": "villanova_wildcats",
        },
    ]


@pytest.fixture
def seed_teams(db: Session) -> dict[str, DimTeam]:
    """
    Seed test database with teams for enrichment tests.

    Returns:
        Dictionary of team_id -> DimTeam for easy reference
    """
    teams = [
        # Team with no enrichment (will be enriched)
        DimTeam(
            team_id="ncaam_duke",
            espn_team_id="duke",
            sport="ncaam",
            team_name="Duke",
            aliases=[],
            primary_color=None,
            secondary_color=None,
            is_current=True,
        ),
        # Team with partial enrichment (has colors but no aliases)
        DimTeam(
            team_id="ncaam_unc",
            espn_team_id="north-carolina",
            sport="ncaam",
            team_name="North Carolina",
            aliases=[],
            primary_color="#7BAFD4",
            secondary_color="#FFFFFF",
            is_current=True,
        ),
        # Team with full enrichment (will be skipped unless force=True)
        DimTeam(
            team_id="ncaam_kansas",
            espn_team_id="kansas",
            sport="ncaam",
            team_name="Kansas",
            aliases=["kansas", "jayhawks"],
            primary_color="#0051BA",
            secondary_color="#E8000D",
            is_current=True,
        ),
        # Team with no external match (programmatic aliases only)
        DimTeam(
            team_id="ncaam_unknown",
            espn_team_id="unknown",
            sport="ncaam",
            team_name="Unknown State",
            aliases=[],
            primary_color=None,
            secondary_color=None,
            is_current=True,
        ),
        # Team with compound name (tests alias generation)
        DimTeam(
            team_id="ncaam_am-corpus-chris",
            espn_team_id="am-corpus-chris",
            sport="ncaam",
            team_name="A&M-Corpus Christi",
            aliases=[],
            primary_color=None,
            secondary_color=None,
            is_current=True,
        ),
    ]

    for team in teams:
        db.add(team)
    db.commit()

    # Refresh to get database-generated fields
    for team in teams:
        db.refresh(team)

    return {team.team_id: team for team in teams}


class TestTeamEnricher:
    """Test suite for TeamEnricher service."""

    def test_fetch_colors_dataset(
        self, db: Session, mock_colors_dataset: list[dict[str, object]]
    ) -> None:
        """Test fetching external colors dataset from GitHub."""
        enricher = TeamEnricher(db)

        with patch("httpx.get") as mock_get:
            # Mock HTTP response
            mock_response = Mock()
            mock_response.json.return_value = mock_colors_dataset
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Fetch dataset
            data = enricher.fetch_colors_dataset()

            # Verify
            assert len(data) == 5
            assert data[0]["name"] == "Duke Blue Devils"
            assert data[0]["colors"] == ["#003087", "#FFFFFF"]
            assert enricher.colors_data is not None
            mock_get.assert_called_once()

    def test_match_team_to_colors_dataset_exact(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test exact team name matching to colors dataset."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_duke"]

        # Match (Duke -> Duke Blue Devils)
        colors = enricher.match_team_to_colors_dataset(team)

        assert colors is not None
        assert colors["primary"] == "#003087"
        assert colors["secondary"] == "#FFFFFF"

    def test_match_team_to_colors_dataset_fuzzy(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test fuzzy team name matching to colors dataset."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_unc"]

        # Fuzzy match (North Carolina -> North Carolina Tar Heels)
        colors = enricher.match_team_to_colors_dataset(team)

        assert colors is not None
        assert colors["primary"] == "#7BAFD4"
        assert colors["secondary"] == "#FFFFFF"

    def test_match_team_to_colors_dataset_no_match(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test no match returns None."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_unknown"]

        colors = enricher.match_team_to_colors_dataset(team)

        assert colors is None

    def test_generate_aliases_simple(self, db: Session) -> None:
        """Test alias generation for simple team names."""
        enricher = TeamEnricher(db)

        # Single word team name
        aliases = enricher.generate_aliases("Duke")
        assert "duke" in aliases
        assert len(aliases) == 1

    def test_generate_aliases_compound(self, db: Session) -> None:
        """Test alias generation for compound team names."""
        enricher = TeamEnricher(db)

        # Team with mascot
        aliases = enricher.generate_aliases("Duke Blue Devils")
        assert "duke blue devils" in aliases  # Full name
        assert "duke" in aliases  # School name
        assert "blue devils" in aliases  # Mascot
        assert len(aliases) >= 3

    def test_generate_aliases_multi_word_school(self, db: Session) -> None:
        """Test alias generation for multi-word school names."""
        enricher = TeamEnricher(db)

        # Multi-word school + mascot
        aliases = enricher.generate_aliases("North Carolina Tar Heels")
        assert "north carolina tar heels" in aliases  # Full name
        assert "north carolina" in aliases  # School name (2 words)
        assert "north" in aliases  # First word
        assert "tar heels" in aliases  # Mascot

    def test_generate_aliases_abbreviation(self, db: Session) -> None:
        """Test alias generation handles abbreviations correctly."""
        enricher = TeamEnricher(db)

        aliases = enricher.generate_aliases("Alabama St.")
        assert "alabama st." in aliases  # Full name with abbreviation

        aliases = enricher.generate_aliases("A&M-Corpus Christi")
        assert "a&m-corpus christi" in aliases

    def test_merge_aliases_no_duplicates(self, db: Session) -> None:
        """Test alias merging removes duplicates (case-insensitive)."""
        enricher = TeamEnricher(db)

        existing = ["duke", "Blue Devils"]
        new = ["Duke", "blue devils", "Duke Blue Devils"]

        merged = enricher.merge_aliases(existing, new)

        # Should preserve existing, add only new ones
        assert "duke" in merged
        assert "Blue Devils" in merged or "blue devils" in merged
        assert "Duke Blue Devils" in merged or "duke blue devils" in merged

        # Check no case-sensitive duplicates
        merged_lower = [alias.lower() for alias in merged]
        assert len(merged_lower) == len(set(merged_lower))

    def test_merge_aliases_preserves_existing(self, db: Session) -> None:
        """Test alias merging preserves existing aliases."""
        enricher = TeamEnricher(db)

        existing = ["manual_alias_1", "manual_alias_2"]
        new = ["generated_alias"]

        merged = enricher.merge_aliases(existing, new)

        assert "manual_alias_1" in merged
        assert "manual_alias_2" in merged
        assert "generated_alias" in merged

    def test_enrich_team_with_colors(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test enriching a team with colors from external dataset."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_duke"]
        assert team.primary_color is None
        assert team.secondary_color is None

        # Enrich
        changed = enricher.enrich_team(team, force=False)

        assert changed is True
        assert team.primary_color == "#003087"
        assert team.secondary_color == "#FFFFFF"
        assert len(team.aliases) > 0
        assert team.updated_at is not None

    def test_enrich_team_with_aliases(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test enriching a team with programmatic aliases."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_unknown"]
        assert len(team.aliases) == 0

        # Enrich (no color match, but aliases generated)
        changed = enricher.enrich_team(team, force=False)

        assert changed is True
        assert team.primary_color is None  # No external match
        assert len(team.aliases) > 0
        assert "unknown state" in team.aliases

    def test_enrich_team_skip_if_already_enriched(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test team is skipped if already enriched (unless force=True)."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_kansas"]
        original_aliases_count = len(team.aliases)

        # Should skip (already has colors and aliases)
        # But will still merge new programmatic aliases
        enricher.enrich_team(team, force=False)

        # Aliases may change (merge), but colors should stay same
        assert team.primary_color == "#0051BA"
        assert len(team.aliases) >= original_aliases_count

    def test_enrich_team_force_update(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test force=True updates even if already enriched."""
        enricher = TeamEnricher(db)
        enricher.colors_data = mock_colors_dataset

        team = seed_teams["ncaam_kansas"]

        # Force update
        enricher.enrich_team(team, force=True)

        # Colors may change if dataset differs
        # At minimum, updated_at should change
        assert team.updated_at is not None

    def test_enrich_all_teams_dry_run(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test dry run mode doesn't commit changes."""
        enricher = TeamEnricher(db)

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_colors_dataset
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Mock session.commit to verify it's not called in dry_run mode
            with patch.object(db, "commit", wraps=db.commit) as mock_commit:
                # Run dry run
                report = enricher.enrich_all_teams(
                    sport="ncaam", dry_run=True, force=False
                )

                # Verify report shows enrichment happened
                assert report.teams_processed > 0
                assert report.teams_enriched > 0

                # Verify commit was NOT called in dry_run mode
                mock_commit.assert_not_called()

    def test_enrich_all_teams_success(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test successful enrichment of all teams."""
        enricher = TeamEnricher(db)

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_colors_dataset
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # Run enrichment
            report = enricher.enrich_all_teams(
                sport="ncaam", dry_run=False, force=False
            )

            # Verify report
            assert report.teams_processed == 5  # 5 teams in seed_teams
            assert (
                report.teams_enriched >= 3
            )  # At least duke, unc, unknown should be enriched
            assert report.teams_failed == 0
            assert report.errors is not None
            assert len(report.errors) == 0

            # Verify database changes persisted
            db.commit()
            db.refresh(seed_teams["ncaam_duke"])
            assert seed_teams["ncaam_duke"].primary_color is not None
            aliases = seed_teams["ncaam_duke"].aliases
            assert aliases is not None
            assert len(aliases) > 0

    def test_enrich_all_teams_idempotency(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        mock_colors_dataset: list[dict[str, object]],
    ) -> None:
        """Test enrichment is idempotent (same result when run multiple times)."""
        enricher = TeamEnricher(db)

        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_colors_dataset
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response

            # First run
            report1 = enricher.enrich_all_teams(
                sport="ncaam", dry_run=False, force=False
            )
            db.commit()

            # Capture state after first run
            team_after_first = db.exec(
                select(DimTeam).where(DimTeam.team_id == "ncaam_duke")
            ).first()
            assert team_after_first is not None
            assert team_after_first.aliases is not None
            aliases_after_first = team_after_first.aliases.copy()
            color_after_first = team_after_first.primary_color

            # Second run
            report2 = enricher.enrich_all_teams(
                sport="ncaam", dry_run=False, force=False
            )
            db.commit()

            # Verify second run skipped already-enriched teams
            assert report2.teams_enriched <= report1.teams_enriched

            # Verify data is same (or very similar)
            team_after_second = db.exec(
                select(DimTeam).where(DimTeam.team_id == "ncaam_duke")
            ).first()
            assert team_after_second is not None
            assert team_after_second.primary_color == color_after_first
            # Aliases might have minimal additions but should not differ significantly
            assert team_after_second.aliases is not None
            assert set(aliases_after_first).issubset(set(team_after_second.aliases))

    def test_enrich_all_teams_handles_errors(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test enrichment handles errors gracefully."""
        enricher = TeamEnricher(db)

        with patch("httpx.get") as mock_get:
            # Simulate HTTP error
            mock_get.side_effect = Exception("Network error")

            # Run enrichment
            report = enricher.enrich_all_teams(
                sport="ncaam", dry_run=False, force=False
            )

            # Should have errors but not crash
            assert report.errors is not None
            assert len(report.errors) > 0
            assert "Network error" in str(report.errors)

    def test_is_abbreviation(self, db: Session) -> None:
        """Test abbreviation detection helper."""
        enricher = TeamEnricher(db)

        # Test cases
        assert enricher._is_abbreviation("St.") is True  # Period
        assert enricher._is_abbreviation("A&M") is True  # Ampersand
        assert enricher._is_abbreviation("UNC") is True  # Short uppercase
        assert enricher._is_abbreviation("UK") is True  # Short uppercase
        assert enricher._is_abbreviation("Duke") is False  # Normal word
        assert enricher._is_abbreviation("Blue") is False  # Normal word
        assert enricher._is_abbreviation("UMBC") is True  # 4-char uppercase

    def test_enrichment_report_initialization(self) -> None:
        """Test EnrichmentReport dataclass initialization."""
        report = EnrichmentReport()

        assert report.teams_processed == 0
        assert report.teams_enriched == 0
        assert report.teams_failed == 0
        assert report.errors == []

        # Test with values
        report = EnrichmentReport(teams_processed=10, teams_enriched=8, teams_failed=2)
        assert report.teams_processed == 10
        assert report.teams_enriched == 8
        assert report.teams_failed == 2
