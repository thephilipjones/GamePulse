# TimescaleDB Data Integrity Improvements

**Priority:** Low
**Epic:** Post-Epic 5
**Effort:** 2-4 hours

## Context

Epic 4 introduced a hybrid table architecture for the social media pipeline:

- **Hypertables** (TimescaleDB): `raw_reddit_posts`, `raw_bluesky_posts`, `stg_social_posts`
- **Regular table** (PostgreSQL): `fact_social_sentiment`

This design was chosen because:
1. TimescaleDB hypertables cannot support unique indexes propagated to chunks via `op.create_index()`
2. Foreign keys cannot reference hypertable columns without a unique constraint
3. `fact_social_sentiment` needs to support FK references from dimension tables

As a result, the FK from `fact_social_sentiment.social_post_key` to `stg_social_posts.social_post_key` was removed. Referential integrity is enforced at the application level in `backend/app/models/social.py`.

This document outlines optional improvements to strengthen data integrity monitoring and lifecycle management.

---

## 1. Orphan Detection Query

Detect `fact_social_sentiment` records that reference non-existent `stg_social_posts`:

```sql
-- Find orphaned sentiment records
SELECT
    fss.sentiment_key,
    fss.social_post_key,
    fss.created_at,
    fss.platform
FROM fact_social_sentiment fss
LEFT JOIN stg_social_posts ssp
    ON fss.social_post_key = ssp.social_post_key
WHERE ssp.social_post_key IS NULL;
```

### Implementation Options

**Option A: Dagster Sensor**
```python
@sensor(job=orphan_alert_job, minimum_interval_seconds=86400)
def orphan_detection_sensor(context):
    """Daily check for orphaned sentiment records."""
    with get_db_session() as session:
        orphan_count = session.execute(text("""
            SELECT COUNT(*)
            FROM fact_social_sentiment fss
            LEFT JOIN stg_social_posts ssp
                ON fss.social_post_key = ssp.social_post_key
            WHERE ssp.social_post_key IS NULL
        """)).scalar()

        if orphan_count > 0:
            context.log.warning(f"Found {orphan_count} orphaned sentiment records")
            # Trigger alert or cleanup job
```

**Option B: Monitoring Query**
Add to CloudWatch or Grafana dashboard as a metric to track over time.

---

## 2. Retention Policy for fact_social_sentiment

Currently, only `stg_social_posts` has a 90-day retention policy via TimescaleDB compression. `fact_social_sentiment` will grow unbounded.

### Recommended Configuration

Match the staging table retention:

```sql
-- Add retention policy (90 days)
-- Note: fact_social_sentiment is a regular table, not hypertable
-- Use scheduled job instead of TimescaleDB policy

-- Option 1: Direct SQL (run via Dagster scheduled job)
DELETE FROM fact_social_sentiment
WHERE created_at < NOW() - INTERVAL '90 days';

-- Option 2: Add to existing cleanup_old_data Dagster job
-- See backend/app/assets/orchestration.py
```

### Integration with Existing Cleanup Job

The `cleanup_old_data` asset in `backend/app/assets/orchestration.py` already handles retention for raw tables. Extend it:

```python
@asset(
    description="Clean up old data across all social media tables",
    automation_condition=AutomationCondition.on_cron("0 2 * * *"),  # Daily 2 AM
)
def cleanup_old_data(context):
    """Delete data older than retention period."""
    retention_days = 90

    with get_db_session() as session:
        # Existing raw table cleanup...

        # Add fact_social_sentiment cleanup
        result = session.execute(text("""
            DELETE FROM fact_social_sentiment
            WHERE created_at < NOW() - INTERVAL :days
            RETURNING sentiment_key
        """), {"days": f"{retention_days} days"})

        deleted_count = len(result.fetchall())
        context.log.info(f"Deleted {deleted_count} old sentiment records")
```

---

## 3. Cascade-Aware Cleanup Pattern

Due to removed FK constraints, deletions must be performed in correct order to avoid orphans:

1. Delete from `fact_social_sentiment` first
2. Then delete from `stg_social_posts`

### Safe Deletion Pattern

```sql
-- Step 1: Delete sentiment records for posts being removed
DELETE FROM fact_social_sentiment fss
WHERE fss.social_post_key IN (
    SELECT ssp.social_post_key
    FROM stg_social_posts ssp
    WHERE ssp.created_at < NOW() - INTERVAL '90 days'
);

-- Step 2: Delete staging posts (TimescaleDB retention handles this automatically)
-- But if manual deletion needed:
DELETE FROM stg_social_posts
WHERE created_at < NOW() - INTERVAL '90 days';
```

### Implementation in cleanup_old_data

```python
def cleanup_social_data(session, retention_days: int):
    """
    Clean up social media data with proper cascade order.

    Order matters:
    1. fact_social_sentiment (references stg_social_posts)
    2. stg_social_posts (referenced by fact_social_sentiment)
    """
    cutoff = f"{retention_days} days"

    # Step 1: Delete sentiment records first
    sentiment_result = session.execute(text("""
        DELETE FROM fact_social_sentiment fss
        WHERE fss.social_post_key IN (
            SELECT ssp.social_post_key
            FROM stg_social_posts ssp
            WHERE ssp.created_at < NOW() - INTERVAL :cutoff
        )
        RETURNING sentiment_key
    """), {"cutoff": cutoff})

    # Step 2: Staging posts (if not using TimescaleDB auto-retention)
    # Note: TimescaleDB retention policy may handle this automatically
    staging_result = session.execute(text("""
        DELETE FROM stg_social_posts
        WHERE created_at < NOW() - INTERVAL :cutoff
        RETURNING social_post_key
    """), {"cutoff": cutoff})

    return {
        "sentiment_deleted": len(sentiment_result.fetchall()),
        "staging_deleted": len(staging_result.fetchall())
    }
```

---

## Implementation Notes

### When to Implement

- **Epic 5+**: After core moment detection features are complete
- **Trigger**: If orphan records are observed in production
- **Trigger**: Before scaling to multi-sport (data volume increase)

### Testing Approach

1. Create test data with known orphan scenarios
2. Verify orphan detection query returns expected results
3. Test cascade deletion order with transaction rollback
4. Verify retention policy deletes correct date range

### Monitoring Metrics

- `gamepulse.sentiment.orphan_count` - Daily count of orphaned records
- `gamepulse.sentiment.retention_deleted` - Records deleted by retention policy
- `gamepulse.staging.retention_deleted` - Staging posts deleted by retention

---

## Related Files

- Migration (staging key): [f1a2b3c4d5e6_add_social_post_key_to_stg_social_posts.py](../../backend/app/alembic/versions/f1a2b3c4d5e6_add_social_post_key_to_stg_social_posts.py)
- Migration (sentiment table): [f3c4d5e6f7g8_create_fact_social_sentiment_table.py](../../backend/app/alembic/versions/f3c4d5e6f7g8_create_fact_social_sentiment_table.py)
- Cleanup job: [backend/app/assets/orchestration.py](../../backend/app/assets/orchestration.py)
- Model documentation: [backend/app/models/social.py](../../backend/app/models/social.py)
