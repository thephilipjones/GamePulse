# Story 2.4: Implement Dagster Data Orchestration and NCAA Game Asset

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** review
**Assignee:** Claude Code (Amelia)
**Sprint:** Week 1

---

## User Story

As a developer,
I want a Dagster asset that materializes NCAA game data on a 15-minute schedule,
So that game data is continuously updated with full observability and lineage tracking.

---

## Acceptance Criteria

**Given** I have an NCAA API client and Game SQLModel
**When** I create a Dagster asset for NCAA game ingestion
**Then** the asset:
- Materializes on a 15-minute schedule (cron: `*/15 * * * *`)
- Fetches today's games from NCAA API using the async client
- For each game, upserts to database (INSERT or UPDATE if game_id exists)
- Logs materialization events with game count: "ncaa_games_asset_completed, games_processed=8"
- Handles API failures gracefully using Dagster's built-in retry policy

**And** I have Dagster infrastructure running:
- Dagster webserver container accessible at http://localhost:3000 (dev) or https://dagster.gamepulse.top (prod)
- Dagster daemon container running schedules and materializations
- Both containers share database connection with FastAPI backend
- Dagster uses PostgreSQL for metadata storage (separate schema from app data)

**And** I can observe asset behavior in Dagster UI:
- Asset catalog shows `ncaa_games` asset with description and group
- Asset lineage graph displays data flow: NCAA API → ncaa_games → PostgreSQL
- Schedule shows active with next run time
- Run history displays materialization events with metadata (games_processed count)
- Failed runs show retry attempts with exponential backoff (2s, 4s, 8s)

**And** I run an immediate materialization on first deployment:
- Manual "Materialize" button in Dagster UI triggers immediate run
- OR use CLI: `dagster asset materialize -m app.dagster_definitions ncaa_games`

**And** I can verify the asset is working:
- Check Dagster logs for "ncaa_games_asset_started" events every 15 min
- Check database: `SELECT COUNT(*) FROM fact_game WHERE game_date = CURRENT_DATE` returns results
- Check Dagster UI: Asset shows recent successful materialization timestamp

---

## Prerequisites

- Story 2.2 (NCAA API client)
- Story 2.3 (Game model and schemas)
- Docker Compose configured with dagster-webserver and dagster-daemon services

---

## Technical Notes

### Architecture Overview

Dagster runs **independently** from the FastAPI application:
- **FastAPI**: Serves HTTP API requests (port 8000)
- **Dagster Daemon**: Runs scheduled data pipelines (background service)
- **Dagster Webserver**: Provides UI for observability (port 3000)
- **Separation**: No FastAPI lifecycle integration needed - Dagster daemon manages scheduling

### File Structure

Create the following files:

```
backend/app/
├── dagster_definitions.py  # Main Dagster definitions (assets, schedules, resources)
├── assets/
│   └── ncaa_games.py       # NCAA game ingestion asset
├── resources/
│   └── database.py         # Dagster database resource
└── workspace.yaml          # Dagster workspace configuration
```

### 1. Dagster Workspace Configuration

**Create File:** `backend/workspace.yaml`

```yaml
load_from:
  - python_module: app.dagster_definitions
```

**Note:** This tells Dagster where to find asset definitions. The file should be at the root of the backend directory (same level as `app/`).

### 2. Database Resource for Dagster

**Create File:** `backend/app/resources/database.py`

```python
from dagster import ConfigurableResource
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class DatabaseResource(ConfigurableResource):
    """Dagster resource for async PostgreSQL database access"""

    engine: AsyncEngine = None
    async_session_maker: sessionmaker = None

    def setup_for_execution(self, context) -> None:
        """Initialize database engine and session factory"""
        database_url = str(settings.SQLALCHEMY_DATABASE_URI).replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )

        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info("dagster_database_resource_initialized")

    @asynccontextmanager
    async def get_session(self):
        """Provide async database session"""
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def teardown_after_execution(self, context) -> None:
        """Cleanup database connections"""
        if self.engine:
            # Note: Dagster handles async cleanup internally
            logger.info("dagster_database_resource_teardown")


# Singleton instance for Dagster definitions
database_resource = DatabaseResource()
```

### 3. NCAA Games Asset

**Create File:** `backend/app/assets/ncaa_games.py`

