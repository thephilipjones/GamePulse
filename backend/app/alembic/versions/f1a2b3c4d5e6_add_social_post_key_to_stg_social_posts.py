"""Add social_post_key to stg_social_posts

Revision ID: f1a2b3c4d5e6
Revises: e80dc47e43de
Create Date: 2025-11-16 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e80dc47e43de'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add social_post_key surrogate key to stg_social_posts table.

    This enables simple foreign key relationships from fact_social_sentiment.
    Maintains existing composite PK (platform, post_id, created_at) as unique constraint.

    TimescaleDB Constraint: Hypertables with columnstore cannot have columns with
    non-constant default expressions. Workaround: Add column without default, then backfill.

    Steps:
    1. Create sequence for social_post_key
    2. Add social_post_key column (nullable, no default)
    3. Backfill existing rows with sequence values
    4. Set default for future inserts
    5. Set NOT NULL constraint
    6. Create unique index for FK lookups
    """

    # Step 1: Create sequence
    op.execute("""
        CREATE SEQUENCE stg_social_posts_social_post_key_seq;
    """)

    # Step 2: Add column without default (TimescaleDB hypertable constraint)
    op.add_column(
        'stg_social_posts',
        sa.Column('social_post_key', sa.BigInteger(), nullable=True)
    )

    # Step 3: Backfill existing rows with unique sequence values
    op.execute("""
        UPDATE stg_social_posts
        SET social_post_key = nextval('stg_social_posts_social_post_key_seq');
    """)

    # Step 4: Set default for future inserts (after initial backfill)
    op.execute("""
        ALTER TABLE stg_social_posts
        ALTER COLUMN social_post_key SET DEFAULT nextval('stg_social_posts_social_post_key_seq');
    """)

    # Step 5: Make column NOT NULL and set sequence ownership
    op.execute("""
        ALTER TABLE stg_social_posts
        ALTER COLUMN social_post_key SET NOT NULL;
    """)

    op.execute("""
        ALTER SEQUENCE stg_social_posts_social_post_key_seq
        OWNED BY stg_social_posts.social_post_key;
    """)

    # Step 6: Create unique index for FK lookups from fact_social_sentiment
    # Note: TimescaleDB requires partitioning column (created_at) in unique indexes
    op.create_index(
        'ix_stg_social_posts_social_post_key',
        'stg_social_posts',
        ['social_post_key', 'created_at'],
        unique=True
    )


def downgrade():
    """
    Remove social_post_key column from stg_social_posts table.

    Steps:
    1. Drop index
    2. Drop column (CASCADE will drop sequence)
    """

    # Step 1: Drop index
    op.drop_index('ix_stg_social_posts_social_post_key', 'stg_social_posts')

    # Step 2: Drop column and sequence
    op.drop_column('stg_social_posts', 'social_post_key')

    # Sequence will be dropped automatically due to OWNED BY
