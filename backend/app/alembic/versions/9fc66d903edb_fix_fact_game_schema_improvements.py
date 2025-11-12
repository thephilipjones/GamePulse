"""fix fact_game schema improvements

Revision ID: 9fc66d903edb
Revises: eae821e42c50
Create Date: 2025-11-12 10:12:07.789560

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '9fc66d903edb'
down_revision = 'eae821e42c50'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix fact_game schema issues identified in code review.

    Addresses action items:
    1. Add DEFAULT constraint to game_key (ACTION ITEM 1)
    2. Rename sequence for naming consistency (ACTION ITEM 4)
    3. Add composite index on team keys (ACTION ITEM 2)
    4. Migrate to timezone-aware timestamps (ACTION ITEM 3)
    5. Drop duplicate legacy indexes (cleanup)
    6. Fix dim_date.date_key autoincrement (manually assigned YYYYMMDD)
    """

    # Step 1 & 2: Normalize sequence state with defensive checks
    # Check which sequence name exists (if any) and normalize to expected state
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = 'games_game_key_seq' AND relkind = 'S'
        ) as old_exists,
        EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = 'fact_game_game_key_seq' AND relkind = 'S'
        ) as new_exists
    """))
    row = result.fetchone()

    if row[0]:  # old_exists: games_game_key_seq exists
        # Set DEFAULT to old sequence name first (for clean rename)
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('games_game_key_seq'::regclass)
        """)
        # Rename to new consistent name
        op.execute("ALTER SEQUENCE games_game_key_seq RENAME TO fact_game_game_key_seq")
        # Update DEFAULT to new name
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('fact_game_game_key_seq'::regclass)
        """)
    elif row[1]:  # new_exists: fact_game_game_key_seq already exists
        # Sequence already has correct name, just ensure DEFAULT is set
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('fact_game_game_key_seq'::regclass)
        """)
    else:  # Neither exists: create new sequence with correct name
        # This shouldn't happen if migrations ran correctly, but handle it defensively
        op.execute("""
            CREATE SEQUENCE fact_game_game_key_seq
            OWNED BY fact_game.game_key
        """)
        # Set sequence value to current max + 1
        op.execute("""
            SELECT setval('fact_game_game_key_seq',
                COALESCE((SELECT MAX(game_key) FROM fact_game), 0) + 1,
                false)
        """)
        # Set DEFAULT constraint
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('fact_game_game_key_seq'::regclass)
        """)

    # Step 3: Add composite index on (home_team_key, away_team_key) for team matchup queries
    op.create_index(
        'idx_fact_game_teams',
        'fact_game',
        ['home_team_key', 'away_team_key']
    )

    # Step 4: Migrate all timestamp columns to TIMESTAMP WITH TIME ZONE
    # Convert existing naive timestamps to UTC-aware (assumes all data is UTC)
    op.execute("""
        ALTER TABLE fact_game
        ALTER COLUMN game_date TYPE timestamptz
            USING game_date AT TIME ZONE 'UTC',
        ALTER COLUMN game_start_time TYPE timestamptz
            USING game_start_time AT TIME ZONE 'UTC',
        ALTER COLUMN game_end_time TYPE timestamptz
            USING game_end_time AT TIME ZONE 'UTC',
        ALTER COLUMN created_at TYPE timestamptz
            USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at TYPE timestamptz
            USING updated_at AT TIME ZONE 'UTC'
    """)

    # Step 5: Drop duplicate legacy indexes from old 'games' table
    # These were not removed during table rename (d115685a3652 migration)
    op.drop_index('ix_games_game_date', 'fact_game', if_exists=True)
    op.drop_index('ix_games_game_status', 'fact_game', if_exists=True)
    op.drop_index('ix_games_game_type', 'fact_game', if_exists=True)
    op.drop_index('ix_games_sport', 'fact_game', if_exists=True)

    # Step 6: Remove DEFAULT constraint from dim_date.date_key (manually assigned YYYYMMDD)
    # DimDate uses manually assigned date_key in YYYYMMDD format (e.g., 20250311)
    # PostgreSQL auto-created a sequence, but it should NOT have autoincrement
    op.execute("ALTER TABLE dim_date ALTER COLUMN date_key DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS dim_date_date_key_seq")


def downgrade():
    """
    Reverse all schema improvements.

    Note: This is for development/testing only. Reverting to naive timestamps
    may result in timezone data loss.
    """

    # Step 1: Recreate dim_date sequence and DEFAULT (reverse of Step 6)
    op.execute("CREATE SEQUENCE IF NOT EXISTS dim_date_date_key_seq OWNED BY dim_date.date_key")
    op.execute("""
        ALTER TABLE dim_date
        ALTER COLUMN date_key
        SET DEFAULT nextval('dim_date_date_key_seq'::regclass)
    """)

    # Step 2: Recreate legacy indexes (reverse of Step 5)
    op.create_index('ix_games_sport', 'fact_game', ['sport'])
    op.create_index('ix_games_game_type', 'fact_game', ['game_type'])
    op.create_index('ix_games_game_status', 'fact_game', ['game_status'])
    op.create_index('ix_games_game_date', 'fact_game', ['game_date'])

    # Step 3: Revert timestamp columns to TIMESTAMP WITHOUT TIME ZONE (reverse of Step 4)
    # WARNING: This loses timezone information
    op.execute("""
        ALTER TABLE fact_game
        ALTER COLUMN game_date TYPE timestamp
            USING game_date AT TIME ZONE 'UTC',
        ALTER COLUMN game_start_time TYPE timestamp
            USING game_start_time AT TIME ZONE 'UTC',
        ALTER COLUMN game_end_time TYPE timestamp
            USING game_end_time AT TIME ZONE 'UTC',
        ALTER COLUMN created_at TYPE timestamp
            USING created_at AT TIME ZONE 'UTC',
        ALTER COLUMN updated_at TYPE timestamp
            USING updated_at AT TIME ZONE 'UTC'
    """)

    # Step 4: Drop composite team index (reverse of Step 3)
    op.drop_index('idx_fact_game_teams', 'fact_game')

    # Step 5 & 6: Revert sequence to old name with defensive checks
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = 'fact_game_game_key_seq' AND relkind = 'S'
        ) as new_exists,
        EXISTS (
            SELECT 1 FROM pg_class
            WHERE relname = 'games_game_key_seq' AND relkind = 'S'
        ) as old_exists
    """))
    row = result.fetchone()

    if row[0]:  # new_exists: fact_game_game_key_seq exists
        # Rename back to old name
        op.execute("ALTER SEQUENCE fact_game_game_key_seq RENAME TO games_game_key_seq")
        # Update DEFAULT to old name
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('games_game_key_seq'::regclass)
        """)
    elif row[1]:  # old_exists: already has old name
        # Just ensure DEFAULT is set correctly
        op.execute("""
            ALTER TABLE fact_game
            ALTER COLUMN game_key
            SET DEFAULT nextval('games_game_key_seq'::regclass)
        """)
    # If neither exists, downgrade doesn't need to do anything

    # Finally, remove DEFAULT constraint completely (reverse of Step 1)
    # Note: This will break inserts that don't specify game_key
    op.execute("ALTER TABLE fact_game ALTER COLUMN game_key DROP DEFAULT")
