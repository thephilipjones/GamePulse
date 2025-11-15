# Story 4-6: Orchestration & Data Management

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-6
**Status:** TODO
**Estimated Effort:** 10-15 hours
**Priority:** Medium (Week 3 - polish & operational readiness)
**Dependencies:** Stories 4-1, 4-2, 4-4, 4-5 (all Dagster assets created)

---

## User Story

**As a** data engineer,
**I want** all Dagster schedules configured with proper intervals, retry policies, and observability,
**So that** the Epic 4 pipeline runs reliably end-to-end with <10 min latency and 99% uptime.

---

## Context

Stories 4-1 through 4-5 created individual Dagster assets and schedules. This story:
1. **Validates end-to-end pipeline** (extract → load → transform → sentiment)
2. **Optimizes schedules** for non-overlapping execution and efficient resource usage
3. **Implements data management** (retention, compression, cleanup)
4. **Adds observability** (structured logging, Dagster metadata, monitoring queries)
5. **Prepares for Epic 5** (schema validation, query pattern testing)

**Success Criteria:** Pipeline runs for 7 days with no manual intervention, <10 min latency, 99% uptime.

---

## Acceptance Criteria

### 1. All Schedules Configured & Running

✅ **GIVEN** Dagster daemon is running
**WHEN** I view Dagster UI → Schedules tab
**THEN** all 4 schedules show `RUNNING` status:
- `extract_reddit_posts_schedule`: `*/10 * * * *` (every 10 min)
- `extract_bluesky_posts_schedule`: `*/5 * * * *` (every 5 min)
- `transform_social_posts_schedule`: `15 * * * *` (hourly at :15)
- `calculate_sentiment_schedule`: `30 * * * *` (hourly at :30)

**AND** schedules execute without overlap
**AND** asset dependencies respected (transform waits for extracts, sentiment waits for transform)

### 2. Retry Policies on All Assets

✅ **GIVEN** each Dagster asset
**WHEN** I inspect asset definitions
**THEN** all assets have retry policies:
```python
retry_policy=RetryPolicy(
    max_retries=3,
    delay=2-5,  # Seconds, varies by asset
    backoff=Backoff.EXPONENTIAL,
)
```

**AND** retries logged with structured events: `asset_retry_attempt: attempt=2, error="..."`

### 3. Data Retention Policies Active

✅ **GIVEN** TimescaleDB hypertables for Epic 4
**WHEN** I query retention policies:
```sql
SELECT hypertable_name, drop_after
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_retention';
```

**THEN** all 4 tables have 90-day retention:
- `raw_reddit_posts`: 90 days
- `raw_bluesky_posts`: 90 days
- `stg_social_posts`: 90 days
- `fact_social_sentiment`: 90 days

**AND** data older than 90 days is automatically dropped

### 4. Compression Policies Active

✅ **GIVEN** raw tables
**WHEN** I query compression policies:
```sql
SELECT hypertable_name, compress_after
FROM timescaledb_information.jobs
WHERE proc_name = 'policy_compression';
```

**THEN** raw tables compress after 7 days:
- `raw_reddit_posts`: 7 days
- `raw_bluesky_posts`: 7 days

**AND** `stg_social_posts` has no compression (active querying)

### 5. Cleanup Job for Unmatched Posts

✅ **GIVEN** cleanup_unmatched_posts asset exists
**WHEN** it runs daily at 2 AM
**THEN** it deletes raw posts where:
- `created_at < NOW() - INTERVAL '7 days'`
- `matched_to_game = FALSE`

**AND** logs `cleanup_unmatched_posts_completed: reddit_deleted=X, bluesky_deleted=Y`
**AND** storage savings: ~200 MB over 90 days

### 6. End-to-End Latency < 10 Minutes

✅ **GIVEN** a new Reddit post is published at 12:00:00
**WHEN** I track it through the pipeline
**THEN** timestamps show:
- 12:00:00 - Post published on Reddit
- 12:10:00 - Extracted to `raw_reddit_posts` (next 10-min schedule)
- 12:15:00 - Transformed to `stg_social_posts` (hourly at :15)
- 12:30:00 - Sentiment in `fact_social_sentiment` (hourly at :30)

