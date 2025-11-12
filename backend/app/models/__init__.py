"""
GamePulse SQLModel database models.

This package exports all database models for Alembic auto-detection.
All models must be imported here for migration generation to work.
"""

from sqlmodel import SQLModel

from .dim_date import DimDate
from .dim_team import DimTeam
from .fact_game import FactGame

__all__ = [
    # SQLModel base
    "SQLModel",
    # Dimensional models
    "DimDate",
    "DimTeam",
    "FactGame",
]
