# Story 2.5: Validate Retry Logic and Error Handling

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** ready-for-dev
**Assignee:** TBD
**Sprint:** Week 1
**Story Points:** 3
**Dependencies:** Stories 2.2 (NCAA Client), 2.4 (Dagster Orchestration)

---

## User Story

**As a** data pipeline developer
**I want** to verify that error handling works correctly across all failure scenarios
**So that** the NCAA game ingestion pipeline is resilient to API outages and transient failures

---

## Business Context

GamePulse's NCAA game data ingestion pipeline must handle external API failures gracefully to maintain the "near real-time" data freshness promised in the PRD (NFR-1.4: data updated within 20 minutes). Stories 2.2 and 2.4 have already implemented two layers of retry logic - this story validates that implementation through comprehensive testing.

**Impact of Poor Error Handling:**
- Failed polls leave dashboard with stale data (>30 minutes old)
- Dagster daemon crashes prevent future automatic recovery
- Users see "Last updated 2 hours ago" warning (degraded UX)
- Demo reliability suffers during March Madness peak loads

**Success Criteria:**
- Temporary API failures auto-recover within 15 minutes (next poll)
- Daemon never crashes, even during prolonged outages
- Health check endpoint accurately reports degraded status

---

## Acceptance Criteria

### AC1: Verify Dagster RetryPolicy Configuration
**Given** the `ncaa_games` asset from Story 2.4
**When** I inspect the asset decorator
**Then** it has `RetryPolicy(max_retries=3, delay=2, backoff=2.0)` configured
**And** exponential backoff is: 2s, 4s, 8s

**Validation:**
```python
from app.assets.ncaa_games import ncaa_games
assert ncaa_games._retry_policy.max_retries == 3
assert ncaa_games._retry_policy.delay == 2
assert ncaa_games._retry_policy.backoff == 2.0
```

---

### AC2: Verify NCAA Client Tenacity Retry Decorator
**Given** the NCAAClient from Story 2.2
**When** I inspect the `fetch_games()` method
**Then** it has `@retry(stop=stop_after_attempt(3))` decorator
**And** uses exponential backoff with `wait_exponential(multiplier=1, min=2, max=10)`

**Validation:**
```python
from app.services.ncaa_client import NCAAClient
import inspect
source = inspect.getsource(NCAAClient.fetch_games)
assert "@retry" in source
assert "stop_after_attempt(3)" in source
```

---

