"""fix_stg_social_posts_initialize_first_chunk

Revision ID: c2073349c669
Revises: 0c51279163bd
Create Date: 2025-11-20 14:10:52.913078

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c2073349c669'
down_revision = '0c51279163bd'
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix TimescaleDB async first-chunk creation issue.

    Root Cause:
    - TimescaleDB hypertable with composite PK on (platform, post_id, created_at)
    - First chunk creation via asyncpg + ON CONFLICT fails with "index for constraint
      not found on chunk" error
    - Happens when table has 0 chunks and async insert tries to create first chunk
    - Subsequent chunks create fine once any chunk exists

    Solution:
    - Force creation of initial chunk using synchronous SQL (Alembic uses psycopg2)
    - Insert dummy row to trigger chunk creation with proper index propagation
    - Delete dummy row immediately (chunk remains allocated)
    - Future async inserts work correctly once chunks exist

    This follows TimescaleDB best practices:
    - Keep composite PK with partitioning column (required by TimescaleDB)
    - Use ON CONFLICT with column names (recommended approach)
    - Fix chunk propagation issue without changing schema

    Refs:
    - TimescaleDB docs: Unique constraints must include partitioning column
    - GitHub issue #2101: "could not find arbiter index for hypertable"
    - Research: TimescaleDB 2.16+ has 10-100x better ON CONFLICT performance
    """

    # Force creation of first chunk using synchronous SQL
    # This ensures index propagation works correctly (unlike async first insert)
    op.execute("""
        INSERT INTO stg_social_posts (
            platform,
            post_id,
            created_at,
            fetched_at,
            engagement_score,
            raw_json,
            social_post_key
        )
        VALUES (
            '__init__',
            '__chunk_init__',
            NOW(),
            NOW(),
            0,
            '{}'::jsonb,
            DEFAULT
        )
        ON CONFLICT (platform, post_id, created_at) DO NOTHING;
    """)

    # Delete the dummy row (chunk remains allocated with proper indexes)
    op.execute("""
        DELETE FROM stg_social_posts
        WHERE platform = '__init__' AND post_id = '__chunk_init__';
    """)

    # Verify chunk was created with proper index
    op.execute("""
        DO $$
        DECLARE
            chunk_count INTEGER;
            indexed_chunk_count INTEGER;
        BEGIN
            -- Count total chunks
            SELECT COUNT(*) INTO chunk_count
            FROM timescaledb_information.chunks
            WHERE hypertable_name = 'stg_social_posts';

            -- Count chunks with PK index
            SELECT COUNT(DISTINCT c.chunk_name) INTO indexed_chunk_count
            FROM timescaledb_information.chunks c
            INNER JOIN pg_indexes i
                ON i.tablename = c.chunk_name
                AND i.indexname LIKE '%stg_social_posts_pkey%'
            WHERE c.hypertable_name = 'stg_social_posts';

            -- Log results
            RAISE NOTICE 'stg_social_posts: % chunks created, % with PK index',
                chunk_count, indexed_chunk_count;

            -- Warn if mismatch (should never happen)
            IF chunk_count > 0 AND indexed_chunk_count < chunk_count THEN
                RAISE WARNING 'Some stg_social_posts chunks missing PK index: % total, % indexed',
                    chunk_count, indexed_chunk_count;
            END IF;
        END $$;
    """)


def downgrade():
    """
    No downgrade needed - this migration only ensures chunks are properly indexed.

    Chunks will be naturally dropped by TimescaleDB retention policy (90 days).
    No schema changes were made.
    """
    pass
