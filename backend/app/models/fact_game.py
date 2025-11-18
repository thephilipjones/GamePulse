"""
Game fact model for GamePulse dimensional data model.

Implements Kimball-style fact table with surrogate keys and dimension foreign keys.
Sport-agnostic design supporting basketball, football, and other sports.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DECIMAL, BigInteger, Column, DateTime
from sqlmodel import Field, SQLModel


class FactGame(SQLModel, table=True):
    """
    Game fact table with surrogate keys and dimensional foreign keys.

    Uses surrogate key (game_key) for stable primary key.
    Natural key (game_id) preserved for API queryability.
    Foreign keys reference dimension tables via surrogate keys.
    """

    __tablename__ = "fact_game"

    # Surrogate key (PK) - stable identifier
    game_key: int = Field(
        sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )

    # Natural key (unique, indexed) - format: "{sport}_{api_id}"
    game_id: str = Field(unique=True, index=True, max_length=50)

    # Dimension foreign keys (using surrogate keys)
    game_date_key: int | None = Field(
        default=None, foreign_key="dim_date.date_key"
    )  # FK to dim_date.date_key
    home_team_key: int = Field(foreign_key="dim_team.team_key")
    away_team_key: int = Field(foreign_key="dim_team.team_key")

    # Degenerate dimensions (no separate dimension table)
    sport: str = Field(index=True, max_length=20)  # "ncaam", "nfl", "nba"
    game_status: str | None = Field(
        default=None, index=True, max_length=20
    )  # "scheduled", "in_progress", "final"
    game_type: str = Field(
        default="regular_season", index=True, max_length=50
    )  # "regular_season", "postseason", "tournament"
    venue: str | None = Field(default=None, max_length=200)
    broadcast_network: str | None = Field(default=None, max_length=50)

    # Measures (numeric facts)
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    attendance: int | None = None
    rivalry_factor: Decimal | None = Field(
        default=None, sa_column=Column(DECIMAL(3, 2))
    )  # 1.00 = normal, 1.50 = rivalry

    # Timestamps (context, not measures) - timezone-aware
    game_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), index=True, nullable=False)
    )
    game_start_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    game_end_time: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    game_clock: str | None = Field(default=None, max_length=50)
    game_period: str | None = Field(
        default=None, max_length=50
    )  # "1st Half", "2nd Half", "OT", "FINAL"

    # Audit timestamps - timezone-aware
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
