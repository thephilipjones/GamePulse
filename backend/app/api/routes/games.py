"""API routes for game data."""

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import DatabaseError, OperationalError
from sqlalchemy.orm import aliased
from sqlmodel import and_, select

from app.api.deps import SessionDep
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.schemas.game import GameListResponse, GamePublic, TeamInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=GameListResponse)
async def get_games(
    session: SessionDep,
    date_param: str | None = Query(
        None,
        alias="date",
        description="Date in YYYY-MM-DD format (defaults to today in UTC)",
    ),
    request_id: str | None = Query(None, alias="X-Request-ID", include_in_schema=False),
) -> GameListResponse:
    """
    Get NCAA Men's Basketball games for a specific date.

    Note: When date parameter is omitted, uses current date in UTC timezone.
    Frontend should handle timezone conversion for user display.

    Args:
        session: Database session (injected)
        date_param: Optional date in YYYY-MM-DD format (defaults to today in UTC)

    Returns:
        GameListResponse with list of games and metadata

    Raises:
        HTTPException 400: Invalid date format
        HTTPException 500: Database error
    """
    # Parse and validate date parameter
    try:
        if date_param is None:
            target_date = date.today()
        else:
            # Manual validation for consistent HTTP 400 responses
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )

    # Convert to date_key format (YYYYMMDD integer)
    date_key = int(target_date.strftime("%Y%m%d"))

    # Log the request
    logger.info(
        "Games endpoint called",
        extra={
            "requested_date": target_date.isoformat(),
            "date_key": date_key,
        },
    )

    try:
        # Alias dim_team twice for home and away teams
        home_team = aliased(DimTeam)
        away_team = aliased(DimTeam)

        # Build query with dimensional model JOINs
        statement = (
            select(FactGame, home_team, away_team)
            .join(
                home_team,
                and_(
                    FactGame.home_team_key == home_team.team_key,
                    home_team.is_current == True,  # noqa: E712
                ),
            )
            .join(
                away_team,
                and_(
                    FactGame.away_team_key == away_team.team_key,
                    away_team.is_current == True,  # noqa: E712
                ),
            )
            .where(FactGame.game_date_key == date_key)
            .where(FactGame.sport == "ncaam")  # NCAA Men's Basketball only
            .order_by(FactGame.game_start_time)  # type: ignore[arg-type]  # ASC is default
        )

        # Execute query
        results = session.exec(statement).all()

        # Transform results to Pydantic models
        games = []
        for game, home, away in results:
            # Create TeamInfo objects
            home_team_info = TeamInfo(
                team_key=home.team_key,
                team_id=home.team_id,
                team_name=home.team_name,
                team_group_name=home.team_group_name,
                primary_color=home.primary_color,
                secondary_color=home.secondary_color,
            )
            away_team_info = TeamInfo(
                team_key=away.team_key,
                team_id=away.team_id,
                team_name=away.team_name,
                team_group_name=away.team_group_name,
                primary_color=away.primary_color,
                secondary_color=away.secondary_color,
            )

            # Create GamePublic object
            game_public = GamePublic(
                game_key=game.game_key,
                game_id=game.game_id,
                game_date=game.game_date,
                game_start_time=game.game_start_time,
                game_status=game.game_status,
                game_clock=game.game_clock,
                game_period=game.game_period,
                home_team=home_team_info,
                away_team=away_team_info,
                home_score=game.home_score,
                away_score=game.away_score,
            )
            games.append(game_public)

        # Log success
        logger.info(
            "Games query successful",
            extra={
                "requested_date": target_date.isoformat(),
                "result_count": len(games),
            },
        )

        # Build response
        response = GameListResponse(
            games=games,
            total_count=len(games),
            generated_at=datetime.now(timezone.utc),
            requested_date=target_date.isoformat(),
        )

        return response

    except (OperationalError, DatabaseError) as e:
        # Log database errors with full context
        logger.error(
            "Database error in games endpoint",
            exc_info=True,
            extra={
                "endpoint": "/api/v1/games",
                "request_id": request_id or "unknown",
                "requested_date": target_date.isoformat(),
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail="Database connection failed") from e


@router.get("/today", response_model=GameListResponse, deprecated=True)
async def get_games_today(session: SessionDep) -> GameListResponse:
    """
    Get today's NCAA Men's Basketball games (convenience endpoint).

    **DEPRECATED:** This endpoint uses UTC timezone to determine "today", which
    causes incorrect results for users in western timezones during evening hours.

    **Recommended:** Use `GET /games?date={YYYY-MM-DD}` instead, calculating the
    date parameter in the user's local timezone on the client side.

    Example (JavaScript):
    ```js
    // Get local date in YYYY-MM-DD format (not UTC!)
    const localDate = new Date().toLocaleDateString('en-CA');  // en-CA uses YYYY-MM-DD
    fetch(`/api/v1/games?date=${localDate}`);

    // Or with date-fns:
    // import { format } from 'date-fns';
    // const localDate = format(new Date(), 'yyyy-MM-dd');
    ```

    Args:
        session: Database session (injected)

    Returns:
        GameListResponse with list of today's games (UTC) and metadata
    """
    return await get_games(session=session, date_param=None)
