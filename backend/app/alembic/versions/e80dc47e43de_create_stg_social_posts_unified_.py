"""create_stg_social_posts_unified_transform

Revision ID: e80dc47e43de
Revises: bbbc5e8428a3
Create Date: 2025-11-16 15:38:13.535215

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e80dc47e43de"
down_revision = "bbbc5e8428a3"
branch_labels = None
depends_on = None


def upgrade():
    """
    Create stg_social_posts unified transform layer (Story 4-4).

    Creates TimescaleDB hypertable for Reddit + Bluesky posts with:
    - Composite PK (platform, post_id) for cross-platform deduplication
    - Engagement scoring for prioritization
    - Game matching metadata
    - 90-day retention with 7-day compression
    """

    # Step 1: Create stg_social_posts table
    op.create_table(
        "stg_social_posts",
        # Composite PK columns
        sa.Column(
            "platform",
            sa.String(length=20),
            nullable=False,
            comment="Source platform: reddit or bluesky",
        ),
        sa.Column(
            "post_id",
            sa.String(length=300),
            nullable=False,
            comment="Platform-specific post ID (Reddit: t3_abc, Bluesky: URI)",
        ),
        # Temporal columns
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When user created post (partitioning column for TimescaleDB)",
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When we extracted this post",
        ),
        # Normalized post content
        sa.Column(
            "author_handle",
            sa.String(length=100),
            nullable=True,
            comment="Platform-specific author handle",
        ),
        sa.Column(
            "post_text",
            sa.Text(),
            nullable=True,
            comment="Post text content (Reddit: title + selftext, Bluesky: post_text)",
        ),
        # Engagement metrics
        sa.Column(
            "engagement_score",
            sa.Float(),
            nullable=False,
            comment="Platform-normalized engagement (Reddit: score + comments, Bluesky: likes + replies)",
        ),
        # Game matching metadata
        sa.Column(
            "matched_to_game",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Has this been matched to a game?",
        ),
        sa.Column(
            "match_confidence",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            comment="Game matching confidence (0.00-1.00)",
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When transform layer processed this",
        ),
        # Raw JSON for debugging and ML
        sa.Column(
            "raw_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Original platform JSON for debugging and future ML",
        ),
        # Composite primary key (must include created_at for TimescaleDB hypertable)
        sa.PrimaryKeyConstraint("platform", "post_id", "created_at", name="stg_social_posts_pkey"),
    )

    # Step 2: Create indexes for query performance
    op.create_index(
        "ix_stg_social_posts_created_at",
        "stg_social_posts",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_stg_social_posts_processed_at",
        "stg_social_posts",
        ["processed_at"],
        unique=False,
        postgresql_where=sa.text("processed_at IS NULL"),  # Partial index for unprocessed posts
    )
    op.create_index(
        "ix_stg_social_posts_matched",
        "stg_social_posts",
        ["matched_to_game", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_stg_social_posts_raw_json_gin",
        "stg_social_posts",
        ["raw_json"],
        unique=False,
        postgresql_using="gin",
    )

    # Step 3: Convert to TimescaleDB hypertable (partitioned by created_at)
    op.execute(
        """
        SELECT create_hypertable(
            'stg_social_posts',
            'created_at',
            chunk_time_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        );
        """
    )

    # Step 4: Add retention policy (90 days, matching raw_bluesky_posts)
    op.execute(
        """
        SELECT add_retention_policy(
            'stg_social_posts',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );
        """
    )

    # Step 5: Add compression policy (compress after 7 days)
    op.execute(
        """
        ALTER TABLE stg_social_posts SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'platform'
        );
        """
    )
    op.execute(
        """
        SELECT add_compression_policy(
            'stg_social_posts',
            INTERVAL '7 days',
            if_not_exists => TRUE
        );
        """
    )


def downgrade():
    """
    Drop stg_social_posts table and associated TimescaleDB policies.

    Note: Dropping a hypertable automatically removes retention and compression policies.
    """
    op.drop_index("ix_stg_social_posts_raw_json_gin", table_name="stg_social_posts")
    op.drop_index("ix_stg_social_posts_matched", table_name="stg_social_posts")
    op.drop_index("ix_stg_social_posts_processed_at", table_name="stg_social_posts")
    op.drop_index("ix_stg_social_posts_created_at", table_name="stg_social_posts")
    op.drop_table("stg_social_posts")
