"""create raw_reddit_posts hypertable

Revision ID: ac724facbab1
Revises: 4152bfe2efaf
Create Date: 2025-11-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'ac724facbab1'
down_revision = '4152bfe2efaf'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create raw_reddit_posts TimescaleDB hypertable with dual storage:
    - Parsed columns for queryability (post_id, title, score, etc.)
    - raw_json JSONB for complete preservation and future ML

    TimescaleDB configuration:
    - Hypertable on fetched_at (1-day chunks)
    - 90-day retention policy
    - 7-day compression policy
    """

    # Step 1: Create raw_reddit_posts table
    # Note: TimescaleDB hypertables require partitioning column (fetched_at) in all unique indexes
    # Using composite PK (post_id, fetched_at) even though post_id is globally unique
    op.create_table(
        'raw_reddit_posts',
        # Natural key and timestamps (composite primary key for TimescaleDB)
        sa.Column('post_id', sa.String(length=50), nullable=False, comment='Reddit post ID (e.g., t3_abc123)'),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='When we extracted this post'),

        # Subreddit and post creation time
        sa.Column('subreddit', sa.String(length=50), nullable=False, comment='Source subreddit name'),
        sa.Column('post_created_at', sa.DateTime(timezone=True), nullable=False, comment='When Reddit user created post'),

        # Parsed metadata columns (for efficient querying)
        sa.Column('author', sa.String(length=50), nullable=True, comment='Reddit username (null if deleted)'),
        sa.Column('title', sa.Text(), nullable=True, comment='Post title'),
        sa.Column('selftext', sa.Text(), nullable=True, comment='Post body text (for self posts)'),
        sa.Column('score', sa.Integer(), nullable=True, comment='Upvotes - downvotes'),
        sa.Column('num_comments', sa.Integer(), nullable=True, comment='Total comment count'),
        sa.Column('upvote_ratio', sa.Float(), nullable=True, comment='Upvote percentage (0.0-1.0)'),
        sa.Column('permalink', sa.String(length=500), nullable=True, comment='Relative Reddit URL'),
        sa.Column('flair_text', sa.String(length=100), nullable=True, comment='Post flair (for filtering)'),
        sa.Column('post_type', sa.String(length=20), nullable=True, comment='link | self | image | video'),

        # Raw JSON storage (complete preservation)
        sa.Column('raw_json', JSONB, nullable=False, comment='Complete Reddit API response JSON'),

        # Game matching fields (for Story 4-4)
        sa.Column('matched_to_game', sa.Boolean(), nullable=False, server_default='false', comment='Has this been matched to a game?'),
        sa.Column('match_confidence', sa.Numeric(precision=3, scale=2), nullable=True, comment='Game matching confidence (0.00-1.00)'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='When transform layer processed this'),

        # Constraints - composite PK required for TimescaleDB hypertable
        sa.PrimaryKeyConstraint('post_id', 'fetched_at', name='raw_reddit_posts_pkey'),
        sa.ForeignKeyConstraint(['subreddit'], ['dim_subreddit.subreddit_name'], name='fk_raw_reddit_posts_subreddit', ondelete='RESTRICT')
    )

    # Step 2: Convert to TimescaleDB hypertable (1-day chunks)
    op.execute("""
        SELECT create_hypertable(
            'raw_reddit_posts',
            'fetched_at',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)

    # Step 3: Add indexes for query performance
    # Index on post_id (unique already enforced by constraint)
    op.create_index('ix_raw_reddit_posts_post_id', 'raw_reddit_posts', ['post_id'])

    # Index on subreddit for filtering
    op.create_index('ix_raw_reddit_posts_subreddit', 'raw_reddit_posts', ['subreddit'])

    # Index on post_created_at for chronological queries
    op.create_index('ix_raw_reddit_posts_post_created_at', 'raw_reddit_posts', ['post_created_at'])

    # Partial index for unmatched posts (Story 4-4 will query this heavily)
    op.execute("""
        CREATE INDEX ix_raw_reddit_posts_unmatched
        ON raw_reddit_posts (subreddit, post_created_at)
        WHERE matched_to_game = FALSE;
    """)

    # GIN index on raw_json for JSONB queries (future analytics)
    op.execute("""
        CREATE INDEX ix_raw_reddit_posts_raw_json_gin
        ON raw_reddit_posts USING GIN (raw_json);
    """)

    # Step 4: Add TimescaleDB retention policy (90 days)
    op.execute("""
        SELECT add_retention_policy(
            'raw_reddit_posts',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );
    """)

    # Step 5: Enable compression on hypertable
    op.execute("""
        ALTER TABLE raw_reddit_posts SET (
            timescaledb.compress = true,
            timescaledb.compress_segmentby = 'subreddit'
        );
    """)

    # Step 6: Add compression policy (compress chunks older than 7 days)
    op.execute("""
        SELECT add_compression_policy(
            'raw_reddit_posts',
            INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)


def downgrade():
    """
    Reverse all operations to remove raw_reddit_posts hypertable.
    """

    # Drop the hypertable (CASCADE removes chunks, policies, etc.)
    op.execute("DROP TABLE IF EXISTS raw_reddit_posts CASCADE;")
