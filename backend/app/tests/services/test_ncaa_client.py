"""
Tests for NCAA API client.

Comprehensive test suite covering:
- fetch_todays_games() with mocked httpx responses
- fetch_game_details() with mocked httpx responses
- parse_game_data() transformation logic
- Retry logic (tenacity decorator)
- HTTP error handling (4xx/5xx)
- Resource cleanup
- Module-level wrapper functions
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.ncaa_client import (
    NCAAClient,
    fetch_game_details,
    fetch_todays_games,
    parse_game_data,
)

# Sample API response data
SAMPLE_API_RESPONSE = {
    "games": [
        {
            "game_id": "401234567",
            "home": {
                "id": "150",
                "name": "Duke",
                "score": 75,
            },
            "away": {
                "id": "62",
                "name": "UNC",
                "score": 72,
            },
            "status": "Final",
            "clock": "0:00",
            "start_date": "2024-01-15T19:00:00Z",
            "venue": "Cameron Indoor Stadium",
            "game_type": "regular_season",
        },
        {
            "game_id": "401234568",
            "home": {
                "id": "26",
                "name": "Kentucky",
                "score": 68,
            },
            "away": {
                "id": "2390",
                "name": "Louisville",
                "score": 70,
            },
            "status": "Final",
            "clock": "0:00",
            "start_date": "2024-01-15T20:00:00Z",
            "venue": "Rupp Arena",
            "game_type": "regular_season",
        },
    ]
}

SAMPLE_GAME_DETAILS = {
    "game_id": "401234567",
    "home": {
        "id": "150",
        "name": "Duke",
        "score": 75,
    },
    "away": {
        "id": "62",
        "name": "UNC",
        "score": 72,
    },
    "status": "Final",
    "clock": "0:00",
    "start_date": "2024-01-15T19:00:00Z",
    "venue": "Cameron Indoor Stadium",
    "game_type": "regular_season",
}


class TestNCAAClientFetchTodaysGames:
    """Test fetch_todays_games() method."""

    @pytest.mark.asyncio
    async def test_fetch_todays_games_success(self) -> None:
        """AC1: fetch_todays_games returns list of game dictionaries."""
        client = NCAAClient()

        # Mock httpx.AsyncClient.get
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Execute
        games = await client.fetch_todays_games()

        # Assert
        assert isinstance(games, list)
        assert len(games) == 2
        assert games[0]["game_id"] == "401234567"
        assert games[1]["game_id"] == "401234568"

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_todays_games_empty_response(self) -> None:
        """Test handling of empty games list."""
        client = NCAAClient()

        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = {"games": []}
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Execute
        games = await client.fetch_todays_games()

        # Assert
        assert games == []

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_todays_games_http_error(self) -> None:
        """AC5: Verify 4xx/5xx responses raise HTTPStatusError."""
        client = NCAAClient()

        # Mock 404 response that always fails (exhausts retries)
        mock_response = MagicMock()
        mock_response.status_code = 404

        def raise_status_error() -> None:
            raise httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

        mock_response.raise_for_status = raise_status_error

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Execute & Assert - retry will exhaust after 3 attempts, then raise
        with pytest.raises(httpx.HTTPStatusError):
            await client.fetch_todays_games()

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_todays_games_generic_exception_returns_empty(self) -> None:
        """AC5: Verify graceful degradation on total failure."""
        client = NCAAClient()

        # Mock generic exception (e.g., connection error)
        client.client.get = AsyncMock(side_effect=Exception("Connection failed"))  # type: ignore[method-assign]

        # Execute
        games = await client.fetch_todays_games()

        # Assert - should return empty list, not raise
        assert games == []

        await client.close()


class TestNCAAClientFetchGameDetails:
    """Test fetch_game_details() method."""

    @pytest.mark.asyncio
    async def test_fetch_game_details_success(self) -> None:
        """AC1: fetch_game_details returns game detail dictionary."""
        client = NCAAClient()

        # Mock httpx.AsyncClient.get
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_GAME_DETAILS
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Execute
        game_details = await client.fetch_game_details("401234567")

        # Assert
        assert isinstance(game_details, dict)
        assert game_details["game_id"] == "401234567"
        assert game_details["home"]["name"] == "Duke"

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_game_details_http_error(self) -> None:
        """AC5: Verify 4xx/5xx responses raise HTTPStatusError."""
        client = NCAAClient()

        # Mock 500 response that always fails (exhausts retries)
        mock_response = MagicMock()
        mock_response.status_code = 500

        def raise_status_error() -> None:
            raise httpx.HTTPStatusError(
                "Internal Server Error",
                request=MagicMock(),
                response=mock_response,
            )

        mock_response.raise_for_status = raise_status_error

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Execute & Assert - retry will exhaust after 3 attempts, then raise
        with pytest.raises(httpx.HTTPStatusError):
            await client.fetch_game_details("401234567")

        await client.close()

    @pytest.mark.asyncio
    async def test_fetch_game_details_generic_exception_returns_empty(self) -> None:
        """AC5: Verify graceful degradation on total failure."""
        client = NCAAClient()

        # Mock generic exception
        client.client.get = AsyncMock(side_effect=Exception("Network error"))  # type: ignore[method-assign]

        # Execute
        game_details = await client.fetch_game_details("401234567")

        # Assert - should return empty dict, not raise
        assert game_details == {}

        await client.close()


class TestParseGameData:
    """Test parse_game_data() transformation function."""

    def test_parse_game_data_success(self) -> None:
        """AC1: parse_game_data correctly transforms API dict to FactGame dict with natural keys."""
        raw_data = SAMPLE_GAME_DETAILS

        # Execute
        game = parse_game_data(raw_data)

        # Assert - returns dict, not model instance (FK resolution happens in Dagster layer)
        assert isinstance(game, dict)
        assert game["game_id"] == "ncaam_401234567"
        assert game["sport"] == "ncaam"
        assert game["home_team_id"] == "ncaam_150"  # Natural key (string)
        assert game["away_team_id"] == "ncaam_62"  # Natural key (string)
        assert game["home_score"] == 75
        assert game["away_score"] == 72
        assert game["game_status"] == "Final"
        assert game["game_clock"] == "0:00"
        assert game["venue"] == "Cameron Indoor Stadium"
        assert game["game_type"] == "regular_season"
        assert isinstance(game["game_date"], datetime)

    def test_parse_game_data_missing_fields(self) -> None:
        """Test parse_game_data handles missing optional fields."""
        raw_data = {
            "game_id": "401234567",
            "home": {"id": "150", "score": 0},
            "away": {"id": "62", "score": 0},
        }

        # Execute
        game = parse_game_data(raw_data)

        # Assert
        assert game["game_id"] == "ncaam_401234567"
        assert game["game_status"] is None
        assert game["game_clock"] is None
        assert game["venue"] is None
        assert game["game_type"] == "regular_season"  # default

    def test_parse_game_data_date_parsing(self) -> None:
        """Test parse_game_data correctly parses ISO 8601 date strings."""
        raw_data = {
            **SAMPLE_GAME_DETAILS,
            "start_date": "2024-01-15T19:00:00Z",
        }

        # Execute
        game = parse_game_data(raw_data)

        # Assert
        assert isinstance(game["game_date"], datetime)
        assert game["game_date"].year == 2024
        assert game["game_date"].month == 1
        assert game["game_date"].day == 15


class TestNCAAClientRetryLogic:
    """Test tenacity retry logic."""

    @pytest.mark.asyncio
    async def test_fetch_todays_games_retries_on_failure(self) -> None:
        """AC3: Verify @retry decorator retries 3 times on failure."""
        client = NCAAClient()

        # Mock that fails twice then succeeds
        call_count = 0

        async def mock_get(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                # First 2 calls fail
                response = MagicMock()
                response.status_code = 503
                response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Service Unavailable",
                    request=MagicMock(),
                    response=response,
                )
                return response
            else:
                # 3rd call succeeds
                response = MagicMock()
                response.json.return_value = SAMPLE_API_RESPONSE
                response.raise_for_status = MagicMock()
                return response

        client.client.get = mock_get  # type: ignore[method-assign]

        # Execute
        games = await client.fetch_todays_games()

        # Assert - should succeed after retries
        assert len(games) == 2
        assert call_count == 3  # Retried twice, succeeded on 3rd

        await client.close()


class TestNCAAClientRateLimiting:
    """Test rate limiting implementation."""

    @pytest.mark.asyncio
    async def test_consecutive_requests_enforces_200ms_gap(self) -> None:
        """AC4: Verify 200ms minimum gap between consecutive requests."""
        import time

        client = NCAAClient()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Make first request (should complete immediately)
        await client.fetch_todays_games()

        # Make second request and measure gap
        start_time = time.time()
        await client.fetch_todays_games()
        elapsed_time = time.time() - start_time

        # Assert - second request should wait ~200ms before starting
        assert elapsed_time >= 0.2, f"Expected >= 0.2s gap, got {elapsed_time}s"

        await client.close()

    @pytest.mark.asyncio
    async def test_first_request_has_no_delay(self) -> None:
        """AC4: Verify first request completes immediately (no rate limit)."""
        import time

        client = NCAAClient()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Make first request and measure time
        start_time = time.time()
        await client.fetch_todays_games()
        elapsed_time = time.time() - start_time

        # Assert - should complete quickly (< 100ms, just mock overhead)
        assert elapsed_time < 0.1, f"Expected < 0.1s, got {elapsed_time}s"

        await client.close()

    @pytest.mark.asyncio
    async def test_natural_delay_skips_rate_limit_sleep(self) -> None:
        """AC4: Verify no sleep if natural delay exceeds rate limit."""
        import time

        client = NCAAClient()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_API_RESPONSE
        mock_response.raise_for_status = MagicMock()

        client.client.get = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        # Make first request
        await client.fetch_todays_games()

        # Wait longer than rate limit (300ms > 200ms)
        await asyncio.sleep(0.3)

        # Make second request and measure time
        start_time = time.time()
        await client.fetch_todays_games()
        elapsed_time = time.time() - start_time

        # Assert - should complete quickly since natural delay satisfied rate limit
        assert elapsed_time < 0.1, f"Expected < 0.1s, got {elapsed_time}s"

        await client.close()


class TestNCAAClientResourceCleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_releases_httpx_client(self) -> None:
        """Test NCAAClient.close() properly releases httpx.AsyncClient."""
        client = NCAAClient()

        # Mock aclose
        client.client.aclose = AsyncMock()  # type: ignore[method-assign]

        # Execute
        await client.close()

        # Assert
        client.client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self) -> None:
        """Test async context manager properly cleans up resources."""
        # Use context manager
        async with NCAAClient() as client:
            # Mock aclose to verify it's called
            client.client.aclose = AsyncMock()  # type: ignore[method-assign]

        # Assert - aclose should have been called on exit
        client.client.aclose.assert_called_once()


class TestModuleLevelWrapperFunctions:
    """Test module-level wrapper functions for AC1 compliance."""

    @pytest.mark.asyncio
    async def test_fetch_todays_games_wrapper(self) -> None:
        """Test module-level fetch_todays_games() wrapper function."""
        # Mock NCAAClient.fetch_todays_games
        with patch(
            "app.services.ncaa_client.NCAAClient.fetch_todays_games",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = [{"game_id": "401234567"}]

            # Mock aclose for cleanup
            with patch(
                "app.services.ncaa_client.NCAAClient.close",
                new_callable=AsyncMock,
            ):
                # Execute module-level function
                games = await fetch_todays_games()

                # Assert
                assert len(games) == 1
                assert games[0]["game_id"] == "401234567"

    @pytest.mark.asyncio
    async def test_fetch_game_details_wrapper(self) -> None:
        """Test module-level fetch_game_details() wrapper function."""
        # Mock NCAAClient.fetch_game_details
        with patch(
            "app.services.ncaa_client.NCAAClient.fetch_game_details",
            new_callable=AsyncMock,
        ) as mock_fetch:
            mock_fetch.return_value = {"game_id": "401234567", "status": "Final"}

            # Mock aclose for cleanup
            with patch(
                "app.services.ncaa_client.NCAAClient.close",
                new_callable=AsyncMock,
            ):
                # Execute module-level function
                details = await fetch_game_details("401234567")

                # Assert
                assert details["game_id"] == "401234567"
                assert details["status"] == "Final"
