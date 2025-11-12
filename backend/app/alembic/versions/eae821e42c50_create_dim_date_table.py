"""create dim_date table

Revision ID: eae821e42c50
Revises: de4a5062ce6e
Create Date: 2025-11-12 05:52:55.501012

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'eae821e42c50'
down_revision = 'de4a5062ce6e'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create dim_date dimension table with NCAA-specific attributes.

    Steps:
    1. Create dim_date table with surrogate key (date_key) and natural key (full_date)
    2. Add Kimball standard date attributes
    3. Add NCAA-specific attributes (is_march_madness, tournament_round)
    4. Create indexes for query performance
    5. Add FK constraint from fact_game.game_date_key to dim_date.date_key
    6. Add index on fact_game.game_date_key for join performance
    """

    # Step 1: Create dim_date table
    op.create_table(
        'dim_date',
        sa.Column('date_key', sa.Integer(), nullable=False, comment='Surrogate key in YYYYMMDD format'),
        sa.Column('full_date', sa.Date(), nullable=False, comment='Natural key - the actual date'),

        # Kimball standard date attributes
        sa.Column('day_of_week', sa.Integer(), nullable=False, comment='ISO 8601: Monday=1, Sunday=7'),
        sa.Column('day_name', sa.String(length=9), nullable=False, comment='Monday, Tuesday, etc.'),
        sa.Column('day_of_month', sa.Integer(), nullable=False, comment='1-31'),
        sa.Column('month', sa.Integer(), nullable=False, comment='1-12'),
        sa.Column('month_name', sa.String(length=9), nullable=False, comment='January, February, etc.'),
        sa.Column('quarter', sa.Integer(), nullable=False, comment='1-4'),
        sa.Column('year', sa.Integer(), nullable=False, comment='Four-digit year'),
        sa.Column('is_weekend', sa.Boolean(), nullable=False, comment='Saturday or Sunday'),

        # NCAA-specific attributes
        sa.Column('is_march_madness', sa.Boolean(), nullable=False, comment='Falls within March Madness tournament window'),
        sa.Column('tournament_round', sa.String(length=50), nullable=True, comment='First Four, Round of 64, etc. Null for off days'),

        sa.PrimaryKeyConstraint('date_key', name='dim_date_pkey')
    )

    # Step 2: Create indexes for query performance
    # Unique index on natural key (full_date)
    op.create_index('ix_dim_date_full_date', 'dim_date', ['full_date'], unique=True)

    # Index on year for annual queries
    op.create_index('ix_dim_date_year', 'dim_date', ['year'])

    # Composite index on year+month for monthly queries
    op.create_index('ix_dim_date_year_month', 'dim_date', ['year', 'month'])

    # Index on is_march_madness for tournament queries
    op.create_index('ix_dim_date_is_march_madness', 'dim_date', ['is_march_madness'])

    # Step 3: Add FK constraint from fact_game.game_date_key to dim_date.date_key
    # Note: game_date_key column already exists (added in Story 2-3a), just adding FK constraint
    op.create_foreign_key(
        'fk_fact_game_game_date',
        'fact_game',
        'dim_date',
        ['game_date_key'],
        ['date_key'],
        ondelete='SET NULL'  # If date removed, set FK to NULL
    )

    # Step 4: Add index on fact_game.game_date_key for join performance
    op.create_index('ix_fact_game_game_date_key', 'fact_game', ['game_date_key'])


def downgrade():
    """
    Reverse all operations to remove dim_date table.
    """

    # Step 1: Drop index on fact_game.game_date_key
    op.drop_index('ix_fact_game_game_date_key', 'fact_game')

    # Step 2: Drop FK constraint from fact_game
    op.drop_constraint('fk_fact_game_game_date', 'fact_game', type_='foreignkey')

    # Step 3: Drop indexes on dim_date
    op.drop_index('ix_dim_date_is_march_madness', 'dim_date')
    op.drop_index('ix_dim_date_year_month', 'dim_date')
    op.drop_index('ix_dim_date_year', 'dim_date')
    op.drop_index('ix_dim_date_full_date', 'dim_date')

    # Step 4: Drop dim_date table
    op.drop_table('dim_date')
