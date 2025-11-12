"""
Seed dim_date dimension table with dates from 2024-2026.

Generates ~1,095 date records with Kimball standard attributes and NCAA-specific
March Madness tournament flags.

Usage:
    docker compose exec backend python -m app.scripts.seed_dim_date
"""

import logging
from datetime import date, timedelta

from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.models.dim_date import DimDate

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# March Madness date ranges (hardcoded for 2024-2026)
# Format: (start_date, end_date, selection_sunday)
MARCH_MADNESS_WINDOWS = {
    2024: (date(2024, 3, 19), date(2024, 4, 8), date(2024, 3, 17)),  # Selection Sunday
    2025: (date(2025, 3, 18), date(2025, 4, 7), date(2025, 3, 16)),
    2026: (date(2026, 3, 17), date(2026, 4, 6), date(2026, 3, 15)),
}

# Tournament round mappings (day offset from Selection Sunday -> round name)
TOURNAMENT_ROUNDS = {
    0: None,  # Selection Sunday (off day)
    1: None,  # Monday (off day)
    2: "First Four",  # Tuesday
    3: "First Four",  # Wednesday
    4: "Round of 64",  # Thursday
    5: "Round of 64",  # Friday
    6: "Round of 32",  # Saturday
    7: "Round of 32",  # Sunday
    8: None,  # Monday (off day)
    9: None,  # Tuesday (off day)
    10: "Sweet 16",  # Wednesday (1 week after R64 starts)
    11: "Sweet 16",  # Thursday
    12: "Elite 8",  # Friday
    13: "Elite 8",  # Saturday
    14: None,  # Sunday (off day)
    15: None,  # Monday (off day)
    16: None,  # Tuesday (off day)
    17: "Final Four",  # Wednesday (semifinal games)
    18: None,  # Thursday (off day)
    19: None,  # Friday (off day)
    20: "Championship",  # Saturday
}


def calculate_tournament_round(dt: date) -> tuple[bool, str | None]:
    """
    Calculate if a date falls within March Madness and which tournament round.

    Args:
        dt: Date to check

    Returns:
        Tuple of (is_march_madness, tournament_round)
        - is_march_madness: True if date falls within tournament window
        - tournament_round: Round name or None for off days
    """
    year = dt.year

    if year not in MARCH_MADNESS_WINDOWS:
        return (False, None)

    start_date, end_date, selection_sunday = MARCH_MADNESS_WINDOWS[year]

    # Check if date is within tournament window
    if not (start_date <= dt <= end_date):
        return (False, None)

    # Calculate day offset from Selection Sunday
    day_offset = (dt - selection_sunday).days

    # Look up tournament round (may be None for off days)
    tournament_round = TOURNAMENT_ROUNDS.get(day_offset)

    return (True, tournament_round)


def seed_dim_date() -> None:
    """
    Seed dim_date table with dates from 2024-01-01 to 2026-12-31.

    Generates ~1,095 date records with all Kimball attributes and NCAA tournament flags.
    Uses batch insert (100 rows per transaction) and session.merge() for idempotency.
    """
    logger.info("Starting dim_date seed...")

    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    # Date range: 2024-01-01 to 2026-12-31
    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)

    current_date = start_date
    total_count = 0
    batch_size = 100
    batch = []

    # Day names (ISO 8601: Monday=1, Sunday=7)
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Month names
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    with Session(engine) as session:
        while current_date <= end_date:
            # Calculate date_key in YYYYMMDD format
            date_key = (
                current_date.year * 10000 + current_date.month * 100 + current_date.day
            )

            # Kimball standard attributes
            day_of_week = current_date.isoweekday()  # Monday=1, Sunday=7
            day_name = day_names[day_of_week - 1]
            day_of_month = current_date.day
            month = current_date.month
            month_name = month_names[month - 1]
            quarter = (month - 1) // 3 + 1
            year = current_date.year
            is_weekend = day_of_week in (6, 7)  # Saturday or Sunday

            # NCAA-specific attributes
            is_march_madness, tournament_round = calculate_tournament_round(
                current_date
            )

            # Create DimDate record
            dim_date = DimDate(
                date_key=date_key,
                full_date=current_date,
                day_of_week=day_of_week,
                day_name=day_name,
                day_of_month=day_of_month,
                month=month,
                month_name=month_name,
                quarter=quarter,
                year=year,
                is_weekend=is_weekend,
                is_march_madness=is_march_madness,
                tournament_round=tournament_round,
            )

            # Add to batch
            batch.append(dim_date)

            # Insert batch when full
            if len(batch) >= batch_size:
                for record in batch:
                    session.merge(record)  # Upsert using merge (idempotent)
                session.commit()
                total_count += len(batch)
                logger.info(
                    f"Inserted batch of {len(batch)} records (total: {total_count})"
                )
                batch = []

            current_date += timedelta(days=1)

        # Insert remaining batch
        if batch:
            for record in batch:
                session.merge(record)
            session.commit()
            total_count += len(batch)
            logger.info(
                f"Inserted final batch of {len(batch)} records (total: {total_count})"
            )

    logger.info(f"dim_date seed complete! Total records: {total_count}")

    # Verify March Madness dates
    with Session(engine) as session:
        for year in [2024, 2025, 2026]:
            results = session.exec(
                select(DimDate).where(
                    DimDate.year == year,
                    DimDate.is_march_madness == True,  # noqa: E712
                )
            ).all()
            march_madness_count = len(results)

            logger.info(f"Year {year}: {march_madness_count} March Madness dates")


if __name__ == "__main__":
    seed_dim_date()
