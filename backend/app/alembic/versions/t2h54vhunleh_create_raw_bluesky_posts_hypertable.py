"""create raw_bluesky_posts hypertable

Revision ID: t2h54vhunleh
Revises: ac724facbab1
Create Date: 2025-11-15 18:37:44.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 't2h54vhunleh'
down_revision = 'ac724facbab1'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create raw_bluesky_posts TimescaleDB hypertable with dual storage:
    - Parsed columns for queryability (post_uri, text, author, etc.)
    - raw_json JSONB for complete preservation and future ML

    TimescaleDB configuration:
    - Hypertable on created_at (1-day chunks)
    - 90-day retention policy
    - 7-day compression policy
    """

    # Step 1: Create raw_bluesky_posts table
    # Note: TimescaleDB requires partitioning column in all unique indexes
    # Using composite PK (post_uri, created_at) even though post_uri is globally unique
    # atproto URIs have format: at://did:plc:abc123.../app.bsky.feed.post/xyz456...
    op.create_table(
        'raw_bluesky_posts',
        # Composite primary key columns (required by TimescaleDB hypertable)
        sa.Column('post_uri', sa.String(length=300), nullable=False, comment='atproto URI (e.g., at://did:plc:abc/app.bsky.feed.post/xyz)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, comment='Post creation time from Bluesky (partitioning column)'),

        # Content identifier (immutable hash)
        sa.Column('post_cid', sa.String(length=100), nullable=False, comment='Content ID (CID) - immutable hash of post record'),

        # Timestamps
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='When we extracted this post'),

        # Author information
        sa.Column('author_did', sa.String(length=100), nullable=False, comment='Decentralized identifier (DID) of post author'),
        sa.Column('author_handle', sa.String(length=100), nullable=True, comment='Human-readable handle (e.g., user.bsky.social)'),

        # Post content
        sa.Column('post_text', sa.Text(), nullable=True, comment='Post text content'),

        # Raw JSON storage (complete preservation)
        sa.Column('raw_json', JSONB, nullable=False, comment='Complete Bluesky post JSON for future analysis and ML'),

        # Game matching fields (for Story 4-4)
        sa.Column('matched_to_game', sa.Boolean(), nullable=False, server_default='false', comment='Has this been matched to a game?'),
        sa.Column('match_confidence', sa.Numeric(precision=3, scale=2), nullable=True, comment='Game matching confidence (0.00-1.00)'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='When transform layer processed this'),

        # Constraints - composite PK required for TimescaleDB hypertable
        sa.PrimaryKeyConstraint('post_uri', 'created_at', name='raw_bluesky_posts_pkey'),
    )

    # Step 2: Convert to TimescaleDB hypertable (1-day chunks on created_at)
    # Note: Using created_at instead of fetched_at as partitioning column for better query performance
    op.execute("""
        SELECT create_hypertable(
            'raw_bluesky_posts',
            'created_at',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
    """)

    # Step 3: Add indexes for query performance
    # Index on fetched_at for incremental extraction queries
    op.create_index('ix_raw_bluesky_posts_fetched_at', 'raw_bluesky_posts', ['fetched_at'], postgresql_using='btree')

    # Index on created_at (already indexed as partitioning column, but explicit for clarity)
    op.create_index('ix_raw_bluesky_posts_created_at', 'raw_bluesky_posts', ['created_at'])

    # Index on author_did for author-based queries
    op.create_index('ix_raw_bluesky_posts_author_did', 'raw_bluesky_posts', ['author_did'])

    # Partial index for unmatched posts (Story 4-4 will query this heavily)
    op.execute("""
        CREATE INDEX ix_raw_bluesky_posts_unmatched
        ON raw_bluesky_posts (created_at)
        WHERE matched_to_game = FALSE;
    """)

    # GIN index on raw_json for JSONB queries (future analytics)
    op.execute("""
        CREATE INDEX ix_raw_bluesky_posts_raw_json_gin
        ON raw_bluesky_posts USING GIN (raw_json);
    """)

    # Step 4: Add TimescaleDB retention policy (90 days)
    op.execute("""
        SELECT add_retention_policy(
            'raw_bluesky_posts',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );
    """)

    # Step 5: Enable compression on hypertable
    # Note: No segmentby column (unlike Reddit's subreddit) since hashtags aren't stored in columns
    # Compression will still work, just without segmentation
    op.execute("""
        ALTER TABLE raw_bluesky_posts SET (
            timescaledb.compress = true
        );
    """)

    # Step 6: Add compression policy (compress chunks older than 7 days)
    op.execute("""
        SELECT add_compression_policy(
            'raw_bluesky_posts',
            INTERVAL '7 days',
            if_not_exists => TRUE
        );
    """)


def downgrade():
    """
    Reverse all operations to remove raw_bluesky_posts hypertable.
    """

    # Drop the hypertable (CASCADE removes chunks, policies, etc.)
    op.execute("DROP TABLE IF EXISTS raw_bluesky_posts CASCADE;")
