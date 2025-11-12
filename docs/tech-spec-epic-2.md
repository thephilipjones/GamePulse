# Epic Technical Specification: Game Data Ingestion (Batch)

Date: 2025-11-10
Author: Philip
Epic ID: 2
Status: Draft

---

## Overview

Epic 2 establishes the foundational batch data ingestion pipeline for NCAA Men's Basketball game data, implementing scheduled polling of the NCAA API every 15 minutes to capture game schedules, live scores, and final results. This epic demonstrates modern data orchestration patterns using Dagster's asset-oriented paradigm, async Python (httpx), and resilient error handling (tenacity retry logic with Dagster's built-in retry policies).

The epic builds upon Epic 1's infrastructure foundation by implementing the first production data source, utilizing the dimensional schema (teams, conferences, games) established in Story 1.4. Game data flows from the henrygd/ncaa-api self-hosted client into PostgreSQL as Dagster software-defined assets, with rivalry detection automatically computed from conference relationships. This represents the "batch processing paradigm" component of GamePulse's dual-paradigm architecture (batch + streaming), optimized for rate-limited APIs (5 req/sec NCAA limit) where 15-minute polling provides sufficient freshness for basketball score tracking while respecting API constraints. Dagster's asset catalog provides visual data lineage demonstrating how game data flows through the system, valuable for portfolio demonstrations in data solutions architect interviews.

## Objectives and Scope

**In Scope:**

- Create multi-sport dimensional data (teams, conferences) as JSON seed files loaded into database
- Implement async NCAA API client using httpx with 5 req/sec rate limiting
- Create Game SQLModel schema and Alembic migration for games table
- Implement Dagster self-hosted orchestration with software-defined assets for NCAA game data
- Define Dagster assets and sensors for game polling every 15 minutes (900 seconds) during NCAA basketball season
- Configure Dagster webserver and daemon containers in Docker Compose
- Add Dagster's built-in retry policies with exponential backoff for external API failures
- Implement rivalry detection based on conference matching (same conference = rivalry)
- Store game data with proper timestamp handling (UTC) and status transitions (scheduled → live → final)
- Comprehensive error handling with structured logging and Dagster's observability UI

**Out of Scope:**

- Reddit social sentiment ingestion (Epic 4)
- Excitement score calculation (Epic 5)
- Betfair streaming odds integration (Epic 6)
- Frontend dashboard enhancements (Epic 8) - basic display from Epic 3 sufficient
- Real-time WebSocket updates - 15-minute polling acceptable for MVP
- Historical data backfill beyond current season
- Player-level data ingestion - focus on team/game aggregates only
- Advanced analytics or win probability calculations

## System Architecture Alignment

Epic 2 implements the **Data Ingestion Layer (Batch Processing)** as defined in the Architecture document's module boundaries. Key architectural alignments:

**Architecture Components Referenced:**
- **Backend Stack**: FastAPI 0.115+ async framework with SQLModel ORM and Alembic migrations (from Epic 1)
- **Orchestration**: Dagster 1.9+ self-hosted (webserver + daemon containers) for asset-oriented data pipeline orchestration
- **Batch Processing**: httpx 0.28.1 for async HTTP client within Dagster assets
- **Database**: PostgreSQL 16 + TimescaleDB for both application data (teams, games) and Dagster metadata storage
- **Error Handling**: Dagster's built-in retry policies with exponential backoff per Architecture NFR-4.2 (Graceful Degradation)
- **Logging**: structlog 25.5.0 for structured JSON logs + Dagster's observability UI for asset lineage and run history

**Design Constraints:**
- **Single EC2 instance** (t2.micro, 1 vCPU, 1GB RAM) - Dagster webserver and daemon run as separate Docker containers alongside FastAPI
- **Rate limiting compliance**: NCAA API enforces 5 req/sec limit - client implements 200ms delay between requests
- **Polling frequency**: 15-minute intervals balance API limits vs data freshness (NFR-1.4 acceptable staleness)
- **Multi-sport support**: Epic 1 schema designed for sport-agnostic data - Epic 2 seeds NCAAM data only, but structure supports NFL/NBA expansion
- **Dagster deployment strategy**: Start with Dagster Cloud 30-day trial for learning, migrate to self-hosted before trial ends (cost savings: $200-600/month → $0)

**Integration Points:**
- **Data Flow**: NCAA API (henrygd/ncaa-api) → httpx client (in Dagster asset) → SQLModel ORM → PostgreSQL games table
- **Orchestration**: Dagster daemon runs sensors that trigger asset materializations every 15 minutes
- **Observability**: Dagster webserver UI (port 3000) provides asset lineage graph and run history
- **Epic 3 Dependency**: Games endpoint (`GET /api/games/today`) reads from games table populated by Dagster NCAA games asset

## Detailed Design

### Services and Modules

**Epic 2 Module Structure:**

| Module | Responsibility | Location | Inputs | Outputs |
|--------|---------------|----------|--------|---------|
| **NCAA API Client** | Fetch game schedules and scores from NCAA API | `backend/app/services/ncaa_client.py` | Game date, division filter | List[GameData] (raw API response) |
| **Dagster Definitions** | Define software-defined assets and schedules | `backend/app/dagster_definitions.py` | Asset dependencies, sensor triggers | Dagster repository with assets |
| **NCAA Games Asset** | Dagster asset for ingesting NCAA game data | `backend/app/assets/ncaa_games.py` | None (sensor-triggered) | Materialized game data in PostgreSQL |
| **Game Model** | SQLModel schema for games table | `backend/app/models/game.py` | API data transformation | ORM object for database persistence |
| **Dimensional Data Seed** | JSON files for teams and conferences | `backend/app/data/teams.json`, `conferences.json` | Manual curation | Database seed data via Alembic migration |
| **Rivalry Detection Service** | Compute rivalry_factor from conference matching | `backend/app/services/rivalry_detector.py` | home_team, away_team conference IDs | rivalry_factor (float 1.0-1.5) |
| **Database Resource** | Dagster resource for PostgreSQL connection | `backend/app/resources/database.py` | Connection config | SQLModel async session factory |

**Module Interaction Flow:**

```
Dagster Daemon (separate container)
    ↓ (sensor checks every 30s)
game_polling_sensor() evaluates (triggers every 15 min)
    ↓ (triggers materialization)
@asset: ncaa_games
    ↓ (async call within asset)
ncaa_client.py::fetch_today_games()
    ↓ (httpx GET with Dagster retry policy)
NCAA API (henrygd/ncaa-api)
    ↓ (JSON response)
ncaa_client.py::parse_game_data()
    ↓ (transform to Game SQLModel)
rivalry_detector.py::calculate_rivalry()
    ↓ (lookup team conferences, compute factor)
game.py::Game (SQLModel ORM)
    ↓ (async session.add, session.commit via Dagster resource)
PostgreSQL games table
    ↓
Dagster records asset materialization metadata
```

**Dagster Configuration (Workspace & Repository):**

```python
# backend/app/dagster_definitions.py
from dagster import Definitions, ScheduleDefinition, define_asset_job
from app.assets.ncaa_games import ncaa_games
from app.resources.database import database_resource

# Define job that materializes NCAA games asset
ncaa_ingestion_job = define_asset_job(
    name="ncaa_ingestion",
    selection=[ncaa_games],
)

# Schedule job every 15 minutes
ncaa_schedule = ScheduleDefinition(
    job=ncaa_ingestion_job,
    cron_schedule="*/15 * * * *",  # Every 15 minutes
)

defs = Definitions(
    assets=[ncaa_games],
    schedules=[ncaa_schedule],
    resources={"database": database_resource},
)
```

**Note:** FastAPI lifecycle integration is no longer needed - Dagster daemon manages scheduling independently.

**Detailed Module Specifications:**

**1. NCAA API Client (`backend/app/services/ncaa_client.py`):**

```python
import httpx
from typing import List
from datetime import datetime, date
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

class NCAAClient:
    """Async client for NCAA Men's Basketball API (henrygd/ncaa-api)"""

    BASE_URL = "https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1"
    RATE_LIMIT_DELAY = 0.2  # 200ms = 5 req/sec

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch_games(self, game_date: date = None) -> List[dict]:
        """
        Fetch games for specified date (defaults to today).
        Returns raw API response as list of game dicts.
        """
        date_str = (game_date or date.today()).strftime("%Y%m%d")
        url = f"{self.BASE_URL}/{date_str}/scoreboard.json"

        logger.info("ncaa_api_fetch_started", url=url, date=date_str)

        response = await self.client.get(url)
        response.raise_for_status()

        data = response.json()
        games = data.get("games", [])

        logger.info("ncaa_api_fetch_completed", games_count=len(games))
        return games

    async def close(self):
        await self.client.aclose()
```

**2. NCAA Games Asset (`backend/app/assets/ncaa_games.py`):**

```python
from dagster import asset, RetryPolicy, AssetExecutionContext
from app.services.ncaa_client import NCAAClient
from app.services.rivalry_detector import calculate_rivalry_factor
from app.models.game import Game
from datetime import datetime
from sqlmodel import select
import structlog

logger = structlog.get_logger()

@asset(
    name="ncaa_games",
    description="NCAA Men's Basketball game data fetched from NCAA API",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,  # seconds
        backoff=2.0,  # exponential: 2s, 4s, 8s
    ),
    group_name="data_ingestion",
)
async def ncaa_games(context: AssetExecutionContext) -> dict:
    """
    Dagster asset: Fetch and materialize NCAA game data.

    Returns:
        Dict with games_processed count and status
    """
    logger.info("ncaa_games_asset_started")
    context.log.info("Fetching NCAA games for today")

    client = NCAAClient()
    try:
        # Fetch today's games from NCAA API
        raw_games = await client.fetch_games()

        # Get database session from Dagster resource
        async with context.resources.database.get_session() as session:
            for game_data in raw_games:
                # Transform API response to Game model
                game = await transform_game_data(game_data, session)

                # Upsert (insert or update existing game)
                existing = await session.get(Game, game.game_id)
                if existing:
                    # Update scores and status
                    existing.home_score = game.home_score
                    existing.away_score = game.away_score
                    existing.game_status = game.game_status
                    existing.game_clock = game.game_clock
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(game)

            await session.commit()

        logger.info("ncaa_games_asset_completed", games_processed=len(raw_games))
        context.log.info(f"Materialized {len(raw_games)} games")

        # Return metadata for Dagster to track
        return {
            "games_processed": len(raw_games),
            "status": "success"
        }

    except Exception as e:
        logger.error("ncaa_games_asset_failed", error=str(e), exc_info=True)
        context.log.error(f"Asset materialization failed: {e}")
        raise
    finally:
        await client.close()


async def transform_game_data(game_data: dict, session) -> Game:
    """Transform NCAA API response to Game SQLModel"""
    home_team_id = f"ncaam_{game_data['home']['id']}"
    away_team_id = f"ncaam_{game_data['away']['id']}"

    rivalry_factor = await calculate_rivalry_factor(
        home_team_id, away_team_id, session
    )

    return Game(
        game_id=f"ncaam_{game_data['id']}",
        sport="ncaam",
        game_date=datetime.fromisoformat(game_data['date']),
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_score=int(game_data['home'].get('score', 0)),
        away_score=int(game_data['away'].get('score', 0)),
        game_status=map_status(game_data['status']['state']),
        game_clock=game_data['status'].get('clock'),
        venue=game_data.get('venue', {}).get('fullName'),
        rivalry_factor=rivalry_factor,
    )


def map_status(api_status: str) -> str:
    """Map NCAA API status to GamePulse status"""
    mapping = {"pre": "scheduled", "in": "live", "post": "final"}
    return mapping.get(api_status, "scheduled")
```

**3. Rivalry Detection Service (`backend/app/services/rivalry_detector.py`):**

```python
from app.models.team import Team
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

async def calculate_rivalry_factor(
    home_team_id: str,
    away_team_id: str,
    session: AsyncSession
) -> float:
    """
    Calculate rivalry factor based on conference matching.

    Returns:
        1.0 = normal game (different conferences)
        1.2 = same conference (conference rivalry)
        1.5 = explicit rivalry (from team_rivalries table - future)
    """
    home_team = await session.get(Team, home_team_id)
    away_team = await session.get(Team, away_team_id)

    if not home_team or not away_team:
        return 1.0

    # Same conference = conference rivalry
    if home_team.team_group_id == away_team.team_group_id:
        return 1.2

    # TODO: Epic 5+ - Check team_rivalries table for explicit rivalries

    return 1.0
```

### Data Models and Contracts

**Game SQLModel Schema (`backend/app/models/game.py`):**

```python
from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional

class Game(SQLModel, table=True):
    """
    SQLModel for games table (inherits from Epic 1 schema).
    Tracks NCAA Men's Basketball games with live score updates.
    """
    __tablename__ = "games"

    # Primary key
    game_id: str = Field(primary_key=True)  # Format: "ncaam_{api_id}"

    # Multi-sport support
    sport: str = Field(index=True, default="ncaam")

    # Game metadata
    game_date: datetime = Field(index=True)
    game_start_time: Optional[datetime] = None
    game_end_time: Optional[datetime] = None
    venue: Optional[str] = None

    # Teams (foreign keys to teams table from Epic 1)
    home_team_id: str = Field(foreign_key="teams.team_id")
    away_team_id: str = Field(foreign_key="teams.team_id")

    # Live scores (updated every 15 min)
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)

    # Game status tracking
    game_status: Optional[str] = Field(index=True)  # "scheduled", "live", "halftime", "final"
    game_clock: Optional[str] = None  # "2:34 2nd Half"

    # Game type classification
    game_type: str = Field(default="regular_season", index=True)
    # Enum values: "regular_season", "conference_tournament", "ncaa_tournament"

    # Rivalry detection (calculated from team conferences)
    rivalry_factor: Optional[float] = None  # 1.0 = normal, 1.2 = conference, 1.5 = historic

    # Optional enrichment fields
    broadcast_network: Optional[str] = None
    attendance: Optional[int] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**NCAA API Response Contract (henrygd/ncaa-api):**

```json
// GET https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/20251110/scoreboard.json
{
  "games": [
    {
      "id": "401234567",
      "date": "2025-11-10T19:00:00Z",
      "home": {
        "id": "150",
        "names": {
          "short": "Duke",
          "full": "Duke Blue Devils"
        },
        "score": "78"
      },
      "away": {
        "id": "153",
        "names": {
          "short": "UNC",
          "full": "North Carolina Tar Heels"
        },
        "score": "81"
      },
      "status": {
        "state": "post",  // "pre", "in", "post"
        "detail": "Final",
        "clock": "0:00"
      },
      "venue": {
        "fullName": "Cameron Indoor Stadium"
      }
    }
  ]
}
```

**API Status Mapping:**

| NCAA API Status | GamePulse Status | Description |
|----------------|------------------|-------------|
| `pre` | `scheduled` | Game not yet started |
| `in` | `live` | Game in progress |
| `in` (halftime) | `halftime` | Detected via clock analysis |
| `post` | `final` | Game completed |

### APIs and Interfaces

**Epic 2 does not expose new REST API endpoints** - it provides backend data ingestion only. The games table populated by Epic 2 will be consumed by Epic 3's `GET /api/games/today` endpoint.

**Internal Interfaces:**

**1. NCAA API Client Interface (`ncaa_client.py`):**

```python
class NCAAClient:
    async def fetch_games(self, game_date: date = None) -> List[dict]
    async def close()
```

**2. Rivalry Detection Interface (`rivalry_detector.py`):**

```python
async def calculate_rivalry_factor(
    home_team_id: str,
    away_team_id: str,
    session: AsyncSession
) -> float
```

**3. Dagster Asset Interface (`assets/ncaa_games.py`):**

```python
@asset
async def ncaa_games(context: AssetExecutionContext) -> dict
    # Returns metadata dict with games_processed count
```

**Database Write Interface (SQLModel ORM):**

Epic 2 writes to the `games` table established in Epic 1:

```python
# Upsert pattern (insert or update)
async with get_session() as session:
    existing_game = await session.get(Game, game_id)
    if existing_game:
        existing_game.home_score = new_score
        existing_game.updated_at = datetime.utcnow()
    else:
        session.add(new_game)
    await session.commit()
```

### Workflows and Sequencing

**Workflow 1: Initial Dimensional Data Seeding (One-Time Setup)**

```
Developer executes Story 2.1:
    ↓
Create backend/app/data/teams.json (20 NCAAM teams)
Create backend/app/data/conferences.json (major conferences)
    ↓
Create Alembic migration: seed_dimensional_data.py
    ↓
Migration reads JSON files and inserts into teams, team_groups tables
    ↓
Execute: alembic upgrade head
    ↓
Verify: SELECT COUNT(*) FROM teams; (expect 20 rows)
        SELECT COUNT(*) FROM team_groups; (expect ~6 conferences)
    ↓
Dimensional data ready for game ingestion
```

**Workflow 2: Scheduled Game Polling (Continuous - Every 15 Minutes)**

```
Dagster Schedule (cron: */15 * * * *)
    ↓
Dagster daemon checks schedule → triggers run
    ↓
@asset: ncaa_games materialization starts
    ↓
NCAAClient.fetch_games(today) within asset
    ↓
httpx GET with Dagster RetryPolicy (3 attempts, exponential backoff 2s, 4s, 8s)
    ↓
NCAA API responds with games JSON
    ↓
For each game in response:
    Parse API data → Transform to Game SQLModel
    Lookup home_team, away_team from teams table
    Calculate rivalry_factor (conference matching)
    Check if game_id exists in games table
        IF exists: UPDATE scores, status, clock, updated_at
        ELSE: INSERT new Game record
    ↓
Commit transaction (all games in single commit)
    ↓
Log completion: "ncaa_games_asset_completed", games_processed=N
    ↓
Dagster records asset materialization metadata
    ↓
Wait 15 minutes (next schedule tick) → Repeat
```

**Workflow 3: Error Handling and Retry Logic**

```
NCAA API call initiated
    ↓
[Attempt 1] httpx.get(url, timeout=10s)
    ↓
    ├─ Success (HTTP 200) → Parse JSON, proceed
    │
    ├─ Timeout (>10s) → Wait 2s, retry
    │   ↓
    │   [Attempt 2] httpx.get(url)
    │   ↓
    │   ├─ Success → Proceed
    │   ├─ HTTP 5xx → Wait 4s, retry
    │   │   ↓
    │   │   [Attempt 3] httpx.get(url)
    │   │   ↓
    │   │   ├─ Success → Proceed
    │   │   └─ Failure → Log error, abort job, wait 15 min for next cycle
    │   │
    │   └─ HTTP 4xx (client error) → Log error, abort (no retry)
    │
    └─ Network error → Wait 2s, retry (same as timeout)
```

**Workflow 4: Game Status Transition Detection**

```
Poll at T=0 (7:00 PM):
    game_status = "scheduled"
    home_score = 0, away_score = 0
    game_clock = null
    ↓
Poll at T=15 (7:15 PM):
    NCAA API: status.state = "in"
    → game_status = "live"
    home_score = 15, away_score = 12
    game_clock = "10:34 1st Half"
    ↓
Poll at T=30 (7:30 PM):
    NCAA API: status.state = "in", clock = "20:00 2nd Half"
    → game_status = "halftime" (detected via clock analysis)
    home_score = 38, away_score = 35
    ↓
Poll at T=120 (9:00 PM):
    NCAA API: status.state = "post", detail = "Final"
    → game_status = "final"
    home_score = 78, away_score = 81
    game_clock = "0:00"
    game_end_time = NOW()
```

**Workflow 5: Dagster Daemon Lifecycle**

```
[Docker Compose Startup]
    ↓
Start dagster-webserver container (port 3000)
    ↓
Start dagster-daemon container
    ↓
Dagster daemon connects to PostgreSQL (dagster schema)
    ↓
Load workspace from dagster_definitions.py
    ↓
Discover assets: ncaa_games
    ↓
Activate schedules: ncaa_schedule (*/15 * * * *)
    ↓
Daemon enters run loop (checks schedules every 30s)
    ↓
... [Normal operation - materializes assets per schedule] ...
    ↓
[Docker Compose Shutdown Signal - SIGTERM]
    ↓
Dagster daemon receives shutdown signal
    ↓
Wait for current asset materialization to complete
    ↓
Close PostgreSQL connections
    ↓
Graceful shutdown complete
```

**Note:** FastAPI and Dagster run independently - no lifecycle integration needed.

## Non-Functional Requirements

### Performance

**Polling Job Performance Targets:**

| Metric | Target | Rationale |
|--------|--------|-----------|
| API fetch latency (p95) | <2 seconds | NCAA API typically responds <500ms, 2s allows network variance |
| Game transformation time | <50ms per game | Simple data mapping, minimal computation |
| Database upsert (10 games) | <500ms | Batch commit, indexed lookups |
| **Total job execution time** | **<5 seconds** | Well under 15-min interval, minimal resource blocking |
| Memory footprint (poller) | <50MB | Lightweight async operations, no large data structures |
| CPU usage during poll | <10% (single vCPU) | Async I/O-bound workload, not CPU-intensive |

**Rate Limiting Compliance:**

- **NCAA API limit**: 5 requests/second
- **Implementation**: 200ms delay between requests (if multiple date queries needed)
- **Actual usage**: 1 request per 15 minutes = 0.001 req/sec (well under limit)

**Scalability Considerations:**

- **Current load**: 1 API call every 15 min = 96 calls/day
- **Peak season**: March Madness 64-team tournament = ~32 games/day = still 1 API call (all games in single response)
- **Database growth**: 5,000 games/season × 500 bytes ≈ 2.5MB (negligible)

### Security

**API Credentials:**

- **NCAA API**: No authentication required (public henrygd/ncaa-api endpoint)
- **Future consideration**: If migrating to official ESPN API, credentials stored in environment variables

**Rate Limiting Protection:**

- **Client-side throttling**: 200ms delay prevents accidental bursts exceeding 5 req/sec
- **Retry backoff**: Exponential backoff (2s, 4s, 8s) prevents aggressive retries that could trigger IP bans

**Data Validation:**

- **Input sanitization**: NCAA API responses parsed via Pydantic models (type validation)
- **SQL injection prevention**: SQLModel ORM parameterized queries (no raw SQL)
- **No user input**: Polling job has no external user interface, only internal scheduler triggers

**Logging Security:**

- **No sensitive data logged**: Only game_id, scores, status (public sports data)
- **Structured logs**: JSON format prevents log injection attacks
- **CloudWatch access**: IAM-restricted (only EC2 instance role can write)

### Reliability/Availability

**Graceful Degradation:**

| Failure Mode | System Behavior | Recovery |
|--------------|----------------|----------|
| NCAA API down (HTTP 5xx) | Retry 3 times with backoff, then skip cycle | Next poll in 15 min retries |
| Network timeout | Retry 3 times, then skip cycle | Auto-retry next cycle |
| Database unavailable | Log error, skip cycle | FastAPI health check detects DB failure |
| Invalid API response | Log error, skip invalid game, process others | Partial success (good games saved) |
| Dagster daemon crash | Docker restart policy auto-recovers daemon | Lost cycle, resumes in 15 min |

**Data Consistency:**

- **Upsert pattern**: INSERT or UPDATE ensures no duplicate game_id entries
- **Transaction safety**: All games in single commit (atomic batch operation)
- **Idempotency**: Polling same game multiple times produces same result (score updates)

**Acceptable Data Loss:**

- **Missed poll cycle**: If one 15-min cycle fails, scores are stale by max 30 min (next cycle recovers)
- **Race conditions**: None (single poller process, sequential execution)

**Monitoring Targets:**

- **Job success rate**: >95% (allow occasional API failures)
- **Data freshness**: Games updated within 20 minutes (15min + 5min buffer)
- **Uptime**: Dagster daemon runs continuously via Docker (Epic 1's 95% uptime target)

### Observability

**Structured Logging Events:**

```python
# Job lifecycle
logger.info("ncaa_poll_job_started")
logger.info("ncaa_poll_job_completed", games_processed=N, duration_ms=X)
logger.error("ncaa_poll_job_failed", error=str(e), exc_info=True)

# API interactions
logger.info("ncaa_api_fetch_started", url=url, date=date_str)
logger.info("ncaa_api_fetch_completed", games_count=N, status_code=200)
logger.warning("ncaa_api_retry", attempt=2, error="timeout")

# Data operations
logger.info("game_upserted", game_id=id, status="updated", score="78-81")
logger.warning("team_not_found", team_id=id, game_id=game_id)

# Dagster daemon lifecycle
logger.info("dagster_daemon_started")
logger.info("dagster_daemon_shutdown")
```

**Key Metrics to Track:**

| Metric | Log Field | Purpose |
|--------|-----------|---------|
| Games processed per cycle | `games_processed` | Detect API data anomalies (expect 5-20 games/day) |
| Job execution duration | `duration_ms` | Detect performance degradation |
| API failures | `ncaa_api_fetch_failed` count | Alert on repeated failures |
| Missing team mappings | `team_not_found` | Identify gaps in dimensional data |
| Rivalry detection rate | `rivalry_factor > 1.0` count | Validate conference matching logic |

**Health Check Integration (Epic 3):**

```python
# backend/app/api/routes/health.py
{
  "ncaa_ingestion": {
    "status": "ok",
    "last_materialization": "2025-11-10T14:00:00Z",  # From Dagster metadata API
    "games_tracked": 12,  # COUNT(*) WHERE game_date = TODAY
    "next_scheduled_run": "2025-11-10T14:15:00Z"  # From Dagster schedule
  }
}
```

**Note:** Health check can query Dagster GraphQL API for asset materialization metadata.

**Alerting Thresholds (CloudWatch Alarms):**

- **Data staleness**: Alert if MAX(updated_at) > 30 minutes old
- **Job failure rate**: Alert if >3 consecutive failures (45 min no data)
- **API errors**: Alert if HTTP 4xx errors (client misconfiguration)

## Dependencies and Integrations

**Python Dependencies (Added to pyproject.toml):**

| Dependency | Version | Purpose | Story |
|------------|---------|---------|-------|
| httpx | 0.27.0+ | Async HTTP client for NCAA API | 2.2 (already in Epic 1) |
| tenacity | 9.0.0+ | Retry logic with exponential backoff (optional with Dagster) | 2.5 (already in Epic 1) |
| dagster | 1.9.0+ | Data orchestration framework (core library) | 2.4 (NEW - requires `uv add`) |
| dagster-webserver | 1.9.0+ | Dagster UI webserver | 2.4 (NEW - requires `uv add`) |
| dagster-postgres | 0.25.0+ | PostgreSQL storage backend for Dagster | 2.4 (NEW - requires `uv add`) |
| structlog | 25.5.0+ | Structured logging | Epic 1 (already installed) |

**New Dependency Installation:**

```bash
cd backend
uv add "dagster>=1.9.0"
uv add "dagster-webserver>=1.9.0"
uv add "dagster-postgres>=0.25.0"
```

**Docker Dependencies:**

Dagster webserver and daemon run as separate containers. The following services are configured in `docker-compose.yml`:

```yaml
dagster-webserver:
  # Dagster UI webserver for asset catalog, lineage graphs, and run history
  image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
  restart: always
  command: dagster-webserver -h 0.0.0.0 -p 3000 -w /app/workspace.yaml
  networks:
    - traefik-public
    - default
  depends_on:
    db:
      condition: service_healthy
      restart: true
    prestart:
      condition: service_completed_successfully
  environment:
    - DAGSTER_POSTGRES_USER=${POSTGRES_USER}
    - DAGSTER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - DAGSTER_POSTGRES_DB=${POSTGRES_DB}
    - DAGSTER_POSTGRES_HOSTNAME=db
    - DAGSTER_POSTGRES_PORT=${POSTGRES_PORT}
    - POSTGRES_SERVER=db
    - POSTGRES_PORT=${POSTGRES_PORT}
    - POSTGRES_DB=${POSTGRES_DB}
  labels:
    - traefik.enable=true
    - traefik.http.services.${STACK_NAME}-dagster.loadbalancer.server.port=3000
    - traefik.http.routers.${STACK_NAME}-dagster-https.rule=Host(`dagster.${DOMAIN}`)
    - traefik.http.routers.${STACK_NAME}-dagster-https.entrypoints=https
    - traefik.http.routers.${STACK_NAME}-dagster-https.tls=true
    - traefik.http.routers.${STACK_NAME}-dagster-https.tls.certresolver=le

dagster-daemon:
  # Dagster daemon for running schedules, sensors, and background operations
  image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
  restart: always
  command: dagster-daemon run -w /app/workspace.yaml
  networks:
    - default
  depends_on:
    db:
      condition: service_healthy
      restart: true
    prestart:
      condition: service_completed_successfully
  environment:
    - DAGSTER_POSTGRES_USER=${POSTGRES_USER}
    - DAGSTER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - DAGSTER_POSTGRES_DB=${POSTGRES_DB}
    - DAGSTER_POSTGRES_HOSTNAME=db
    - DAGSTER_POSTGRES_PORT=${POSTGRES_PORT}
    - POSTGRES_SERVER=db
    - POSTGRES_PORT=${POSTGRES_PORT}
    - POSTGRES_DB=${POSTGRES_DB}
```

**Key Configuration Details:**
- **Workspace Configuration**: Both services reference `/app/workspace.yaml` which loads `app.dagster_definitions`
- **Database Connection**: Both services connect to the same PostgreSQL instance as FastAPI
- **Metadata Storage**: Dagster creates a separate `dagster` schema for its metadata
- **Service Independence**: Dagster runs independently from FastAPI (no lifecycle coupling)
- **Production Access**: Webserver exposed at https://dagster.gamepulse.top via Traefik
- **Development Access**: Webserver accessible at http://localhost:3000 for local testing

**External API Dependencies:**

| API | Endpoint | Rate Limit | Authentication | Cost |
|-----|----------|------------|----------------|------|
| henrygd/ncaa-api | `https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{date}/scoreboard.json` | 5 req/sec | None (public) | Free |

**Database Dependencies:**

- **Teams table** (Epic 1): Foreign key for `home_team_id`, `away_team_id`
- **Team_groups table** (Epic 1): Used for rivalry detection via `team_group_id` matching
- **Games table** (Epic 1 schema): Epic 2 writes to this table

**Epic Dependencies:**

| Depends On | Provides To | Integration Point |
|------------|-------------|-------------------|
| **Epic 1**: Database schema (teams, team_groups, games tables) | **Epic 3**: Games endpoint reads from games table | SQLModel ORM queries |
| **Epic 1**: FastAPI app structure, structlog configuration | **Epic 5**: Excitement scoring reads game data | Games table JOIN operations |
| **Epic 1**: Alembic migrations | **Epic 8**: Frontend displays games | API response from Epic 3 |

**Integration Points:**

**1. NCAA API → Backend:**
- Protocol: HTTP REST
- Format: JSON
- Frequency: Every 15 minutes
- Error handling: 3 retries with exponential backoff

**2. Backend → PostgreSQL:**
- Protocol: SQLModel async ORM (psycopg3)
- Operations: INSERT (new games), UPDATE (score updates)
- Transaction: Batch commit per polling cycle

**3. Dagster → PostgreSQL:**
- Integration: Dagster uses same PostgreSQL instance for metadata storage
- Separate schemas: `dagster` schema for metadata, `public` schema for application data
- Resource management: Dagster resource provides database connections to assets

## Acceptance Criteria (Authoritative)

**AC-1: Dimensional Data Seeding (Story 2.1)**
- [ ] Created `backend/app/data/teams.json` with minimum 20 NCAAM teams
- [ ] Created `backend/app/data/conferences.json` with minimum 6 major conferences (ACC, Big 12, SEC, Big Ten, Pac-12, Big East)
- [ ] Alembic migration created: `seed_dimensional_data.py`
- [ ] Migration successfully inserts teams and conferences into database
- [ ] Query `SELECT COUNT(*) FROM teams WHERE sport = 'ncaam'` returns >=20
- [ ] Query `SELECT COUNT(*) FROM team_groups WHERE sport = 'ncaam'` returns >=6
- [ ] Teams have proper `team_group_id` foreign keys linking to conferences
- [ ] Sample rivalry pair exists: Duke (team_group_id='ncaam_acc') and UNC (team_group_id='ncaam_acc')

**AC-2: NCAA API Client Implementation (Story 2.2)**
- [ ] File created: `backend/app/services/ncaa_client.py`
- [ ] `NCAAClient` class implements async `fetch_games(game_date: date)` method
- [ ] Client uses httpx.AsyncClient with 10-second timeout
- [ ] Can fetch today's games: `client.fetch_games()` returns List[dict]
- [ ] Can fetch specific date: `client.fetch_games(date(2025, 11, 10))` works
- [ ] Client properly closes: `await client.close()` releases resources
- [ ] Unit test: Mock NCAA API response, verify parsing logic
- [ ] Integration test: Fetch live NCAA API (if games scheduled), verify response structure

**AC-3: Game Model and Migration (Story 2.3)**
- [ ] File created: `backend/app/models/game.py`
- [ ] `Game` SQLModel class matches Epic 1 schema specification
- [ ] Foreign keys defined: `home_team_id`, `away_team_id` reference `teams.team_id`
- [ ] Indexes created: `sport`, `game_date`, `game_status`, `game_type`
- [ ] Alembic migration generated: `alembic revision --autogenerate -m "Add game model"`
- [ ] Migration applied: `alembic upgrade head` succeeds
- [ ] Database table exists: `\d games` shows correct schema
- [ ] Can insert test game: `INSERT INTO games (game_id, sport, ...) VALUES (...)`
- [ ] Foreign key constraint enforced: Invalid `home_team_id` raises error

**AC-4: Dagster Orchestration Setup (Story 2.4)**
- [ ] File created: `backend/app/dagster_definitions.py`
- [ ] File created: `backend/app/assets/ncaa_games.py`
- [ ] File created: `backend/app/resources/database.py`
- [ ] `ncaa_games` asset implements game ingestion logic with async httpx calls
- [ ] Dagster `Definitions` object configured with assets, schedules, and resources
- [ ] Schedule defined with cron expression `*/15 * * * *` (every 15 minutes)
- [ ] Docker Compose updated: dagster-webserver and dagster-daemon containers added
- [ ] Dagster webserver accessible at http://localhost:3000
- [ ] Asset catalog shows `ncaa_games` asset with description and metadata
- [ ] Schedule triggers asset materialization every 15 minutes
- [ ] Games upserted correctly: New games inserted, existing games updated
- [ ] Rivalry detection: Games with same-conference teams have `rivalry_factor=1.2`
- [ ] Dagster logs show asset materialization events with games_processed count

**AC-5: Retry Logic and Error Handling (Story 2.5)**
- [ ] `ncaa_games` asset decorated with `RetryPolicy(max_retries=3, delay=2, backoff=2.0)`
- [ ] Dagster retry policy: exponential backoff (2s, 4s, 8s)
- [ ] HTTP 5xx errors trigger retry (verified via mock NCAA API returning 500)
- [ ] Network timeouts trigger retry (verified via mock server with 15s delay)
- [ ] HTTP 4xx errors do not retry (client error, logged and failed)
- [ ] After 3 failed attempts, asset materialization fails and Dagster records failure
- [ ] Failed asset materialization does not crash daemon (next schedule continues)
- [ ] Partial failures handled: If 1 of 10 games has invalid data, other 9 games saved
- [ ] Database failures logged with `exc_info=True` for stack trace
- [ ] Dagster UI shows retry attempts in run timeline

**AC-6: End-to-End Integration**
- [ ] Start Dagster daemon → Schedule activates → First materialization executes
- [ ] Asset fetches NCAA API → Transforms data → Inserts into games table
- [ ] Query games table: `SELECT * FROM games WHERE game_date = CURRENT_DATE` returns results
- [ ] Games have correct rivalry factors based on conference matching
- [ ] Dagster UI shows complete lineage: ncaa_games asset → PostgreSQL
- [ ] Dagster logs show complete workflow: fetch → transform → upsert → commit → metadata
- [ ] Asset catalog displays ncaa_games with last materialization timestamp
- [ ] Stop Dagster daemon → Graceful shutdown → No orphaned processes

**AC-7: Data Quality Validation**
- [ ] All games have non-null `game_id`, `sport`, `game_date`, `home_team_id`, `away_team_id`
- [ ] Scores are non-negative integers (0 ≤ home_score, away_score)
- [ ] Status values are valid enum: "scheduled", "live", "halftime", "final"
- [ ] Timestamps are UTC: `game_date`, `created_at`, `updated_at` have timezone info
- [ ] Team IDs exist in teams table (foreign key constraint enforced)
- [ ] Rivalry factors are valid: 1.0 (normal) or 1.2 (conference rivalry)

## Traceability Mapping

| Acceptance Criteria | PRD Requirement | Architecture Component | Story | Test Coverage |
|---------------------|-----------------|------------------------|-------|---------------|
| AC-1: Dimensional Data | FR-1.2: Team dimensional data | SQLModel, teams/team_groups tables | 2.1 | Integration: Query team counts |
| AC-2: NCAA API Client | FR-2.1: Game data ingestion | httpx async client, NCAA API | 2.2 | Unit: Mock API, Integration: Live API |
| AC-3: Game Model | FR-2.2: Game status tracking | SQLModel Game class, Alembic | 2.3 | Integration: Database schema validation |
| AC-4: Dagster Orchestration | FR-2.3: Scheduled batch polling | Dagster assets, schedules, daemon | 2.4 | Integration: Asset materialization, E2E: Full pipeline |
| AC-5: Retry Logic | NFR-4.2: Graceful degradation | tenacity retry decorator | 2.5 | Unit: Mock failures, Integration: Retry behavior |
| AC-6: End-to-End | Success Criteria: Week 1 demo | Full Epic 2 stack integration | All | E2E: Startup → Poll → Database → Shutdown |
| AC-7: Data Quality | NFR-2.1: Data accuracy | SQLModel validation, constraints | All | Integration: Data integrity checks |

**PRD Requirements Coverage:**

- **FR-1.2**: Team dimensional data (Epic 1) → Story 2.1 seeds NCAAM teams
- **FR-2.1**: NCAA game data ingestion → Stories 2.2-2.4 implement polling pipeline
- **FR-2.2**: Game status tracking (scheduled/live/final) → Story 2.3 game_status field + Story 2.4 updates
- **FR-2.3**: 15-minute batch polling → Story 2.4 Dagster schedule with cron `*/15 * * * *`
- **NFR-1.4**: Data freshness <20 min → 15-min polling + 5-min processing buffer
- **NFR-4.2**: Graceful degradation → Story 2.5 retry logic + error handling
- **NFR-4.3**: Structured logging → All stories use structlog with context fields

## Risks, Assumptions, Open Questions

**Risks:**

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| henrygd/ncaa-api service downtime | High - no game data | Low | Retry logic + 15-min recovery window; could fallback to official ESPN API if prolonged |
| NCAA API rate limit enforcement | Medium - blocked requests | Low | Client throttling (200ms delay); actual usage well under 5 req/sec |
| Team ID mismatch (API vs seed data) | High - foreign key errors | Medium | **Story 2.1**: Use official NCAA team IDs from API docs; validate mappings with test poll |
| Dagster daemon resource contention | Medium - concurrent writes | Low | Single daemon instance, sequential asset materializations |
| Database connection pool exhaustion | Medium - failed polls | Low | SQLModel default pool size (5-10); polling job releases connections promptly |
| March Madness traffic spike | Low - API throttling | Medium | 1 API call per 15 min unchanged; scale concern is Future phase |

**Assumptions:**

- henrygd/ncaa-api maintains stable API contract (no breaking changes during MVP)
- NCAA game IDs are globally unique and stable across seasons
- PostgreSQL 16 + TimescaleDB handle 5,000 games/season without performance degradation
- 15-minute polling frequency acceptable for MVP (real-time streaming deferred to Growth)
- Top 20 NCAAM teams sufficient for initial demo (can expand to all Division I teams later)
- Dagster self-hosted deployment on single EC2 instance sufficient (no need for distributed execution)
- Single Dagster daemon adequate (no horizontal scaling required for MVP)
- PostgreSQL metadata storage sufficient (no need for separate Dagster database)

**Open Questions:**

1. **Team ID mapping strategy**: Should Story 2.1 use hardcoded NCAA API team IDs or scrape from API /teams endpoint?
   - **Recommendation**: Hardcode top 20 teams for MVP; automate scraping in Growth phase

2. **Historical data backfill**: Should Epic 2 include logic to backfill past games (e.g., season start to today)?
   - **Recommendation**: Out of scope for Epic 2; add backfill script in Epic 10 (Documentation & Polish)

3. **Polling during off-season**: Should Dagster schedule pause when no games scheduled (June-October)?
   - **Recommendation**: Run year-round for simplicity; no-op materializations during off-season cost negligible

4. **Game type detection**: How to distinguish conference_tournament vs ncaa_tournament vs regular_season?
   - **Recommendation**: Default to `regular_season` for Epic 2; enhance with tournament detection in Epic 4+ using game date ranges

5. **Timezone handling**: NCAA API returns UTC or local venue time?
   - **Action Required**: Test with Story 2.2 - verify timestamp format, convert to UTC if needed

## Test Strategy Summary

**Unit Tests (pytest):**

**Story 2.2 - NCAA Client:**
```python
@pytest.mark.asyncio
async def test_ncaa_client_fetch_games_success(mock_httpx):
    """Test successful API fetch with mocked response"""
    mock_httpx.get.return_value.json.return_value = {"games": [...]}
    client = NCAAClient()
    games = await client.fetch_games(date(2025, 11, 10))
    assert len(games) > 0
    assert games[0]["id"] == "401234567"

@pytest.mark.asyncio
async def test_ncaa_client_retry_on_timeout(mock_httpx):
    """Test retry logic on timeout"""
    mock_httpx.get.side_effect = [httpx.TimeoutError(), {"games": [...]}]
    client = NCAAClient()
    games = await client.fetch_games()  # Should retry and succeed
    assert mock_httpx.get.call_count == 2
```

**Story 2.5 - Retry Logic:**
```python
@pytest.mark.asyncio
async def test_retry_stops_after_3_attempts(mock_httpx):
    """Test retry stops after 3 failed attempts"""
    mock_httpx.get.side_effect = httpx.HTTPStatusError(...)
    client = NCAAClient()
    with pytest.raises(RetryError):
        await client.fetch_games()
    assert mock_httpx.get.call_count == 3
```

**Integration Tests (pytest + test database):**

**Story 2.1 - Dimensional Data:**
```python
def test_dimensional_data_migration(test_db_session):
    """Test teams and conferences seeded correctly"""
    teams_count = test_db_session.exec(
        select(func.count(Team.team_id)).where(Team.sport == "ncaam")
    ).one()
    assert teams_count >= 20

    duke = test_db_session.get(Team, "ncaam_duke")
    assert duke.team_group_id == "ncaam_acc"
```

**Story 2.4 - Polling Worker:**
```python
@pytest.mark.asyncio
async def test_poll_games_job_upsert_logic(test_db_session, mock_ncaa_client):
    """Test game upsert: insert new, update existing"""
    # First poll: insert new game
    await poll_games_job()
    game = test_db_session.get(Game, "ncaam_401234567")
    assert game.home_score == 15

    # Second poll: update score
    mock_ncaa_client.return_games[0]["home"]["score"] = "78"
    await poll_games_job()
    test_db_session.refresh(game)
    assert game.home_score == 78
```

**End-to-End Tests (pytest + Dagster test runner):**

**Story 2.4 - Full Pipeline:**
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_dagster_pipeline(test_db_session):
    """E2E: Trigger asset materialization → Verify database"""
    from dagster import build_asset_context
    from app.assets.ncaa_games import ncaa_games
    from app.resources.database import database_resource

    # Build Dagster context with test database resource
    context = build_asset_context(resources={"database": database_resource})

    # Materialize asset
    result = await ncaa_games(context)
    assert result["status"] == "success"

    # Verify games in database
    games = test_db_session.exec(
        select(Game).where(Game.game_date == date.today())
    ).all()

    assert len(games) > 0, "No games found - check NCAA season schedule"
    assert all(g.rivalry_factor is not None for g in games)
```

**Manual Testing Checklist:**

- [ ] Verify Dagster webserver accessible at http://localhost:3000
- [ ] Confirm asset catalog shows `ncaa_games` asset with description
- [ ] Verify schedule is active in Dagster UI (every 15 minutes)
- [ ] Trigger manual materialization from UI, verify games inserted in PostgreSQL
- [ ] Simulate API failure: Block ncaa-api.henrygd.me in /etc/hosts, verify retries in run timeline
- [ ] Verify graceful shutdown: `docker compose down` during materialization, confirm asset completes
- [ ] Check rivalry detection: Query conference rivalry games, verify `rivalry_factor=1.2`
- [ ] View asset lineage graph in Dagster UI showing ncaa_games → PostgreSQL

**Test Coverage Targets:**

| Module | Target Coverage | Rationale |
|--------|----------------|-----------|
| `ncaa_client.py` | 90% | Critical API integration, high test value |
| `assets/ncaa_games.py` | 85% | Core asset logic, Dagster context integration |
| `dagster_definitions.py` | 70% | Configuration code, validated by integration tests |
| `rivalry_detector.py` | 95% | Simple logic, easy to test exhaustively |
| `models/game.py` | 60% | SQLModel schema, validated by integration tests |
| **Epic 2 Overall** | **75%** | Above architecture 70% target for core logic |

**Test Execution:**

```bash
# Unit tests only
pytest backend/app/tests/unit/ -v

# Integration tests (requires test DB)
pytest backend/app/tests/integration/ -v

# E2E tests (requires live NCAA API - may fail during off-season)
pytest backend/app/tests/e2e/ -v -m e2e

# Coverage report
pytest --cov=app --cov-report=html
```

---

## Post-Review Follow-ups

This section tracks action items identified during code reviews for Epic 2 stories.

### Story 2-3b: Sync Team Metadata from NCAA API

**Code Review Date**: 2025-11-12
**Reviewer**: Philip (AI Senior Developer Review)
**Fix Date**: 2025-11-12
**Developer**: Amelia (Dev Agent)
**Status**: ✅ **COMPLETE** - All issues resolved, all tests passing

**All Issues Resolved**:

1. ✅ **[HIGH]** Migration `d115685a3652` missing DEFAULT constraints - **FIXED**
   - **Fix Applied**: Added ALTER TABLE statements for DEFAULT constraints in migration
   - **Changes**:
     - `ALTER TABLE dim_team ALTER COLUMN team_key SET DEFAULT nextval('teams_team_key_seq'::regclass)`
     - `ALTER TABLE dim_team ALTER COLUMN created_at SET DEFAULT NOW()`
     - `ALTER TABLE dim_team ALTER COLUMN updated_at SET DEFAULT NOW()`
   - **Validation**: Schema verified with `\d dim_team`, DEFAULT constraints present
   - **File**: [d115685a3652_refactor_to_dimensional_model_with_.py](../backend/app/alembic/versions/d115685a3652_refactor_to_dimensional_model_with_.py)

2. ✅ **[HIGH]** All tests passing - **VERIFIED**
   - **Result**: 13/13 team_sync tests passing (was 1/13)
   - **Additional**: 2/2 new migration tests passing
   - **Validation**: `pytest app/tests/services/test_team_sync.py -v` → all green
   - **ACs Validated**: AC1-AC6 all verified through passing tests

3. ✅ **[MED]** Removed unused `type: ignore` comment - **FIXED**
   - **Fix Applied**: Deleted `# type: ignore[arg-type]` from line 136
   - **Validation**: `mypy app/services/team_sync.py` → Success: no issues found
   - **File**: [team_sync.py:136](../backend/app/services/team_sync.py)

4. ✅ **[LOW]** Migration tests added - **COMPLETE**
   - **Files Created**:
     - `backend/app/tests/migrations/__init__.py`
     - `backend/app/tests/migrations/test_dim_team_migration.py`
   - **Tests**: Validate DEFAULT constraints exist and INSERT works without explicit values
   - **Result**: 2/2 tests passing

5. ✅ **[LOW]** AC4 WARNING logging implemented - **COMPLETE**
   - **Fix Applied**: Changed log level from INFO to WARNING for new team discoveries
   - **Message**: "Team {team_id} auto-created with minimal data - consider adding colors/aliases in teams.json"
   - **Validation**: `test_logging_output` passing with WARNING level verification

**Lessons Learned**:
- Always verify DEFAULT constraints are properly set when using Alembic `add_column()` with autoincrement
- SQLModel Field defaults don't translate to database-level DEFAULT constraints when using raw SQL INSERT
- Consider using SQLModel ORM methods over raw PostgreSQL dialect for better portability
- Function-scoped test fixtures prevent unique constraint violations from seed data
- Migration tests should validate schema constraints, not just table existence

**Story Completion**:
- All 6 Acceptance Criteria verified ✅
- 15/15 tests passing (13 team_sync + 2 migration) ✅
- Type checking passing ✅
- No regressions introduced ✅
- Ready for merge ✅
