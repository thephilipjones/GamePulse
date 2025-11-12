"""Add espn_team_id to dim_team

Revision ID: de4a5062ce6e
Revises: d115685a3652
Create Date: 2025-11-12 04:53:24.007352

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'de4a5062ce6e'
down_revision = 'd115685a3652'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add espn_team_id column to dim_team table and backfill from team_id.

    Steps:
    1. Add espn_team_id column (VARCHAR, nullable)
    2. Backfill by extracting numeric portion from team_id
    3. Create index on espn_team_id for lookup performance
    """

    # Step 1: Add espn_team_id column
    op.add_column('dim_team', sa.Column('espn_team_id', sa.String(), nullable=True))

    # Step 2: Backfill existing rows by extracting ESPN ID from team_id
    # Format: "ncaam_150" → espn_team_id = "150"
    op.execute("""
        UPDATE dim_team
        SET espn_team_id = SPLIT_PART(team_id, '_', 2)
        WHERE team_id LIKE '%_%'
    """)

    # Step 3: Create index on espn_team_id for lookup performance
    op.create_index('ix_dim_team_espn_team_id', 'dim_team', ['espn_team_id'])


def downgrade():
    """
    Remove espn_team_id column from dim_team table.

    Steps:
    1. Drop index (if exists)
    2. Drop column (if exists)
    """

    # Step 1: Drop index (if exists)
    op.drop_index('ix_dim_team_espn_team_id', 'dim_team', if_exists=True)

    # Step 2: Drop espn_team_id column
    op.drop_column('dim_team', 'espn_team_id')
