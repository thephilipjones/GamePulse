"""Add matched_teams to stg_social_posts

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2025-11-16 18:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers, used by Alembic.
revision = 'f2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add matched_teams column to stg_social_posts table.

    This stores the team IDs matched during transform layer (Story 4-4).
    Enables game_key resolution in sentiment analysis (Story 4-5) without re-running matching logic.

    Steps:
    1. Add matched_teams TEXT[] column (nullable)
    2. Backfill empty arrays for existing rows where matched_to_game = FALSE
    3. Create GIN index for array searches (if needed in future)

    Note: Transform layer will populate this for new posts going forward.
    Existing posts can be backfilled by re-running transform, or left NULL.
    """

    # Step 1: Add matched_teams column (TEXT[] for team_id values like ["ncaam_duke", "ncaam_unc"])
    op.add_column(
        'stg_social_posts',
        sa.Column('matched_teams', ARRAY(sa.String(length=50)), nullable=True)
    )

    # Step 2: Backfill empty arrays for existing rows where no game was matched
    # Posts with matched_to_game = TRUE will need re-running transform to populate actual teams
    op.execute("""
        UPDATE stg_social_posts
        SET matched_teams = ARRAY[]::TEXT[]
        WHERE matched_to_game = FALSE;
    """)

    # Step 3: Create GIN index for array searches (useful for "contains" queries)
    # Note: May not be needed if we only query matched_teams by row, but good for analytics
    op.execute("""
        CREATE INDEX ix_stg_social_posts_matched_teams_gin
        ON stg_social_posts USING gin(matched_teams);
    """)


def downgrade():
    """
    Remove matched_teams column from stg_social_posts table.

    Steps:
    1. Drop GIN index
    2. Drop column
    """

    # Step 1: Drop GIN index
    op.execute("DROP INDEX IF EXISTS ix_stg_social_posts_matched_teams_gin;")

    # Step 2: Drop matched_teams column
    op.drop_column('stg_social_posts', 'matched_teams')