**Total latency:** 30 minutes (worst case)
**Average latency:** 15-20 minutes (mid-cycle extraction)

### 7. Observability - Structured Logging

✅ **GIVEN** assets run successfully
**WHEN** I view Dagster UI → Runs → Latest Run → Logs
**THEN** structured events are visible:
- `extract_reddit_posts_started`
- `reddit_fetch_completed: posts_count=42`
- `transform_social_posts_completed: posts_matched=23, posts_filtered=19`
- `calculate_sentiment_completed: posts_analyzed=20`

**AND** errors logged with context: `error="HTTP 503", attempt=2, retry_delay=4s`

### 8. Week 3 Uptime Metric

✅ **GIVEN** pipeline runs for 7 days (168 hours)
**WHEN** I calculate uptime:
```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
    COUNT(*) AS total_runs,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'SUCCESS') / COUNT(*), 1) AS uptime_pct
FROM dagster_runs
WHERE asset_key IN ('extract_reddit_posts', 'extract_bluesky_posts', 'transform_social_posts', 'calculate_sentiment')
  AND created_at > NOW() - INTERVAL '7 days';
```

**THEN** `uptime_pct >= 99.0%` (max 2 failed runs out of 168)

### 9. Asset Checks for Data Quality

✅ **GIVEN** Dagster asset checks are defined for Epic 4 assets
**WHEN** I view Dagster UI → Assets → extract_reddit_posts → Checks tab
**THEN** I see 2 checks:
- `check_reddit_freshness` - Verifies data <2 hours old
- `check_reddit_volume_anomaly` - Detects >50% deviation from 7-day average

**AND** when I view extract_bluesky_posts → Checks tab
**THEN** I see 2 checks:
- `check_bluesky_freshness` - Verifies data <2 hours old
- `check_bluesky_volume_anomaly` - Detects volume anomalies

**AND** check results display actionable metadata:
- Freshness: `age_hours`, `last_fetch`, `sla_threshold_hours`
- Volume: `recent_count_24h`, `7_day_avg_daily`, `deviation_pct`

**AND** checks are non-blocking (`blocking=False`) - asset materializes even if checks fail

---

## Technical Tasks

### Task 1: Validate All Schedules in Dagster Definitions

**File:** `backend/app/dagster_definitions.py` (verify existing)

**Verification:**
```bash
# Restart Dagster daemon to load all schedules
docker compose restart dagster-daemon dagster-webserver

# Check Dagster UI
# Navigate to http://localhost:3000 → Schedules
# Verify all 4 schedules show RUNNING
```

**Expected Schedules:**
| Schedule | Cron | Status | Timezone |
|----------|------|--------|----------|
| extract_reddit_posts_schedule | `*/10 * * * *` | RUNNING | America/New_York |
| extract_bluesky_posts_schedule | `*/5 * * * *` | RUNNING | America/New_York |
| transform_social_posts_schedule | `15 * * * *` | RUNNING | America/New_York |
| calculate_sentiment_schedule | `30 * * * *` | RUNNING | America/New_York |
| cleanup_unmatched_posts_schedule | `0 2 * * *` | RUNNING | America/New_York |

---

### Task 2: Verify Retry Policies on All Assets

**Verification:**
```python
# In Python REPL
from app.assets.reddit_posts import extract_reddit_posts
from app.assets.bluesky_posts import extract_bluesky_posts
from app.assets.social_transform import transform_social_posts
from app.assets.social_sentiment import calculate_sentiment

print(extract_reddit_posts.retry_policy)
# Expected: RetryPolicy(max_retries=3, delay=5, backoff=<Backoff.EXPONENTIAL>)
```

**If missing:** Add retry_policy to asset decorators (see Stories 4-1 through 4-5)

---

### Task 3: Validate TimescaleDB Retention Policies

**Verification:**
```bash
# Connect to database
docker compose exec db psql -U postgres -d app

# Check retention policies
SELECT
    h.hypertable_name,
    j.config->>'drop_after' AS retention_interval
FROM timescaledb_information.hypertables h
JOIN timescaledb_information.jobs j
    ON j.hypertable_name = h.hypertable_name
WHERE j.proc_name = 'policy_retention'
  AND h.hypertable_name LIKE 'raw_%' OR h.hypertable_name LIKE 'stg_%' OR h.hypertable_name LIKE 'fact_%';
```

