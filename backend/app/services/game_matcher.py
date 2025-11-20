"""
Game matching service for GamePulse (Epic 4, Story 4-3).

Implements fuzzy team name matching to detect NCAA teams in social media posts.
Uses RapidFuzz for high-performance string matching and calculates confidence scores.
Optionally resolves matched teams to specific game keys.

Performance: 1000 matches in <1 second via in-memory cache and C++ RapidFuzz.
"""

from datetime import datetime, timedelta

import structlog
from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame

logger = structlog.get_logger(__name__)


class GameMatchResult:
    """
    Result of team matching operation.

    Attributes:
        matched_teams: List of matched team IDs (natural keys)
        match_confidence: Overall confidence score (0.0-1.0)
        is_game_related: True if confidence >= 0.6 threshold
        game_key: Optional resolved game key if unique match found
    """

    def __init__(
        self,
        matched_teams: list[str],
        match_confidence: float,
        is_game_related: bool,
        game_key: int | None = None,
    ):
        self.matched_teams = matched_teams
        self.match_confidence = match_confidence
        self.is_game_related = is_game_related
        self.game_key = game_key


class GameMatcher:
    """
    Fuzzy team name matching service for social media posts.

    Features:
    - In-memory team cache with aliases for fast matching
    - Multi-tier matching: exact match for short acronyms (≤3 chars), token-based for longer names
    - Confidence scoring (average of top 2 matches, normalized 0-1)
    - Optional game key resolution (2 teams → head-to-head, 1 team → any game)
    - Structured logging (teams_loaded, match_result, resolution events)

    Matching Strategy (improved for false positive reduction):
    - Tier 1: Exact word match for aliases ≤3 characters (prevents UMBC→ULM false matches)
    - Tier 2: partial_ratio for aliases >3 characters (substring matching for team names)
    - Threshold: 70/100 (increased from 60 to reduce false positives like "buzzer beater"→"Baylor Bears")

    Usage:
        matcher = GameMatcher(session)
        await matcher.initialize()
        result = matcher.match_post_to_teams("Duke vs UNC tonight!")
        # result.matched_teams = ["ncaam_duke", "ncaam_unc"]
        # result.match_confidence = 0.95
        # result.is_game_related = True

        game_key = await matcher.resolve_game_key(result.matched_teams, post_date)
    """

    MATCH_THRESHOLD = 75  # RapidFuzz score threshold (0-100 scale) - increased from 70 to reduce false positives
    CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for is_game_related flag
    TOP_N_MATCHES = 5  # Number of top matches to consider
    SHORT_ACRONYM_LENGTH = 5  # Aliases ≤ this length require exact match (prevents "wake"→"basketball", "elon"→"oregon")

    # Common words that should never match team names (prevents "college" → "Colgate")
    WORD_BLACKLIST = {
        # Educational institutions
        "college",
        "university",
        "state",
        "school",
        # Sports terms
        "team",
        "game",
        "play",
        "player",
        "coach",
        "basketball",
        "football",
        "sports",
        "season",
        # Time references
        "tonight",
        "today",
        "yesterday",
        "tomorrow",
        "week",
        "year",
        # Common articles/prepositions that appear in team names
        "the",
        "of",
        "at",
        "in",
        "and",
        "a",
        "an",
        # Geographic/directional words (too ambiguous when standalone)
        "north",
        "south",
        "east",
        "west",
        "central",
        "northern",
        "southern",
        "eastern",
        "western",
        # Common nouns that appear in team names
        "forest",
        "city",
        "bay",
        "valley",
        "river",
        "lake",
        "mountain",
        "coast",
    }

    def __init__(self, session: Session | AsyncSession):
        """
        Initialize GameMatcher with teams cache from database.

        Args:
            session: Database session (sync or async) for loading teams

        Raises:
            RuntimeError: If team cache loading fails

        Note:
            For sync sessions, cache is loaded automatically in __init__.
            For async sessions, call await initialize() after construction.
        """
        self.session = session
        self.teams_cache: dict[str, str] = {}  # alias -> team_id mapping
        self._is_async = isinstance(session, AsyncSession)

        # For sync sessions, load cache immediately (test compatibility)
        if not self._is_async:
            self._load_teams_cache_sync()

    async def initialize(self) -> None:
        """Load teams cache from database. Must be called after __init__ for async sessions."""
        await self._load_teams_cache()

    def _load_teams_cache_sync(self) -> None:
        """
        Load NCAA basketball teams with aliases into in-memory cache (synchronous version).

        Queries dim_team for all current NCAA basketball teams (sport='ncaam', is_current=True).
        Builds searchable dictionary with team names + aliases as keys, team_id as value.

        Raises:
            RuntimeError: If database query fails or no teams found
        """
        try:
            # Query all current NCAA basketball teams
            statement = select(DimTeam).where(
                DimTeam.sport == "ncaam",
                DimTeam.is_current == True,  # noqa: E712
            )
            result = self.session.execute(statement)
            teams = result.scalars().all()  # type: ignore[union-attr]

            if not teams:
                raise RuntimeError(
                    "No NCAA basketball teams found in dim_team (sport='ncaam', is_current=True)"
                )

            # Build alias cache: lowercase alias -> team_id
            for team in teams:
                # Add primary team name (unless blacklisted)
                team_name_lower = team.team_name.lower()
                if team_name_lower not in self.WORD_BLACKLIST:
                    self.teams_cache[team_name_lower] = team.team_id

                # Add all aliases from TEXT[] column (skip blacklisted words)
                if team.aliases:
                    for alias in team.aliases:
                        alias_lower = alias.lower()
                        if alias_lower not in self.WORD_BLACKLIST:
                            self.teams_cache[alias_lower] = team.team_id

            logger.info(
                "game_matcher_teams_loaded",
                teams_count=len(teams),
                aliases_count=len(self.teams_cache),
            )

        except Exception as e:
            logger.error(
                "game_matcher_cache_load_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise RuntimeError(f"Failed to load teams cache: {e}") from e

    async def _load_teams_cache(self) -> None:
        """
        Load NCAA basketball teams with aliases into in-memory cache.

        Queries dim_team for all current NCAA basketball teams (sport='ncaam', is_current=True).
        Builds searchable dictionary with team names + aliases as keys, team_id as value.

        Raises:
            RuntimeError: If database query fails or no teams found
        """
        try:
            # Query all current NCAA basketball teams
            statement = select(DimTeam).where(
                DimTeam.sport == "ncaam",
                DimTeam.is_current == True,  # noqa: E712
            )
            result = await self.session.execute(statement)  # type: ignore[misc]
            teams = result.scalars().all()

            if not teams:
                raise RuntimeError(
                    "No NCAA basketball teams found in dim_team (sport='ncaam', is_current=True)"
                )

            # Build alias cache: lowercase alias -> team_id
            for team in teams:
                # Add primary team name (unless blacklisted)
                team_name_lower = team.team_name.lower()
                if team_name_lower not in self.WORD_BLACKLIST:
                    self.teams_cache[team_name_lower] = team.team_id

                # Add all aliases from TEXT[] column (skip blacklisted words)
                if team.aliases:
                    for alias in team.aliases:
                        alias_lower = alias.lower()
                        if alias_lower not in self.WORD_BLACKLIST:
                            self.teams_cache[alias_lower] = team.team_id

            logger.info(
                "game_matcher_teams_loaded",
                teams_count=len(teams),
                aliases_count=len(self.teams_cache),
            )

        except Exception as e:
            logger.error(
                "game_matcher_cache_load_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise RuntimeError(f"Failed to load teams cache: {e}") from e

    def _remove_urls(self, text: str) -> str:
        """
        Remove URLs from text to prevent false positive matches.

        Example: "Check /r/CollegeBasketball" contains "College" which fuzzy matches "Colgate"
        This function strips URLs to prevent such false positives.

        Args:
            text: Input text possibly containing URLs

        Returns:
            Text with URLs removed
        """
        import re

        # Remove http/https URLs
        text = re.sub(r"https?://\S+", "", text)
        # Remove www URLs
        text = re.sub(r"www\.\S+", "", text)
        # Remove markdown links [text](url)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove /r/subreddit and /u/user patterns
        text = re.sub(r"/[ru]/\w+", "", text)

        return text

    def match_post_to_teams(self, post_text: str) -> GameMatchResult:
        """
        Match social media post text to NCAA teams using multi-tier fuzzy matching.

        Multi-tier matching strategy to reduce false positives:
        - Tier 1: Exact word match for short acronyms (≤3 chars) - prevents UMBC→ULM
        - Tier 2: partial_ratio for longer aliases (>3 chars) - finds team names in text
        - Threshold: 70/100 (increased from 60 to reduce false positives)

        Returns top 5 matches with scores >= 70/100 threshold.
        Deduplicates multiple aliases for same team.
        Confidence = average of top 2 match scores, normalized to 0-1.

        Args:
            post_text: Social media post text to analyze

        Returns:
            GameMatchResult with matched teams, confidence, and is_game_related flag

        Examples:
            >>> result = matcher.match_post_to_teams("Duke vs UNC tonight!")
            >>> result.matched_teams
            ['ncaam_duke', 'ncaam_unc']
            >>> result.match_confidence
            0.95
            >>> result.is_game_related
            True
        """
        if not post_text or not post_text.strip():
            logger.debug(
                "game_match_result",
                post_text_preview="<empty>",
                matched_teams=[],
                confidence=0.0,
                is_game_related=False,
            )
            return GameMatchResult(
                matched_teams=[], match_confidence=0.0, is_game_related=False
            )

        # Normalize post text for matching
        # Remove URLs to prevent false positives (e.g., "College" in URLs matching "Colgate")
        text_cleaned = self._remove_urls(post_text)
        text_lower = text_cleaned.lower()

        # Find all matches above threshold using multi-tier strategy
        matches: list[tuple[str, float]] = []  # (team_id, score)

        for alias, team_id in self.teams_cache.items():
            # Skip if alias is a common word in blacklist (prevents "college" → "Colgate")
            if alias in self.WORD_BLACKLIST:
                continue

            # Tier 1: Short acronyms (≤3 chars) require exact word match
            if len(alias) <= self.SHORT_ACRONYM_LENGTH:
                # Check if alias appears as a complete word (word boundary check)
                # This prevents "UMBC" from matching "ULM" and vice versa
                words = text_lower.split()
                if alias in words:
                    score = 100.0  # Exact match = perfect score
                else:
                    score = 0.0  # No fuzzy matching for short acronyms
            # Tier 2: Longer aliases - use partial_ratio but with higher threshold
            else:
                # Use partial_ratio for substring matching (finds "Duke" in "Duke vs UNC")
                # Higher threshold (70 vs old 60) reduces false positives
                score = fuzz.partial_ratio(alias, text_lower)

            if score >= self.MATCH_THRESHOLD:
                matches.append((team_id, score))

        # Sort by score descending and take top N
        matches.sort(key=lambda x: x[1], reverse=True)
        top_matches = matches[: self.TOP_N_MATCHES]

        # Deduplicate by team_id (multiple aliases can match same team)
        seen_teams: set[str] = set()
        unique_matches: list[tuple[str, float]] = []
        for team_id, score in top_matches:
            if team_id not in seen_teams:
                seen_teams.add(team_id)
                unique_matches.append((team_id, score))

        # Extract team IDs and scores
        matched_teams = [team_id for team_id, _ in unique_matches]
        scores = [score for _, score in unique_matches]

        # Calculate confidence: average of top 2 scores, normalized to 0-1
        if len(scores) >= 2:
            confidence = (scores[0] + scores[1]) / 2 / 100.0
        elif len(scores) == 1:
            confidence = scores[0] / 100.0
        else:
            confidence = 0.0

        # Set is_game_related flag based on confidence threshold
        is_game_related = confidence >= self.CONFIDENCE_THRESHOLD

        logger.debug(
            "game_match_result",
            post_text_preview=post_text[:50] + "..."
            if len(post_text) > 50
            else post_text,
            matched_teams=matched_teams,
            confidence=round(confidence, 3),
            is_game_related=is_game_related,
            top_scores=scores[:3],  # Log top 3 scores for debugging
        )

        return GameMatchResult(
            matched_teams=matched_teams,
            match_confidence=confidence,
            is_game_related=is_game_related,
        )

    def resolve_game_key_sync(
        self, team_ids: list[str], post_date: datetime
    ) -> int | None:
        """
        Resolve matched teams to a specific game key (synchronous version).

        Logic:
        - 2 teams: Query for head-to-head game on that date
        - 1 team: Query for any game (home or away) for that team
        - 0 or 3+ teams: Return None (ambiguous or irrelevant)

        Args:
            team_ids: List of matched team IDs (natural keys from dim_team.team_id)
            post_date: Date of the social media post (timezone-aware)

        Returns:
            Game key (surrogate PK) if unique match found, else None
        """
        # Handle edge cases: 0 or 3+ teams (ambiguous)
        if len(team_ids) == 0 or len(team_ids) >= 3:
            if len(team_ids) >= 3:
                logger.warning(
                    "game_resolution_ambiguous",
                    team_ids=team_ids,
                    post_date=post_date.isoformat(),
                    reason="too_many_teams",
                )
            return None

        try:
            # Get team_key surrogate keys from team_id natural keys
            team_keys: list[int] = []
            for team_id in team_ids:
                statement = select(DimTeam.team_key).where(DimTeam.team_id == team_id)
                result = self.session.execute(statement)
                team_key = result.scalar_one_or_none()  # type: ignore[union-attr]
                if team_key:
                    team_keys.append(team_key)

            if len(team_keys) != len(team_ids):
                logger.warning(
                    "game_resolution_failed",
                    team_ids=team_ids,
                    reason="team_keys_not_found",
                )
                return None

            # Case 1: Two teams - query for head-to-head game
            if len(team_keys) == 2:
                start_of_day = post_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_of_day = start_of_day + timedelta(days=1)

                statement = (
                    select(FactGame.game_key)
                    .where(
                        FactGame.game_date >= start_of_day,
                        FactGame.game_date < end_of_day,
                    )
                    .where(
                        (
                            (FactGame.home_team_key == team_keys[0])
                            & (FactGame.away_team_key == team_keys[1])
                        )
                        | (
                            (FactGame.home_team_key == team_keys[1])
                            & (FactGame.away_team_key == team_keys[0])
                        )
                    )
                )
                result = self.session.execute(statement)
                game_key = result.scalar_one_or_none()  # type: ignore[union-attr]
                return game_key

            # Case 2: One team - query for any game (home or away)
            elif len(team_keys) == 1:
                start_of_day = post_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_of_day = start_of_day + timedelta(days=1)

                statement = (
                    select(FactGame.game_key)
                    .where(
                        FactGame.game_date >= start_of_day,
                        FactGame.game_date < end_of_day,
                    )
                    .where(
                        (FactGame.home_team_key == team_keys[0])
                        | (FactGame.away_team_key == team_keys[0])
                    )
                )
                result = self.session.execute(statement)
                games = list(result.scalars().all())  # type: ignore[union-attr]

                # Return game_key only if exactly one game found (unambiguous)
                if len(games) == 1:
                    return games[0]  # type: ignore[no-any-return]
                elif len(games) > 1:
                    logger.warning(
                        "game_resolution_ambiguous",
                        team_id=team_ids[0],
                        post_date=post_date.isoformat(),
                        reason="multiple_games_found",
                        games_count=len(games),
                    )
                    return None
                else:
                    return None

        except Exception as e:
            logger.error(
                "game_resolution_error",
                team_ids=team_ids,
                post_date=post_date.isoformat(),
                error_type=type(e).__name__,
                error=str(e),
            )
            return None

        return None

    async def resolve_game_key(
        self, team_ids: list[str], post_date: datetime
    ) -> int | None:
        """
        Resolve matched teams to a specific game key on the post date.

        Logic:
        - 2 teams: Query for head-to-head game on that date
        - 1 team: Query for any game (home or away) for that team
        - 0 or 3+ teams: Return None (ambiguous or irrelevant)

        Args:
            team_ids: List of matched team IDs (natural keys from dim_team.team_id)
            post_date: Date of the social media post (timezone-aware)

        Returns:
            Game key (surrogate PK) if unique match found, else None

        Examples:
            >>> game_key = matcher.resolve_game_key(["ncaam_duke", "ncaam_unc"], post_date)
            >>> game_key
            12345
        """
        # Handle edge cases: 0 or 3+ teams (ambiguous)
        if len(team_ids) == 0 or len(team_ids) >= 3:
            if len(team_ids) >= 3:
                logger.warning(
                    "game_resolution_ambiguous",
                    team_ids=team_ids,
                    post_date=post_date.isoformat(),
                    reason="too_many_teams",
                )
            return None

        try:
            # Get team_key surrogate keys from team_id natural keys
            team_keys: list[int] = []
            for team_id in team_ids:
                statement = select(DimTeam.team_key).where(DimTeam.team_id == team_id)
                result = await self.session.execute(statement)  # type: ignore[misc]
                team_key = result.scalar_one_or_none()
                if team_key:
                    team_keys.append(team_key)

            if len(team_keys) != len(team_ids):
                logger.warning(
                    "game_resolution_failed",
                    team_ids=team_ids,
                    reason="team_keys_not_found",
                )
                return None

            # Case 1: Two teams - query for head-to-head game
            if len(team_keys) == 2:
                start_of_day = post_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_of_day = start_of_day + timedelta(days=1)

                statement = (
                    select(FactGame.game_key)
                    .where(
                        FactGame.game_date >= start_of_day,
                        FactGame.game_date < end_of_day,
                    )
                    .where(
                        (
                            (FactGame.home_team_key == team_keys[0])
                            & (FactGame.away_team_key == team_keys[1])
                        )
                        | (
                            (FactGame.home_team_key == team_keys[1])
                            & (FactGame.away_team_key == team_keys[0])
                        )
                    )
                )
                result = await self.session.execute(statement)  # type: ignore[misc]
                game_key = result.scalar_one_or_none()
                return game_key  # type: ignore[no-any-return]

            # Case 2: One team - query for any game (home or away)
            elif len(team_keys) == 1:
                start_of_day = post_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_of_day = start_of_day + timedelta(days=1)

                statement = (
                    select(FactGame.game_key)
                    .where(
                        FactGame.game_date >= start_of_day,
                        FactGame.game_date < end_of_day,
                    )
                    .where(
                        (FactGame.home_team_key == team_keys[0])
                        | (FactGame.away_team_key == team_keys[0])
                    )
                )
                result = await self.session.execute(statement)  # type: ignore[misc]
                games = list(result.scalars().all())

                # Return game_key only if exactly one game found (unambiguous)
                if len(games) == 1:
                    return games[0]  # type: ignore[no-any-return]
                elif len(games) > 1:
                    logger.warning(
                        "game_resolution_ambiguous",
                        team_id=team_ids[0],
                        post_date=post_date.isoformat(),
                        reason="multiple_games_found",
                        games_count=len(games),
                    )
                    return None
                else:
                    return None

        except Exception as e:
            logger.error(
                "game_resolution_error",
                team_ids=team_ids,
                post_date=post_date.isoformat(),
                error_type=type(e).__name__,
                error=str(e),
            )
            return None

        return None

    async def resolve_single_team_game(
        self, team_id: str, post_date: datetime, time_window_hours: int = 24
    ) -> int | None:
        """
        Resolve a single team mention to a game within a time window.

        Used for high-confidence single-team posts (≥0.85 confidence) to capture:
        - Pre-game hype posts
        - Post-game reaction posts
        - General team discussion near game time

        Args:
            team_id: Matched team ID (natural key from dim_team.team_id)
            post_date: Timestamp of the social media post (timezone-aware)
            time_window_hours: Hours before and after post to search for games (default: 24)

        Returns:
            Game key (surrogate PK) if exactly one game found in window, else None

        Examples:
            >>> # Post 6 hours before Duke vs UNC game
            >>> game_key = await matcher.resolve_single_team_game("ncaam_duke", post_date, 24)
            >>> game_key
            12345
        """
        try:
            # Get team_key surrogate key from team_id natural key
            statement = select(DimTeam.team_key).where(DimTeam.team_id == team_id)
            result = await self.session.execute(statement)  # type: ignore[misc]
            team_key = result.scalar_one_or_none()

            if not team_key:
                logger.warning(
                    "single_team_game_resolution_failed",
                    team_id=team_id,
                    reason="team_key_not_found",
                )
                return None

            # Define time window: ±time_window_hours from post_date
            window_start = post_date - timedelta(hours=time_window_hours)
            window_end = post_date + timedelta(hours=time_window_hours)

            # Query for games in time window where team is home or away
            statement = (
                select(FactGame.game_key)
                .where(
                    FactGame.game_date >= window_start,
                    FactGame.game_date <= window_end,
                )
                .where(
                    (FactGame.home_team_key == team_key)
                    | (FactGame.away_team_key == team_key)
                )
            )
            result = await self.session.execute(statement)  # type: ignore[misc]
            games = list(result.scalars().all())

            # Return game_key only if exactly one game found (unambiguous)
            if len(games) == 1:
                logger.debug(
                    "single_team_game_resolved",
                    team_id=team_id,
                    post_date=post_date.isoformat(),
                    game_key=games[0],
                    window_hours=time_window_hours,
                )
                return games[0]  # type: ignore[no-any-return]
            elif len(games) > 1:
                logger.debug(
                    "single_team_game_ambiguous",
                    team_id=team_id,
                    post_date=post_date.isoformat(),
                    reason="multiple_games_in_window",
                    games_count=len(games),
                    window_hours=time_window_hours,
                )
                return None
            else:
                logger.debug(
                    "single_team_game_not_found",
                    team_id=team_id,
                    post_date=post_date.isoformat(),
                    window_hours=time_window_hours,
                )
                return None

        except Exception as e:
            logger.error(
                "single_team_game_resolution_error",
                team_id=team_id,
                post_date=post_date.isoformat(),
                error_type=type(e).__name__,
                error=str(e),
            )
            return None
