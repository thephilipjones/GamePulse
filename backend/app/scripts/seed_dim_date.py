"""
Seed or extend dim_date dimension table with Kimball attributes and NCAA tournament flags.

Automatically detects existing data and extends as needed. Default range: (current_year - 1)
to (current_year + 2), ensuring 2+ years of future dates are always available.

Usage:
    # Auto-detect and extend (recommended)
    docker compose exec backend python -m app.scripts.seed_dim_date

    # Specify custom date range
    docker compose exec backend python -m app.scripts.seed_dim_date --start-year 2024 --end-year 2028

    # Force full re-seed (idempotent via merge)
    docker compose exec backend python -m app.scripts.seed_dim_date --force
"""

import logging
from datetime import date, timedelta

from sqlalchemy import Engine
from sqlmodel import Session, create_engine, func, select

from app.core.config import settings
from app.models.dim_date import DimDate

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# March Madness date ranges (hardcoded for 2024-2028)
# Format: (start_date, end_date, selection_sunday)
# Note: Extend this dict annually or calculate dates programmatically
MARCH_MADNESS_WINDOWS = {
    2024: (date(2024, 3, 19), date(2024, 4, 8), date(2024, 3, 17)),  # Selection Sunday
    2025: (date(2025, 3, 18), date(2025, 4, 7), date(2025, 3, 16)),
    2026: (date(2026, 3, 17), date(2026, 4, 6), date(2026, 3, 15)),
    2027: (date(2027, 3, 16), date(2027, 4, 5), date(2027, 3, 14)),
    2028: (date(2028, 3, 21), date(2028, 4, 10), date(2028, 3, 19)),
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


def get_existing_date_range(engine: Engine) -> tuple[date | None, date | None]:
    """
    Detect existing date range in dim_date table.

    Args:
        engine: SQLAlchemy engine

    Returns:
        Tuple of (min_date, max_date) or (None, None) if table is empty
    """
    with Session(engine) as session:
        result = session.exec(
            select(func.min(DimDate.full_date), func.max(DimDate.full_date))
        ).first()

        if result and result[0] and result[1]:
            return (result[0], result[1])
        return (None, None)


def seed_dim_date(
    start_year: int | None = None,
    end_year: int | None = None,
    force_full_seed: bool = False,
) -> None:
    """
    Seed or extend dim_date table with dates.

    Automatically detects existing data and extends as needed. Default range:
    (current_year - 1) to (current_year + 2), ensuring 2+ years of future dates.

    Args:
        start_year: Override start year (default: current_year - 1)
        end_year: Override end year (default: current_year + 2)
        force_full_seed: Force full re-seed (ignore existing data)

    Generates date records with all Kimball attributes and NCAA tournament flags.
    Uses batch insert (100 rows per transaction) and session.merge() for idempotency.
    """
    logger.info("Starting dim_date seed/extension...")

    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    # Detect existing date range
    min_existing, max_existing = get_existing_date_range(engine)

    if min_existing and max_existing and not force_full_seed:
        logger.info(
            f"Existing data detected: {min_existing} to {max_existing} "
            f"({(max_existing - min_existing).days + 1} days)"
        )

    # Determine date range
    from datetime import datetime

    current_year = datetime.now().year

    if start_year is None:
        if force_full_seed or not min_existing:
            # New seed: default to (current_year - 1)
            start_year = current_year - 1
        else:
            # Extension: start from day after max existing date
            start_year = min_existing.year

    if end_year is None:
        if force_full_seed or not max_existing:
            # New seed: default to (current_year + 2)
            end_year = current_year + 2
        else:
            # Extension: extend to (current_year + 2)
            end_year = max(max_existing.year, current_year + 2)

    # Build date range
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    # Optimize: skip existing range if extending
    if not force_full_seed and min_existing and max_existing:
        if start_date < min_existing:
            # Need to backfill before existing data
            logger.info(
                f"Backfilling dates: {start_date} to {min_existing - timedelta(days=1)}"
            )
        if end_date > max_existing:
            # Need to extend after existing data
            logger.info(
                f"Extending dates: {max_existing + timedelta(days=1)} to {end_date}"
            )

        # Check if we're fully covered
        if start_date >= min_existing and end_date <= max_existing:
            logger.info(
                f"Date range {start_date} to {end_date} already covered by existing data. "
                "Nothing to insert."
            )
            return

    logger.info(f"Seeding date range: {start_date} to {end_date}")

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
        for year in [2024, 2025, 2026, 2027, 2028]:
            results = session.exec(
                select(DimDate).where(
                    DimDate.year == year,
                    DimDate.is_march_madness == True,  # noqa: E712
                )
            ).all()
            march_madness_count = len(results)

            logger.info(f"Year {year}: {march_madness_count} March Madness dates")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed or extend dim_date dimension table with Kimball attributes and NCAA tournament flags."
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="Start year (default: current_year - 1)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="End year (default: current_year + 2)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force full re-seed (ignore existing data)",
    )

    args = parser.parse_args()

    seed_dim_date(
        start_year=args.start_year,
        end_year=args.end_year,
        force_full_seed=args.force,
    )