**Expected Output:**
```
hypertable_name       | retention_interval
----------------------|-------------------
raw_reddit_posts      | 90 days
raw_bluesky_posts     | 90 days
stg_social_posts      | 90 days
fact_social_sentiment | 90 days
```

**If missing:** Retention policies added in migrations (Stories 4-1, 4-2, 4-4, 4-5)

---

### Task 4: Validate TimescaleDB Compression Policies

**Verification:**
```sql
SELECT
    h.hypertable_name,
    j.config->>'compress_after' AS compression_interval
FROM timescaledb_information.hypertables h
JOIN timescaledb_information.jobs j
    ON j.hypertable_name = h.hypertable_name
WHERE j.proc_name = 'policy_compression';
```

**Expected Output:**
```
hypertable_name     | compression_interval
--------------------|---------------------
raw_reddit_posts    | 7 days
raw_bluesky_posts   | 7 days
```

**Note:** `stg_social_posts` and `fact_social_sentiment` not compressed (active querying)

---

### Task 5: Cleanup Job Implementation

**File:** `backend/app/assets/cleanup_raw_posts.py` (created in Story 4-4)

**Verify implementation and schedule exist.**

**Manual Test:**
```bash
# Insert old unmatched test post
docker compose exec db psql -U postgres -d app -c "
INSERT INTO raw_reddit_posts (post_id, subreddit, raw_json, created_at, fetched_at, matched_to_game)
VALUES ('test_old_post', 'CollegeBasketball', '{}', NOW() - INTERVAL '10 days', NOW(), FALSE);
"

# Run cleanup asset
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions cleanup_unmatched_raw_posts

# Verify test post deleted
docker compose exec db psql -U postgres -d app -c "SELECT * FROM raw_reddit_posts WHERE post_id = 'test_old_post';"
# Should return 0 rows
```

---

### Task 6: End-to-End Latency Testing

**Manual Test:**
1. Monitor Dagster UI for next extraction cycle
2. Note timestamp of new post in `raw_reddit_posts`
3. Wait for transform schedule (:15)
4. Verify post appears in `stg_social_posts`
5. Wait for sentiment schedule (:30)
6. Verify post appears in `fact_social_sentiment`
7. Calculate total latency: sentiment.created_at - raw.created_at

**Expected:** 15-30 minutes depending on when post arrives in extraction cycle

---

### Task 7: Observability - Structured Logging Verification

**Verification:**
1. Run each asset manually in Dagster UI
2. Navigate to Runs → Latest Run → Logs tab
3. Verify structured log events appear with JSON context

**Expected Log Events:**
```
extract_reddit_posts_started
reddit_fetch_completed: posts_count=42, after=null
transform_social_posts_completed: posts_processed=50, posts_matched=23, posts_filtered=27
calculate_sentiment_completed: posts_analyzed=20, posts_matched_to_game=18
```

**If missing:** Check `structlog` configuration in asset code

---

### Task 8: Uptime Monitoring Query

**Create Monitoring Query:**

**File:** `backend/scripts/monitor_epic4_uptime.sql` (new file)

```sql
-- Epic 4 Pipeline Uptime Monitoring
-- Run daily to verify 99% uptime SLA

WITH asset_runs AS (
    SELECT
        asset_key,
        status,
        created_at
    FROM dagster_runs
    WHERE asset_key IN ('extract_reddit_posts', 'extract_bluesky_posts', 'transform_social_posts', 'calculate_sentiment')
      AND created_at > NOW() - INTERVAL '7 days'
)
SELECT
    asset_key,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_runs,
    COUNT(*) FILTER (WHERE status = 'FAILURE') AS failed_runs,
    COUNT(*) AS total_runs,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'SUCCESS') / COUNT(*), 2) AS uptime_pct
FROM asset_runs
GROUP BY asset_key
ORDER BY uptime_pct ASC;

-- Expected uptime_pct >= 99.0 for all assets
```

**Usage:**
```bash
docker compose exec db psql -U postgres -d dagster -f /opt/gamepulse/backend/scripts/monitor_epic4_uptime.sql
```

---

### Task 9: Dagster Asset Checks for Data Quality

