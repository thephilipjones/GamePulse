"""
Team dimension model for GamePulse dimensional data model.

Implements Kimball-style dimensional modeling with surrogate keys and SCD Type 2 readiness.
Supports multi-sport expansion via sport-namespaced team IDs.
"""

from datetime import datetime, timezone

from sqlalchemy import ARRAY, Column, Integer, String
from sqlmodel import Field, SQLModel


class DimTeam(SQLModel, table=True):
    """
    Team dimension table with surrogate keys and SCD Type 2 support.

    Flattens team_group (conference/division) for query performance.
    Uses surrogate key (team_key) for stable foreign key references.
    Natural key (team_id) preserved for API queryability.
    """

    __tablename__ = "dim_team"

    # Surrogate key (PK) - stable identifier for foreign key references
    team_key: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=True)
    )

    # Natural key (unique, indexed) - format: "{sport}_{slug}"
    team_id: str = Field(unique=True, index=True, max_length=50)

    # Core attributes
    sport: str = Field(index=True, max_length=20)  # "ncaam", "nfl", "nba"
    team_name: str = Field(max_length=100)
    team_abbr: str | None = Field(default=None, max_length=10)

    # Flattened team_group (denormalized for query performance)
    team_group_id: str | None = Field(default=None, max_length=50)
    team_group_name: str | None = Field(default=None, max_length=100)

    # UI metadata
    primary_color: str | None = Field(default=None, max_length=7)  # Hex color
    secondary_color: str | None = Field(default=None, max_length=7)
    aliases: list[str] = Field(
        default_factory=list, sa_column=Column(ARRAY(String))
    )  # For Reddit fuzzy matching

    # SCD Type 2 fields (for future conference realignment tracking)
    is_current: bool = Field(default=True)  # TRUE = current version
    valid_from: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )  # When this version became effective
    valid_to: datetime | None = Field(default=None)  # NULL = still current

    # Audit timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
