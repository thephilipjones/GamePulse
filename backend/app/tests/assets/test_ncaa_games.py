"""
Tests for NCAA games Dagster asset.

Comprehensive test suite covering:
- Asset materialization with mocked NCAA API
- Game upsert logic (insert vs update tracking)
- Team sync integration
- FK resolution and rivalry factor calculation
- Error handling and retry policy
- Metadata reporting
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dagster import build_asset_context
from sqlmodel import select

from app.assets.ncaa_games import (
    ncaa_games,
    sync_teams_from_api,
    transform_to_fact_game,
)
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.resources.database import DatabaseResource


class TestNCAAGamesAssetMaterialization:
    """Test ncaa_games asset end-to-end materialization."""

    @pytest.mark.asyncio
    async def test_materialize_success_inserts_new_games(self, db):
        """
        AC1: Asset materializes games from NCAA API and returns correct metadata.

        Verifies:
        - NCAA API is called via fetch_todays_games()
        - Games are inserted into fact_game table
        - Metadata returned with correct counts
        """
        # Arrange: Mock NCAA API response with 2 games
        mock_api_games = [
            {
                "game": {
                    "gameID": "401234567",
                    "startDate": "11/13/2025",
                    "home": {
                        "names": {"seo": "duke", "short": "Duke"},
                        "score": 78,
                    },
                    "away": {
                        "names": {"seo": "unc", "short": "UNC"},
                        "score": 81,
                    },
                    "gameState": "final",
                    "contestClock": "0:00",
                    "title": "Cameron Indoor Stadium",
                }
            },
            {
                "game": {
                    "gameID": "401234568",
                    "startDate": "11/13/2025",
                    "home": {
                        "names": {"seo": "kansas", "short": "Kansas"},
                        "score": 0,
                    },
                    "away": {
                        "names": {"seo": "kentucky", "short": "Kentucky"},
                        "score": 0,
                    },
                    "gameState": "pre",
                    "contestClock": None,
                    "title": "Allen Fieldhouse",
                }
            },
        ]

        # Create teams in dim_team (required for FK resolution)
        teams = [
            DimTeam(
                team_id="ncaam_duke",
                team_name="Duke",
                sport="ncaam",
                team_group_id="ncaam_acc",
                team_group_name="ACC",
            ),
            DimTeam(
                team_id="ncaam_unc",
                team_name="UNC",
                sport="ncaam",
                team_group_id="ncaam_acc",
                team_group_name="ACC",
            ),
            DimTeam(
                team_id="ncaam_kansas",
                team_name="Kansas",
                sport="ncaam",
                team_group_id="ncaam_big12",
                team_group_name="Big 12",
            ),
            DimTeam(
                team_id="ncaam_kentucky",
                team_name="Kentucky",
                sport="ncaam",
                team_group_id="ncaam_sec",
                team_group_name="SEC",
            ),
        ]
        for team in teams:
            db.add(team)
        await db.commit()

        # Mock NCAA client
        with patch("app.assets.ncaa_games.NCAAClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.fetch_todays_games.return_value = mock_api_games
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Create mock database resource
            mock_db_resource = MagicMock(spec=DatabaseResource)
            mock_db_resource.get_session = MagicMock()
            mock_db_resource.get_session.return_value.__aenter__ = AsyncMock(
                return_value=db
            )
            mock_db_resource.get_session.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            # Build Dagster context with database resource
            context = build_asset_context(resources={"database": mock_db_resource})

            # Act: Materialize asset (resource passed via context, not kwargs)
            result = await ncaa_games(context)

            # Assert: Verify metadata
            assert result["games_processed"] == 2
            assert result["games_inserted"] == 2
            assert result["games_updated"] == 0

            # Assert: Verify games in database
            games = await db.execute(select(FactGame))
            games_list = games.scalars().all()
            assert len(games_list) == 2

            # Assert: Verify game details
            duke_unc_game = next(
                g for g in games_list if g.game_id == "ncaam_401234567"
            )
            assert duke_unc_game.home_score == 78
            assert duke_unc_game.away_score == 81
            assert duke_unc_game.game_status == "final"
            assert duke_unc_game.rivalry_factor == Decimal("1.2")  # Same conference

            kansas_kentucky_game = next(
                g for g in games_list if g.game_id == "ncaam_401234568"
            )
            assert kansas_kentucky_game.home_score == 0
            assert kansas_kentucky_game.game_status == "pre"
            assert kansas_kentucky_game.rivalry_factor == Decimal(
                "1.0"
            )  # Different conferences

    @pytest.mark.asyncio
    async def test_materialize_updates_existing_games(self, db):
        """
        AC1: Existing games are updated with new scores on subsequent materializations.

        Verifies:
        - Upsert logic correctly identifies existing games
        - Score updates are applied
        - games_updated count is correct
        """
        # Arrange: Create teams
        teams = [
            DimTeam(
                team_id="ncaam_duke",
                team_name="Duke",
                sport="ncaam",
                team_group_id="ncaam_acc",
            ),
            DimTeam(
                team_id="ncaam_unc",
                team_name="UNC",
                sport="ncaam",
                team_group_id="ncaam_acc",
            ),
        ]
        for team in teams:
            db.add(team)
        await db.commit()

        # Fetch team keys
        duke = await db.execute(select(DimTeam).where(DimTeam.team_id == "ncaam_duke"))
        unc = await db.execute(select(DimTeam).where(DimTeam.team_id == "ncaam_unc"))
        duke_team = duke.scalar_one()
        unc_team = unc.scalar_one()

        # Arrange: Insert existing game (in-progress)
        existing_game = FactGame(
            game_id="ncaam_401234567",
            sport="ncaam",
            game_date=datetime(2025, 11, 13),
            game_date_key=20251113,
            home_team_key=duke_team.team_key,
            away_team_key=unc_team.team_key,
            home_score=40,  # Halftime score
            away_score=38,
            game_status="in_progress",
            rivalry_factor=Decimal("1.2"),
        )
        db.add(existing_game)
        await db.commit()

        # Arrange: Mock NCAA API with updated scores (final)
        mock_api_games = [
            {
                "game": {
                    "gameID": "401234567",
                    "startDate": "11/13/2025",
                    "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 78},
                    "away": {"names": {"seo": "unc", "short": "UNC"}, "score": 81},
                    "gameState": "final",
                    "contestClock": "0:00",
                    "title": "Cameron Indoor Stadium",
                }
            }
        ]

        # Mock NCAA client
        with patch("app.assets.ncaa_games.NCAAClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.fetch_todays_games.return_value = mock_api_games
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Create mock database resource
            mock_db_resource = MagicMock(spec=DatabaseResource)
            mock_db_resource.get_session = MagicMock()
            mock_db_resource.get_session.return_value.__aenter__ = AsyncMock(
                return_value=db
            )
            mock_db_resource.get_session.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            # Build Dagster context
            context = build_asset_context(resources={"database": mock_db_resource})

            # Act: Materialize asset (should update existing game)
            result = await ncaa_games(context, mock_db_resource)

            # Assert: Verify metadata
            assert result["games_processed"] == 1
            assert result["games_inserted"] == 0
            assert result["games_updated"] == 1

            # Assert: Verify game was updated
            games = await db.execute(
                select(FactGame).where(FactGame.game_id == "ncaam_401234567")
            )
            updated_game = games.scalar_one()
            assert updated_game.home_score == 78  # Updated from 40
            assert updated_game.away_score == 81  # Updated from 38
            assert updated_game.game_status == "final"  # Updated from in_progress

    @pytest.mark.asyncio
    async def test_materialize_empty_games_returns_zero_counts(self, db):
        """
        AC1: Asset handles empty games gracefully (off-season scenario).

        Verifies:
        - No errors when API returns empty list
        - Metadata shows zero counts
        """
        # Arrange: Mock NCAA API with no games
        mock_api_games = []

        # Mock NCAA client
        with patch("app.assets.ncaa_games.NCAAClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.fetch_todays_games.return_value = mock_api_games
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Create mock database resource
            mock_db_resource = MagicMock(spec=DatabaseResource)

            # Build Dagster context with database resource
            context = build_asset_context(resources={"database": mock_db_resource})

            # Act: Materialize asset (resource passed via context, not kwargs)
            result = await ncaa_games(context)

            # Assert: Verify metadata
            assert result["games_processed"] == 0
            assert result["games_inserted"] == 0
            assert result["games_updated"] == 0


class TestSyncTeamsFromAPI:
    """Test team sync helper function (Story 2-3b integration)."""

    @pytest.mark.asyncio
    async def test_sync_discovers_new_teams(self, db):
        """
        AC1: New teams from API are auto-discovered and inserted into dim_team.

        Verifies Story 2-3b integration.
        """
        # Arrange: Mock games with new teams
        games_data = [
            {
                "game": {
                    "home": {"names": {"seo": "duke", "short": "Duke"}},
                    "away": {"names": {"seo": "unc", "short": "UNC"}},
                }
            }
        ]

        # Act: Sync teams
        metadata = await sync_teams_from_api(games_data, db)

        # Assert: Verify metadata
        assert metadata["teams_discovered"] == 2
        assert metadata["teams_updated"] == 0
        assert metadata["teams_unchanged"] == 0

        # Assert: Verify teams in database
        teams = await db.execute(select(DimTeam))
        teams_list = teams.scalars().all()
        assert len(teams_list) == 2
        assert any(t.team_id == "ncaam_duke" for t in teams_list)
        assert any(t.team_id == "ncaam_unc" for t in teams_list)

    @pytest.mark.asyncio
    async def test_sync_updates_existing_teams_with_name_changes(self, db):
        """
        AC1: Existing teams with name changes are updated.
        """
        # Arrange: Create existing team with old name
        existing_team = DimTeam(
            team_id="ncaam_duke",
            team_name="Duke Blue Devils (Old)",
            sport="ncaam",
        )
        db.add(existing_team)
        await db.commit()

        # Arrange: Mock games with updated team name
        games_data = [
            {
                "game": {
                    "home": {"names": {"seo": "duke", "short": "Duke"}},
                    "away": {"names": {"seo": "unc", "short": "UNC"}},
                }
            }
        ]

        # Act: Sync teams
        metadata = await sync_teams_from_api(games_data, db)

        # Assert: Verify metadata
        assert metadata["teams_discovered"] == 1  # UNC is new
        assert metadata["teams_updated"] == 1  # Duke name updated
        assert metadata["teams_unchanged"] == 0

        # Assert: Verify Duke was updated
        duke = await db.execute(select(DimTeam).where(DimTeam.team_id == "ncaam_duke"))
        duke_team = duke.scalar_one()
        assert duke_team.team_name == "Duke"  # Updated from old name

    @pytest.mark.asyncio
    async def test_sync_handles_empty_games(self, db):
        """
        AC1: Empty games list returns zero counts.
        """
        # Act: Sync with empty games
        metadata = await sync_teams_from_api([], db)

        # Assert: Verify metadata
        assert metadata["teams_discovered"] == 0
        assert metadata["teams_updated"] == 0
        assert metadata["teams_unchanged"] == 0


class TestTransformToFactGame:
    """Test game transformation with FK lookups."""

    @pytest.mark.asyncio
    async def test_transform_resolves_foreign_keys(self, db):
        """
        AC1: Transform correctly resolves surrogate keys for home/away teams.

        Verifies dimensional model FK resolution.
        """
        # Arrange: Create teams in dim_team
        duke = DimTeam(
            team_id="ncaam_duke",
            team_name="Duke",
            sport="ncaam",
            team_group_id="ncaam_acc",
        )
        unc = DimTeam(
            team_id="ncaam_unc",
            team_name="UNC",
            sport="ncaam",
            team_group_id="ncaam_acc",
        )
        db.add(duke)
        db.add(unc)
        await db.commit()

        # Arrange: Mock game data
        game_data = {
            "game": {
                "gameID": "401234567",
                "startDate": "11/13/2025",
                "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 78},
                "away": {"names": {"seo": "unc", "short": "UNC"}, "score": 81},
                "gameState": "final",
                "contestClock": "0:00",
                "title": "Cameron Indoor Stadium",
            }
        }

        # Build Dagster context
        context = build_asset_context()

        # Act: Transform game
        fact_game = await transform_to_fact_game(game_data, db, context)

        # Assert: Verify FK resolution
        assert fact_game["home_team_key"] == duke.team_key
        assert fact_game["away_team_key"] == unc.team_key

        # Assert: Verify other fields
        assert fact_game["game_id"] == "ncaam_401234567"
        assert fact_game["game_date_key"] == 20251113
        assert fact_game["home_score"] == 78
        assert fact_game["away_score"] == 81
        assert fact_game["game_status"] == "final"
        assert fact_game["rivalry_factor"] == Decimal("1.2")  # Same conference

    @pytest.mark.asyncio
    async def test_transform_raises_error_on_missing_team(self, db):
        """
        AC1: Transform raises ValueError if team not found in dim_team.

        This prevents FK constraint violations.
        """
        # Arrange: Create only one team (Duke missing)
        unc = DimTeam(
            team_id="ncaam_unc",
            team_name="UNC",
            sport="ncaam",
        )
        db.add(unc)
        await db.commit()

        # Arrange: Mock game data with missing Duke team
        game_data = {
            "game": {
                "gameID": "401234567",
                "startDate": "11/13/2025",
                "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 78},
                "away": {"names": {"seo": "unc", "short": "UNC"}, "score": 81},
                "gameState": "final",
            }
        }

        # Build Dagster context
        context = build_asset_context()

        # Act & Assert: Verify ValueError raised
        with pytest.raises(ValueError, match="Home team not found in dim_team"):
            await transform_to_fact_game(game_data, db, context)

    @pytest.mark.asyncio
    async def test_transform_calculates_rivalry_factor_correctly(self, db):
        """
        AC1: Transform correctly calculates rivalry factor based on conference matching.
        """
        # Arrange: Create teams - Duke and UNC in same conference (ACC)
        duke = DimTeam(
            team_id="ncaam_duke",
            team_name="Duke",
            sport="ncaam",
            team_group_id="ncaam_acc",
            team_group_name="ACC",
        )
        unc = DimTeam(
            team_id="ncaam_unc",
            team_name="UNC",
            sport="ncaam",
            team_group_id="ncaam_acc",
            team_group_name="ACC",
        )
        db.add(duke)
        db.add(unc)
        await db.commit()

        # Arrange: Mock game data
        game_data = {
            "game": {
                "gameID": "401234567",
                "startDate": "11/13/2025",
                "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 78},
                "away": {"names": {"seo": "unc", "short": "UNC"}, "score": 81},
                "gameState": "final",
            }
        }

        # Build Dagster context
        context = build_asset_context()

        # Act: Transform game
        fact_game = await transform_to_fact_game(game_data, db, context)

        # Assert: Verify rivalry factor for conference matchup
        assert fact_game["rivalry_factor"] == Decimal("1.2")

        # Test non-conference game
        kentucky = DimTeam(
            team_id="ncaam_kentucky",
            team_name="Kentucky",
            sport="ncaam",
            team_group_id="ncaam_sec",  # Different conference
            team_group_name="SEC",
        )
        db.add(kentucky)
        await db.commit()

        game_data_non_conf = {
            "game": {
                "gameID": "401234568",
                "startDate": "11/13/2025",
                "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 70},
                "away": {
                    "names": {"seo": "kentucky", "short": "Kentucky"},
                    "score": 68,
                },
                "gameState": "final",
            }
        }

        # Act: Transform non-conference game
        fact_game_non_conf = await transform_to_fact_game(
            game_data_non_conf, db, context
        )

        # Assert: Verify rivalry factor for non-conference game
        assert fact_game_non_conf["rivalry_factor"] == Decimal("1.0")


class TestErrorHandling:
    """Test error handling and retry policy."""

    @pytest.mark.asyncio
    async def test_asset_handles_missing_team_gracefully(self, db):
        """
        AC1: Asset continues processing other games if one game has missing team.

        Partial failure scenario.
        """
        # Arrange: Create only 2 teams (missing kansas and kentucky)
        duke = DimTeam(
            team_id="ncaam_duke",
            team_name="Duke",
            sport="ncaam",
            team_group_id="ncaam_acc",
        )
        unc = DimTeam(
            team_id="ncaam_unc",
            team_name="UNC",
            sport="ncaam",
            team_group_id="ncaam_acc",
        )
        db.add(duke)
        db.add(unc)
        await db.commit()

        # Arrange: Mock 2 games - one valid, one with missing teams
        mock_api_games = [
            {
                "game": {
                    "gameID": "401234567",
                    "startDate": "11/13/2025",
                    "home": {"names": {"seo": "duke", "short": "Duke"}, "score": 78},
                    "away": {"names": {"seo": "unc", "short": "UNC"}, "score": 81},
                    "gameState": "final",
                }
            },
            {
                "game": {
                    "gameID": "401234568",
                    "startDate": "11/13/2025",
                    "home": {
                        "names": {"seo": "kansas", "short": "Kansas"},
                        "score": 70,
                    },
                    "away": {
                        "names": {"seo": "kentucky", "short": "Kentucky"},
                        "score": 68,
                    },
                    "gameState": "final",
                }
            },
        ]

        # Mock NCAA client
        with patch("app.assets.ncaa_games.NCAAClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.fetch_todays_games.return_value = mock_api_games
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Create mock database resource
            mock_db_resource = MagicMock(spec=DatabaseResource)
            mock_db_resource.get_session = MagicMock()
            mock_db_resource.get_session.return_value.__aenter__ = AsyncMock(
                return_value=db
            )
            mock_db_resource.get_session.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            # Build Dagster context
            context = build_asset_context(resources={"database": mock_db_resource})

            # Act: Materialize asset (should process valid game, skip invalid)
            result = await ncaa_games(context, mock_db_resource)

            # Assert: Verify only valid game was processed
            assert result["games_processed"] == 2
            assert result["games_inserted"] == 1  # Only Duke-UNC game
            assert result["games_updated"] == 0

            # Assert: Verify only Duke-UNC game in database
            games = await db.execute(select(FactGame))
            games_list = games.scalars().all()
            assert len(games_list) == 1
            assert games_list[0].game_id == "ncaam_401234567"