```python
from dagster import asset, RetryPolicy, AssetExecutionContext
from app.services.ncaa_client import NCAAClient
from app.services.rivalry_detector import calculate_rivalry_factor
from app.models.fact_game import FactGame
from app.models.dim_team import DimTeam
from datetime import datetime
from sqlmodel import select
import structlog

logger = structlog.get_logger()


@asset(
    name="ncaa_games",
    description="NCAA Men's Basketball game data fetched from NCAA API and stored in PostgreSQL",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=2,  # seconds
        backoff=2.0,  # exponential: 2s, 4s, 8s
    ),
    group_name="data_ingestion",
)
async def ncaa_games(context: AssetExecutionContext) -> dict:
    """
    Dagster asset: Fetch NCAA game data and materialize to database.

    This asset:
    - Polls NCAA API for today's games
    - Transforms API response to Game models
    - Upserts games to PostgreSQL (insert new, update existing)
    - Detects rivalries based on conference matching
    - Returns metadata for Dagster to track

    Returns:
        Dict with games_processed count and status
    """
    logger.info("ncaa_games_asset_started")
    context.log.info("Fetching NCAA games for today")

    client = NCAAClient()
    try:
        # Fetch today's games from NCAA API
        raw_games = await client.fetch_games()
        context.log.info(f"Fetched {len(raw_games)} games from NCAA API")

        # Get database session from Dagster resource
        async with context.resources.database.get_session() as session:
            for game_data in raw_games:
                # Transform API response to Game model
                game = await transform_game_data(game_data, session)

                # Upsert using PostgreSQL INSERT ... ON CONFLICT
                # Check if game exists (for insert/update tracking)
                existing_game = await session.execute(
                    select(FactGame).where(FactGame.game_id == fact_game["game_id"])
                )
                is_update = existing_game.scalar_one_or_none() is not None

                # Upsert with ON CONFLICT DO UPDATE
                stmt = insert(FactGame).values(fact_game)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["game_id"],  # Natural key
                    set_={
                        "home_score": stmt.excluded.home_score,
                        "away_score": stmt.excluded.away_score,
                        "game_status": stmt.excluded.game_status,
                        "game_clock": stmt.excluded.game_clock,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                await session.execute(stmt)

                if is_update:
                    games_updated += 1
                    context.log.debug(f"Updated game {fact_game['game_id']}")
                else:
                    games_inserted += 1
                    context.log.debug(f"Inserted game {fact_game['game_id']}")

            await session.commit()

        logger.info("ncaa_games_asset_completed", games_processed=len(raw_games))
        context.log.info(f"Materialized {len(raw_games)} games successfully")

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


async def transform_game_data(game_data: dict, session) -> dict:
    """
    Transform NCAA API response to FactGame dimensional model dictionary.

    Dimensional Model Transformations:
    1. Lookup home_team_key and away_team_key via dim_team natural keys
    2. Derive game_date_key from game_date timestamp (YYYYMMDD integer)
    3. Calculate rivalry_factor based on conference matching
    4. Build game_id natural key: "sport_apiid"

    Args:
        game_data: Raw game data from NCAA API
        session: Database session for FK lookups and rivalry detection

    Returns:
        Dictionary ready for FactGame upsert (game_key auto-generated)
    """
    # Unwrap nested game object
    game = game_data.get("game", {})
    home_espn_id = game.get("home", {}).get("names", {}).get("seo")
    away_espn_id = game.get("away", {}).get("names", {}).get("seo")

    # Build team_id natural keys
    home_team_id = f"ncaam_{home_espn_id}"
    away_team_id = f"ncaam_{away_espn_id}"

    # Lookup surrogate keys (team_key) via dim_team
    home_team = await session.execute(
        select(DimTeam).where(DimTeam.team_id == home_team_id, DimTeam.is_current == True)
    )
    away_team = await session.execute(
        select(DimTeam).where(DimTeam.team_id == away_team_id, DimTeam.is_current == True)
    )
    home_team_obj = home_team.scalar_one()
    away_team_obj = away_team.scalar_one()

    # Derive game_date_key from timestamp
    game_date_str = game.get("startDate", "")
    game_date = datetime.strptime(game_date_str, "%m/%d/%Y")
    game_date_key = int(game_date.strftime("%Y%m%d"))

    # Calculate rivalry factor
    rivalry_factor = await calculate_rivalry_factor(home_team_id, away_team_id, session)

    return {
        "game_id": f"ncaam_{game.get('gameID')}",
        "sport": "ncaam",
        "game_date": game_date,
        "game_date_key": game_date_key,
        "home_team_key": home_team_obj.team_key,
        "away_team_key": away_team_obj.team_key,
        "home_score": int(game.get("home", {}).get("score", 0) or 0),
        "away_score": int(game.get("away", {}).get("score", 0) or 0),
        "game_status": game.get("gameState", "scheduled"),
        "game_clock": game.get("contestClock"),
        "venue": game.get("title"),
        "rivalry_factor": rivalry_factor,
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
    }


def map_status(api_status: str) -> str:
    """Map NCAA API status to GamePulse status enum"""
    mapping = {
        "pre": "scheduled",
        "in": "live",
        "post": "final"
    }
    return mapping.get(api_status, "scheduled")
```

