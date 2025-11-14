"""Pydantic schemas for game API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class TeamInfo(BaseModel):
    """Team information for game responses."""

    team_key: int = Field(..., description="Surrogate key for team dimension")
    team_id: str = Field(..., description="Natural key (sport_slug format)")
    team_name: str = Field(..., description="Full team name")
    team_group_name: str | None = Field(None, description="Conference or division name")
    primary_color: str | None = Field(None, description="Primary team color (hex)")
    secondary_color: str | None = Field(None, description="Secondary team color (hex)")

    model_config = {"from_attributes": True}


class GamePublic(BaseModel):
    """Public game response with team details."""

    game_key: int = Field(..., description="Surrogate key for game fact")
    game_id: str = Field(..., description="Natural key (sport_api_id format)")
    game_date: datetime = Field(..., description="Game date (timezone-aware)")
    game_start_time: datetime | None = Field(
        None, description="Game start time (timezone-aware)"
    )
    game_status: str | None = Field(
        None, description="Game status (scheduled, in_progress, final)"
    )
    home_team: TeamInfo = Field(..., description="Home team details")
    away_team: TeamInfo = Field(..., description="Away team details")
    home_score: int = Field(default=0, description="Home team score")
    away_score: int = Field(default=0, description="Away team score")

    model_config = {"from_attributes": True}


class GameListResponse(BaseModel):
    """Response schema for games list endpoint."""

    games: list[GamePublic] = Field(..., description="List of games")
    total_count: int = Field(..., description="Total number of games returned")
    generated_at: datetime = Field(
        ..., description="Response generation timestamp (UTC)"
    )
    requested_date: str = Field(..., description="Requested date in YYYY-MM-DD format")

    model_config = {"from_attributes": True}
