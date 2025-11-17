-- Epic 5 Query Pattern Validation (Story 4-7 Task 10)
--
-- PURPOSE:
-- Validate schema supports Epic 5 (Social Sentiment Analysis UI) query patterns
-- Tests common queries that will be needed for sentiment dashboards and analytics
--
-- USAGE:
-- Run against app database (NOT dagster database):
--   docker compose exec db psql -U postgres -d app -f /app/scripts/test_epic5_queries.sql
--
-- Or via Python:
--   python backend/scripts/run_epic5_validation.py
--
-- EXPECTED RESULTS:
-- All queries should return results without errors
-- Schema should support: joins, aggregations, time-series queries, filtering
--
-- VALIDATION CRITERIA:
-- ✅ Query executes without error
-- ✅ Returns results in <1 second (performance check)
-- ✅ Result schema matches expected columns

\timing on

-- ====================
-- QUERY 1: Top Teams by Sentiment (Last 7 Days)
-- ====================
-- Epic 5 Use Case: "Which teams have the most positive sentiment this week?"
SELECT
    t.team_name,
    t.team_group_name AS conference,
    COUNT(DISTINCT fss.sentiment_key) AS post_count,
    ROUND(AVG(fss.sentiment_compound), 3) AS avg_sentiment,
    ROUND(AVG(fss.sentiment_positive), 3) AS avg_positive,
    ROUND(AVG(fss.sentiment_negative), 3) AS avg_negative,
    ROUND(AVG(fss.engagement_score), 1) AS avg_engagement
FROM fact_social_sentiment fss
JOIN fact_game fg ON fss.game_key = fg.game_key
JOIN dim_team t ON fg.home_team_id = t.team_id  -- Simplified: just home team
WHERE
    fss.created_at >= NOW() - INTERVAL '7 days'
GROUP BY t.team_id, t.team_name, t.team_group_name
HAVING COUNT(DISTINCT fss.sentiment_key) >= 5  -- Minimum sample size
ORDER BY avg_sentiment DESC
LIMIT 20;

-- ====================
-- QUERY 2: Trending Topics by Platform
-- ====================
-- Epic 5 Use Case: "What are people talking about on Reddit vs Bluesky?"
SELECT
    platform,
    COUNT(*) AS post_count,
    ROUND(AVG(sentiment_compound), 3) AS avg_sentiment,
    ROUND(AVG(engagement_score), 1) AS avg_engagement,
    COUNT(*) FILTER (WHERE sentiment_compound > 0.5) AS very_positive,
    COUNT(*) FILTER (WHERE sentiment_compound < -0.5) AS very_negative
FROM fact_social_sentiment
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY platform
ORDER BY post_count DESC;

-- ====================
-- QUERY 3: Game-Specific Sentiment Timeline
-- ====================
-- Epic 5 Use Case: "Show sentiment trend for Duke vs UNC game"
SELECT
    DATE_TRUNC('hour', fss.created_at) AS hour_bucket,
    COUNT(*) AS post_count,
    ROUND(AVG(fss.sentiment_compound), 3) AS avg_sentiment,
    ROUND(AVG(fss.engagement_score), 1) AS avg_engagement
FROM fact_social_sentiment fss
JOIN fact_game fg ON fss.game_key = fg.game_key
WHERE
    fg.game_key = (
        SELECT game_key
        FROM fact_game
        WHERE game_date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY game_date DESC
        LIMIT 1  -- Most recent game
    )
GROUP BY hour_bucket
ORDER BY hour_bucket ASC;

-- ====================
-- QUERY 4: Platform Comparison for Specific Team
-- ====================
-- Epic 5 Use Case: "How does Reddit sentiment compare to Bluesky for Duke?"
SELECT
    platform,
    COUNT(*) AS post_count,
    ROUND(AVG(sentiment_compound), 3) AS avg_sentiment,
    ROUND(STDDEV(sentiment_compound), 3) AS sentiment_stddev,
    MIN(created_at) AS first_post,
    MAX(created_at) AS last_post
FROM fact_social_sentiment fss
JOIN fact_game fg ON fss.game_key = fg.game_key
WHERE
    (fg.home_team_id LIKE '%duke%' OR fg.away_team_id LIKE '%duke%')
    AND fss.created_at >= NOW() - INTERVAL '7 days'
GROUP BY platform
ORDER BY post_count DESC;

-- ====================
-- QUERY 5: High-Engagement Posts (Viral Detection)
-- ====================
-- Epic 5 Use Case: "Show me posts that went viral (high engagement + strong sentiment)"
SELECT
    fss.platform,
    LEFT(fss.post_text, 100) AS post_preview,
    fss.engagement_score,
    fss.sentiment_compound,
    fss.created_at,
    t_home.team_name AS home_team,
    t_away.team_name AS away_team