**Purpose:** Production-grade data quality monitoring with freshness and volume anomaly detection.

**File:** `backend/app/assets/quality_checks.py` (new file)

**Implementation:**

```python
"""
Dagster asset checks for Epic 4 data quality monitoring.

Checks for:
- Freshness: Data recency (SLA: <2 hours)
- Volume anomalies: Deviation from historical averages
"""

from datetime import datetime, timedelta
from dagster import asset_check, AssetCheckResult
from sqlmodel import Session, select, func

from app.resources.database import DatabaseResource
from app.models.social import RawRedditPost, RawBlueskyPost


@asset_check(asset="extract_reddit_posts", blocking=False)
async def check_reddit_freshness(database: DatabaseResource) -> AssetCheckResult:
    """
    Verify Reddit data is less than 2 hours old.

    SLA: Data must be fetched within 2-hour window (12 extraction cycles @ 10 min each).
    """
    async with database.get_session() as session:
        # Get most recent post timestamp
        stmt = select(func.max(RawRedditPost.fetched_at))
        result = await session.execute(stmt)
        max_timestamp = result.scalar_one_or_none()

        if not max_timestamp:
            return AssetCheckResult(
                passed=False,
                metadata={"error": "No data found in raw_reddit_posts"}
            )

        age_hours = (datetime.now() - max_timestamp).total_seconds() / 3600
        passed = age_hours < 2.0

        return AssetCheckResult(
            passed=passed,
            metadata={
                "age_hours": round(age_hours, 2),
                "last_fetch": max_timestamp.isoformat(),
                "sla_threshold_hours": 2.0,
            }
        )


@asset_check(asset="extract_reddit_posts", blocking=False)
async def check_reddit_volume_anomaly(database: DatabaseResource) -> AssetCheckResult:
    """
    Detect Reddit volume anomalies (>50% deviation from 7-day average).

    Alerts on:
    - Unexpectedly low volume (potential API issues)
    - Unexpectedly high volume (potential spam/bot activity)
    """
    async with database.get_session() as session:
        # Get posts in last 24 hours
        recent_stmt = select(func.count()).select_from(RawRedditPost).where(
            RawRedditPost.created_at > datetime.now() - timedelta(hours=24)
        )
        recent_result = await session.execute(recent_stmt)
        recent_count = recent_result.scalar_one()

        # Get 7-day average daily count
        avg_stmt = select(func.count()).select_from(RawRedditPost).where(
            RawRedditPost.created_at > datetime.now() - timedelta(days=7)
        )
        avg_result = await session.execute(avg_stmt)
        total_7day = avg_result.scalar_one()
        avg_count = total_7day / 7.0

        if avg_count == 0:
            return AssetCheckResult(
                passed=False,
                metadata={"error": "No historical data for baseline"}
            )

        # Check if within 50% of average (0.5x to 2.0x range)
        lower_bound = 0.5 * avg_count
        upper_bound = 2.0 * avg_count
        is_normal = lower_bound <= recent_count <= upper_bound

        deviation_pct = ((recent_count / avg_count) - 1) * 100 if avg_count > 0 else 0

        return AssetCheckResult(
            passed=is_normal,
            metadata={
                "recent_count_24h": recent_count,
                "7_day_avg_daily": round(avg_count, 1),
                "deviation_pct": round(deviation_pct, 1),
                "lower_bound": round(lower_bound, 1),
                "upper_bound": round(upper_bound, 1),
            }
        )


@asset_check(asset="extract_bluesky_posts", blocking=False)
async def check_bluesky_freshness(database: DatabaseResource) -> AssetCheckResult:
    """Verify Bluesky data is less than 2 hours old."""
    async with database.get_session() as session:
        stmt = select(func.max(RawBlueskyPost.fetched_at))
        result = await session.execute(stmt)
        max_timestamp = result.scalar_one_or_none()

        if not max_timestamp:
            return AssetCheckResult(
                passed=False,
                metadata={"error": "No data found in raw_bluesky_posts"}
            )

        age_hours = (datetime.now() - max_timestamp).total_seconds() / 3600
        passed = age_hours < 2.0

        return AssetCheckResult(
            passed=passed,
            metadata={
                "age_hours": round(age_hours, 2),
                "last_fetch": max_timestamp.isoformat(),
                "sla_threshold_hours": 2.0,
            }
        )


@asset_check(asset="extract_bluesky_posts", blocking=False)
async def check_bluesky_volume_anomaly(database: DatabaseResource) -> AssetCheckResult:
    """Detect Bluesky volume anomalies (>50% deviation from 7-day average)."""
    async with database.get_session() as session:
        # Get posts in last 24 hours
        recent_stmt = select(func.count()).select_from(RawBlueskyPost).where(
            RawBlueskyPost.created_at > datetime.now() - timedelta(hours=24)
        )
        recent_result = await session.execute(recent_stmt)
        recent_count = recent_result.scalar_one()

        # Get 7-day average
        avg_stmt = select(func.count()).select_from(RawBlueskyPost).where(
            RawBlueskyPost.created_at > datetime.now() - timedelta(days=7)
        )
        avg_result = await session.execute(avg_stmt)
        total_7day = avg_result.scalar_one()
        avg_count = total_7day / 7.0

        if avg_count == 0:
            return AssetCheckResult(
                passed=False,
                metadata={"error": "No historical data for baseline"}
            )

        lower_bound = 0.5 * avg_count
        upper_bound = 2.0 * avg_count
        is_normal = lower_bound <= recent_count <= upper_bound

        deviation_pct = ((recent_count / avg_count) - 1) * 100 if avg_count > 0 else 0

        return AssetCheckResult(
            passed=is_normal,
            metadata={
                "recent_count_24h": recent_count,
                "7_day_avg_daily": round(avg_count, 1),
                "deviation_pct": round(deviation_pct, 1),
                "lower_bound": round(lower_bound, 1),
                "upper_bound": round(upper_bound, 1),
            }
        )
```

