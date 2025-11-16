"""create_dim_keyword_and_migrate_subreddits

Revision ID: bbbc5e8428a3
Revises: t2h54vhunleh
Create Date: 2025-11-16 09:43:16.704677

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbbc5e8428a3'
down_revision = 't2h54vhunleh'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create unified dim_keyword table to replace dim_subreddit.

    Migrates existing subreddit data and adds Bluesky hashtag support.
    Follows dim_subreddit pattern but adds platform and keyword_type columns
    for future extensibility (e.g., Reddit user searches, Bluesky custom feeds).

    Tables:
    1. dim_keyword - Unified keyword configuration (replaces dim_subreddit)
    2. keyword_sport_mapping - Many-to-many junction table (replaces subreddit_sport_mapping)

    Migration Strategy:
    - Create new tables alongside existing ones (parallel tables pattern)
    - Migrate data from dim_subreddit → dim_keyword
    - Seed Bluesky hashtags
    - Update raw_reddit_posts FK to point to dim_keyword
    - Keep old tables for rollback safety (drop in future migration)
    """

    # Step 1: Create dim_keyword table (generalized from dim_subreddit)
    op.create_table(
        'dim_keyword',
        sa.Column('keyword_key', sa.BigInteger(), nullable=False, autoincrement=True,
                  comment='Surrogate key'),
        sa.Column('keyword_value', sa.String(length=100), nullable=False,
                  comment='Keyword text (subreddit name or hashtag without prefix)'),
        sa.Column('platform', sa.String(length=20), nullable=False,
                  comment='Platform: reddit or bluesky'),
        sa.Column('keyword_type', sa.String(length=20), nullable=False,
                  comment='Type: subreddit, hashtag, user_search, custom_feed'),
        sa.Column('url', sa.String(length=300), nullable=True,
                  comment='Platform URL (required for Reddit, null for Bluesky hashtags)'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true',
                  comment='Enable/disable polling'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('keyword_key', name='dim_keyword_pkey'),
        sa.UniqueConstraint('platform', 'keyword_value', name='uq_dim_keyword_platform_value'),
        sa.CheckConstraint("platform IN ('reddit', 'bluesky')", name='ck_dim_keyword_platform'),
        sa.CheckConstraint("keyword_type IN ('subreddit', 'hashtag', 'user_search', 'custom_feed')",
                          name='ck_dim_keyword_type')
    )
    op.create_index('ix_dim_keyword_is_active', 'dim_keyword', ['is_active'])
    op.create_index('ix_dim_keyword_platform_type', 'dim_keyword', ['platform', 'keyword_type'])

    # Step 2: Create keyword_sport_mapping junction table
    op.create_table(
        'keyword_sport_mapping',
        sa.Column('keyword_key', sa.BigInteger(), nullable=False),
        sa.Column('sport_key', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['keyword_key'], ['dim_keyword.keyword_key'],
                               name='fk_keyword_mapping_keyword', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sport_key'], ['dim_sport.sport_key'],
                               name='fk_keyword_mapping_sport', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('keyword_key', 'sport_key', name='keyword_sport_mapping_pkey')
    )

    # Step 3: Migrate data from dim_subreddit → dim_keyword
    # Map all existing subreddits with platform='reddit', keyword_type='subreddit'
    op.execute("""
        INSERT INTO dim_keyword (keyword_value, platform, keyword_type, url, is_active, created_at, updated_at)
        SELECT
            subreddit_name AS keyword_value,
            'reddit' AS platform,
            'subreddit' AS keyword_type,
            reddit_url AS url,
            is_active,
            created_at,
            updated_at
        FROM dim_subreddit
    """)

    # Step 4: Migrate sport mappings from subreddit_sport_mapping → keyword_sport_mapping
    op.execute("""
        INSERT INTO keyword_sport_mapping (keyword_key, sport_key, created_at)
        SELECT
            k.keyword_key,
            m.sport_key,
            m.created_at
        FROM dim_keyword k
        JOIN dim_subreddit s ON s.subreddit_name = k.keyword_value AND k.platform = 'reddit'
        JOIN subreddit_sport_mapping m ON m.subreddit_key = s.subreddit_key
    """)

    # Step 5: Seed Bluesky hashtags (platform='bluesky', keyword_type='hashtag')
    bluesky_hashtags = [
        'CollegeBasketball',
        'MarchMadness',
        'NCAAM'
    ]

    for hashtag in bluesky_hashtags:
        op.execute(f"""
            INSERT INTO dim_keyword (keyword_value, platform, keyword_type, url, is_active)
            VALUES ('{hashtag}', 'bluesky', 'hashtag', NULL, true)
        """)

    # Step 6: Map Bluesky hashtags to ncaam sport
    op.execute("""
        INSERT INTO keyword_sport_mapping (keyword_key, sport_key)
        SELECT k.keyword_key, sp.sport_key
        FROM dim_keyword k
        CROSS JOIN dim_sport sp
        WHERE k.platform = 'bluesky'
          AND k.keyword_type = 'hashtag'
          AND sp.sport_code = 'ncaam'
    """)

    # Step 7: Drop raw_reddit_posts FK constraint to dim_subreddit
    # Note: We don't create a new FK to dim_keyword because keyword_value is not unique
    # alone (it's part of composite unique constraint with platform). Application-level
    # validation will ensure referential integrity.
    op.drop_constraint('fk_raw_reddit_posts_subreddit', 'raw_reddit_posts', type_='foreignkey')

    # Note: dim_subreddit and subreddit_sport_mapping tables are kept for rollback safety
    # They will be dropped in a future migration after thorough testing (1-2 weeks)


def downgrade():
    """
    Reverse dim_keyword migration and restore dim_subreddit FK.

    WARNING: This will lose any new Bluesky hashtag data added after migration.
    """

    # Step 1: Restore raw_reddit_posts FK to dim_subreddit
    op.create_foreign_key(
        'fk_raw_reddit_posts_subreddit',
        'raw_reddit_posts', 'dim_subreddit',
        ['subreddit'], ['subreddit_name'],
        ondelete='RESTRICT'
    )

    # Step 2: Drop keyword tables (data loss for Bluesky hashtags!)
    op.drop_table('keyword_sport_mapping')
    op.drop_table('dim_keyword')

    # dim_subreddit and subreddit_sport_mapping are still intact, so FK restore works