### AC3: Test API Timeout Scenario
**Given** a mocked NCAA API with 15-second response delay (exceeds 10s timeout)
**When** the asset materialization executes
**Then** Dagster retries 3 times with exponential backoff
**And** after all retries fail, the run is marked "Failed" in Dagster UI
**And** the daemon continues running (doesn't crash)
**And** logs show all retry attempts with timestamps

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_api_timeout_triggers_retry(mocker, test_context):
    """Verify timeout triggers Dagster RetryPolicy"""
    # Mock httpx with 15s delay
    mock_client = mocker.patch('app.services.ncaa_client.httpx.AsyncClient')
    mock_client.return_value.get.side_effect = httpx.TimeoutException()

    # Asset should fail after 3 retries
    with pytest.raises(httpx.TimeoutException):
        await ncaa_games(test_context)

    # Verify 3 attempts (initial + 2 retries from tenacity, then Dagster retries)
    assert mock_client.return_value.get.call_count == 3
```

---

### AC4: Test API 5xx Error Scenario
**Given** a mocked NCAA API returning HTTP 500 (Internal Server Error)
**When** the asset materialization executes
**Then** tenacity retries within the client (3 attempts)
**And** if all client retries fail, Dagster RetryPolicy triggers (3 more attempts)
**And** exponential backoff is applied: 2s, 4s, 8s
**And** final failure is logged with full stack trace (`exc_info=True`)

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_api_500_error_retry_backoff(mocker, caplog, test_context):
    """Verify 5xx errors trigger retry with exponential backoff"""
    import time
    mock_get = mocker.patch('httpx.AsyncClient.get')
    mock_get.side_effect = httpx.HTTPStatusError(
        message="500", request=None, response=mocker.Mock(status_code=500)
    )

    start_time = time.time()
    with pytest.raises(httpx.HTTPStatusError):
        await ncaa_games(test_context)
    elapsed = time.time() - start_time

    # Verify total backoff time: 2 + 4 + 8 = ~14 seconds
    assert elapsed >= 14, "Exponential backoff not applied"

    # Verify structured logging
    assert "ncaa_games_asset_failed" in caplog.text
    assert "exc_info" in caplog.records[-1].__dict__
```

---

### AC5: Test HTTP 4xx Error Scenario
**Given** a mocked NCAA API returning HTTP 404 (Not Found) or 401 (Unauthorized)
**When** the asset materialization executes
**Then** no retries are triggered (client errors are not retryable)
**And** asset fails immediately
**And** error is logged with descriptive message

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_api_404_no_retry(mocker, caplog, test_context):
    """Verify 4xx errors do NOT trigger retry"""
    mock_get = mocker.patch('httpx.AsyncClient.get')
    mock_get.side_effect = httpx.HTTPStatusError(
        message="404", request=None, response=mocker.Mock(status_code=404)
    )

    with pytest.raises(httpx.HTTPStatusError):
        await ncaa_games(test_context)

    # Only 1 attempt (no retries)
    assert mock_get.call_count == 1
    assert "ncaa_games_asset_failed" in caplog.text
```

---

### AC6: Test Network Failure Scenario
**Given** Docker network disconnected during asset materialization
**When** the NCAA API call times out
**Then** retries are attempted
**And** after all retries fail, the run is marked "Failed"
**And** Dagster daemon continues running (verified via `docker compose ps`)
**And** next scheduled run (15 min later) executes automatically

**Manual Test Procedure:**
```bash
# 1. Start Dagster
docker compose up -d

# 2. Trigger manual materialization
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games

# 3. Immediately disconnect network
docker network disconnect gamepulse_default dagster-daemon

# 4. Watch logs for retry attempts
docker compose logs -f dagster-daemon

# 5. Verify daemon stays running
docker compose ps | grep dagster-daemon | grep "Up"

# 6. Reconnect network
docker network connect gamepulse_default dagster-daemon

# 7. Verify next scheduled run succeeds (wait 15 min or trigger manually)
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games
```

---

### AC7: Test Partial Failure Handling
**Given** NCAA API returns 10 games, but 1 game has invalid data (missing team_id)
**When** asset materialization processes the batch
**Then** the 9 valid games are saved to database
**And** the 1 invalid game is skipped with logged warning
**And** asset materialization completes successfully
**And** metadata shows `games_processed=9, games_skipped=1`

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_partial_failure_saves_valid_games(mocker, test_db_session, test_context):
    """Verify partial failures don't prevent valid data from being saved"""
    mock_fetch = mocker.patch('app.services.ncaa_client.NCAAClient.fetch_games')
    mock_fetch.return_value = [
        {"id": "1", "home": {"id": "duke"}, "away": {"id": "unc"}, ...},  # Valid
        {"id": "2", "home": {}, "away": {"id": "uk"}, ...},  # Missing home team
        {"id": "3", "home": {"id": "kansas"}, "away": {"id": "kentucky"}, ...},  # Valid
    ]

    result = await ncaa_games(test_context)

    # Verify 2 games saved (1 skipped)
    games = test_db_session.exec(select(Game)).all()
    assert len(games) == 2
    assert result["games_processed"] == 2
    assert result["games_skipped"] == 1
```

---

### AC8: Verify Dagster UI Retry Timeline
**Given** a failed asset materialization with 3 retries
**When** I navigate to Dagster UI at http://localhost:3000
**Then** the "Runs" tab shows the failed run
**And** clicking the run shows a timeline with 4 attempts (initial + 3 retries)
**And** each attempt has its own log output
**And** final attempt shows the failure reason
**And** asset status page shows last successful materialization timestamp

**Manual Verification:**
1. Trigger failure (mock API with 500 error)
2. Open http://localhost:3000
3. Navigate to Runs → Select failed run
4. Verify timeline shows 4 attempts
5. Verify logs contain error messages for each attempt
6. Navigate to Assets → ncaa_games
7. Verify last successful materialization timestamp displayed

---

### AC9: Verify Cached Data Retention
**Given** the last successful poll was 30 minutes ago
**And** current poll is failing due to API outage
**When** I query the games table
**Then** the last successful poll's data is still present
**And** `updated_at` timestamps show data is 30 minutes old
**And** no data is lost or corrupted

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_failed_poll_retains_cached_data(test_db_session, mocker, test_context):
    """Verify failed polls don't corrupt existing data"""
    # First successful poll
    mocker.patch('app.services.ncaa_client.NCAAClient.fetch_games').return_value = [
        {"id": "1", "home": {"id": "duke", "score": 50}, "away": {"id": "unc", "score": 48}, ...}
    ]
    await ncaa_games(test_context)

    original_game = test_db_session.get(Game, "ncaam_1")
    assert original_game.home_score == 50

    # Second poll fails
    mocker.patch('app.services.ncaa_client.NCAAClient.fetch_games').side_effect = Exception()

    with pytest.raises(Exception):
        await ncaa_games(test_context)

    # Verify original data unchanged
    test_db_session.refresh(original_game)
    assert original_game.home_score == 50  # Not corrupted
```

---

### AC10: Verify Structured Logging
**Given** various failure scenarios (timeout, 5xx, network)
**When** errors occur
**Then** all errors are logged with structured context:
- `event="ncaa_games_asset_failed"`
- `error=<exception message>`
- `exc_info=True` (full stack trace)
- `retry_attempt=<1-3>`
- `next_retry_delay_seconds=<2|4|8>`

**Test Implementation:**
```python
@pytest.mark.asyncio
async def test_structured_error_logging(mocker, caplog, test_context):
    """Verify error logging includes all required context fields"""
    mocker.patch('httpx.AsyncClient.get').side_effect = Exception("API down")

    with pytest.raises(Exception):
        await ncaa_games(test_context)

    # Verify structured logging fields
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) > 0

    last_error = error_logs[-1]
    assert "ncaa_games_asset_failed" in last_error.message
    assert "error" in last_error.__dict__
    assert last_error.exc_info is not None  # Stack trace present