FROM fact_social_sentiment fss
JOIN fact_game fg ON fss.game_key = fg.game_key
JOIN dim_team t_home ON fg.home_team_id = t_home.team_id
JOIN dim_team t_away ON fg.away_team_id = t_away.team_id
WHERE
    fss.created_at >= NOW() - INTERVAL '24 hours'
    AND fss.engagement_score > 100  -- High engagement threshold
    AND ABS(fss.sentiment_compound) > 0.5  -- Strong sentiment (positive or negative)
ORDER BY fss.engagement_score DESC
LIMIT 10;

-- ====================
-- QUERY 6: Conference Sentiment Leaderboard
-- ====================
-- Epic 5 Use Case: "Which conference has the most engaged fanbase?"
SELECT
    t.team_group_name AS conference,
    COUNT(DISTINCT fss.sentiment_key) AS total_posts,
    COUNT(DISTINCT fg.game_key) AS games_discussed,
    ROUND(AVG(fss.sentiment_compound), 3) AS avg_sentiment,
    ROUND(AVG(fss.engagement_score), 1) AS avg_engagement,
    SUM(fss.engagement_score) AS total_engagement
FROM fact_social_sentiment fss
JOIN fact_game fg ON fss.game_key = fg.game_key
JOIN dim_team t ON fg.home_team_id = t.team_id  -- Simplified: home team conference
WHERE
    fss.created_at >= NOW() - INTERVAL '7 days'
    AND t.sport = 'ncaam'
GROUP BY t.team_group_name
HAVING COUNT(DISTINCT fss.sentiment_key) >= 10  -- Minimum sample size
ORDER BY total_engagement DESC
LIMIT 15;

-- ====================
-- QUERY 7: Time-Series Sentiment by Hour (Last 24h)
-- ====================
-- Epic 5 Use Case: "Show hourly sentiment trend for live game monitoring"
SELECT
    DATE_TRUNC('hour', created_at) AS hour_bucket,
    platform,
    COUNT(*) AS post_count,
    ROUND(AVG(sentiment_compound), 3) AS avg_sentiment,
    ROUND(AVG(engagement_score), 1) AS avg_engagement
FROM fact_social_sentiment
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour_bucket, platform
ORDER BY hour_bucket ASC, platform;

-- ====================
-- QUERY 8: Post Volume Anomaly Detection
-- ====================
-- Epic 5 Use Case: "Detect unusual spikes in posting activity (game start detection)"
WITH hourly_volumes AS (
    SELECT
        DATE_TRUNC('hour', created_at) AS hour_bucket,
        COUNT(*) AS post_count
    FROM fact_social_sentiment
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY hour_bucket
),
volume_stats AS (
    SELECT
        AVG(post_count) AS mean_volume,
        STDDEV(post_count) AS stddev_volume
    FROM hourly_volumes
)
SELECT
    hv.hour_bucket,
    hv.post_count,
    vs.mean_volume,
    ROUND((hv.post_count - vs.mean_volume) / NULLIF(vs.stddev_volume, 0), 2) AS z_score,
    CASE
        WHEN (hv.post_count - vs.mean_volume) / NULLIF(vs.stddev_volume, 0) > 2 THEN 'SPIKE'
        WHEN (hv.post_count - vs.mean_volume) / NULLIF(vs.stddev_volume, 0) < -2 THEN 'DROP'
        ELSE 'NORMAL'
    END AS anomaly_status
FROM hourly_volumes hv
CROSS JOIN volume_stats vs
WHERE hv.hour_bucket >= NOW() - INTERVAL '24 hours'
ORDER BY hv.hour_bucket DESC;

-- ====================
-- QUERY 9: Schema Validation - Column Types
-- ====================
-- Verify all expected columns exist with correct types
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'fact_social_sentiment'
ORDER BY ordinal_position;

-- ====================
-- QUERY 10: Index Performance Check
-- ====================
-- Verify indexes exist for common query patterns
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('fact_social_sentiment', 'fact_game', 'dim_team')
ORDER BY tablename, indexname;

-- ====================
-- VALIDATION SUMMARY
-- ====================
\echo ''
\echo '==================================='
\echo 'Epic 5 Query Validation Complete'
\echo '==================================='
\echo ''
\echo 'All queries should execute without errors and return results in <1 second.'
\echo 'If any query fails or performs slowly, Epic 5 schema may need optimization.'
\echo ''
\echo 'Next Steps:'
\echo '  1. Review query results for data completeness'
\echo '  2. Check EXPLAIN ANALYZE for slow queries'
\echo '  3. Add indexes if needed for Epic 5 query patterns'
\echo '  4. Consider materialized views for dashboard queries'
\echo ''

\timing off
