-- Epic 4 Pipeline Uptime Monitoring Query (Story 4-7 AC8)
--
-- PURPOSE:
-- Calculate uptime percentage for Epic 4 social data pipeline over specified time period.
-- Uptime defined as: (successful runs / total runs) * 100%
-- Target SLA: ≥99% uptime over 7-day rolling window
--
-- USAGE:
-- Run against Dagster database (NOT app database):
--   docker compose exec db psql -U postgres -d dagster -f /app/scripts/monitor_epic4_uptime.sql
--
-- Or via Python script:
--   python backend/scripts/run_uptime_monitor.py
--
-- CONFIGURATION:
-- Adjust @lookback_hours variable to change monitoring window
-- Default: 168 hours (7 days) for Story 4-7 validation
--
-- OUTPUT:
-- - Asset name
-- - Total runs
-- - Successful runs
-- - Failed runs
-- - Uptime percentage
-- - SLA status (PASS/FAIL for 99% threshold)

-- Set monitoring window (default: 7 days = 168 hours)
\set lookback_hours 168

-- Epic 4 Pipeline Uptime Report
SELECT
    asset_name,
    total_runs,
    successful_runs,
    failed_runs,
    ROUND((successful_runs::numeric / NULLIF(total_runs, 0)) * 100, 2) AS uptime_percentage,
    CASE
        WHEN (successful_runs::numeric / NULLIF(total_runs, 0)) >= 0.99 THEN 'PASS'
        ELSE 'FAIL'
    END AS sla_status,
    window_start,
    window_end
FROM (
    SELECT
        'extract_reddit_posts' AS asset_name,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
        NOW() - INTERVAL ':lookback_hours hours' AS window_start,
        NOW() AS window_end
    FROM runs
    WHERE
        pipeline_name = 'materialize_extract_reddit_posts'
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'

    UNION ALL

    SELECT
        'extract_bluesky_posts' AS asset_name,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
        NOW() - INTERVAL ':lookback_hours hours' AS window_start,
        NOW() AS window_end
    FROM runs
    WHERE
        pipeline_name = 'materialize_extract_bluesky_posts'
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'

    UNION ALL

    SELECT
        'transform_social_posts' AS asset_name,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
        NOW() - INTERVAL ':lookback_hours hours' AS window_start,
        NOW() AS window_end
    FROM runs
    WHERE
        pipeline_name = 'transform_social_posts'
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'

    UNION ALL

    SELECT
        'calculate_sentiment' AS asset_name,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
        NOW() - INTERVAL ':lookback_hours hours' AS window_start,
        NOW() AS window_end
    FROM runs
    WHERE
        pipeline_name = 'calculate_sentiment'
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'

    UNION ALL

    SELECT
        'cleanup_unmatched_posts' AS asset_name,
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
        NOW() - INTERVAL ':lookback_hours hours' AS window_start,
        NOW() AS window_end
    FROM runs
    WHERE
        pipeline_name = 'cleanup_unmatched_posts_job'
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'
) AS asset_stats
ORDER BY asset_name;

-- Overall Epic 4 Pipeline Uptime Summary
SELECT
    'Epic 4 Overall' AS pipeline,
    SUM(total_runs) AS total_runs,
    SUM(successful_runs) AS successful_runs,
    SUM(failed_runs) AS failed_runs,
    ROUND((SUM(successful_runs)::numeric / NULLIF(SUM(total_runs), 0)) * 100, 2) AS overall_uptime,
    CASE
        WHEN (SUM(successful_runs)::numeric / NULLIF(SUM(total_runs), 0)) >= 0.99 THEN 'PASS'
        ELSE 'FAIL'
    END AS sla_status,
    NOW() - INTERVAL ':lookback_hours hours' AS window_start,
    NOW() AS window_end
FROM (
    SELECT
        COUNT(*) AS total_runs,
        COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs
    FROM runs
    WHERE
        pipeline_name IN (
            'materialize_extract_reddit_posts',
            'materialize_extract_bluesky_posts',
            'transform_social_posts',
            'calculate_sentiment',
            'cleanup_unmatched_posts_job'
        )
        AND created_at >= NOW() - INTERVAL ':lookback_hours hours'
) AS combined_stats;

-- Latency Analysis: End-to-End Pipeline Duration
-- Measures time from Reddit/Bluesky extract to sentiment calculation complete
SELECT
    'Latency Analysis' AS metric,
    ROUND(AVG(EXTRACT(EPOCH FROM (sentiment_end - extract_start)) / 60), 2) AS avg_latency_minutes,
    ROUND(MAX(EXTRACT(EPOCH FROM (sentiment_end - extract_start)) / 60), 2) AS max_latency_minutes,
    ROUND(MIN(EXTRACT(EPOCH FROM (sentiment_end - extract_start)) / 60), 2) AS min_latency_minutes,
    COUNT(*) AS sample_size
FROM (
    SELECT
        r.created_at AS extract_start,
        s.created_at AS sentiment_end
    FROM runs r
    JOIN runs s ON s.created_at > r.created_at
    WHERE
        r.pipeline_name IN ('materialize_extract_reddit_posts', 'materialize_extract_bluesky_posts')
        AND s.pipeline_name = 'calculate_sentiment'
        AND r.status = 'SUCCESS'
        AND s.status = 'SUCCESS'
        AND r.created_at >= NOW() - INTERVAL ':lookback_hours hours'
    ORDER BY r.created_at DESC
    LIMIT 100  -- Sample last 100 successful pipeline runs
) AS latency_samples;

-- Notes:
-- 1. This query assumes Dagster schema v1.0+ (runs table structure)
-- 2. Pipeline names may vary - verify via: SELECT DISTINCT pipeline_name FROM runs;
-- 3. For production monitoring, consider creating a materialized view or scheduled job
-- 4. Latency calculation approximates end-to-end time (may not capture exact dependency chain)
