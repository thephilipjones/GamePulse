# Story 2.2: Build NCAA API Client with httpx

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** review
**Assignee:** TBD
**Sprint:** Week 1

## Dev Agent Record

### Context Reference
- [Story Context File](2-2-build-ncaa-client.context.xml) - Generated: 2025-11-11

---

## User Story

As a developer,
I want to create an async NCAA API client that fetches game schedules and scores,
So that I can retrieve today's games and their current status.

---

## Acceptance Criteria

**Given** the henrygd/ncaa-api is available at `https://site.web.api.espn.com/apis/v2/scoreboard/basketball`
**When** I create the NCAA API client module
**Then** the client includes these async functions:
- `fetch_todays_games() -> List[dict]`: Returns all games for current date
- `fetch_game_details(game_id: str) -> dict`: Returns detailed info for single game
- `parse_game_data(raw_data: dict) -> GameCreate`: Transforms API response to SQLModel schema

**And** the client uses httpx.AsyncClient for requests

**And** the client includes retry logic with tenacity (3 attempts, exponential backoff)

**And** the client respects the 5 req/sec rate limit (200ms delay between requests)

**And** the client includes error handling for 4xx/5xx responses

**And** I can test the client manually: `python -m app.services.ncaa_client` fetches today's games

---

## Prerequisites

- Story 1.3 (Game SQLModel exists)
- Story 2.1 (teams exist for foreign key constraints)

---

## Technical Notes

**Create File:** `backend/app/services/ncaa_client.py`

**NCAA API Endpoint:**
```
https://site.web.api.espn.com/apis/v2/scoreboard/basketball/mens-college-basketball
```

**Query Params:**
- `?dates={YYYYMMDD}` for specific date (default today)

**Response Structure:**
- JSON with `events[]` array, each event is a game

**Parse Fields:**
- game ID
- home/away team IDs
- scores
- status (scheduled/in-progress/final)
- game clock

**Rate Limit Implementation:**
```python
await asyncio.sleep(0.2)  # 200ms delay between requests
```

**Retry Decorator:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=2, max=60)
)
async def fetch_todays_games():
    # Implementation
```

**Error Handling:**
- Log failures with structlog
- Return empty list on total failure (graceful degradation)

**Add Dependencies to pyproject.toml:**
```toml
httpx = "^0.28.1"
tenacity = "^9.1.2"
```

**Client Pattern:**
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

class NCAAClient:
    BASE_URL = "https://site.web.api.espn.com/apis/v2/scoreboard/basketball/mens-college-basketball"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=60))
    async def fetch_todays_games(self) -> List[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL)
            response.raise_for_status()
            return response.json()
```

---

## Definition of Done

- [x] NCAA client module created
- [x] All three functions implemented (fetch_todays_games, fetch_game_details, parse_game_data)
- [x] httpx.AsyncClient used for async requests
- [x] Retry logic with tenacity implemented
- [x] Rate limiting (200ms delay) implemented
- [x] Error handling for HTTP errors
- [x] Dependencies added to pyproject.toml
- [x] Manual test successful (fetches today's games)
- [x] Structured logging added
- [x] Code follows architecture patterns (async/await, absolute imports)
- [ ] Changes committed to git