```

---

## Technical Implementation

### Existing Retry Logic (Already Implemented)

**Layer 1: NCAA Client Tenacity Retry (Story 2.2)**
```python
# backend/app/services/ncaa_client.py
from tenacity import retry, stop_after_attempt, wait_exponential

class NCAAClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch_games(self, game_date: date = None) -> List[dict]:
        """
        HTTP-level retries for transient network issues.
        Retries: 3 attempts with exponential backoff (2s, 4s, 8s max)
        """
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
```

**Layer 2: Dagster Asset RetryPolicy (Story 2.4)**
```python
# backend/app/assets/ncaa_games.py
from dagster import asset, RetryPolicy

@asset(
    name="ncaa_games",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,  # seconds
        backoff=2.0,  # exponential: 2s, 4s, 8s
    ),
    group_name="data_ingestion",
)
async def ncaa_games(context: AssetExecutionContext) -> dict:
    """
    Asset-level retries for any failure in materialization.
    Covers: API failures, database errors, transform logic errors.
    """
    try:
        client = NCAAClient()
        raw_games = await client.fetch_games()
        # ... upsert logic
        return {"games_processed": len(raw_games), "status": "success"}
    except Exception as e:
        logger.error("ncaa_games_asset_failed", error=str(e), exc_info=True)
        raise  # Re-raise to trigger Dagster retry