### 4. Dagster Definitions (Main Configuration)

**Create File:** `backend/app/dagster_definitions.py`

```python
from dagster import Definitions, ScheduleDefinition, define_asset_job
from app.assets.ncaa_games import ncaa_games
from app.resources.database import database_resource

# Define job that materializes NCAA games asset
ncaa_ingestion_job = define_asset_job(
    name="ncaa_ingestion",
    selection=[ncaa_games],
    description="Ingest NCAA Men's Basketball game data from API",
)

# Schedule job to run every 15 minutes
ncaa_schedule = ScheduleDefinition(
    job=ncaa_ingestion_job,
    cron_schedule="*/15 * * * *",  # Every 15 minutes
    description="Poll NCAA API for updated game data every 15 minutes",
)

# Main Dagster definitions object
defs = Definitions(
    assets=[ncaa_games],
    schedules=[ncaa_schedule],
    resources={
        "database": database_resource,
    },
)
```

### 5. Add Dagster Dependencies

**Update `backend/pyproject.toml`:**

```bash
cd backend
uv add "dagster>=1.9.0"
uv add "dagster-webserver>=1.9.0"
uv add "dagster-postgres>=0.25.0"
```

**Why these packages:**
- `dagster`: Core orchestration framework
- `dagster-webserver`: UI for asset catalog and observability
- `dagster-postgres`: PostgreSQL storage for Dagster metadata

### 6. Docker Compose Configuration

**Verify in `docker-compose.yml`:**

The following services should already be configured:

```yaml
dagster-webserver:
  # Dagster UI webserver for asset catalog, lineage graphs, and run history
  image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
  restart: always
  command: dagster-webserver -h 0.0.0.0 -p 3000 -w /app/workspace.yaml
  ports:
    - "3000:3000"  # Development only
  depends_on:
    - db
  environment:
    - DAGSTER_POSTGRES_USER=${POSTGRES_USER}
    - DAGSTER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - DAGSTER_POSTGRES_DB=${POSTGRES_DB}
    - DAGSTER_POSTGRES_HOSTNAME=db
    - POSTGRES_SERVER=db
  labels:
    - traefik.enable=true
    - traefik.http.routers.dagster-https.rule=Host(`dagster.${DOMAIN}`)
    # ... (Traefik SSL configuration)

dagster-daemon:
  # Dagster daemon for running schedules, sensors, and background operations
  image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
  restart: always
  command: dagster-daemon run -w /app/workspace.yaml
  depends_on:
    - db
  environment:
    - DAGSTER_POSTGRES_USER=${POSTGRES_USER}
    - DAGSTER_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - DAGSTER_POSTGRES_DB=${POSTGRES_DB}
    - DAGSTER_POSTGRES_HOSTNAME=db
    - POSTGRES_SERVER=db
```

**Key Points:**
- Both services use the same backend Docker image
- Both connect to the same PostgreSQL database (different schema for metadata)
- Webserver exposes UI on port 3000
- Daemon runs schedules in the background
- Production uses Traefik for HTTPS (dagster.gamepulse.top)

### 7. Structured Logging

Use structlog consistently:

```python
logger = structlog.get_logger()

# Log events with context
logger.info("ncaa_games_asset_started")
logger.info("ncaa_games_asset_completed", games_processed=12)
logger.error("ncaa_games_asset_failed", error=str(e), exc_info=True)
```

### 8. Testing and Verification

**Start Dagster services:**
```bash
docker compose up -d dagster-webserver dagster-daemon
```

**Access Dagster UI:**
- Development: http://localhost:3000
- Production: https://dagster.gamepulse.top

**Verify asset catalog:**
1. Navigate to "Assets" tab
2. Find `ncaa_games` asset
3. Click "Materialize" to trigger immediate run
4. View run logs and metadata