**Add to Dagster Definitions:**

**File:** `backend/app/dagster_definitions.py` (modify)

```python
# Add to imports
from app.assets.quality_checks import (
    check_reddit_freshness,
    check_reddit_volume_anomaly,
    check_bluesky_freshness,
    check_bluesky_volume_anomaly,
)

# Asset checks automatically discovered via decorators
# No need to explicitly add to Definitions
```

**Verification:**

```bash
# View asset checks in Dagster UI
# Navigate to http://localhost:3000 → Assets → extract_reddit_posts
# Click "Checks" tab
# Should see 2 checks: freshness + volume_anomaly

# Manually execute checks
docker compose exec dagster-daemon dagster asset check extract_reddit_posts

# View check results in UI
# Green checkmark = passed, Red X = failed with metadata
```

**Expected Check Results:**

```
✅ check_reddit_freshness
   age_hours: 0.5
   last_fetch: 2025-11-15T14:30:00Z
   sla_threshold_hours: 2.0

✅ check_reddit_volume_anomaly
   recent_count_24h: 2,500
   7_day_avg_daily: 2,200
   deviation_pct: +13.6
   lower_bound: 1,100
   upper_bound: 4,400
```

**Benefits:**
- **Visibility:** Checks appear in Dagster UI alongside assets
- **Non-blocking:** `blocking=False` means asset materializes even if checks fail (alerts only)
- **Actionable metadata:** Deviation % and thresholds help diagnose issues
- **Production-ready:** Demonstrates SLA monitoring and anomaly detection

---

### Task 10: Epic 5 Integration Validation

**Create Epic 5 Query Test:**

**File:** `backend/scripts/test_epic5_queries.sql` (new file)

```sql
-- Test query patterns Epic 5 will use

-- Pre-game excitement (24 hours before tip-off)
SELECT
    g.game_id,
    g.home_team_name,
    g.away_team_name,
    COUNT(*) AS pre_game_post_count,
    AVG(s.sentiment_compound) AS avg_pre_game_sentiment,
    SUM(s.engagement_score) AS total_pre_game_engagement
FROM fact_game g
LEFT JOIN fact_social_sentiment s
    ON g.game_key = s.game_key
    AND s.created_at BETWEEN (g.game_datetime - INTERVAL '24 hours') AND g.game_datetime
WHERE g.game_date = CURRENT_DATE
GROUP BY g.game_key, g.game_id, g.home_team_name, g.away_team_name
LIMIT 10;

-- Live excitement (during game)
SELECT
    g.game_id,
    COUNT(*) AS live_post_count,
    AVG(s.sentiment_compound) AS avg_live_sentiment,
    STDDEV(s.sentiment_compound) AS sentiment_volatility
FROM fact_game g
LEFT JOIN fact_social_sentiment s
    ON g.game_key = s.game_key
    AND s.created_at BETWEEN g.game_datetime AND (g.game_datetime + INTERVAL '3 hours')
WHERE g.game_date = CURRENT_DATE
GROUP BY g.game_key, g.game_id
LIMIT 10;
```

