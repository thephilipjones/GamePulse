"""
GamePulse SQLModel database models.

This package exports all database models for Alembic auto-detection.
All models must be imported here for migration generation to work.
"""

from sqlmodel import SQLModel

from .dim_date import DimDate
from .dim_team import DimTeam
from .fact_game import FactGame

# Legacy models (kept for backward compatibility during migration)
from .game import Game

# Template demo models (to be removed before production)
from .item import (
    Item,
    ItemBase,
    ItemCreate,
    ItemPublic,
    ItemsPublic,
    ItemUpdate,
    Message,
)
from .team import Team, TeamGroup, TeamRivalry

__all__ = [
    # SQLModel base
    "SQLModel",
    # Template models
    "Item",
    "ItemBase",
    "ItemCreate",
    "ItemUpdate",
    "ItemPublic",
    "ItemsPublic",
    "Message",
    # Dimensional models (new)
    "DimDate",
    "DimTeam",
    "FactGame",
    # Legacy models (deprecated, will be removed in future)
    "Team",
    "TeamGroup",
    "TeamRivalry",
    "Game",
]
