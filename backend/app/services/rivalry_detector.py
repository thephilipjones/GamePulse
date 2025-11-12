"""Rivalry detection service for calculating rivalry factors between teams."""

from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.dim_team import DimTeam

logger = structlog.get_logger()


async def calculate_rivalry_factor(
    home_team_id: str,
    away_team_id: str,
    session: AsyncSession,
) -> Decimal:
    """
    Calculate rivalry factor based on team conference/division matching.

    Rivalry factors enhance game excitement scoring:
    - 1.2: Conference rivals (same team_group_id)
    - 1.0: Non-conference games

    Args:
        home_team_id: Natural key for home team (format: "sport_slug", e.g., "ncaam_duke")
        away_team_id: Natural key for away team
        session: Async database session

    Returns:
        Decimal rivalry factor (1.0 or 1.2)

    Raises:
        ValueError: If team not found in dim_team table
    """
    logger.debug(
        "Calculating rivalry factor",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )

    # Lookup home team by natural key (team_id), filtering for current version (SCD Type 2)
    home_team_result = await session.execute(
        select(DimTeam).where(
            DimTeam.team_id == home_team_id,
            DimTeam.is_current == True,  # noqa: E712
        )
    )
    home_team = home_team_result.scalar_one_or_none()

    if not home_team:
        raise ValueError(f"Home team not found in dim_team: {home_team_id}")

    # Lookup away team by natural key (team_id), filtering for current version
    away_team_result = await session.execute(
        select(DimTeam).where(
            DimTeam.team_id == away_team_id,
            DimTeam.is_current == True,  # noqa: E712
        )
    )
    away_team = away_team_result.scalar_one_or_none()

    if not away_team:
        raise ValueError(f"Away team not found in dim_team: {away_team_id}")

    # Compare team_group_id (conference/division)
    # 1.2 for conference rivals, 1.0 otherwise
    if (
        home_team.team_group_id
        and away_team.team_group_id
        and home_team.team_group_id == away_team.team_group_id
    ):
        rivalry_factor = Decimal("1.2")
        logger.info(
            "Conference rivalry detected",
            home_team=home_team.team_name,
            away_team=away_team.team_name,
            conference=home_team.team_group_name,
            rivalry_factor=str(rivalry_factor),
        )
    else:
        rivalry_factor = Decimal("1.0")
        logger.debug(
            "Non-conference game",
            home_team=home_team.team_name,
            away_team=away_team.team_name,
            rivalry_factor=str(rivalry_factor),
        )

    return rivalry_factor
