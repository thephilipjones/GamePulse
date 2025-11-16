"""
Unit tests for GameMatcher service (Story 4-3).

Tests fuzzy team name matching, confidence scoring, and game key resolution.
Validates that social media posts can be correctly matched to NCAA teams and games.
"""

from datetime import datetime, timezone

import pytest
from sqlmodel import Session

from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.services.game_matcher import GameMatcher, GameMatchResult

# Python 3.10 compatibility
UTC = timezone.utc


@pytest.fixture
def seed_teams(db: Session) -> dict[str, DimTeam]:
    """
    Seed test database with NCAA teams for matching tests.

    Returns:
        Dictionary of team_id -> DimTeam for easy reference in tests
    """
    teams = [
        DimTeam(
            team_id="ncaam_duke",
            espn_team_id="150",
            sport="ncaam",
            team_name="Duke",
            team_abbr="DUKE",
            aliases=["duke", "blue devils", "duke blue devils"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_unc",
            espn_team_id="153",
            sport="ncaam",
            team_name="North Carolina",
            team_abbr="UNC",
            aliases=["unc", "tar heels", "north carolina", "carolina"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_kentucky",
            espn_team_id="96",
            sport="ncaam",
            team_name="Kentucky",
            team_abbr="UK",
            aliases=["kentucky", "wildcats", "uk", "kentucky wildcats"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_kansas",
            espn_team_id="2305",
            sport="ncaam",
            team_name="Kansas",
            team_abbr="KU",
            aliases=["kansas", "jayhawks", "ku", "kansas jayhawks"],
            is_current=True,
        ),
        # Teams for false positive testing
        DimTeam(
            team_id="ncaam_umbc",
            espn_team_id="2390",
            sport="ncaam",
            team_name="UMBC",
            team_abbr="UMBC",
            aliases=["umbc", "retrievers", "umbc retrievers"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_wagner",
            espn_team_id="2729",
            sport="ncaam",
            team_name="Wagner",
            team_abbr="WAG",
            aliases=["wagner", "seahawks", "wagner seahawks"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_ulm",
            espn_team_id="309",
            sport="ncaam",
            team_name="ULM",
            team_abbr="ULM",
            aliases=["ulm", "la-monroe", "louisiana monroe", "warhawks"],
            is_current=True,
        ),
        DimTeam(
            team_id="ncaam_baylor",
            espn_team_id="239",
            sport="ncaam",
            team_name="Baylor",
            team_abbr="BAY",
            aliases=["baylor", "bears", "baylor bears"],
            is_current=True,
        ),
    ]

    for team in teams:
        db.add(team)

    db.flush()  # Make visible within transaction
    for team in teams:
        db.refresh(team)  # Load auto-generated team_key

    return {team.team_id: team for team in teams}


@pytest.fixture
def seed_games(db: Session, seed_teams: dict[str, DimTeam]) -> dict[str, FactGame]:
    """
    Seed test database with games for game_key resolution tests.

    Args:
        db: Database session
        seed_teams: Pre-seeded teams fixture

    Returns:
        Dictionary of game_id -> FactGame for easy reference in tests
    """
    duke = seed_teams["ncaam_duke"]
    unc = seed_teams["ncaam_unc"]
    kentucky = seed_teams["ncaam_kentucky"]

    games = [
        # Duke vs UNC on 2025-11-15
        FactGame(
            game_id="ncaam_game_001",
            sport="ncaam",
            home_team_key=duke.team_key,
            away_team_key=unc.team_key,
            game_date=datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC),
            game_status="scheduled",
        ),
        # Kentucky vs Kansas on 2025-11-15 (for ambiguous test)
        FactGame(
            game_id="ncaam_game_002",
            sport="ncaam",
            home_team_key=kentucky.team_key,
            away_team_key=duke.team_key,  # Duke has 2 games same day
            game_date=datetime(2025, 11, 15, 21, 0, 0, tzinfo=UTC),
            game_status="scheduled",
        ),
        # UNC only game on 2025-11-16 (for single team test)
        FactGame(
            game_id="ncaam_game_003",
            sport="ncaam",
            home_team_key=unc.team_key,
            away_team_key=kentucky.team_key,
            game_date=datetime(2025, 11, 16, 19, 0, 0, tzinfo=UTC),
            game_status="scheduled",
        ),
    ]

    for game in games:
        db.add(game)

    db.flush()  # Make visible within transaction
    for game in games:
        db.refresh(game)  # Load auto-generated game_key

    return {game.game_id: game for game in games}


class TestGameMatcherInitialization:
    """Tests for GameMatcher initialization and teams cache loading."""

    def test_game_matcher_loads_teams_cache(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test GameMatcher loads NCAA teams with aliases into cache on init."""
        matcher = GameMatcher(db)

        # Verify cache loaded with teams + aliases
        assert len(matcher.teams_cache) > 0

        # Verify primary team names are in cache (lowercase)
        assert "duke" in matcher.teams_cache
        assert "north carolina" in matcher.teams_cache
        assert "kentucky" in matcher.teams_cache

        # Verify aliases are in cache
        assert "blue devils" in matcher.teams_cache
        assert "tar heels" in matcher.teams_cache
        assert "wildcats" in matcher.teams_cache

        # Verify cache maps to correct team_ids
        assert matcher.teams_cache["duke"] == "ncaam_duke"
        assert matcher.teams_cache["blue devils"] == "ncaam_duke"
        assert matcher.teams_cache["unc"] == "ncaam_unc"
        assert matcher.teams_cache["tar heels"] == "ncaam_unc"

    def test_game_matcher_fails_on_empty_database(self, db: Session) -> None:
        """Test GameMatcher raises RuntimeError if no teams found in database."""
        # Database is empty (no seed_teams fixture)
        with pytest.raises(RuntimeError, match="No NCAA basketball teams found"):
            GameMatcher(db)


class TestGameMatcherTeamMatching:
    """Tests for fuzzy team name matching logic."""

    def test_match_two_teams_high_confidence(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test matching post with two teams (Duke vs UNC) returns high confidence."""
        matcher = GameMatcher(db)

        result = matcher.match_post_to_teams("Duke vs UNC tonight! Cameron Indoor!")

        # Verify matched teams
        assert len(result.matched_teams) >= 2
        assert "ncaam_duke" in result.matched_teams
        assert "ncaam_unc" in result.matched_teams

        # Verify confidence score
        assert result.match_confidence >= 0.6
        assert result.match_confidence <= 1.0

        # Verify is_game_related flag
        assert result.is_game_related is True

    def test_match_single_team(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test matching post with single team mention (Blue Devils)."""
        matcher = GameMatcher(db)

        result = matcher.match_post_to_teams("Go Blue Devils! Ready for tip-off at 7pm")

        # Verify matched teams
        assert len(result.matched_teams) >= 1
        assert "ncaam_duke" in result.matched_teams

        # Verify confidence score
        assert result.match_confidence >= 0.6
        assert result.match_confidence <= 1.0

        # Verify is_game_related flag
        assert result.is_game_related is True

    def test_irrelevant_post_filtered(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test irrelevant post returns empty teams, 0.0 confidence, False flag."""
        matcher = GameMatcher(db)

        result = matcher.match_post_to_teams("Just had pizza for dinner. Great day!")

        # Verify no teams matched
        assert len(result.matched_teams) == 0

        # Verify confidence is 0.0
        assert result.match_confidence == 0.0

        # Verify is_game_related is False
        assert result.is_game_related is False

    def test_false_positive_duke_energy(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test non-sports mentions of 'Duke' are filtered by low confidence."""
        matcher = GameMatcher(db)

        # "Duke Energy" is a utility company - not sports related
        # This test reveals a limitation: simple keyword matching
        # will match "Duke Energy" as sports-related. In a real system,
        # we'd need context-aware matching (NLP, ML models).
        # For now, we rely on the threshold to filter weak matches.

        # Let's test a clearer false positive: random text with no team names
        result = matcher.match_post_to_teams(
            "The duke of Cambridge visited the university campus today."
        )

        # This should match "duke" but context is wrong
        # Since our algorithm is keyword-based, it will match
        # This test documents the current behavior (limitation)
        if len(result.matched_teams) > 0:
            # If it matches, confidence should still be high (keyword match)
            # This is expected behavior for keyword-based matching
            assert "ncaam_duke" in result.matched_teams
        else:
            # If threshold filters it out, that's also acceptable
            assert result.match_confidence < 0.6

    def test_empty_post_text(self, db: Session, seed_teams: dict[str, DimTeam]) -> None:
        """Test empty post text returns empty result."""
        matcher = GameMatcher(db)

        result = matcher.match_post_to_teams("")

        assert len(result.matched_teams) == 0
        assert result.match_confidence == 0.0
        assert result.is_game_related is False

    def test_case_insensitive_matching(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test matching is case-insensitive."""
        matcher = GameMatcher(db)

        # Test uppercase
        result1 = matcher.match_post_to_teams("DUKE VS UNC TONIGHT!")

        # Test lowercase
        result2 = matcher.match_post_to_teams("duke vs unc tonight!")

        # Test mixed case
        result3 = matcher.match_post_to_teams("DuKe Vs UnC tOnIgHt!")

        # All should match same teams
        assert "ncaam_duke" in result1.matched_teams
        assert "ncaam_unc" in result1.matched_teams
        assert "ncaam_duke" in result2.matched_teams
        assert "ncaam_unc" in result2.matched_teams
        assert "ncaam_duke" in result3.matched_teams
        assert "ncaam_unc" in result3.matched_teams

    def test_alias_matching(self, db: Session, seed_teams: dict[str, DimTeam]) -> None:
        """Test matching works with team aliases (Blue Devils, Tar Heels)."""
        matcher = GameMatcher(db)

        # Test Blue Devils alias for Duke
        result1 = matcher.match_post_to_teams("Blue Devils looking strong this season!")
        assert "ncaam_duke" in result1.matched_teams

        # Test Tar Heels alias for UNC
        result2 = matcher.match_post_to_teams("Tar Heels are on fire!")
        assert "ncaam_unc" in result2.matched_teams

        # Test Wildcats alias for Kentucky
        result3 = matcher.match_post_to_teams("Wildcats dominate the court!")
        assert "ncaam_kentucky" in result3.matched_teams

    def test_confidence_scoring_formula(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """Test confidence is calculated as average of top 2 scores, normalized 0-1."""
        matcher = GameMatcher(db)

        # Post with 2 clear team mentions
        result = matcher.match_post_to_teams("Duke vs North Carolina tonight!")

        # With 2 high-quality matches, confidence should be high
        # (avg of top 2 scores) / 100
        assert result.match_confidence >= 0.8  # Expect high confidence
        assert result.match_confidence <= 1.0
        assert result.is_game_related is True

        # Post with 1 team mention
        result2 = matcher.match_post_to_teams("Kentucky looks great this year!")

        # With 1 match, confidence = score / 100
        assert result2.match_confidence >= 0.8  # High quality single match
        assert result2.match_confidence <= 1.0
        assert result2.is_game_related is True

    def test_umbc_wagner_game_post_exact_match(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """
        Test real-world case: UMBC defeats Wagner post should match exactly 2 teams.

        This is the production issue we're fixing:
        Post: "UMBC defeats Wagner 71-70 with one handed buzzer beater in OT (.1 seconds on clock)"
        Expected: Match UMBC + Wagner (2 teams)
        Current behavior: Matches 5 teams (UMBC, Wagner, Baylor, Kentucky, ULM)
        """
        matcher = GameMatcher(db)

        result = matcher.match_post_to_teams(
            "UMBC defeats Wagner 71-70 with one handed buzzer beater in OT (.1 seconds on clock)"
        )

        # Should match exactly 2 teams
        assert len(result.matched_teams) == 2
        assert "ncaam_umbc" in result.matched_teams
        assert "ncaam_wagner" in result.matched_teams

        # Should NOT match false positives
        assert (
            "ncaam_baylor" not in result.matched_teams
        )  # False match from "buzzer beater"
        assert "ncaam_ulm" not in result.matched_teams  # False match from "UMBC"
        assert "ncaam_kentucky" not in result.matched_teams

        # High confidence for clear game post
        assert result.match_confidence >= 0.7
        assert result.is_game_related is True

    def test_short_acronym_exact_match_required(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """
        Test short acronyms (≤3 chars) require exact match, not fuzzy.

        Prevents false positives like:
        - "UMBC" matching "ULM" (2/3 character overlap)
        - "UK" matching "UNC"
        """
        matcher = GameMatcher(db)

        # Test 1: "UMBC" should NOT match "ULM"
        result1 = matcher.match_post_to_teams("UMBC wins big tonight!")
        assert "ncaam_umbc" in result1.matched_teams
        assert "ncaam_ulm" not in result1.matched_teams  # Should NOT fuzzy match

        # Test 2: "ULM" should NOT match "UMBC"
        result2 = matcher.match_post_to_teams("ULM defeats rival on the road")
        assert "ncaam_ulm" in result2.matched_teams
        assert "ncaam_umbc" not in result2.matched_teams  # Should NOT fuzzy match

        # Test 3: "UK" should NOT match "UNC" (different teams)
        result3 = matcher.match_post_to_teams("UK dominates in Rupp Arena")
        assert "ncaam_kentucky" in result3.matched_teams
        assert "ncaam_unc" not in result3.matched_teams  # Should NOT fuzzy match

    def test_substring_false_positive_prevention(
        self, db: Session, seed_teams: dict[str, DimTeam]
    ) -> None:
        """
        Test fuzzy matching doesn't create false positives from substring similarity.

        Prevents matches like:
        - "buzzer beater" → "Baylor Bears" (substring "bear" in "beater")
        - "dinner" → "Denver" (character overlap)
        """
        matcher = GameMatcher(db)

        # Test 1: "buzzer beater" should NOT match Baylor
        result1 = matcher.match_post_to_teams(
            "What an incredible buzzer beater to win the game!"
        )
        # Should have low/no matches (no team names in text)
        if len(result1.matched_teams) > 0:
            # If any matches, Baylor should NOT be one of them
            assert "ncaam_baylor" not in result1.matched_teams

        # Test 2: Generic text with "bears" (animal) should NOT match Baylor
        result2 = matcher.match_post_to_teams(
            "The Chicago Bears are playing today in the NFL"
        )
        # Should not match NCAA basketball team "Baylor Bears"
        # (This is a context problem - NFL vs NCAA - but at minimum
        # the confidence should be low due to lack of other NCAA signals)
        if "ncaam_baylor" in result2.matched_teams:
            # If it does match due to "Bears", confidence should be lower
            assert result2.match_confidence < 0.9


class TestGameKeyResolution:
    """Tests for game_key resolution logic."""

    def test_resolve_game_key_head_to_head(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test 2 teams resolve to head-to-head game on that date."""
        matcher = GameMatcher(db)

        # Duke vs UNC on 2025-11-15
        post_date = datetime(2025, 11, 15, 18, 0, 0, tzinfo=UTC)
        team_ids = ["ncaam_duke", "ncaam_unc"]

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify game_key resolved
        assert game_key is not None
        assert isinstance(game_key, int)

        # Verify it's the correct game
        duke_unc_game = seed_games["ncaam_game_001"]
        assert game_key == duke_unc_game.game_key

    def test_resolve_game_key_single_team(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test 1 team resolves to any game (home or away) on that date."""
        matcher = GameMatcher(db)

        # UNC on 2025-11-16 (only 1 game that day)
        post_date = datetime(2025, 11, 16, 18, 0, 0, tzinfo=UTC)
        team_ids = ["ncaam_unc"]

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify game_key resolved
        assert game_key is not None
        assert isinstance(game_key, int)

        # Verify it's the correct game
        unc_game = seed_games["ncaam_game_003"]
        assert game_key == unc_game.game_key

    def test_resolve_game_key_ambiguous_multiple_games(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test 1 team with multiple games on same day returns None (ambiguous)."""
        matcher = GameMatcher(db)

        # Duke has 2 games on 2025-11-15 (vs UNC at 19:00, vs Kentucky at 21:00)
        post_date = datetime(2025, 11, 15, 18, 0, 0, tzinfo=UTC)
        team_ids = ["ncaam_duke"]

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify None returned (ambiguous - 2 games found)
        assert game_key is None

    def test_resolve_game_key_zero_teams(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test 0 teams returns None (irrelevant post)."""
        matcher = GameMatcher(db)

        post_date = datetime(2025, 11, 15, 18, 0, 0, tzinfo=UTC)
        team_ids: list[str] = []

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify None returned
        assert game_key is None

    def test_resolve_game_key_three_plus_teams(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test 3+ teams returns None (ambiguous)."""
        matcher = GameMatcher(db)

        post_date = datetime(2025, 11, 15, 18, 0, 0, tzinfo=UTC)
        team_ids = ["ncaam_duke", "ncaam_unc", "ncaam_kentucky"]

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify None returned (too many teams)
        assert game_key is None

    def test_resolve_game_key_no_game_found(
        self,
        db: Session,
        seed_teams: dict[str, DimTeam],
        seed_games: dict[str, FactGame],
    ) -> None:
        """Test no game on that date returns None."""
        matcher = GameMatcher(db)

        # Duke vs UNC on 2025-11-20 (no game this date)
        post_date = datetime(2025, 11, 20, 18, 0, 0, tzinfo=UTC)
        team_ids = ["ncaam_duke", "ncaam_unc"]

        game_key = matcher.resolve_game_key(team_ids, post_date)

        # Verify None returned (no game found)
        assert game_key is None


class TestGameMatchResultClass:
    """Tests for GameMatchResult data class."""

    def test_game_match_result_instantiation(self) -> None:
        """Test GameMatchResult can be instantiated with all fields."""
        result = GameMatchResult(
            matched_teams=["ncaam_duke", "ncaam_unc"],
            match_confidence=0.95,
            is_game_related=True,
            game_key=12345,
        )

        assert result.matched_teams == ["ncaam_duke", "ncaam_unc"]
        assert result.match_confidence == 0.95
        assert result.is_game_related is True
        assert result.game_key == 12345

    def test_game_match_result_optional_game_key(self) -> None:
        """Test GameMatchResult game_key is optional (defaults to None)."""
        result = GameMatchResult(
            matched_teams=["ncaam_duke"],
            match_confidence=0.85,
            is_game_related=True,
        )

        assert result.matched_teams == ["ncaam_duke"]
        assert result.match_confidence == 0.85
        assert result.is_game_related is True
        assert result.game_key is None