**Validation:**
```bash
docker compose exec db psql -U postgres -d app -f /opt/gamepulse/backend/scripts/test_epic5_queries.sql
# Verify queries return results without errors
```

---

## Testing Requirements

### Integration Tests (Week 3)

**File:** `backend/app/tests/integration/test_epic4_pipeline_e2e.py`

**Test Cases:**
1. `test_end_to_end_reddit_to_sentiment()` - Insert raw Reddit post, verify it flows through all layers
2. `test_end_to_end_bluesky_to_sentiment()` - Same for Bluesky
3. `test_cleanup_deletes_old_unmatched()` - Verify cleanup job works

**Priority:** Medium (manual testing sufficient for Week 3)

### Manual Testing Checklist

- [ ] All 5 schedules running in Dagster UI
- [ ] No overlapping executions (check run history)
- [ ] Retry policies trigger on simulated failures
- [ ] Retention policies drop data >90 days old
- [ ] Compression policies compress chunks >7 days old
- [ ] Cleanup job deletes unmatched posts
- [ ] End-to-end latency <30 min (measured)
- [ ] Uptime >99% over 7 days (measured)
- [ ] Epic 5 queries return correct results

---

## Dependencies

### Upstream (Must Complete First)
- Story 4-1: Reddit Data Pipeline ✅
- Story 4-2: Bluesky Data Pipeline ✅
- Story 4-4: Unified Transform Layer ✅
- Story 4-5: Sentiment Analysis & Fact Table ✅

### Downstream (Enables)
- Epic 5: Moment Detection & Excitement Scoring (validated ready)

---

## Out of Scope

- ❌ Real-time monitoring dashboards (Epic 9)
- ❌ Automated alerting (Epic 9)
- ❌ Advanced retry strategies (exponential backoff with jitter) - basic retry sufficient
- ❌ Multi-region deployment (single EC2 instance)
- ❌ Blue-green deployments (direct updates acceptable for portfolio)

---

## Definition of Done

- [x] All 5 Dagster schedules running and visible in UI
- [x] Retry policies configured on all assets
- [x] TimescaleDB retention (90 days) and compression (7 days) active
- [x] Cleanup job deletes old unmatched posts daily
- [x] End-to-end latency <30 min (worst case)
- [x] Pipeline uptime >99% over 7-day test period
- [x] Structured logging visible in Dagster UI
- [x] **Asset checks implemented for freshness and volume anomalies** (4 checks total)
- [x] **Asset checks visible in Dagster UI with actionable metadata**
- [x] Epic 5 query patterns tested and validated
- [x] Code reviewed and merged

---

## Notes

### Schedule Optimization

**Why stagger schedules?**
- **Extract:** Every 5-10 min (near real-time)
- **Transform:** Hourly at :15 (15 min after last extract cycle)
- **Sentiment:** Hourly at :30 (15 min after transform)

**Benefits:**
- Avoids concurrent execution (1GB RAM constraint)
- Ensures fresh data for downstream assets
- Predictable execution windows for debugging

### Storage Budget

**Total Epic 4 storage (90 days):**
- Raw Reddit: ~90 MB compressed
- Raw Bluesky: ~40 MB compressed
- Staged posts: ~50 MB uncompressed
- Fact sentiment: ~30 MB uncompressed
- **Total: ~210 MB** (well within 20GB budget)

### Uptime Calculation

**99% uptime = 1.68 hours downtime per week**
- Expected failures: Network issues, Reddit rate limits, Bluesky API instability
- Retry policy handles transient errors (3 attempts)
- Acceptable: 1-2 failed runs per week (out of 168 extract runs)

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 3 (Epic 4 sprint)
