"""
NCAA Men's Basketball API Client.

Async client for fetching game schedules and scores from NCAA API.
Designed to be called by Dagster assets for batch data ingestion.
"""

import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.game import Game

logger = structlog.get_logger()


class NCAAClient:
    """
    Async client for NCAA Men's Basketball API (henrygd/ncaa-api wrapper).

    Provides methods for fetching today's games and game details with built-in
    retry logic, error handling, and structured logging.

    Example:
        async with NCAAClient() as client:
            games = await client.fetch_todays_games()
    """

    BASE_URL = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"
    RATE_LIMIT_DELAY = 0.2  # 200ms = 5 req/sec

    def __init__(self) -> None:
        """Initialize client with httpx AsyncClient."""
        self.client = httpx.AsyncClient(timeout=10.0)
        self._last_request_time: float | None = None
        logger.info("ncaa_client_initialized", base_url=self.BASE_URL)

    async def __aenter__(self) -> "NCAAClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Release httpx AsyncClient resources."""
        await self.client.aclose()
        logger.info("ncaa_client_closed")

    async def _enforce_rate_limit(self) -> None:
        """
        Enforce rate limit by delaying next request if needed.

        Ensures minimum 200ms gap between consecutive requests (5 req/sec max).
        Only sleeps if insufficient time has passed since last request.
        """
        if self._last_request_time is not None:
            import time

            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                sleep_time = self.RATE_LIMIT_DELAY - elapsed
                logger.debug(
                    "rate_limit_delay",
                    elapsed_ms=elapsed * 1000,
                    sleep_ms=sleep_time * 1000,
                )
                await asyncio.sleep(sleep_time)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_todays_games(self) -> list[dict[str, Any]]:
        """
        Fetch all games for today's date from NCAA API.

        Returns:
            List of raw game dictionaries from API response.
            Returns empty list if no games scheduled or on error.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses (after retries exhausted).
        """
        # Enforce rate limit before making request
        await self._enforce_rate_limit()

        today = date.today()
        date_str = today.strftime("%Y%m%d")
        url = f"{self.BASE_URL}?date={date_str}"

        logger.info("ncaa_api_fetch_started", url=url, date=date_str)

        try:
            import time

            response = await self.client.get(url)
            response.raise_for_status()

            # Update timestamp after successful request
            self._last_request_time = time.time()

            data = response.json()
            games = cast(list[dict[str, Any]], data.get("games", []))

            logger.info(
                "ncaa_api_fetch_completed",
                games_count=len(games),
                date=date_str,
            )

            return games

        except httpx.HTTPStatusError as e:
            logger.error(
                "ncaa_api_http_error",
                status_code=e.response.status_code,
                url=url,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error("ncaa_api_fetch_failed", url=url, error=str(e))
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def fetch_game_details(self, game_id: str) -> dict[str, Any]:
        """
        Fetch detailed information for a single game by ID.

        Args:
            game_id: NCAA API game identifier.

        Returns:
            Dictionary with game details.
            Returns empty dict on error.

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses (after retries exhausted).
        """
        # Enforce rate limit before making request
        await self._enforce_rate_limit()

        url = f"{self.BASE_URL}/{game_id}"

        logger.info("ncaa_api_game_details_fetch_started", game_id=game_id, url=url)

        try:
            import time

            response = await self.client.get(url)
            response.raise_for_status()

            # Update timestamp after successful request
            self._last_request_time = time.time()

            data = cast(dict[str, Any], response.json())

            logger.info(
                "ncaa_api_game_details_fetch_completed",
                game_id=game_id,
            )

            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "ncaa_api_http_error",
                status_code=e.response.status_code,
                url=url,
                game_id=game_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "ncaa_api_game_details_fetch_failed",
                game_id=game_id,
                url=url,
                error=str(e),
            )
            return {}


