# Story 2.5: Add Retry Logic and Error Handling

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want robust error handling for NCAA API failures,
So that temporary API outages don't crash the polling worker.

---

## Acceptance Criteria

**Given** the NCAA API may occasionally fail or timeout
**When** an API request fails
**Then** the client retries up to 3 times with exponential backoff (2s, 4s, 8s)

**And** if all retries fail, the worker logs the error and continues (doesn't crash)

**And** the worker serves cached data from previous successful poll

**And** the health check endpoint reports degraded status when API is failing

**And** I can simulate API failure (e.g., disconnect internet) and verify:
- Worker logs error but doesn't crash
- Scheduler continues and retries next cycle
- Database still contains data from last successful poll

---

## Prerequisites

- Story 2.4 (polling worker exists)

---

## Technical Notes

**Retry Logic:**
- Already added in Story 2.2 (tenacity decorator on client functions)
- Decorator: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=60))`

**Add try/except in Worker:**
```python
async def poll_ncaa_games():
    try:
        games = await ncaa_client.fetch_todays_games()
        # ... process games
    except Exception as e:
        logger.error("ncaa_poll_failed", error=str(e))
        # Don't re-raise - let scheduler continue
```

**Cached Data:**
- Database naturally caches last poll's data
- No additional caching mechanism needed
- Queries return last successfully polled data

**Health Check Integration:**
- Will be implemented in Story 3.2
- Health check checks last poll timestamp:
  - If `updated_at` > 30 min ago → status "degraded"
  - If `updated_at` > 60 min ago → status "unhealthy"

**Testing:**
```bash
# Simulate network failure
docker network disconnect gamepulse_default backend

# Watch logs - should see error but no crash
docker-compose logs -f backend

# Reconnect
docker network connect gamepulse_default backend

# Verify scheduler continues
```

**APScheduler Behavior:**
- Continues running even if individual job execution fails
- Will retry on next scheduled interval (15 min later)

**Error Logging Pattern:**
```python
logger.error(
    "ncaa_poll_failed",
    error=str(e),
    retry_attempt=attempt_number,
    next_retry_in_seconds=900
)
```

---

## Definition of Done

- [ ] Retry logic verified in NCAA client (from Story 2.2)
- [ ] try/except added to polling worker
- [ ] Worker doesn't crash on API failure
- [ ] Error logged with structured logging
- [ ] Scheduler continues after failure
- [ ] Database retains cached data from last poll
- [ ] Simulated network failure test passed
- [ ] Worker automatically recovers when API available
- [ ] Documentation added explaining error handling strategy
- [ ] Changes committed to git
