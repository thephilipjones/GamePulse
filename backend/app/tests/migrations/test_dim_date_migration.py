"""
Tests for dim_date migration - validates schema correctness.

This test ensures migration eae821e42c50 correctly creates:
- dim_date table with proper columns and types
- Primary key on date_key
- Unique constraint on full_date
- 4 indexes for query performance
- Foreign key constraint from fact_game
- NOT NULL constraints on all columns except tournament_round
"""

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session

from app.core.db import engine


@pytest.mark.asyncio
async def test_dim_date_table_exists() -> None:
    """Verify dim_date table exists after migration."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "dim_date" in tables, "dim_date table should exist after migration"


@pytest.mark.asyncio
async def test_dim_date_primary_key() -> None:
    """Verify date_key is the primary key."""
    inspector = inspect(engine)
    pk_constraint = inspector.get_pk_constraint("dim_date")

    assert pk_constraint is not None
    assert pk_constraint["constrained_columns"] == ["date_key"]
    assert pk_constraint["name"] == "dim_date_pkey"


@pytest.mark.asyncio
async def test_dim_date_unique_constraint() -> None:
    """Verify full_date has unique constraint via unique index."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("dim_date")

    # Find the full_date unique index
    full_date_index = next(
        (idx for idx in indexes if idx["name"] == "ix_dim_date_full_date"), None
    )

    assert full_date_index is not None, "full_date unique index should exist"
    assert full_date_index["unique"] is True
    assert full_date_index["column_names"] == ["full_date"]


@pytest.mark.asyncio
async def test_dim_date_indexes_exist() -> None:
    """
    Verify all 4 indexes exist for query performance.

    Expected indexes:
    1. ix_dim_date_full_date (unique) - natural key
    2. ix_dim_date_year - annual queries
    3. ix_dim_date_year_month - monthly queries
    4. ix_dim_date_is_march_madness - tournament queries
    """
    inspector = inspect(engine)
    indexes = inspector.get_indexes("dim_date")

    index_names = {idx["name"] for idx in indexes}

    expected_indexes = {
        "ix_dim_date_full_date",
        "ix_dim_date_year",
        "ix_dim_date_year_month",
        "ix_dim_date_is_march_madness",
    }

    assert expected_indexes.issubset(
        index_names
    ), f"Missing indexes: {expected_indexes - index_names}"

    # Verify composite index on year+month
    year_month_index = next(
        (idx for idx in indexes if idx["name"] == "ix_dim_date_year_month"), None
    )
    assert year_month_index is not None
    assert year_month_index["column_names"] == ["year", "month"]


@pytest.mark.asyncio
async def test_dim_date_foreign_key_from_fact_game() -> None:
    """Verify FK constraint exists from fact_game.game_date_key to dim_date.date_key."""
    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys("fact_game")

    # Find the FK constraint for game_date_key
    game_date_fk = next(
        (fk for fk in foreign_keys if fk["constrained_columns"] == ["game_date_key"]),
        None,
    )

    assert game_date_fk is not None, "FK constraint from fact_game should exist"
    assert game_date_fk["referred_table"] == "dim_date"
    assert game_date_fk["referred_columns"] == ["date_key"]
    assert game_date_fk["name"] == "fk_fact_game_game_date"
    assert game_date_fk["options"]["ondelete"] == "SET NULL"


@pytest.mark.asyncio
async def test_dim_date_columns_not_nullable() -> None:
    """
    Verify all columns are NOT NULL except tournament_round.

    This ensures data integrity for the date dimension.
    """
    with Session(engine) as session:
        # Query PostgreSQL information_schema for column nullability
        result = session.execute(
            text("""
                SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'dim_date'
                ORDER BY column_name
            """)
        )

        nullability = {row[0]: row[1] for row in result}

        # All columns should be NOT NULL except tournament_round
        expected_not_null_columns = [
            "date_key",
            "full_date",
            "day_of_week",
            "day_name",
            "day_of_month",
            "month",
            "month_name",
            "quarter",
            "year",
            "is_weekend",
            "is_march_madness",
        ]

        for col in expected_not_null_columns:
            assert col in nullability, f"Column {col} should exist"
            assert nullability[col] == "NO", f"Column {col} should be NOT NULL"

        # tournament_round should be nullable
        assert "tournament_round" in nullability
        assert (
            nullability["tournament_round"] == "YES"
        ), "tournament_round should be nullable"


@pytest.mark.asyncio
async def test_dim_date_insert_without_sequence() -> None:
    """
    Verify that date_key does NOT use autoincrement (no DEFAULT constraint).

    Unlike dim_team which uses auto-increment surrogate keys, dim_date requires
    manually assigned date_key in YYYYMMDD format (e.g., 20250311).

    This test ensures date_key has NO DEFAULT constraint.
    """
    with Session(engine) as session:
        # Query PostgreSQL information_schema for column defaults
        result = session.execute(
            text("""
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_name = 'dim_date'
                AND column_name = 'date_key'
            """)
        )

        row = result.fetchone()

        assert row is not None, "date_key column should exist"
        assert (
            row[1] is None
        ), "date_key should NOT have DEFAULT constraint (manually assigned)"

        # Verify INSERT without date_key fails (proves no autoincrement)
        session.execute(text("BEGIN"))
        try:
            session.execute(
                text("""
                    INSERT INTO dim_date (
                        full_date, day_of_week, day_name, day_of_month,
                        month, month_name, quarter, year, is_weekend,
                        is_march_madness
                    )
                    VALUES (
                        '2099-12-31', 5, 'Friday', 31,
                        12, 'December', 4, 2099, false,
                        false
                    )
                """)
            )
            session.commit()
            # If we get here, autoincrement is enabled (BAD)
            pytest.fail("INSERT without date_key should fail, but it succeeded")
        except Exception:
            # Expected: INSERT should fail without date_key
            session.rollback()
