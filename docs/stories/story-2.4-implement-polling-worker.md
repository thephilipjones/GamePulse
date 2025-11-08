# Story 2.4: Implement Scheduled Polling Worker with APScheduler

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want a background worker that polls the NCAA API every 15 minutes,
So that game data is continuously updated throughout the day.

---

## Acceptance Criteria

**Given** I have an NCAA API client and Game SQLModel
**When** I create a polling worker using APScheduler
**Then** the worker:
- Runs every 15 minutes (900 seconds) automatically
- Fetches today's games from NCAA API using the client
- For each game, upserts to database (INSERT or UPDATE if game_id exists)
- Logs start/completion with game count: "ncaa_poll_completed, games_fetched=8"
- Handles API failures gracefully (logs error, continues next cycle)

**And** I integrate the scheduler into the FastAPI app lifecycle:
- Start scheduler on app startup using `@app.on_event("startup")` or modern lifespan context manager
- Gracefully shutdown scheduler on `@app.on_event("shutdown")` or lifespan cleanup
- Ensure scheduler doesn't block application startup
- Reference: FastAPI documentation on lifespan events for async context manager pattern

**And** I run an immediate poll on first startup (don't wait 15 min)

**And** I can verify the worker is running: check logs for "ncaa_poll_started" every 15 min

**And** database rows update after each poll cycle

---

## Prerequisites

- Story 2.2 (NCAA API client)
- Story 2.3 (Game model and schemas)

---

## Technical Notes

**Create File:** `backend/app/workers/ncaa_poller.py`

**Add Dependency to pyproject.toml:**
```toml
apscheduler = "^3.11.1"
```

**Worker Function:**
```python
import structlog
from app.services.ncaa_client import NCAAClient
from app.core.db import get_session
from app.models.game import Game

logger = structlog.get_logger()

async def poll_ncaa_games():
    logger.info("ncaa_poll_started")

    try:
        client = NCAAClient()
        games = await client.fetch_todays_games()

        async with get_session() as session:
            for game_data in games:
                # Upsert logic: check if game_id exists
                existing = await session.get(Game, game_data['game_id'])
                if existing:
                    # UPDATE
                    for key, value in game_data.items():
                        setattr(existing, key, value)
                else:
                    # INSERT
                    game = Game(**game_data)
                    session.add(game)

            await session.commit()

        logger.info("ncaa_poll_completed", count=len(games))

    except Exception as e:
        logger.error("ncaa_poll_failed", error=str(e))
```

**Integrate in backend/app/main.py:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.workers.ncaa_poller import poll_ncaa_games

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(
        poll_ncaa_games,
        'interval',
        seconds=900,  # 15 minutes
        id='ncaa_poller',
        replace_existing=True
    )
    scheduler.start()

    # Run immediately on startup
    await poll_ncaa_games()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
```

**Structured Logging:**
- Use structlog: `logger = structlog.get_logger()`
- Log events with context: `logger.info("event_name", key=value)`

**Upsert Pattern:**
- Check if game_id exists in database
- UPDATE if yes, INSERT if no
- SQLModel provides `session.get(Game, game_id)` for checking

---

## Definition of Done

- [ ] Polling worker file created
- [ ] APScheduler dependency added
- [ ] Worker function polls NCAA API
- [ ] Upsert logic implemented correctly
- [ ] Scheduler integrated into FastAPI lifecycle
- [ ] Immediate poll on startup implemented
- [ ] Graceful error handling added
- [ ] Structured logging implemented
- [ ] Verify: logs show "ncaa_poll_started" every 15 min
- [ ] Verify: database updates after each poll
- [ ] Code follows architecture patterns (async/await)
- [ ] Changes committed to git
