"""Create fact_social_sentiment table

Revision ID: f3c4d5e6f7g8
Revises: f2b3c4d5e6f7
Create Date: 2025-11-16 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Numeric


# revision identifiers, used by Alembic.
revision = 'f3c4d5e6f7g8'
down_revision = 'f2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create fact_social_sentiment table for VADER sentiment analysis results (Story 4-5).

    This fact table links social posts to games with sentiment scores for Epic 5.
    Regular PostgreSQL table (not hypertable) for data volume ~400-1,200 records (Week 3).

    Design Decision: Regular table instead of TimescaleDB hypertable
    - Data volume is low (~20K-60K annual) - hypertable overhead not justified
    - Enables proper FK to stg_social_posts.social_post_key
    - Simpler index management without TimescaleDB partitioning constraints
    - Performance adequate with standard B-tree indexes
    """

    # Create table with all constraints
    op.create_table(
        'fact_social_sentiment',
        sa.Column('sentiment_key', sa.BigInteger(), autoincrement=True, nullable=False),

        # Foreign keys
        sa.Column('game_key', sa.BigInteger(), nullable=False),
        sa.Column('date_key', sa.Integer(), nullable=False),
        sa.Column('social_post_key', sa.BigInteger(), nullable=False),

        # VADER sentiment scores
        sa.Column('sentiment_compound', Numeric(precision=5, scale=4), nullable=False),
        sa.Column('sentiment_positive', Numeric(precision=5, scale=4), nullable=True),
        sa.Column('sentiment_negative', Numeric(precision=5, scale=4), nullable=True),
        sa.Column('sentiment_neutral', Numeric(precision=5, scale=4), nullable=True),

        # Denormalized fields for Epic 5 queries
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('post_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('engagement_score', Numeric(precision=10, scale=2), nullable=True),

        # Metadata
        sa.Column('analyzed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('sentiment_key', name='fact_social_sentiment_pkey'),
        sa.ForeignKeyConstraint(['game_key'], ['fact_game.game_key'], name='fk_sentiment_game_key'),
        sa.ForeignKeyConstraint(['date_key'], ['dim_date.date_key'], name='fk_sentiment_date_key'),

        # Note: No FK to stg_social_posts due to TimescaleDB hypertable limitations
        # Referential integrity enforced at application level (see social.py model)

        # Unique constraint to prevent duplicate sentiment analysis
        sa.UniqueConstraint('social_post_key', name='uq_sentiment_social_post_key'),
    )

    # Create indexes for query optimization
    # Composite index on game_key + created_at for Epic 5 time-based queries
    op.create_index(
        'ix_fact_sentiment_game_key',
        'fact_social_sentiment',
        ['game_key', 'created_at']
    )

    # Index on date_key for date dimension joins
    op.create_index(
        'ix_fact_sentiment_date_key',
        'fact_social_sentiment',
        ['date_key']
    )

    # Index on sentiment_compound for sentiment analytics queries
    op.create_index(
        'ix_fact_sentiment_compound',
        'fact_social_sentiment',
        ['sentiment_compound']
    )

    # Composite index for "top posts by engagement" queries
    # DESC ordering on engagement_score for efficient sorting
    op.execute("""
        CREATE INDEX ix_fact_sentiment_engagement
        ON fact_social_sentiment (engagement_score DESC, sentiment_compound);
    """)


def downgrade():
    """
    Drop fact_social_sentiment table.

    CASCADE will drop all indexes and constraints automatically.
    """
    op.drop_table('fact_social_sentiment')