def parse_game_data(raw_data: dict[str, Any]) -> Game:
    """
    Transform NCAA API response dictionary to Game SQLModel schema.

    Maps API fields (game ID, teams, scores, status, clock) to Game model fields.

    Args:
        raw_data: Raw game dictionary from NCAA API.

    Returns:
        Game model instance ready for database insertion.

    Example API structure:
        {
            "game_id": "401234567",
            "home": {"id": "150", "name": "Duke", "score": 75},
            "away": {"id": "62", "name": "UNC", "score": 72},
            "status": "Final",
            "clock": "0:00",
            "start_date": "2024-01-15T19:00:00Z",
            "venue": "Cameron Indoor Stadium"
        }
    """
    # Extract game ID (format: ncaam_{api_id})
    api_game_id = raw_data.get("game_id", "")
    game_id = f"ncaam_{api_game_id}"

    # Extract team IDs (format: ncaam_{team_slug})
    home_team_data = raw_data.get("home", {})
    away_team_data = raw_data.get("away", {})

    # NCAA API may provide team IDs or names - prioritize IDs
    home_team_id = f"ncaam_{home_team_data.get('id', '')}"
    away_team_id = f"ncaam_{away_team_data.get('id', '')}"

    # Extract scores
    home_score = home_team_data.get("score", 0)
    away_score = away_team_data.get("score", 0)

    # Extract game metadata
    game_status = raw_data.get("status", None)
    game_clock = raw_data.get("clock", None)
    venue = raw_data.get("venue", None)

    # Parse game date/time
    start_date_str = raw_data.get("start_date", "")
    game_date = (
        datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        if start_date_str
        else datetime.now(UTC)
    )
    game_start_time = game_date

    # Determine game type (regular_season vs postseason)
    game_type = raw_data.get("game_type", "regular_season")

    logger.info(
        "ncaa_game_data_parsed",
        game_id=game_id,
        home_team=home_team_id,
        away_team=away_team_id,
        status=game_status,
    )

    return Game(
        game_id=game_id,
        sport="ncaam",
        game_date=game_date,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_score=home_score,
        away_score=away_score,
        game_status=game_status,
        game_clock=game_clock,
        game_start_time=game_start_time,
        venue=venue,
        game_type=game_type,
    )


# Module-level wrapper functions for AC1 compliance


async def fetch_todays_games() -> list[dict[str, Any]]:
    """
    Fetch all games for current date from NCAA API.

    Module-level function for AC1 compliance.
    Uses NCAAClient internally with proper resource management.

    Returns:
        List of raw game dictionaries from API response.
    """
    async with NCAAClient() as client:
        return await client.fetch_todays_games()


async def fetch_game_details(game_id: str) -> dict[str, Any]:
    """
    Fetch detailed information for a single game by ID.

    Module-level function for AC1 compliance.
    Uses NCAAClient internally with proper resource management.

    Args:
        game_id: NCAA API game identifier.

    Returns:
        Dictionary with game details.
    """
    async with NCAAClient() as client:
        return await client.fetch_game_details(game_id)


# Manual test support


async def _test_client() -> None:
    """Manual test function for AC6 compliance."""
    print("NCAA Client Manual Test")
    print("=" * 50)

    async with NCAAClient() as client:
        # Fetch today's games
        print("\nFetching today's games...")
        games = await client.fetch_todays_games()

        if not games:
            print("No games scheduled for today.")
            return

        print(f"\nFound {len(games)} games:")
        for i, game in enumerate(games, 1):
            home = game.get("home", {})
            away = game.get("away", {})
            status = game.get("status", "Unknown")

            home_name = home.get("name", "Unknown")
            away_name = away.get("name", "Unknown")
            home_score = home.get("score", 0)
            away_score = away.get("score", 0)

            print(f"\n{i}. {away_name} @ {home_name}")
            print(f"   Score: {away_score} - {home_score}")
            print(f"   Status: {status}")

        # Test parse_game_data on first game
        if games:
            print("\n" + "=" * 50)
            print("Testing parse_game_data on first game...")
            first_game = games[0]
            parsed = parse_game_data(first_game)
            print("\nParsed Game Model:")
            print(f"  game_id: {parsed.game_id}")
            print(f"  sport: {parsed.sport}")
            print(f"  home_team_id: {parsed.home_team_id}")
            print(f"  away_team_id: {parsed.away_team_id}")
            print(f"  home_score: {parsed.home_score}")
            print(f"  away_score: {parsed.away_score}")
            print(f"  game_status: {parsed.game_status}")
            print(f"  game_clock: {parsed.game_clock}")
            print(f"  venue: {parsed.venue}")


if __name__ == "__main__":
    asyncio.run(_test_client())
