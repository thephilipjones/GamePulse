"""
GamePulse SQLModel database models.

This package exports all database models for Alembic auto-detection.
All models must be imported here for migration generation to work.
"""
from sqlmodel import SQLModel

# Template demo models (to be removed before production)
from .item import Item, ItemBase, ItemCreate, ItemUpdate, ItemPublic, ItemsPublic, Message

# GamePulse domain models
from .team import Team, TeamGroup, TeamRivalry
from .game import Game

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
    # Domain models
    "Team",
    "TeamGroup",
    "TeamRivalry",
    "Game",
]
