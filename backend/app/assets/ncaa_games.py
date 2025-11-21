"""
NCAA games asset for Dagster orchestration.

Materializes NCAA Men's Basketball game data on a 15-minute schedule with full
observability, lineage tracking, and dimensional model support.

Fetches a 15-day rolling window: 7 days historical + today + 7 days future.
This ensures users can browse recent past games and upcoming scheduled games.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from dagster import AssetExecutionContext, Backoff, RetryPolicy, asset
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.resources.database import DatabaseResource
from app.services.ncaa_client import NCAAClient
from app.services.rivalry_detector import calculate_rivalry_factor

logger = structlog.get_logger()


@asset(
    name="ncaa_games_today",
    description="NCAA Men's Basketball game data for today (live updates every 15 min)",
    group_name="sports_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def ncaa_games_today(
    context: AssetExecutionContext, database: DatabaseResource
) -> dict[str, int]:
    """
    Materialize NCAA Men's Basketball game data for TODAY ONLY.

    Fetches today's games from NCAA API with live score updates.
    Runs every 15 minutes to capture live game progress and final scores.

    For historical/future games, see ncaa_games_window asset (runs daily).

    Schedule: Every 15 minutes (cron: */15 * * * *)

    Returns:
        Metadata: {"games_processed": 8, "games_inserted": 3, "games_updated": 5}
    """
    context.log.info("ncaa_games_today_asset_started")

    async with NCAAClient() as client:
        # Fetch only today's games (fast, frequent updates)
        raw_games = await client.fetch_todays_games()

        if not raw_games:
            context.log.info("ncaa_games_today_completed: games_processed=0")
            return {"games_processed": 0, "games_inserted": 0, "games_updated": 0}

        context.log.info(f"ncaa_api_todays_games_fetched: games_count={len(raw_games)}")

        # Step 2: Sync teams from games (Story 2-3b integration)
        # Ensures all teams exist in dim_team before FK insertions
        async with database.get_session() as session:
            team_sync_metadata = await sync_teams_from_api(raw_games, session)
            context.log.info(f"teams_synced: {team_sync_metadata}")

        # Step 3: Transform and upsert games with dimensional model fixes
        games_inserted = 0
        games_updated = 0

        async with database.get_session() as session:
            for game_data in raw_games:
                try:
                    # Transform to FactGame with FK lookups
                    fact_game = await transform_to_fact_game(
                        game_data, session, context
                    )

                    # Check if game exists (for insert/update tracking)
                    existing_game = await session.execute(
                        select(FactGame).where(FactGame.game_id == fact_game["game_id"])
                    )
                    is_update = existing_game.scalar_one_or_none() is not None

                    # Upsert using PostgreSQL INSERT ... ON CONFLICT
                    stmt = insert(FactGame).values(fact_game)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["game_id"],  # Natural key
                        set_={
                            "home_score": stmt.excluded.home_score,
                            "away_score": stmt.excluded.away_score,
                            "game_status": stmt.excluded.game_status,
                            "game_clock": stmt.excluded.game_clock,
                            "game_period": stmt.excluded.game_period,
                            "rivalry_factor": stmt.excluded.rivalry_factor,
                            "updated_at": stmt.excluded.updated_at,
                            # Preserve: game_key (surrogate PK), game_date, team FKs
                        },
                    )
                    await session.execute(stmt)

                    if is_update:
                        games_updated += 1
                    else:
                        games_inserted += 1

                except ValueError as e:
                    context.log.error(
                        f"game_transform_failed: game_id={game_data.get('id')}, error={str(e)}",
                        exc_info=True,
                    )
                    continue
                except Exception as e:
                    context.log.error(
                        f"game_upsert_failed: game_id={game_data.get('id')}, error={str(e)}",
                        exc_info=True,
                    )
                    continue

            # Commit all upserts in single transaction
            await session.commit()

        games_processed = len(raw_games)
        context.log.info(
            f"ncaa_games_today_completed: games_processed={games_processed}, "
            f"games_inserted={games_inserted}, games_updated={games_updated}"
        )

        return {
            "games_processed": games_processed,
            "games_inserted": games_inserted,
            "games_updated": games_updated,
        }


async def sync_teams_from_api(
    games_data: list[dict[str, Any]], session: AsyncSession
) -> dict[str, int]:
    """
    Async wrapper for team sync - extracts teams from games and upserts to dim_team.

    Args:
        games_data: Raw game dictionaries from NCAA API
        session: Async database session

    Returns:
        Metadata: {"teams_discovered": 2, "teams_updated": 0, "teams_unchanged": 8}
    """
    if not games_data:
        return {"teams_discovered": 0, "teams_updated": 0, "teams_unchanged": 0}

    # Extract unique teams from games (unwrap nested game object)
    now = datetime.now(timezone.utc).replace(
        tzinfo=None
    )  # Naive datetime for TIMESTAMP WITHOUT TIME ZONE
    teams_from_api: dict[str, dict[str, Any]] = {}
    for game_data in games_data:
        # Unwrap nested game object from NCAA API response
        game = game_data.get("game", {})
        if not game:
            continue

        # Home team (use SEO slug as identifier)
        home_team = game.get("home", {})
        home_seo = home_team.get("names", {}).get("seo")
        if home_seo:
            team_id = f"ncaam_{home_seo}"
            if team_id not in teams_from_api:
                teams_from_api[team_id] = {
                    "team_id": team_id,
                    "espn_team_id": home_seo,
                    "team_name": home_team.get("names", {}).get("short", "Unknown"),
                    "sport": "ncaam",
                    "is_current": True,
                    "valid_from": now,
                    "created_at": now,
                    "updated_at": now,
                }

        # Away team (use SEO slug as identifier)
        away_team = game.get("away", {})
        away_seo = away_team.get("names", {}).get("seo")
        if away_seo:
            team_id = f"ncaam_{away_seo}"
            if team_id not in teams_from_api:
                teams_from_api[team_id] = {
                    "team_id": team_id,
                    "espn_team_id": away_seo,
                    "team_name": away_team.get("names", {}).get("short", "Unknown"),
                    "sport": "ncaam",
                    "is_current": True,
                    "valid_from": now,
                    "created_at": now,
                    "updated_at": now,
                }

    if not teams_from_api:
        return {"teams_discovered": 0, "teams_updated": 0, "teams_unchanged": 0}

    # Query existing teams
    existing_teams_result = await session.execute(
        select(DimTeam.team_id, DimTeam.team_name).where(
            DimTeam.team_id.in_(teams_from_api.keys())  # type: ignore[attr-defined]
        )
    )
    existing_teams: dict[str, str] = dict(existing_teams_result.all())  # type: ignore[arg-type]

    # Categorize teams
    teams_to_insert = []
    teams_to_update = []
    for team_id, team_data in teams_from_api.items():
        if team_id not in existing_teams:
            teams_to_insert.append(team_data)
        elif existing_teams[team_id] != team_data["team_name"]:
            teams_to_update.append(team_data)

    teams_unchanged = len(teams_from_api) - len(teams_to_insert) - len(teams_to_update)

    # Batch upsert
    if teams_from_api:
        stmt = insert(DimTeam).values(list(teams_from_api.values()))
        stmt = stmt.on_conflict_do_update(
            index_elements=["team_id"],
            set_={
                "team_name": stmt.excluded.team_name,
                "espn_team_id": stmt.excluded.espn_team_id,
                "updated_at": now,
            },
        )
        await session.execute(stmt)
        await session.commit()

    return {
        "teams_discovered": len(teams_to_insert),
        "teams_updated": len(teams_to_update),
        "teams_unchanged": teams_unchanged,
    }


async def transform_to_fact_game(
    game_data: dict[str, Any],
    session: AsyncSession,
    context: AssetExecutionContext,
) -> dict[str, Any]:
    """
    Transform raw NCAA API game data to FactGame dimensional model.

    Dimensional Model Transformations:
    1. Lookup home_team_key and away_team_key via dim_team natural keys
    2. Derive game_date_key from game_date timestamp (YYYYMMDD integer)
    3. Calculate rivalry_factor based on conference matching
    4. Build game_id natural key: "sport_apiid"
    5. game_key (surrogate PK) auto-generated by database

    Args:
        game_data: Raw game dictionary from NCAA API (with nested "game" object)
        session: Async database session for FK lookups
        context: Dagster execution context for logging

    Returns:
        Dictionary ready for FactGame upsert

    Raises:
        ValueError: If team not found in dim_team (FK constraint would fail)
    """
    # Unwrap nested game object from NCAA API response
    game = game_data.get("game", {})
    if not game:
        raise ValueError("Missing 'game' object in NCAA API response")

    # Extract home and away team ESPN IDs (from nested structure)
    home_espn_id = game.get("home", {}).get("names", {}).get("seo")  # Team SEO slug
    away_espn_id = game.get("away", {}).get("names", {}).get("seo")

    if not home_espn_id or not away_espn_id:
        raise ValueError(f"Missing team IDs in game data: {game.get('gameID')}")

    # Build team_id natural keys (sport prefix + seo slug)
    home_team_id = f"ncaam_{home_espn_id}"
    away_team_id = f"ncaam_{away_espn_id}"

    # FIX 1: Lookup surrogate keys (team_key) via dim_team natural keys
    home_team_result = await session.execute(
        select(DimTeam).where(
            DimTeam.team_id == home_team_id,
            DimTeam.is_current == True,  # noqa: E712 - SCD Type 2 filter
        )
    )
    home_team = home_team_result.scalar_one_or_none()
    if not home_team:
        raise ValueError(f"Home team not found in dim_team: {home_team_id}")

    away_team_result = await session.execute(
        select(DimTeam).where(
            DimTeam.team_id == away_team_id,
            DimTeam.is_current == True,  # noqa: E712
        )
    )
    away_team = away_team_result.scalar_one_or_none()
    if not away_team:
        raise ValueError(f"Away team not found in dim_team: {away_team_id}")

    # FIX 2: Derive game_date_key from game_date timestamp (YYYYMMDD integer)
    # Parse game date from API (format: "11/12/2025")
    game_date_str = game.get("startDate", "")
    if game_date_str:
        # Parse MM/DD/YYYY format - use naive datetime for TIMESTAMP WITHOUT TIME ZONE
        from datetime import datetime as dt

        game_date = dt.strptime(game_date_str, "%m/%d/%Y")
    else:
        game_date = datetime.now(timezone.utc).replace(tzinfo=None)

    game_date_key = int(
        game_date.strftime("%Y%m%d")
    )  # YYYYMMDD integer for dim_date FK

    # FIX 3: Calculate rivalry_factor based on conference matching
    rivalry_factor = await calculate_rivalry_factor(home_team_id, away_team_id, session)

    # Build FactGame dictionary with dimensional model compliance
    game_id = f"ncaam_{game.get('gameID')}"
    home_score = int(game.get("home", {}).get("score", 0) or 0)
    away_score = int(game.get("away", {}).get("score", 0) or 0)
    game_status = game.get("gameState", "scheduled")  # "live", "pre", "final"
    game_clock = game.get("contestClock", None)
    game_period = game.get(
        "currentPeriod", None
    )  # "1st Half", "2nd Half", "OT", "FINAL"
    venue = game.get("title", None)  # Game title often includes venue

    context.log.debug(
        f"game_transformed: game_id={game_id}, home_team_key={home_team.team_key}, "
        f"away_team_key={away_team.team_key}, game_date_key={game_date_key}, "
        f"rivalry_factor={rivalry_factor}"
    )

    return {
        "game_id": game_id,  # Natural key for upserts
        "sport": "ncaam",
        "game_date": game_date,
        "game_date_key": game_date_key,  # FIX 2: FK to dim_date
        "home_team_key": home_team.team_key,  # FIX 1: Surrogate key FK
        "away_team_key": away_team.team_key,  # FIX 1: Surrogate key FK
        "home_score": home_score,
        "away_score": away_score,
        "game_status": game_status,
        "game_clock": game_clock,
        "game_period": game_period,
        "venue": venue,
        "rivalry_factor": rivalry_factor,  # FIX 3: Conference matching
        "created_at": datetime.now(timezone.utc).replace(
            tzinfo=None
        ),  # Naive for TIMESTAMP WITHOUT TIME ZONE
        "updated_at": datetime.now(timezone.utc).replace(
            tzinfo=None
        ),  # Naive for TIMESTAMP WITHOUT TIME ZONE
        # game_key NOT set - auto-generated by BIGSERIAL
    }


@asset(
    name="ncaa_games_window",
    description="NCAA Men's Basketball historical/future games (7 days each direction, runs daily)",
    group_name="sports_data",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def ncaa_games_window(
    context: AssetExecutionContext, database: DatabaseResource
) -> dict[str, Any]:
    """
    Materialize NCAA Men's Basketball games for a 14-day window (excluding today).

    Fetches games from NCAA API for:
    - 7 days historical (yesterday and before)
    - 7 days future (tomorrow and beyond)

    These games don't change frequently, so they're fetched once per day
    instead of every 15 minutes like today's games.

    Schedule: Once daily at 6:00 AM (cron: 0 6 * * *)

    Returns:
        Metadata: {
            "games_processed": 120,
            "games_inserted": 45,
            "games_updated": 75,
            "dates_fetched": 14,
            "date_range": "2025-11-13 to 2025-11-27"
        }
    """
    context.log.info("ncaa_games_window_asset_started")

    async with NCAAClient() as client:
        # Calculate date range (exclude today - handled by ncaa_games_today)
        today = date.today()
        start_date = today - timedelta(days=7)  # 7 days ago
        end_date = today + timedelta(days=7)  # 7 days from now

        context.log.info(
            f"ncaa_api_window_date_range: "
            f"start={start_date.isoformat()}, "
            f"end={end_date.isoformat()}"
        )

        # Fetch games for each date (excluding today)
        all_games = []
        dates_with_games = 0

        current_date = start_date
        while current_date <= end_date:
            # Skip today (handled by ncaa_games_today asset)
            if current_date == today:
                current_date += timedelta(days=1)
                continue

            try:
                date_games = await client.fetch_games_for_date(current_date)
                if date_games:
                    all_games.extend(date_games)
                    dates_with_games += 1
                    context.log.info(
                        f"ncaa_api_games_fetched_for_date: "
                        f"date={current_date.isoformat()}, "
                        f"games_count={len(date_games)}"
                    )
            except Exception as e:
                context.log.error(
                    f"ncaa_api_fetch_failed_for_date: "
                    f"date={current_date.isoformat()}, "
                    f"error={str(e)}"
                )

            current_date += timedelta(days=1)

        if not all_games:
            context.log.info("ncaa_games_window_completed: games_processed=0")
            return {
                "games_processed": 0,
                "games_inserted": 0,
                "games_updated": 0,
                "dates_fetched": 0,
                "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
            }

        context.log.info(
            f"ncaa_api_window_total: "
            f"games_count={len(all_games)}, "
            f"dates_with_games={dates_with_games}"
        )

        raw_games = all_games

        # Sync teams and process games (same logic as ncaa_games_today)
        async with database.get_session() as session:
            team_sync_metadata = await sync_teams_from_api(raw_games, session)
            context.log.info(f"teams_synced: {team_sync_metadata}")

        games_inserted = 0
        games_updated = 0

        async with database.get_session() as session:
            for game_data in raw_games:
                try:
                    fact_game = await transform_to_fact_game(
                        game_data, session, context
                    )

                    existing_game = await session.execute(
                        select(FactGame).where(FactGame.game_id == fact_game["game_id"])
                    )
                    is_update = existing_game.scalar_one_or_none() is not None

                    stmt = insert(FactGame).values(fact_game)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["game_id"],
                        set_={
                            "home_score": stmt.excluded.home_score,
                            "away_score": stmt.excluded.away_score,
                            "game_status": stmt.excluded.game_status,
                            "game_clock": stmt.excluded.game_clock,
                            "game_period": stmt.excluded.game_period,
                            "rivalry_factor": stmt.excluded.rivalry_factor,
                            "updated_at": stmt.excluded.updated_at,
                        },
                    )
                    await session.execute(stmt)

                    if is_update:
                        games_updated += 1
                    else:
                        games_inserted += 1

                except ValueError as e:
                    context.log.error(
                        f"game_transform_failed: game_id={game_data.get('id')}, error={str(e)}",
                        exc_info=True,
                    )
                    continue
                except Exception as e:
                    context.log.error(
                        f"game_upsert_failed: game_id={game_data.get('id')}, error={str(e)}",
                        exc_info=True,
                    )
                    continue

            await session.commit()

        games_processed = len(raw_games)
        context.log.info(
            f"ncaa_games_window_completed: games_processed={games_processed}, "
            f"games_inserted={games_inserted}, games_updated={games_updated}, "
            f"dates_fetched={dates_with_games}"
        )

        return {
            "games_processed": games_processed,
            "games_inserted": games_inserted,
            "games_updated": games_updated,
            "dates_fetched": dates_with_games,
            "date_range": f"{start_date.isoformat()} to {end_date.isoformat()}",
        }
