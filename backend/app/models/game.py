"""
Game domain model for GamePulse multi-sport data schema.

Sport-agnostic fact table supporting basketball, football, and other sports.
Optimized for BI tool queries with indexed fields (sport, date, status, type).
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Game(SQLModel, table=True):
    """
    Games fact table (sport-agnostic).

    Supports NCAAM basketball initially, with expansion to NFL and NBA.
    Indexed fields enable efficient analytical queries from BI tools.
    """

    __tablename__ = "games"

    game_id: str = Field(primary_key=True)  # Format: "{sport}_{api_id}"
    sport: str = Field(index=True)
    game_date: datetime = Field(index=True)
    home_team_id: str = Field(foreign_key="teams.team_id")
    away_team_id: str = Field(foreign_key="teams.team_id")
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    game_status: str | None = Field(default=None, index=True)
    game_clock: str | None = None
    game_start_time: datetime | None = None
    game_end_time: datetime | None = None
    venue: str | None = None
    game_type: str = Field(
        default="regular_season", index=True
    )  # "regular_season", "postseason", etc.
    rivalry_factor: float | None = (
        None  # Cached from team_rivalries for query performance
    )
    broadcast_network: str | None = None
    attendance: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
