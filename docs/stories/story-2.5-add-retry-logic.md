# Story 2.5: Add Retry Logic and Error Handling

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want robust error handling for NCAA API failures,
So that temporary API outages don't crash the data ingestion pipeline.

---

## Acceptance Criteria

**Given** the NCAA API may occasionally fail or timeout
**When** an API request fails during asset materialization
**Then** Dagster's RetryPolicy automatically retries up to 3 times with exponential backoff (2s, 4s, 8s)

**And** if all retries fail, the asset materialization fails gracefully:
- Dagster daemon continues running (doesn't crash)
- Failed run is recorded in Dagster UI with error details
- Next scheduled run (15 minutes later) will retry automatically
- Database retains data from last successful materialization

**And** Dagster UI shows retry attempts and failure details:
- Run timeline displays all 3 retry attempts
- Logs show error messages with full stack traces
- Asset status shows "Failed" with timestamp
- Next scheduled materialization shows in schedules tab

**And** I can verify error handling by simulating failures:
- API timeout: Mock NCAA API with 15s delay → retry triggered
- API 5xx error: Mock server returning 500 → retry triggered
- Network failure: Disconnect network → daemon logs error but continues
- After recovery: Next scheduled run succeeds automatically

**And** the health check endpoint reports degraded status when ingestion is failing (implemented in Story 3.2)

---

## Prerequisites

- Story 2.4 (Dagster asset with RetryPolicy already configured)
- Story 2.2 (NCAA API client with tenacity retry decorator)

---

## Technical Notes

### Retry Logic Architecture

**Two Layers of Retry:**

1. **NCAA Client Layer (tenacity)** - Already implemented in Story 2.2:
   ```python
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10)
   )
   async def fetch_games(self, game_date: date = None) -> List[dict]:
       # HTTP-level retries for transient network issues
   ```

2. **Dagster Asset Layer** - Already implemented in Story 2.4:
   ```python
   @asset(
       retry_policy=RetryPolicy(
           max_retries=3,
           delay=2,  # seconds
           backoff=2.0,  # exponential: 2s, 4s, 8s
       )
   )
   async def ncaa_games(context: AssetExecutionContext) -> dict:
       # Asset-level retries for any failure in materialization
   ```

**Why Two Layers?**
- **Client retries**: Fast recovery for transient network blips (e.g., timeout, connection reset)
- **Asset retries**: Recovery for any failure in the entire materialization (API, database, transform logic)
- Combined: Provides robust error handling at multiple levels

### Error Handling in Dagster Asset

The asset already has proper error handling from Story 2.4:

```python
async def ncaa_games(context: AssetExecutionContext) -> dict:
    logger.info("ncaa_games_asset_started")
    context.log.info("Fetching NCAA games for today")

    client = NCAAClient()
    try:
        raw_games = await client.fetch_games()

        async with context.resources.database.get_session() as session:
            # ... upsert logic
            await session.commit()

        logger.info("ncaa_games_asset_completed", games_processed=len(raw_games))
        return {"games_processed": len(raw_games), "status": "success"}

    except Exception as e:
        # Dagster automatically retries based on RetryPolicy
        logger.error("ncaa_games_asset_failed", error=str(e), exc_info=True)
        context.log.error(f"Asset materialization failed: {e}")
        raise  # Re-raise to trigger Dagster retry
    finally:
        await client.close()
```

**Key Points:**
- Exception is re-raised to trigger Dagster's RetryPolicy
- Full stack trace logged with `exc_info=True`
- Dagster context logger provides observability in UI
- Client cleanup happens in `finally` block

### Dagster Daemon Behavior

**On Asset Materialization Failure:**
1. Dagster RetryPolicy triggers (3 retries with exponential backoff)
2. If all retries fail, run marked as "Failed" in UI
3. Daemon continues running (doesn't crash)
4. Next scheduled run (15 min later) attempts again
5. Previous successful data remains in database

**This is different from APScheduler:**
- No need for try/except to prevent scheduler crash
- Retry logic is declarative (RetryPolicy decorator)
- Full observability in Dagster UI
- Failed runs don't block future runs

### Cached Data

**Natural Caching:**
- Database retains last successful poll's data
- Games table has `updated_at` timestamps
- Queries return last successfully ingested data
- No additional caching mechanism needed

**Staleness Detection:**
```sql
-- Check data freshness
SELECT MAX(updated_at) as last_update,
       NOW() - MAX(updated_at) as age
FROM games
WHERE game_date = CURRENT_DATE;

-- If age > 30 minutes, ingestion may be failing
```

### Health Check Integration

Health check endpoint (Story 3.2) will monitor ingestion status:

```python
# Check Dagster asset materialization via GraphQL API
last_materialization = await get_last_dagster_materialization("ncaa_games")

if last_materialization:
    age_minutes = (datetime.utcnow() - last_materialization.timestamp).total_seconds() / 60

    if age_minutes > 60:
        status = "unhealthy"  # No successful run in 1 hour
    elif age_minutes > 30:
        status = "degraded"  # No successful run in 30 minutes
    else:
        status = "healthy"
```

### Testing Error Handling

**Test 1: Simulate API Timeout**
```python
# Mock NCAA API with slow response
@pytest.mark.asyncio
async def test_api_timeout_triggers_retry(mock_ncaa_api):
    mock_ncaa_api.delay = 15  # 15s delay, exceeds 10s timeout

    # Asset materialization should retry 3 times then fail
    with pytest.raises(Exception):
        await ncaa_games(context)

    # Verify retry attempts logged
    assert "retry_attempt=1" in logs
    assert "retry_attempt=2" in logs
    assert "retry_attempt=3" in logs
```

**Test 2: Simulate Network Failure**
```bash
# Disconnect Docker network
docker network disconnect gamepulse_default dagster-daemon

# Check Dagster logs - should see error but daemon continues
docker compose logs -f dagster-daemon

# Verify Dagster UI shows failed run
open http://localhost:3000

# Reconnect network
docker network connect gamepulse_default dagster-daemon

# Wait for next scheduled run (or trigger manually)
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games

# Verify recovery
```

**Test 3: Simulate API 5xx Error**
```python
@pytest.mark.asyncio
async def test_api_500_error_triggers_retry(mock_ncaa_api):
    mock_ncaa_api.status_code = 500  # Internal server error

    with pytest.raises(Exception):
        await ncaa_games(context)

    # Verify exponential backoff: 2s, 4s, 8s
    assert retry_delays == [2, 4, 8]
```

**Test 4: Database Connection Failure**
```python
@pytest.mark.asyncio
async def test_database_failure_triggers_retry(context):
    # Simulate database connection failure
    context.resources.database.engine = None

    with pytest.raises(Exception):
        await ncaa_games(context)

    # Verify retry policy activated
    assert context.run.retry_count == 3
```

### Verification in Dagster UI

**Failed Run Inspection:**
1. Navigate to http://localhost:3000
2. Go to "Runs" tab
3. Find failed `ncaa_ingestion` run
4. Click run → View timeline:
   - Shows all 3 retry attempts
   - Each attempt has logs
   - Final attempt shows failure reason
5. Check "Assets" tab:
   - `ncaa_games` shows last successful materialization timestamp
   - Status indicator shows "Failed" with recent failed run

**Automatic Recovery:**
1. After fixing issue (API back online, network restored)
2. Next scheduled run (15 min intervals) automatically retries
3. Successful run updates asset status to "Success"
4. Asset lineage graph shows recovery

### Error Logging Pattern

**Structured Logging:**
```python
# Asset start
logger.info("ncaa_games_asset_started")
context.log.info("Fetching NCAA games for today")

# Success
logger.info("ncaa_games_asset_completed", games_processed=12)

# Failure (before retry)
logger.warning("ncaa_games_asset_retry",
    attempt=1,
    error=str(e),
    next_retry_delay_seconds=2
)

# Final failure (after all retries exhausted)
logger.error("ncaa_games_asset_failed",
    error=str(e),
    exc_info=True,
    total_retries=3,
    next_scheduled_run="2025-11-10T15:00:00Z"
)
```

### Monitoring and Alerting

**CloudWatch Alarms (Production):**
- **Data Staleness**: Alert if `MAX(updated_at) > 30 minutes`
- **Consecutive Failures**: Alert if 3+ consecutive Dagster runs fail (45 minutes no data)
- **API Errors**: Alert if seeing HTTP 4xx errors (client misconfiguration)

**Dagster Alerting (Future Enhancement):**
- Configure Dagster sensors to send Slack/email on repeated failures
- Use Dagster's built-in alerting policies for run failures

---

## Definition of Done

- [ ] **Verify RetryPolicy already configured** in Story 2.4's `ncaa_games` asset
- [ ] **Verify tenacity retry decorator** already configured in Story 2.2's NCAA client
- [ ] **Test API timeout scenario**: Mock slow API, verify Dagster retries 3 times
- [ ] **Test API 5xx scenario**: Mock server error, verify exponential backoff (2s, 4s, 8s)
- [ ] **Test network failure**: Disconnect Docker network, verify daemon continues
- [ ] **Test automatic recovery**: Restore connectivity, verify next run succeeds
- [ ] **Verify Dagster UI shows retry attempts** in run timeline
- [ ] **Verify failed runs don't crash daemon**: Check daemon container stays running
- [ ] **Verify database retains cached data**: Last successful poll data remains
- [ ] **Document error handling strategy** in tech-spec or architecture doc
- [ ] **Add tests for error scenarios** to test suite
- [ ] **Verify structured logging** captures all error events with context
- [ ] Changes committed to git

---

## Notes

- **Most retry logic already implemented** in Stories 2.2 and 2.4
- This story focuses on **testing and verification** of error handling
- Dagster's declarative RetryPolicy is more robust than imperative try/except
- Two-layer retry strategy (client + asset) provides defense in depth
- Failed asset materializations are visible in Dagster UI with full context
- Database naturally caches data - no additional caching layer needed
- Health check integration deferred to Story 3.2
