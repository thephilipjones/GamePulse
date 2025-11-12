"""refactor to dimensional model with surrogate keys

Revision ID: d115685a3652
Revises: 61ebb6c6c0da
Create Date: 2025-11-12 04:11:12.664396

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'd115685a3652'
down_revision = '61ebb6c6c0da'
branch_labels = None
depends_on = None


def upgrade():
    """
    Refactor schema from normalized to dimensional model with surrogate keys.

    Steps:
    1. Add surrogate keys and SCD Type 2 fields to teams
    2. Flatten team_groups into teams
    3. Rename teams → dim_team
    4. Make team_key the new PK
    5. Add game_key to games
    6. Add team_key FKs to games
    7. Rename games → fact_game
    8. Make game_key the new PK
    9. Add indexes
    10. Drop team_groups and team_rivalries tables
    """

    # Step 1: Add surrogate key and SCD Type 2 fields to teams
    op.add_column('teams', sa.Column('team_key', sa.Integer(), autoincrement=True, nullable=True))
    op.add_column('teams', sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('teams', sa.Column('valid_from', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')))
    op.add_column('teams', sa.Column('valid_to', sa.TIMESTAMP(), nullable=True))

    # Create sequence for team_key BEFORE using it
    op.execute("CREATE SEQUENCE IF NOT EXISTS teams_team_key_seq OWNED BY teams.team_key")

    # Populate team_key with sequential values (can't use SERIAL on existing table)
    op.execute("UPDATE teams SET team_key = nextval('teams_team_key_seq'::regclass)")

    # Set sequence to correct value
    op.execute("SELECT setval('teams_team_key_seq', (SELECT MAX(team_key) FROM teams))")

    # Make team_key NOT NULL
    op.alter_column('teams', 'team_key', nullable=False)

    # Set DEFAULT constraint for team_key to use sequence (fixes Story 2-3b batch upsert)
    op.execute("ALTER TABLE teams ALTER COLUMN team_key SET DEFAULT nextval('teams_team_key_seq'::regclass)")

    # Step 2: Flatten team_groups into teams (add team_group_name column)
    op.add_column('teams', sa.Column('team_group_name', sa.VARCHAR(100), nullable=True))

    # Populate team_group_name from team_groups table
    op.execute("""
        UPDATE teams t
        SET team_group_name = tg.team_group_name
        FROM team_groups tg
        WHERE t.team_group_id = tg.team_group_id
    """)

    # Remove FK constraint on team_group_id (will become simple VARCHAR)
    op.drop_constraint('teams_team_group_id_fkey', 'teams', type_='foreignkey')

    # Step 3: Rename teams → dim_team
    op.rename_table('teams', 'dim_team')

    # Step 3.5: Drop FK constraints from other tables before changing PK
    # (games and team_rivalries reference teams.team_id, which blocks PK changes)
    op.drop_constraint('games_home_team_id_fkey', 'games', type_='foreignkey')
    op.drop_constraint('games_away_team_id_fkey', 'games', type_='foreignkey')
    op.drop_constraint('team_rivalries_team_a_id_fkey', 'team_rivalries', type_='foreignkey')
    op.drop_constraint('team_rivalries_team_b_id_fkey', 'team_rivalries', type_='foreignkey')

    # Step 4: Make team_key the new PK (drop old PK on team_id first)
    op.drop_constraint('teams_pkey', 'dim_team', type_='primary')
    op.create_primary_key('dim_team_pkey', 'dim_team', ['team_key'])
    op.create_unique_constraint('dim_team_team_id_key', 'dim_team', ['team_id'])

    # Set DEFAULT constraints for audit timestamps (fixes Story 2-3b batch upsert)
    op.execute("ALTER TABLE dim_team ALTER COLUMN created_at SET DEFAULT NOW()")
    op.execute("ALTER TABLE dim_team ALTER COLUMN updated_at SET DEFAULT NOW()")

    # Step 5: Add game_key to games table
    op.add_column('games', sa.Column('game_key', sa.BigInteger(), autoincrement=True, nullable=True))
    op.add_column('games', sa.Column('game_date_key', sa.Integer(), nullable=True))

    # Populate game_key with sequential values
    op.execute("CREATE SEQUENCE IF NOT EXISTS games_game_key_seq OWNED BY games.game_key")
    op.execute("UPDATE games SET game_key = nextval('games_game_key_seq'::regclass)")
    op.execute("SELECT setval('games_game_key_seq', (SELECT MAX(game_key) FROM games))")

    # Make game_key NOT NULL
    op.alter_column('games', 'game_key', nullable=False)

    # Step 6: Add team_key FKs to games (before renaming columns)
    op.add_column('games', sa.Column('home_team_key', sa.Integer(), nullable=True))
    op.add_column('games', sa.Column('away_team_key', sa.Integer(), nullable=True))

    # Populate team_key FKs from natural keys
    op.execute("""
        UPDATE games g
        SET home_team_key = (SELECT team_key FROM dim_team WHERE team_id = g.home_team_id),
            away_team_key = (SELECT team_key FROM dim_team WHERE team_id = g.away_team_id)
    """)

    # Make FKs NOT NULL and add constraints
    op.alter_column('games', 'home_team_key', nullable=False)
    op.alter_column('games', 'away_team_key', nullable=False)
    op.create_foreign_key('fk_games_home_team', 'games', 'dim_team', ['home_team_key'], ['team_key'])
    op.create_foreign_key('fk_games_away_team', 'games', 'dim_team', ['away_team_key'], ['team_key'])

    # Drop old team_id FK columns (data migrated to team_key columns)
    # Note: FK constraints already dropped in step 3.5
    op.drop_column('games', 'home_team_id')
    op.drop_column('games', 'away_team_id')

    # Step 7: Rename games → fact_game
    op.rename_table('games', 'fact_game')

    # Step 8: Make game_key the new PK
    op.drop_constraint('games_pkey', 'fact_game', type_='primary')
    op.create_primary_key('fact_game_pkey', 'fact_game', ['game_key'])
    op.create_unique_constraint('fact_game_game_id_key', 'fact_game', ['game_id'])

    # Step 9: Add indexes for query performance
    op.create_index('ix_fact_game_game_date', 'fact_game', ['game_date'])
    op.create_index('ix_fact_game_game_status', 'fact_game', ['game_status'])
    op.create_index('ix_fact_game_sport', 'fact_game', ['sport'])
    op.create_index('ix_fact_game_game_type', 'fact_game', ['game_type'])

    # Step 10: Drop tables no longer needed
    op.drop_table('team_rivalries')
    op.drop_table('team_groups')


def downgrade():
    """
    Reverse all operations to restore normalized schema.

    Note: This is for development/testing only. Do not use in production
    as it may result in data loss for SCD Type 2 tracked changes.
    """

    # Step 1: Recreate team_groups table from dim_team.team_group_* fields
    op.create_table(
        'team_groups',
        sa.Column('team_group_id', sa.String(), nullable=False),
        sa.Column('team_group_name', sa.String(), nullable=False),
        sa.Column('sport', sa.String(), nullable=False),
        sa.Column('group_type', sa.String(), nullable=False),
        sa.Column('parent_group_id', sa.String(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('team_group_id')
    )

    # Populate team_groups from dim_team
    op.execute("""
        INSERT INTO team_groups (team_group_id, team_group_name, sport, group_type, level, created_at)
        SELECT DISTINCT team_group_id, team_group_name, sport, 'conference', 1, NOW()
        FROM dim_team
        WHERE team_group_id IS NOT NULL
    """)

    # Recreate team_rivalries table (empty)
    op.create_table(
        'team_rivalries',
        sa.Column('rivalry_id', sa.Integer(), nullable=False),
        sa.Column('team_a_id', sa.String(), nullable=False),
        sa.Column('team_b_id', sa.String(), nullable=False),
        sa.Column('rivalry_factor', sa.Float(), nullable=False),
        sa.Column('rivalry_type', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('rivalry_id')
    )

    # Step 2: Drop indexes from fact_game
    op.drop_index('ix_fact_game_game_type', 'fact_game')
    op.drop_index('ix_fact_game_sport', 'fact_game')
    op.drop_index('ix_fact_game_game_status', 'fact_game')
    op.drop_index('ix_fact_game_game_date', 'fact_game')

    # Step 3: Rename fact_game → games
    op.rename_table('fact_game', 'games')

    # Step 4: Restore old PK on game_id
    op.drop_constraint('fact_game_pkey', 'games', type_='primary')
    op.drop_constraint('fact_game_game_id_key', 'games', type_='unique')
    op.create_primary_key('games_pkey', 'games', ['game_id'])

    # Step 5: Add back home_team_id and away_team_id columns
    op.add_column('games', sa.Column('home_team_id', sa.String(), nullable=True))
    op.add_column('games', sa.Column('away_team_id', sa.String(), nullable=True))

    # Step 6: Rename dim_team → teams (temporarily, for FK lookup)
    op.rename_table('dim_team', 'teams_temp')

    # Populate team_id columns from team_key FKs
    op.execute("""
        UPDATE games g
        SET home_team_id = (SELECT team_id FROM teams_temp WHERE team_key = g.home_team_key),
            away_team_id = (SELECT team_id FROM teams_temp WHERE team_key = g.away_team_key)
    """)

    # Make team_id columns NOT NULL
    op.alter_column('games', 'home_team_id', nullable=False)
    op.alter_column('games', 'away_team_id', nullable=False)

    # Drop team_key FK columns
    op.drop_constraint('fk_games_away_team', 'games', type_='foreignkey')
    op.drop_constraint('fk_games_home_team', 'games', type_='foreignkey')
    op.drop_column('games', 'away_team_key')
    op.drop_column('games', 'home_team_key')
    op.drop_column('games', 'game_date_key')
    op.drop_column('games', 'game_key')
    op.execute("DROP SEQUENCE IF EXISTS games_game_key_seq")

    # Step 7: Rename teams_temp → teams
    op.rename_table('teams_temp', 'teams')

    # Step 8: Restore old PK on team_id
    op.drop_constraint('dim_team_pkey', 'teams', type_='primary')
    op.drop_constraint('dim_team_team_id_key', 'teams', type_='unique')
    op.create_primary_key('teams_pkey', 'teams', ['team_id'])

    # Step 9: Add FK constraint back on team_group_id
    op.create_foreign_key('teams_team_group_id_fkey', 'teams', 'team_groups', ['team_group_id'], ['team_group_id'])

    # Step 10: Drop flattened team_group_name column
    op.drop_column('teams', 'team_group_name')

    # Step 11: Remove SCD Type 2 fields
    # Drop DEFAULT constraints before dropping columns (reverse of upgrade)
    op.execute("ALTER TABLE teams ALTER COLUMN team_key DROP DEFAULT")
    op.execute("ALTER TABLE teams ALTER COLUMN created_at DROP DEFAULT")
    op.execute("ALTER TABLE teams ALTER COLUMN updated_at DROP DEFAULT")

    op.drop_column('teams', 'valid_to')
    op.drop_column('teams', 'valid_from')
    op.drop_column('teams', 'is_current')
    op.drop_column('teams', 'team_key')
    op.execute("DROP SEQUENCE IF EXISTS teams_team_key_seq")

    # Step 12: Add back FK constraints on games and team_rivalries
    op.create_foreign_key('games_home_team_id_fkey', 'games', 'teams', ['home_team_id'], ['team_id'])
    op.create_foreign_key('games_away_team_id_fkey', 'games', 'teams', ['away_team_id'], ['team_id'])
    op.create_foreign_key('team_rivalries_team_a_id_fkey', 'team_rivalries', 'teams', ['team_a_id'], ['team_id'])
    op.create_foreign_key('team_rivalries_team_b_id_fkey', 'team_rivalries', 'teams', ['team_b_id'], ['team_id'])
