"""
Team domain models for GamePulse multi-sport data schema.

Supports NCAAM basketball initially, with expansion to NFL and NBA.
Uses SQLModel for type-safe ORM with Pydantic validation.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import ARRAY, String, Column
from sqlmodel import Field, SQLModel


class Team(SQLModel, table=True):
    """
    Teams dimensional table (sport-agnostic).

    Supports multi-sport expansion via sport-namespaced team IDs.
    Format: "{sport}_{slug}" (e.g., "ncaam_duke", "nfl_chiefs")
    """
    __tablename__ = "teams"

    team_id: str = Field(primary_key=True)  # Format: "{sport}_{slug}"
    sport: str = Field(index=True)  # Enables sport-level filtering
    team_name: str
    team_abbr: Optional[str] = None
    team_group_id: Optional[str] = Field(default=None, foreign_key="team_groups.team_group_id")
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    aliases: List[str] = Field(sa_column=Column(ARRAY(String)))  # PostgreSQL array for fuzzy matching
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TeamGroup(SQLModel, table=True):
    """
    Team groups dimensional table (generic: conferences, divisions, leagues).

    Supports both flat structure (NCAAM conferences) and nested hierarchies
    (NFL conference→division) via parent_group_id self-reference.
    """
    __tablename__ = "team_groups"

    team_group_id: str = Field(primary_key=True)
    team_group_name: str
    sport: str = Field(index=True)
    group_type: str  # "conference", "division", "league"
    parent_group_id: Optional[str] = Field(default=None, foreign_key="team_groups.team_group_id")
    level: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeamRivalry(SQLModel, table=True):
    """
    Team rivalry mapping table (many-to-many).

    Tracks rivalry_factor as a mutable value with updated_at timestamp
    for historical analysis. Enforces ordering via CHECK constraint
    (team_a_id < team_b_id) to prevent duplicate rivalries.
    """
    __tablename__ = "team_rivalries"

    rivalry_id: Optional[int] = Field(default=None, primary_key=True)
    team_a_id: str = Field(foreign_key="teams.team_id")
    team_b_id: str = Field(foreign_key="teams.team_id")
    rivalry_factor: float = Field(default=1.0)  # 1.0 = normal, 1.5 = heated rivalry
    rivalry_type: Optional[str] = None  # "historic", "geographic", "playoff", "divisional"
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