```

### Test Files to Create

**File 1: `backend/app/tests/services/test_ncaa_client_retry.py`**
- Test timeout triggers retry
- Test 5xx error triggers retry
- Test 4xx error does NOT retry
- Test exponential backoff timing

**File 2: `backend/app/tests/assets/test_ncaa_games_retry.py`**
- Test Dagster RetryPolicy configuration
- Test partial failure handling
- Test cached data retention on failure
- Test daemon continues after failure

**File 3: Manual test script `backend/scripts/test_network_failure.sh`**
- Disconnect Docker network
- Verify daemon continues
- Reconnect and verify recovery

---

## Definition of Done

### Code Verification
- [ ] Verified `ncaa_games` asset has `RetryPolicy(max_retries=3, delay=2, backoff=2.0)`
- [ ] Verified `NCAAClient.fetch_games()` has `@retry` decorator with exponential backoff
- [ ] Verified error logging uses `exc_info=True` for stack traces
- [ ] Verified `finally` block closes httpx client properly

### Test Coverage
- [ ] Created `test_ncaa_client_retry.py` with 4+ test cases
- [ ] Created `test_ncaa_games_retry.py` with 5+ test cases
- [ ] All retry tests passing (`pytest app/tests/services/test_ncaa_client_retry.py -v`)
- [ ] All asset retry tests passing (`pytest app/tests/assets/test_ncaa_games_retry.py -v`)
- [ ] Test coverage >80% for retry logic paths

### Manual Verification
- [ ] Simulated API timeout → Verified 3 retries in Dagster UI
- [ ] Simulated network failure → Verified daemon stays running
- [ ] Verified Dagster UI shows retry timeline with 4 attempts
- [ ] Verified automatic recovery after network restored
- [ ] Verified database retains cached data during outage
- [ ] Checked logs contain structured error events with full context

### Documentation
- [ ] Updated tech-spec-epic-2.md with retry strategy section
- [ ] Documented two-layer retry architecture (client + asset)
- [ ] Added runbook entry for "How to diagnose failed ingestion"
- [ ] Updated health check documentation (deferred to Story 3.2)

### Quality Gates
- [ ] All 10 acceptance criteria validated (AC1-AC10)
- [ ] No regressions in existing tests
- [ ] Linting passing (`mypy`, `ruff`)
- [ ] Changes committed to git with descriptive message
- [ ] Story marked as DONE in sprint-status.yaml

---

## Dependencies

### Upstream (Blockers)
- **Story 2.2** (NCAA API Client): Must have tenacity retry decorator implemented
- **Story 2.4** (Dagster Orchestration): Must have asset with RetryPolicy configured

### Downstream (Enables)
- **Story 3.2** (Health Check Endpoint): Will query Dagster for last materialization status
- **Epic 4** (Reddit Sentiment): Will use same retry pattern for Reddit API

---

## Technical Notes

### Why Two Layers of Retry?

**Client Layer (tenacity)**:
- Fast recovery for HTTP-level transient failures
- Handles: timeouts, connection resets, 5xx errors
- Retry timing: 2s, 4s, 8s (max 14s total)

**Asset Layer (Dagster RetryPolicy)**:
- Slower recovery for any failure in materialization
- Handles: client failures, database errors, transform errors
- Retry timing: 2s, 4s, 8s (independent of client retries)

**Combined Effect**:
If both layers fail all retries, total time before final failure: ~30 seconds.
Next scheduled run in 15 minutes provides automatic recovery window.

### Dagster Daemon Behavior

**Key Property**: Dagster daemon is designed to never crash on asset failures.

- Failed asset materializations are isolated to individual runs
- Daemon continues scheduling future runs
- No need for defensive try/except to prevent scheduler crashes
- Full observability in Dagster UI (vs APScheduler black box)

### Error Logging Best Practices

**Good Logging** (Implemented):
```python
logger.error("ncaa_games_asset_failed",
    error=str(e),
    exc_info=True,  # Full stack trace
    retry_attempt=attempt_num,
    next_retry_delay=delay_seconds
)
```

**Bad Logging** (Avoid):
```python
logger.error(f"Failed: {e}")  # No stack trace, no context, not queryable
```

### Monitoring Integration

**CloudWatch Alarms (Production)**:
- **Metric**: `MAX(updated_at)` from games table
- **Threshold**: Alert if data >30 minutes stale
- **Action**: SNS notification to ops team

**Dagster Sensors (Future Enhancement)**:
- Configure Dagster sensors to detect repeated failures
- Send Slack notifications after 3 consecutive failures
- Escalate to PagerDuty after 6 consecutive failures

---

## Story Points Justification

**Estimate: 3 points**

**Complexity**:
- Low code changes (retry logic already exists)
- Medium test complexity (need to mock failures correctly)
- Low infrastructure changes (no new services)

**Effort Breakdown**:
- Test implementation: 4 hours (10 test cases)
- Manual testing/verification: 2 hours (network failure scenarios)
- Dagster UI inspection: 1 hour (verify timeline displays)
- Documentation: 1 hour (update tech-spec, runbook)
- **Total**: ~8 hours (~3 story points at 3 hours/point)

---

## References

- **PRD**: NFR-4.2 (Graceful Degradation), NFR-1.4 (Data Freshness)
- **Architecture**: ADR-007 (Dagster for Data Orchestration)
- **Tech Spec**: Epic 2 AC-5 (Retry Logic and Error Handling)
- **Dagster Docs**: [Retry Policies](https://docs.dagster.io/concepts/ops-jobs-graphs/op-retries)
- **Tenacity Docs**: [Exponential Backoff](https://tenacity.readthedocs.io/en/latest/#exponential-backoff)

---

## Dev Agent Record

### Context Reference
- [Story Context XML](./2-5-add-retry-logic.context.xml)

### Completion Notes
*Developer will update this section upon story completion*

**Implementation Summary:**
- [ ] Retry logic verified in Stories 2.2 and 2.4
- [ ] Test suite created and passing
- [ ] Manual scenarios validated
- [ ] Dagster UI behavior confirmed

**Challenges Encountered:**
- TBD

**Lessons Learned:**
- TBD

**Files Modified:**
- TBD

---

**Last Updated:** 2025-11-13
**Generated by:** Bob (Scrum Master) via *create-story workflow
