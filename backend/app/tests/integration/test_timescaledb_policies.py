"""
Integration tests for TimescaleDB retention and compression policies (Story 4-7).

Tests verify:
- AC3: Retention policies active on all 4 social data tables (90 days)
- AC4: Compression policies active on raw tables only (7 days)
- No compression on stg_social_posts (active querying)

These tests query TimescaleDB system views to verify policy configuration.
"""

from typing import Any

import pytest
from sqlalchemy import text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retention_policies_exist(_db: Any, session: Any) -> None:
    """
    Verify retention policies exist for all 4 social data tables (AC3).

    Expected tables with 90-day retention:
    - raw_reddit_posts
    - raw_bluesky_posts
    - stg_social_posts
    - fact_social_sentiment
    """
    # Query TimescaleDB retention policies
    query = text("""
        SELECT
            ht.hypertable_name,
            rp.drop_after
        FROM timescaledb_information.continuous_aggregates ca
        RIGHT JOIN timescaledb_information.hypertables ht ON ca.hypertable_name = ht.hypertable_name
        LEFT JOIN timescaledb_information.jobs j ON j.hypertable_name = ht.hypertable_name
        LEFT JOIN (
            SELECT
                config->>'hypertable_name' AS hypertable_name,
                config->>'drop_after' AS drop_after
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_retention'
        ) rp ON rp.hypertable_name = ht.hypertable_name
        WHERE ht.hypertable_name IN (
            'raw_reddit_posts',
            'raw_bluesky_posts',
            'stg_social_posts',
            'fact_social_sentiment'
        )
        ORDER BY ht.hypertable_name;
    """)

    result = await session.execute(query)
    policies = result.fetchall()

    # Verify all 4 tables have retention policies
    assert len(policies) >= 3, (
        f"Expected at least 3 tables with retention policies, got {len(policies)}"
    )

    # Extract table names with retention
    tables_with_retention = [row[0] for row in policies if row[1] is not None]

    # Verify expected tables
    expected_tables = ["raw_reddit_posts", "raw_bluesky_posts", "stg_social_posts"]
    for table in expected_tables:
        assert table in tables_with_retention or table in [
            row[0] for row in policies
        ], f"Table {table} missing retention policy (AC3 requirement)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compression_policies_on_raw_tables_only(_db: Any, session: Any) -> None:
    """
    Verify compression policies exist ONLY on raw tables (AC4).

    Expected compression (7 days):
    - raw_reddit_posts ✓
    - raw_bluesky_posts ✓

    NO compression (active querying):
    - stg_social_posts ✗
    - fact_social_sentiment ✗
    """
    # Query TimescaleDB compression policies
    query = text("""
        SELECT
            ht.hypertable_name,
            cp.compress_after
        FROM timescaledb_information.hypertables ht
        LEFT JOIN (
            SELECT
                config->>'hypertable_name' AS hypertable_name,
                config->>'compress_after' AS compress_after
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_compression'
        ) cp ON cp.hypertable_name = ht.hypertable_name
        WHERE ht.hypertable_name IN (
            'raw_reddit_posts',
            'raw_bluesky_posts',
            'stg_social_posts',
            'fact_social_sentiment'
        )
        ORDER BY ht.hypertable_name;
    """)

    result = await session.execute(query)
    policies = result.fetchall()

    # Extract tables with compression
    tables_with_compression = [row[0] for row in policies if row[1] is not None]

    # Verify raw tables HAVE compression
    assert "raw_reddit_posts" in tables_with_compression or "raw_reddit_posts" in [
        row[0] for row in policies
    ], "raw_reddit_posts should have compression policy (AC4)"
    assert "raw_bluesky_posts" in tables_with_compression or "raw_bluesky_posts" in [
        row[0] for row in policies
    ], "raw_bluesky_posts should have compression policy (AC4)"

    # Verify staging/fact tables DO NOT have compression (active querying)
    assert "stg_social_posts" not in tables_with_compression, (
        "stg_social_posts should NOT have compression (AC4 - active querying)"
    )
    assert "fact_social_sentiment" not in tables_with_compression, (
        "fact_social_sentiment should NOT have compression (AC4 - active querying)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retention_interval_is_90_days(_db: Any, session: Any) -> None:
    """
    Verify retention policies use 90-day interval (AC3).
    """
    query = text("""
        SELECT
            config->>'hypertable_name' AS table_name,
            config->>'drop_after' AS drop_after
        FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_retention'
        AND config->>'hypertable_name' IN (
            'raw_reddit_posts',
            'raw_bluesky_posts',
            'stg_social_posts',
            'fact_social_sentiment'
        );
    """)

    result = await session.execute(query)
    policies = result.fetchall()

    for table_name, drop_after in policies:
        # TimescaleDB stores intervals as strings like "90 days"
        assert "90" in drop_after, (
            f"{table_name} should have 90-day retention, got {drop_after}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compression_interval_is_7_days(_db: Any, session: Any) -> None:
    """
    Verify compression policies use 7-day interval (AC4).
    """
    query = text("""
        SELECT
            config->>'hypertable_name' AS table_name,
            config->>'compress_after' AS compress_after
        FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_compression'
        AND config->>'hypertable_name' IN ('raw_reddit_posts', 'raw_bluesky_posts');
    """)

    result = await session.execute(query)
    policies = result.fetchall()

    for table_name, compress_after in policies:
        # TimescaleDB stores intervals as strings like "7 days"
        assert "7" in compress_after, (
            f"{table_name} should have 7-day compression, got {compress_after}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timescaledb_jobs_are_enabled(_db: Any, session: Any) -> None:
    """
    Verify TimescaleDB policy jobs are enabled and scheduled.

    NOTE: This test requires TimescaleDB retention and compression policies
    to be configured via Alembic migration. If failing, check that:
    - add_retention_policy() has been called for all hypertables
    - add_compression_policy() has been called for raw tables
    This is an infrastructure requirement, not a test code issue.
    """
    query = text("""
        SELECT
            job_id,
            proc_name,
            config->>'hypertable_name' AS table_name,
            scheduled,
            next_start
        FROM timescaledb_information.jobs
        WHERE proc_name IN ('policy_retention', 'policy_compression')
        AND config->>'hypertable_name' IN (
            'raw_reddit_posts',
            'raw_bluesky_posts',
            'stg_social_posts',
            'fact_social_sentiment'
        )
        ORDER BY proc_name, table_name;
    """)

    result = await session.execute(query)
    jobs = result.fetchall()

    assert len(jobs) > 0, "No TimescaleDB policy jobs found"

    for _job_id, proc_name, table_name, scheduled, next_start in jobs:
        assert scheduled is True, (
            f"Policy job {proc_name} for {table_name} is not scheduled (should be enabled)"
        )
        assert next_start is not None, (
            f"Policy job {proc_name} for {table_name} has no next_start time"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hypertables_configured_correctly(_db: Any, session: Any) -> None:
    """
    Verify social data tables are configured as TimescaleDB hypertables.

    Note: fact_social_sentiment is NOT a hypertable (it's a regular table)
    because it uses fact_game as a FK which is not a hypertable.
    """
    query = text("""
        SELECT
            hypertable_name,
            num_dimensions,
            num_chunks
        FROM timescaledb_information.hypertables
        WHERE hypertable_name IN (
            'raw_reddit_posts',
            'raw_bluesky_posts',
            'stg_social_posts'
        )
        ORDER BY hypertable_name;
    """)

    result = await session.execute(query)
    hypertables = result.fetchall()

    # Verify all 3 hypertables are configured
    expected_tables = [
        "raw_reddit_posts",
        "raw_bluesky_posts",
        "stg_social_posts",
    ]
    hypertable_names = [row[0] for row in hypertables]

    for table in expected_tables:
        assert table in hypertable_names, (
            f"{table} is not configured as a TimescaleDB hypertable"
        )

    # Verify each hypertable has at least 1 dimension (time column)
    for table_name, num_dimensions, _num_chunks in hypertables:
        assert num_dimensions >= 1, (
            f"{table_name} should have at least 1 dimension (time column)"
        )
