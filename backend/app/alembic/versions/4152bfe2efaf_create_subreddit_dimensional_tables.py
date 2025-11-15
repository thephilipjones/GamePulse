"""create subreddit dimensional tables

Revision ID: 4152bfe2efaf
Revises: e85b1a0dd26b
Create Date: 2025-11-15 19:38:36.339714

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision = '4152bfe2efaf'
down_revision = 'e85b1a0dd26b'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create dimensional tables for Reddit subreddit configuration.

    Tables:
    1. dim_sport - Sport reference dimension (NCAAM, NCAAF, NFL, etc.)
    2. dim_subreddit - Subreddit configuration dimension
    3. subreddit_sport_mapping - Many-to-many junction table

    Seed data enables Story 4-4 to match Reddit posts to games via sport.
    """

    # Step 1: Create dim_sport table
    op.create_table(
        'dim_sport',
        sa.Column('sport_key', sa.Integer(), nullable=False, autoincrement=True, comment='Surrogate key'),
        sa.Column('sport_code', sa.String(length=10), nullable=False, comment='Lowercase sport code (ncaam, nfl)'),
        sa.Column('sport_name', sa.String(length=50), nullable=False, comment='Display name (NCAA Men\'s Basketball)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('sport_key', name='dim_sport_pkey'),
        sa.UniqueConstraint('sport_code', name='uq_dim_sport_code')
    )
    op.create_index('ix_dim_sport_sport_code', 'dim_sport', ['sport_code'])

    # Step 2: Create dim_subreddit table
    op.create_table(
        'dim_subreddit',
        sa.Column('subreddit_key', sa.BigInteger(), nullable=False, autoincrement=True, comment='Surrogate key'),
        sa.Column('subreddit_name', sa.String(length=50), nullable=False, comment='Subreddit name without /r/ prefix'),
        sa.Column('reddit_url', sa.String(length=200), nullable=False, comment='Full Reddit URL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Enable/disable polling'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('subreddit_key', name='dim_subreddit_pkey'),
        sa.UniqueConstraint('subreddit_name', name='uq_dim_subreddit_name')
    )
    op.create_index('ix_dim_subreddit_name', 'dim_subreddit', ['subreddit_name'])
    op.create_index('ix_dim_subreddit_is_active', 'dim_subreddit', ['is_active'])

    # Step 3: Create subreddit_sport_mapping junction table
    op.create_table(
        'subreddit_sport_mapping',
        sa.Column('subreddit_key', sa.BigInteger(), nullable=False),
        sa.Column('sport_key', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['subreddit_key'], ['dim_subreddit.subreddit_key'], name='fk_mapping_subreddit', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sport_key'], ['dim_sport.sport_key'], name='fk_mapping_sport', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('subreddit_key', 'sport_key', name='subreddit_sport_mapping_pkey')
    )

    # Step 4: Seed dim_sport with initial sports
    sports_data = [
        {'sport_code': 'ncaam', 'sport_name': 'NCAA Men''s Basketball'},
        {'sport_code': 'ncaaw', 'sport_name': 'NCAA Women''s Basketball'},
        {'sport_code': 'ncaaf', 'sport_name': 'NCAA Football'},
        {'sport_code': 'nfl', 'sport_name': 'NFL'},
        {'sport_code': 'nba', 'sport_name': 'NBA'},
        {'sport_code': 'wnba', 'sport_name': 'WNBA'},
        {'sport_code': 'mlb', 'sport_name': 'MLB'},
        {'sport_code': 'nhl', 'sport_name': 'NHL'},
    ]

    # Use explicit INSERT to maintain sport_key consistency
    for sport in sports_data:
        # Use double quotes to escape apostrophes in SQL
        sport_name_escaped = sport['sport_name'].replace("'", "''")
        op.execute(f"""
            INSERT INTO dim_sport (sport_code, sport_name)
            VALUES ('{sport['sport_code']}', '{sport_name_escaped}')
        """)

    # Step 5: Seed dim_subreddit with initial subreddits
    subreddits_data = [
        {'name': 'CollegeBasketball', 'url': 'https://www.reddit.com/r/CollegeBasketball'},
        {'name': 'CFB', 'url': 'https://www.reddit.com/r/CFB'},
        {'name': 'sports', 'url': 'https://www.reddit.com/r/sports'},
    ]

    for sub in subreddits_data:
        op.execute(f"""
            INSERT INTO dim_subreddit (subreddit_name, reddit_url, is_active)
            VALUES ('{sub['name']}', '{sub['url']}', true)
        """)

    # Step 6: Seed subreddit_sport_mapping (many-to-many relationships)
    # CollegeBasketball -> NCAAM only
    op.execute("""
        INSERT INTO subreddit_sport_mapping (subreddit_key, sport_key)
        SELECT s.subreddit_key, sp.sport_key
        FROM dim_subreddit s, dim_sport sp
        WHERE s.subreddit_name = 'CollegeBasketball'
          AND sp.sport_code = 'ncaam'
    """)

    # CFB -> NCAAF only
    op.execute("""
        INSERT INTO subreddit_sport_mapping (subreddit_key, sport_key)
        SELECT s.subreddit_key, sp.sport_key
        FROM dim_subreddit s, dim_sport sp
        WHERE s.subreddit_name = 'CFB'
          AND sp.sport_code = 'ncaaf'
    """)

    # sports -> ALL sports (multi-sport subreddit)
    op.execute("""
        INSERT INTO subreddit_sport_mapping (subreddit_key, sport_key)
        SELECT s.subreddit_key, sp.sport_key
        FROM dim_subreddit s, dim_sport sp
        WHERE s.subreddit_name = 'sports'
          AND sp.sport_code IN ('ncaam', 'ncaaw', 'ncaaf', 'nfl', 'nba', 'wnba', 'mlb', 'nhl')
    """)


def downgrade():
    """
    Reverse all operations to remove subreddit dimensional tables.
    """

    # Drop tables in reverse order (junction table first due to FK constraints)
    op.drop_table('subreddit_sport_mapping')
    op.drop_table('dim_subreddit')
    op.drop_table('dim_sport')
