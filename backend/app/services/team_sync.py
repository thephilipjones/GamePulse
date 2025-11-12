"""
Team synchronization service for NCAA API data.

Automatically discovers and syncs team metadata from NCAA API responses,
preserving manually curated data (colors, aliases, conferences).
"""

import logging
from typing import Any

from sqlalchemy.dialects import postgresql
from sqlmodel import Session, select

from app.models.dim_team import DimTeam

logger = logging.getLogger(__name__)


async def sync_teams_from_games(
    games_data: list[dict[str, Any]], session: Session
) -> dict[str, int]:
    """
    Sync team metadata from NCAA API game responses.

    Extracts unique teams from game data and upserts them into the database.
    Preserves manually curated data (colors, aliases, team_group_*) while
    updating team names and ESPN IDs from the API.

    Args:
        games_data: List of game dictionaries from NCAA API
        session: SQLModel database session

    Returns:
        Dictionary with sync metadata:
        {
            "teams_discovered": 5,  # New teams inserted
            "teams_updated": 2,     # Existing teams updated
            "teams_unchanged": 13   # Teams in API but no changes needed
        }

    Example:
        >>> games_data = ncaa_client.fetch_todays_games()
        >>> metadata = await sync_teams_from_games(games_data, session)
        >>> print(f"Discovered {metadata['teams_discovered']} new teams")
    """
    if not games_data:
        logger.debug("No games data provided, skipping team sync")
        return {"teams_discovered": 0, "teams_updated": 0, "teams_unchanged": 0}

    # Step 1: Extract unique teams from games (deduplicate)
    teams_from_api: dict[str, dict[str, str]] = {}
    for game in games_data:
        try:
            # Extract home team
            home_team = game.get("home", {})
            if home_team and "id" in home_team:
                team_id = f"ncaam_{home_team['id']}"
                if team_id not in teams_from_api:
                    teams_from_api[team_id] = {
                        "team_id": team_id,
                        "espn_team_id": home_team["id"],
                        "team_name": home_team.get("names", {}).get(
                            "short", home_team.get("id", "Unknown")
                        ),
                    }

            # Extract away team
            away_team = game.get("away", {})
            if away_team and "id" in away_team:
                team_id = f"ncaam_{away_team['id']}"
                if team_id not in teams_from_api:
                    teams_from_api[team_id] = {
                        "team_id": team_id,
                        "espn_team_id": away_team["id"],
                        "team_name": away_team.get("names", {}).get(
                            "short", away_team.get("id", "Unknown")
                        ),
                    }

        except (KeyError, TypeError, AttributeError) as e:
            logger.warning(f"Failed to extract teams from game: {e}", exc_info=True)
            continue

    if not teams_from_api:
        logger.debug("No teams found in game data")
        return {"teams_discovered": 0, "teams_updated": 0, "teams_unchanged": 0}

    logger.debug(
        f"Extracted {len(teams_from_api)} unique teams from {len(games_data)} games"
    )

    # Step 2: Query existing teams to determine new vs. existing
    existing_teams_stmt = select(DimTeam.team_id, DimTeam.team_name).where(
        DimTeam.team_id.in_(teams_from_api.keys())  # type: ignore[attr-defined]
    )
    existing_teams_result = session.exec(existing_teams_stmt).all()
    existing_teams = dict(existing_teams_result)

    # Step 3: Categorize teams
    teams_to_insert = []
    teams_to_update = []

    for team_id, team_data in teams_from_api.items():
        if team_id not in existing_teams:
            # New team - will be inserted
            teams_to_insert.append(team_data)
        elif existing_teams[team_id] != team_data["team_name"]:
            # Existing team with name change - will be updated
            teams_to_update.append(team_data)

    teams_unchanged = len(teams_from_api) - len(teams_to_insert) - len(teams_to_update)

    # Step 4: Build upsert list (all teams from API)
    teams_to_upsert = [
        {
            "team_id": team_data["team_id"],
            "espn_team_id": team_data["espn_team_id"],
            "team_name": team_data["team_name"],
            "sport": "ncaam",  # Default sport
        }
        for team_data in teams_from_api.values()
    ]

    # Step 5: Execute batch upsert using PostgreSQL INSERT ... ON CONFLICT
    if teams_to_upsert:
        stmt = postgresql.insert(DimTeam).values(teams_to_upsert)
        stmt = stmt.on_conflict_do_update(
            index_elements=["team_id"],  # Conflict on natural key
            set_={
                "team_name": stmt.excluded.team_name,
                "espn_team_id": stmt.excluded.espn_team_id,
                "updated_at": stmt.excluded.updated_at,
                # Preserve: team_key (surrogate PK), colors, aliases, team_group_*
            },
        )
        session.exec(stmt)  # type: ignore[arg-type]
        session.commit()

    # Step 6: Structured logging
    for team_data in teams_to_insert:
        logger.info(
            f"Team discovered from API: {team_data['team_id']} "
            f"({team_data['team_name']}) - ESPN ID {team_data['espn_team_id']}"
        )

    for team_data in teams_to_update:
        old_name = existing_teams[team_data["team_id"]]
        logger.debug(
            f"Team updated from API: {team_data['team_id']} - "
            f"name changed from '{old_name}' to '{team_data['team_name']}'"
        )

    # Step 7: Return metadata
    metadata = {
        "teams_discovered": len(teams_to_insert),
        "teams_updated": len(teams_to_update),
        "teams_unchanged": teams_unchanged,
    }

    logger.info(
        f"Team sync complete: {metadata['teams_discovered']} discovered, "
        f"{metadata['teams_updated']} updated, {metadata['teams_unchanged']} unchanged"
    )

    return metadata
