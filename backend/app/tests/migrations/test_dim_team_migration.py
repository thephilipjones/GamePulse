"""
Tests for dim_team migration - validates DEFAULT constraints are properly set.

This test ensures migration d115685a3652 correctly sets DEFAULT constraints
for team_key, created_at, and updated_at columns to prevent NOT NULL violations
during batch upsert operations (Story 2-3b).
"""

import pytest
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import engine


@pytest.mark.asyncio
async def test_dim_team_default_constraints_exist() -> None:
    """
    Verify DEFAULT constraints exist on dim_team table after migration.

    This test queries PostgreSQL schema to confirm:
    - team_key has DEFAULT nextval('teams_team_key_seq'::regclass)
    - created_at has DEFAULT now()
    - updated_at has DEFAULT now()

    These constraints are required for batch upsert in team_sync.py
    """
    with Session(engine) as session:
        # Query PostgreSQL information_schema for column defaults
        result = session.exec(
            text("""
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_name = 'dim_team'
                AND column_name IN ('team_key', 'created_at', 'updated_at')
                ORDER BY column_name
            """)
        )

        defaults = {row[0]: row[1] for row in result}

        # Verify team_key DEFAULT (uses sequence)
        assert "team_key" in defaults
        assert "teams_team_key_seq" in defaults["team_key"]
        assert "nextval" in defaults["team_key"]

        # Verify created_at DEFAULT (uses NOW())
        assert "created_at" in defaults
        assert "now()" in defaults["created_at"]

        # Verify updated_at DEFAULT (uses NOW())
        assert "updated_at" in defaults
        assert "now()" in defaults["updated_at"]


@pytest.mark.asyncio
async def test_dim_team_insert_without_explicit_values() -> None:
    """
    Verify that INSERT works without providing team_key, created_at, updated_at.

    This simulates the batch upsert behavior in team_sync.py which only
    provides: team_id, espn_team_id, team_name, sport, updated_at (in conflict).

    The DEFAULT constraints should auto-populate the missing columns.
    """
    with Session(engine) as session:
        # Clean up any existing test data
        session.exec(
            text("DELETE FROM dim_team WHERE team_id = 'ncaam_test_migration'")
        )
        session.commit()

        # INSERT without team_key, created_at (should use DEFAULTs)
        session.exec(
            text("""
                INSERT INTO dim_team (team_id, sport, team_name, espn_team_id)
                VALUES ('ncaam_test_migration', 'ncaam', 'Test Team', '12345')
            """)
        )
        session.commit()

        # Verify row was inserted and DEFAULT values were applied
        result = session.exec(
            text("""
                SELECT team_key, created_at, updated_at, team_name
                FROM dim_team
                WHERE team_id = 'ncaam_test_migration'
            """)
        ).first()

        assert result is not None
        team_key, created_at, updated_at, team_name = result

        # Verify auto-generated values
        assert team_key is not None  # DEFAULT nextval(...) worked
        assert isinstance(team_key, int)
        assert team_key > 0

        assert created_at is not None  # DEFAULT now() worked
        assert updated_at is not None  # DEFAULT now() worked

        assert team_name == "Test Team"

        # Clean up
        session.exec(
            text("DELETE FROM dim_team WHERE team_id = 'ncaam_test_migration'")
        )
        session.commit()