**Verify schedule:**
1. Navigate to "Schedules" tab
2. Find `ncaa_schedule`
3. Verify status is "Running"
4. Check next tick time (should be within 15 minutes)

**Verify database updates:**
```sql
-- Check games were inserted
SELECT COUNT(*) FROM fact_game WHERE game_date = CURRENT_DATE;

-- Check recent updates (with dimensional model foreign keys)
SELECT game_id, home_team_key, away_team_key, game_status, rivalry_factor, updated_at
FROM fact_game
ORDER BY updated_at DESC
LIMIT 10;
```

**Check logs:**
```bash
docker compose logs -f dagster-daemon
docker compose logs -f dagster-webserver
```

### 9. Manual Materialization (CLI)

For debugging or immediate runs:

```bash
# Option 1: Via Docker Compose
docker compose exec dagster-daemon dagster asset materialize \
  -m app.dagster_definitions ncaa_games

# Option 2: From backend venv (if running locally)
cd backend
source .venv/bin/activate
dagster asset materialize -m app.dagster_definitions ncaa_games
```

### 10. Why Dagster Instead of APScheduler?

**Reference:** [ADR-007: Dagster for Data Orchestration](../architecture.md#L1114-L1141)

**Key Benefits:**
- **Asset-oriented paradigm**: Data assets as first-class citizens
- **Built-in lineage**: Visual data flow graphs for demos
- **Portfolio differentiation**: Modern data engineering tool
- **Interview narrative**: Demonstrates data solutions architect skills
- **Self-hosted deployment**: $0 cost vs $200-600/month for cloud alternatives
- **Full async support**: Native async/await with AsyncIO
- **Better observability**: Rich UI for monitoring and debugging
- **No FastAPI coupling**: Runs independently, no lifecycle integration needed

---

## Definition of Done

- [ ] File created: `backend/app/dagster_definitions.py`
- [ ] File created: `backend/app/assets/ncaa_games.py`
- [ ] File created: `backend/app/resources/database.py`
- [ ] File created: `backend/workspace.yaml`
- [ ] Dagster dependencies added to `pyproject.toml`
- [ ] Docker Compose has dagster-webserver and dagster-daemon services
- [ ] `ncaa_games` asset implements game ingestion with async httpx
- [ ] Schedule defined with cron `*/15 * * * *` (every 15 minutes)
- [ ] Retry policy configured: `RetryPolicy(max_retries=3, delay=2, backoff=2.0)`
- [ ] Database resource provides async sessions to assets
- [ ] Upsert logic correctly handles new and existing games
- [ ] Rivalry detection integrated via `calculate_rivalry_factor()`
- [ ] Dagster webserver accessible at http://localhost:3000 (dev)
- [ ] Asset catalog shows `ncaa_games` with description and metadata
- [ ] Schedule active and shows next run time
- [ ] Manual materialization works from UI
- [ ] Asset lineage graph displays correctly
- [ ] Games upserted to fact_game table after materialization (dimensional model)
- [ ] Rivalry factors correct: 1.2 for same-conference matchups (Decimal type)
- [ ] Structured logging with `structlog` events
- [ ] Logs show "ncaa_games_asset_started" and "ncaa_games_asset_completed"
- [ ] Failed materializations show retry attempts in Dagster UI
- [ ] Dagster daemon gracefully handles shutdown (no orphaned processes)
- [ ] Code follows architecture patterns (async/await, SQLModel)
- [ ] Changes committed to git

---

## Notes

- **No FastAPI lifecycle integration needed** - Dagster daemon is an independent service
- **Dimensional Model:** Uses `fact_game` table with surrogate keys (`game_key`, `home_team_key`, `away_team_key`) and dimensional foreign keys
- **Database Schema:** Dagster uses the same PostgreSQL database but creates its own `dagster` schema for metadata
- **Schedule Auto-Start:** The schedule activates automatically when dagster-daemon starts (default_status=RUNNING)
- Use Dagster UI (not logs) as primary observability tool - provides asset lineage graph
- Asset materialization metadata tracked automatically by Dagster (games_processed, games_inserted, games_updated)
- For production deployment, ensure both dagster-webserver and dagster-daemon containers are running
- **Story 2-3b Integration:** Team sync automatically discovers and upserts teams from API before game insertion

---

## Dev Agent Record

### Context Reference
- Story Context XML: `docs/stories/2-4-implement-polling-worker.context.xml` (generated 2025-11-12)
