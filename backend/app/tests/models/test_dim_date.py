"""
Tests for DimDate model (dim_date dimension table).

Tests verify:
- Basic record creation with surrogate key
- March Madness attributes (is_march_madness, tournament_round)
- Query filtering by tournament round
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.dim_date import DimDate


def test_create_dim_date(db: Session) -> None:
    """Test basic DimDate record creation with manually assigned date_key."""
    # Create a date record for March 11, 2025 (Sweet 16 day)
    dim_date = DimDate(
        date_key=20250311,  # Manually assigned YYYYMMDD format
        full_date=date(2025, 3, 11),
        day_of_week=2,  # Tuesday (ISO 8601)
        day_name="Tuesday",
        day_of_month=11,
        month=3,
        month_name="March",
        quarter=1,
        year=2025,
        is_weekend=False,
        is_march_madness=False,  # Outside tournament window
        tournament_round=None,
    )

    db.add(dim_date)
    db.commit()
    db.refresh(dim_date)

    # Verify record was created
    assert dim_date.date_key == 20250311
    assert dim_date.full_date == date(2025, 3, 11)
    assert dim_date.day_of_week == 2
    assert dim_date.day_name == "Tuesday"
    assert dim_date.month_name == "March"
    assert dim_date.quarter == 1
    assert dim_date.year == 2025
    assert dim_date.is_weekend is False
    assert dim_date.is_march_madness is False
    assert dim_date.tournament_round is None

    # Verify natural key uniqueness (full_date)
    duplicate = DimDate(
        date_key=20250312,  # Different surrogate key
        full_date=date(2025, 3, 11),  # Same natural key
        day_of_week=2,
        day_name="Tuesday",
        day_of_month=11,
        month=3,
        month_name="March",
        quarter=1,
        year=2025,
        is_weekend=False,
        is_march_madness=False,
        tournament_round=None,
    )

    db.add(duplicate)
    with pytest.raises(IntegrityError):  # Should fail on unique constraint
        db.commit()


def test_march_madness_attributes(db: Session) -> None:
    """Test NCAA-specific March Madness attributes."""
    # Create March Madness dates with different tournament rounds
    dates_to_create = [
        # 2025 March Madness: Selection Sunday (off day)
        DimDate(
            date_key=20250316,
            full_date=date(2025, 3, 16),
            day_of_week=7,  # Sunday
            day_name="Sunday",
            day_of_month=16,
            month=3,
            month_name="March",
            quarter=1,
            year=2025,
            is_weekend=True,
            is_march_madness=True,
            tournament_round=None,  # Off day
        ),
        # First Four
        DimDate(
            date_key=20250318,
            full_date=date(2025, 3, 18),
            day_of_week=2,
            day_name="Tuesday",
            day_of_month=18,
            month=3,
            month_name="March",
            quarter=1,
            year=2025,
            is_weekend=False,
            is_march_madness=True,
            tournament_round="First Four",
        ),
        # Round of 64
        DimDate(
            date_key=20250320,
            full_date=date(2025, 3, 20),
            day_of_week=4,
            day_name="Thursday",
            day_of_month=20,
            month=3,
            month_name="March",
            quarter=1,
            year=2025,
            is_weekend=False,
            is_march_madness=True,
            tournament_round="Round of 64",
        ),
        # Championship
        DimDate(
            date_key=20250405,
            full_date=date(2025, 4, 5),
            day_of_week=6,
            day_name="Saturday",
            day_of_month=5,
            month=4,
            month_name="April",
            quarter=2,
            year=2025,
            is_weekend=True,
            is_march_madness=True,
            tournament_round="Championship",
        ),
    ]

    for dim_date in dates_to_create:
        db.add(dim_date)
    db.commit()

    # Verify is_march_madness flag works
    march_madness_dates = db.exec(
        select(DimDate).where(
            DimDate.is_march_madness == True  # noqa: E712
        )
    ).all()

    assert len(march_madness_dates) == 4

    # Verify tournament_round values
    championship = db.exec(
        select(DimDate).where(DimDate.tournament_round == "Championship")
    ).first()

    assert championship is not None
    assert championship.date_key == 20250405
    assert championship.is_march_madness is True

    # Verify off days (is_march_madness=TRUE but tournament_round=NULL)
    off_days = db.exec(
        select(DimDate).where(
            DimDate.is_march_madness == True,  # noqa: E712
            DimDate.tournament_round == None,  # noqa: E711
        )
    ).all()

    assert len(off_days) == 1
    assert off_days[0].date_key == 20250316  # Selection Sunday


def test_query_by_tournament_round(db: Session) -> None:
    """Test filtering dates by tournament round."""
    # Create multiple dates with same tournament round
    sweet_16_dates = [
        DimDate(
            date_key=20250326,
            full_date=date(2025, 3, 26),
            day_of_week=3,
            day_name="Wednesday",
            day_of_month=26,
            month=3,
            month_name="March",
            quarter=1,
            year=2025,
            is_weekend=False,
            is_march_madness=True,
            tournament_round="Sweet 16",
        ),
        DimDate(
            date_key=20250327,
            full_date=date(2025, 3, 27),
            day_of_week=4,
            day_name="Thursday",
            day_of_month=27,
            month=3,
            month_name="March",
            quarter=1,
            year=2025,
            is_weekend=False,
            is_march_madness=True,
            tournament_round="Sweet 16",
        ),
    ]

    for dim_date in sweet_16_dates:
        db.add(dim_date)
    db.commit()

    # Query by tournament round
    results = db.exec(
        select(DimDate).where(DimDate.tournament_round == "Sweet 16")
    ).all()

    assert len(results) == 2
    assert all(r.tournament_round == "Sweet 16" for r in results)
    assert all(r.is_march_madness is True for r in results)

    # Verify date range
    date_keys = sorted([r.date_key for r in results])
    assert date_keys == [20250326, 20250327]
