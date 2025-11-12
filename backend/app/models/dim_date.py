"""
Date dimension model for GamePulse dimensional data model.

Implements Kimball-style date dimension with NCAA-specific attributes.
Enables time-based analysis for March Madness trends, weekend vs weekday patterns, etc.
"""

from datetime import date

from sqlalchemy import Column, Integer
from sqlmodel import Field, SQLModel


class DimDate(SQLModel, table=True):
    """
    Date dimension table with NCAA tournament attributes.

    Uses date_key surrogate key in YYYYMMDD format (e.g., 20250311 for March 11, 2025).
    Natural key (full_date) is the actual date value.

    Includes Kimball standard date attributes and NCAA-specific tournament flags.
    """

    __tablename__ = "dim_date"

    # Surrogate key (PK) - YYYYMMDD format, manually assigned (NO autoincrement)
    date_key: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=False)
    )

    # Natural key (unique, indexed) - the actual date
    full_date: date = Field(unique=True, index=True)

    # Kimball standard date attributes
    day_of_week: int = Field(ge=1, le=7)  # ISO 8601: Monday=1, Tuesday=2, ..., Sunday=7
    day_name: str = Field(max_length=9)  # "Monday", "Tuesday", etc.
    day_of_month: int = Field(ge=1, le=31)  # 1-31
    month: int = Field(ge=1, le=12)  # 1-12
    month_name: str = Field(max_length=9)  # "January", "February", etc.
    quarter: int = Field(ge=1, le=4)  # 1-4
    year: int  # Four-digit year (e.g., 2025)
    is_weekend: bool  # Saturday (6) or Sunday (7)

    # NCAA-specific attributes
    is_march_madness: bool  # Falls within March Madness tournament window
    tournament_round: str | None = Field(
        default=None, max_length=50
    )  # "First Four", "Round of 64", etc. Null for off days
