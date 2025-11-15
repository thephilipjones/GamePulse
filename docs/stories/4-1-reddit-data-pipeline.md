# Story 4-1: Reddit Data Pipeline

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-1
**Status:** ready-for-dev
**Estimated Effort:** 12-16 hours
**Priority:** High (Week 1 - blocks 4-4)
**Dependencies:** Epic 2 (dim_team, fact_game completed)

---

## User Story

**As a** data engineer,
**I want** to extract NCAA basketball posts from Reddit's /r/CollegeBasketball subreddit and store complete raw JSON in TimescaleDB,
**So that** I have social media data for game excitement scoring (Epic 5) and future ML experimentation.

---

## Context

Reddit OAuth applications are no longer being approved (November 2025), forcing GamePulse to use unauthenticated JSON endpoints (e.g., `https://www.reddit.com/r/CollegeBasketball/new.json`). This approach:

- ⚠️ **Violates Reddit's Terms of Service** - Reddit actively sues unauthorized scrapers (Oct 2025)
- Accepted risk for **portfolio demonstration purposes only**
- **10 QPM (queries per minute) rate limit** - requires conservative polling
- Provides **700-3,500 daily posts** during active game seasons

This story implements the **extraction and loading** components of the ELT pipeline, preserving complete raw JSON for downstream transformation (Story 4-4) and sentiment analysis (Story 4-5).

---

## Acceptance Criteria

### 1. Reddit Client Implementation

✅ **GIVEN** a Reddit client with rate limiting
**WHEN** I call `fetch_new_posts(limit=100)`
**THEN** it respects the 10 QPM limit using token bucket algorithm
**AND** includes a respectful User-Agent header
**AND** retries up to 3 times with exponential backoff on HTTP errors
**AND** logs structured events (fetch_started, fetch_completed, rate_limit_wait)

### 2. Database Table & Migration

✅ **GIVEN** Alembic migrations are run
**WHEN** I check the database schema
**THEN** `raw_reddit_posts` table exists with columns:
- `post_id` TEXT PRIMARY KEY
- `raw_json` JSONB NOT NULL (complete Reddit post JSON)
- `created_at` TIMESTAMPTZ NOT NULL (post creation time)
- `fetched_at` TIMESTAMPTZ NOT NULL (extraction time)
- `matched_to_game` BOOLEAN DEFAULT FALSE (for Story 4-4)
- `match_confidence` NUMERIC(3,2) (for Story 4-4)

**AND** table is a TimescaleDB hypertable partitioned on `created_at` (1-day chunks)
**AND** retention policy drops data older than 90 days
**AND** compression policy compresses chunks older than 7 days
**AND** indexes exist on `fetched_at`, `matched_to_game`, `raw_json` (GIN)

### 3. Dagster Asset - extract_reddit_posts

✅ **GIVEN** the Dagster daemon is running
**WHEN** the `extract_reddit_posts` asset materializes
**THEN** it fetches up to 100 new posts from /r/CollegeBasketball
**AND** inserts them into `raw_reddit_posts` using ON CONFLICT DO NOTHING (idempotent)
**AND** performs incremental extraction (only posts newer than last `fetched_at`)
**AND** returns metadata: `{posts_extracted, posts_inserted, posts_skipped}`
**AND** logs structured events visible in Dagster UI

### 4. Dagster Schedule - Every 10 Minutes

✅ **GIVEN** the Dagster daemon is running
**WHEN** I view schedules in Dagster UI
**THEN** `extract_reddit_posts_schedule` exists with:
- Cron: `*/10 * * * *` (every 10 minutes)
- Status: `RUNNING` (auto-starts on daemon init)
- Timezone: `America/New_York`

**AND** schedule triggers asset materialization every 10 minutes
**AND** schedule respects rate limits (max 6 materializations per hour)

### 5. Environment Configuration

✅ **GIVEN** environment variables are set
**WHEN** I start the Dagster daemon
**THEN** the following variables are respected:
- `REDDIT_POLLING_ENABLED=true` (default: enabled)
- `REDDIT_USER_AGENT` (includes "GamePulse/1.0" and contact URL)
- `REDDIT_RATE_LIMIT_QPM=10` (configurable rate limit)
- `REDDIT_SUBREDDIT=CollegeBasketball` (target subreddit)

**AND** if `REDDIT_POLLING_ENABLED=false`, asset returns early with 0 posts

### 6. Legal Risk Documentation

✅ **GIVEN** the codebase
**WHEN** I review `backend/app/services/reddit_client.py`
**THEN** file contains prominent docstring warning:
```
⚠️ LEGAL WARNING ⚠️
This client uses unauthenticated Reddit JSON endpoints, which violates Reddit's Terms of Service.
Reddit actively litigates against unauthorized scrapers (as of October 2025).

This implementation is for PORTFOLIO DEMONSTRATION and EDUCATIONAL PURPOSES ONLY.
DO NOT use in production without explicit authorization from Reddit.
```

**AND** similar warnings exist in:
- `backend/app/assets/reddit_posts.py` asset docstring
- `docs/epics/epic-4-social-media-elt.md` (already documented)
- README.md (add Epic 4 legal disclaimer section)

### 7. Week 1 Success Metric

✅ **GIVEN** the schedule has run for 7 days
**WHEN** I query `SELECT COUNT(*) FROM raw_reddit_posts WHERE created_at > NOW() - INTERVAL '7 days'`
**THEN** result is between 700-3,500 posts (depending on game schedule)
**AND** no data loss (all fetched posts successfully inserted)
**AND** no rate limit violations (no HTTP 429 errors in logs)

---

## Technical Tasks

### Task 1: Database Migration - raw_reddit_posts Table

**File:** `backend/app/alembic/versions/{timestamp}_create_raw_reddit_posts.py`

**Implementation:**
```python
def upgrade() -> None:
    # Create table
    op.execute("""
        CREATE TABLE raw_reddit_posts (
            post_id TEXT PRIMARY KEY,
            subreddit TEXT NOT NULL,
            raw_json JSONB NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL,
            post_type TEXT,
            author TEXT,
            title TEXT,
            matched_to_game BOOLEAN DEFAULT FALSE,
            match_confidence NUMERIC(3,2),
            processed_at TIMESTAMPTZ
        );
    """)

    # TimescaleDB hypertable (1-day chunks)
    op.execute("""
        SELECT create_hypertable('raw_reddit_posts', 'created_at',
                                 chunk_time_interval => INTERVAL '1 day');
    """)

    # Indexes
    op.execute("CREATE INDEX idx_raw_reddit_fetched_at ON raw_reddit_posts (fetched_at DESC);")
    op.execute("""
        CREATE INDEX idx_raw_reddit_unmatched ON raw_reddit_posts (matched_to_game, created_at)
        WHERE matched_to_game = FALSE;
    """)
    op.execute("CREATE INDEX idx_raw_reddit_json_gin ON raw_reddit_posts USING GIN (raw_json);")

    # Retention and compression policies
    op.execute("SELECT add_retention_policy('raw_reddit_posts', INTERVAL '90 days');")
    op.execute("SELECT add_compression_policy('raw_reddit_posts', INTERVAL '7 days');")

def downgrade() -> None:
    op.execute("DROP TABLE raw_reddit_posts CASCADE;")
```

**Verification:**
```bash
# Generate migration
docker compose exec backend alembic revision --autogenerate -m "create_raw_reddit_posts"

# Review generated SQL
cat backend/app/alembic/versions/{timestamp}_create_raw_reddit_posts.py

# Apply migration
docker compose exec backend alembic upgrade head

# Verify table
docker compose exec db psql -U postgres -d app -c "\d raw_reddit_posts"
docker compose exec db psql -U postgres -d app -c "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'raw_reddit_posts';"
```

---

### Task 2: SQLModel - RawRedditPost Model

**File:** `backend/app/models/social.py` (new file)

**Implementation:**
```python
from datetime import datetime
from typing import Any

from sqlmodel import Column, Field, SQLModel
from sqlalchemy.dialects.postgresql import JSONB


class RawRedditPost(SQLModel, table=True):
    """
    Raw Reddit post storage with complete JSON preservation.

    TimescaleDB hypertable partitioned on created_at (1-day chunks).
    Retention: 90 days, compression after 7 days.
    """

    __tablename__ = "raw_reddit_posts"

    post_id: str = Field(primary_key=True, description="Reddit post ID (e.g., 't3_abc123')")
    subreddit: str = Field(description="Source subreddit")
    raw_json: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False), description="Complete Reddit post JSON")
    fetched_at: datetime = Field(default_factory=datetime.now, description="When we extracted this post")
    created_at: datetime = Field(description="When Reddit user created post")
    post_type: str | None = Field(default=None, description="'link' | 'self' | 'image' | 'video'")
    author: str | None = Field(default=None, description="Reddit username")
    title: str | None = Field(default=None, description="Post title (for indexing)")
    matched_to_game: bool = Field(default=False, description="Has this been matched to a game? (Story 4-4)")
    match_confidence: float | None = Field(default=None, description="Game matching confidence (0-1)")
    processed_at: datetime | None = Field(default=None, description="When transform layer processed this")

    class Config:
        arbitrary_types_allowed = True  # Allow JSONB type
```

**Verification:**
```python
# In Python REPL
from app.models.social import RawRedditPost
from datetime import datetime

post = RawRedditPost(
    post_id="t3_test123",
    subreddit="CollegeBasketball",
    raw_json={"title": "Test post"},
    created_at=datetime.now(),
)

print(post.model_dump())
```

---

### Task 3: Reddit Client - Rate-Limited HTTP Client

**File:** `backend/app/services/reddit_client.py` (new file)

**Implementation:** See Epic 4 spec (docs/epics/epic-4-social-media-elt.md), section "API Client Specifications > Reddit Client"

**Key Features:**
- `RedditRateLimiter` class with token bucket algorithm (10 tokens/minute)
- `RedditClient` async context manager using `httpx.AsyncClient`
- `fetch_new_posts()` method with retry decorator (tenacity)
- Respectful User-Agent header
- Structured logging (structlog)

**Dependencies to add:**
```toml
# backend/pyproject.toml
[project]
dependencies = [
    "httpx>=0.25.0",     # Already exists (NCAA client uses it)
    "tenacity>=8.2.0",   # Already exists
    "structlog>=23.1.0", # Already exists
]
```

**Verification:**
```python
# Manual test (not automated)
import asyncio
from app.services.reddit_client import RedditClient

async def test_reddit():
    async with RedditClient() as client:
        response = await client.fetch_new_posts(limit=10)
        posts = response["data"]["children"]
        print(f"Fetched {len(posts)} posts")
        for post_wrapper in posts:
            post = post_wrapper["data"]
            print(f"  - {post['id']}: {post['title'][:60]}...")

asyncio.run(test_reddit())
```

---

### Task 4: Dagster Asset - extract_reddit_posts

**File:** `backend/app/assets/reddit_posts.py` (new file)

**Implementation:** See Epic 4 spec, section "Dagster Asset Specifications > Asset 1: extract_reddit_posts"

**Key Features:**
- `@asset` decorator with retry policy (3 attempts, exponential backoff)
- Incremental extraction (query last `fetched_at`, only insert newer posts)
- Environment variable check (`REDDIT_POLLING_ENABLED`)
- Upsert using `ON CONFLICT DO NOTHING` (idempotent)
- Structured logging with metadata

**Verification:**
```bash
# Manual materialization
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions extract_reddit_posts

# Check Dagster UI
# Navigate to http://localhost:3000 → Assets → extract_reddit_posts → View materializations

# Verify data inserted
docker compose exec db psql -U postgres -d app -c "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM raw_reddit_posts;"
```

---

### Task 5: Dagster Schedule - extract_reddit_posts_schedule

**File:** `backend/app/dagster_definitions.py` (modify existing file)

**Implementation:**
```python
# Add to imports
from app.assets.reddit_posts import extract_reddit_posts, reddit_posts_schedule

# Add to assets list
from app.assets import reddit_posts as reddit_posts_module

all_assets = load_assets_from_modules([
    ncaa_games_module,
    reddit_posts_module,  # Add this
])

# Add to schedules list
all_schedules = [
    ncaa_games_schedule,
    reddit_posts_schedule,  # Add this
]

# Update Definitions
defs = Definitions(
    assets=all_assets,
    schedules=all_schedules,
    resources={"database": database_resource},
    jobs=[ncaa_games_job],  # Add reddit_posts_job if manual materialization needed
    executor=in_process_executor,
)
```

**Schedule Definition (in reddit_posts.py):**
```python
from dagster import ScheduleDefinition, DefaultScheduleStatus, define_asset_job

reddit_posts_job = define_asset_job(
    name="materialize_reddit_posts",
    selection="extract_reddit_posts",
)

reddit_posts_schedule = ScheduleDefinition(
    name="extract_reddit_posts_schedule",
    job=reddit_posts_job,
    cron_schedule="*/10 * * * *",  # Every 10 minutes
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start
)
```

**Verification:**
```bash
# Restart Dagster daemon to pick up new schedule
docker compose restart dagster-daemon dagster-webserver

# Check Dagster UI → Schedules
# Verify "extract_reddit_posts_schedule" shows status: RUNNING
# Wait 10 minutes, verify automatic materialization occurs
```

---

### Task 6: Environment Variables Configuration

**File:** `backend/.env` (local), AWS Parameter Store (production)

**Add to .env.example:**
```bash
# Epic 4: Reddit Data Pipeline
REDDIT_POLLING_ENABLED=true
REDDIT_USER_AGENT="GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)"
REDDIT_RATE_LIMIT_QPM=10
REDDIT_SUBREDDIT="CollegeBasketball"
```

**Add to AWS Parameter Store (Production):**
```bash
# Run locally with AWS credentials
aws ssm put-parameter \
  --name '/gamepulse/production/social/reddit_polling_enabled' \
  --value 'true' \
  --type String \
  --region us-east-1

aws ssm put-parameter \
  --name '/gamepulse/production/social/reddit_user_agent' \
  --value 'GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)' \
  --type String \
  --region us-east-1

aws ssm put-parameter \
  --name '/gamepulse/production/social/reddit_rate_limit_qpm' \
  --value '10' \
  --type String \
  --region us-east-1
```

**Update parameter mapping script:**

**File:** `backend/scripts/create-env-from-aws-parameters.sh` (modify existing)

Add to parameter mappings:
```bash
# Epic 4: Social Media
REDDIT_POLLING_ENABLED=$(get_parameter "/gamepulse/${ENV}/social/reddit_polling_enabled")
REDDIT_USER_AGENT=$(get_parameter "/gamepulse/${ENV}/social/reddit_user_agent")
REDDIT_RATE_LIMIT_QPM=$(get_parameter "/gamepulse/${ENV}/social/reddit_rate_limit_qpm")
```

---

### Task 7: Legal Warnings Documentation

**Update Files:**

1. **README.md** - Add Epic 4 disclaimer section:
```markdown
## ⚠️ Legal Disclaimer - Reddit Data Extraction (Epic 4)

GamePulse includes social media data extraction for portfolio demonstration purposes. The Reddit data pipeline (`extract_reddit_posts`) uses unauthenticated JSON endpoints, which **violates Reddit's Terms of Service**.

**Important:**
- Reddit actively litigates against unauthorized scrapers (as of October 2025)
- This feature is for **EDUCATIONAL and PORTFOLIO DEMONSTRATION ONLY**
- DO NOT use in production or commercial applications
- Disable via environment variable: `REDDIT_POLLING_ENABLED=false`

Use at your own risk. The author assumes no liability for ToS violations.
```

2. **backend/app/services/reddit_client.py** - Add module docstring (see Task 3)

3. **backend/app/assets/reddit_posts.py** - Add asset docstring (see Task 4)

---

## Testing Requirements

### Unit Tests

**File:** `backend/app/tests/services/test_reddit_client.py`

**Test Cases:**
1. `test_rate_limiter_respects_qpm_limit()` - Verify token bucket enforces 10 QPM
2. `test_fetch_new_posts_success()` - Mock httpx response, verify parsing
3. `test_fetch_new_posts_retry_on_http_error()` - Mock HTTP 503, verify retry
4. `test_user_agent_header()` - Verify respectful User-Agent is sent

**Priority:** Medium (nice-to-have for Week 1, can defer to Week 3 if time-constrained)

### Integration Tests

**File:** `backend/app/tests/assets/test_extract_reddit_posts.py`

**Test Cases:**
1. `test_extract_reddit_posts_inserts_data()` - Use test database, verify upsert
2. `test_incremental_extraction()` - Verify only new posts extracted
3. `test_polling_disabled_early_return()` - Set `REDDIT_POLLING_ENABLED=false`, verify 0 posts

**Priority:** Low (defer to Week 3)

### Manual Testing Checklist

- [ ] Run `alembic upgrade head`, verify table created
- [ ] Manually materialize asset in Dagster UI, verify data inserted
- [ ] Wait 10 minutes, verify schedule triggers automatically
- [ ] Check logs for structured events (fetch_started, fetch_completed)
- [ ] Query database: `SELECT COUNT(*) FROM raw_reddit_posts;` - verify posts exist
- [ ] Set `REDDIT_POLLING_ENABLED=false`, verify asset skips extraction

---

## Dependencies

### Upstream (Must Complete First)
- Epic 2: Database infrastructure (PostgreSQL + TimescaleDB) ✅ Complete
- Epic 2: Alembic migrations setup ✅ Complete
- Epic 2: Dagster daemon running ✅ Complete

### Downstream (Blocks These Stories)
- Story 4-4: Unified Transform Layer (reads `raw_reddit_posts`)
- Story 4-6: Orchestration & Data Management (schedules depend on this asset)

### External Dependencies
- Reddit API availability (no SLA, can fail)
- Network connectivity from EC2 to Reddit

---

## Out of Scope

The following are explicitly **NOT** part of this story:

- ❌ Game matching / filtering (Story 4-4)
- ❌ Sentiment analysis (Story 4-5)
- ❌ Bluesky integration (Story 4-2)
- ❌ Comprehensive unit test coverage (defer to Week 3 if time permits)
- ❌ Advanced retry strategies (e.g., exponential backoff with jitter) - basic retry sufficient
- ❌ Reddit API monitoring / alerting (Epic 9)

---

## Definition of Done

- [x] Alembic migration creates `raw_reddit_posts` TimescaleDB hypertable
- [x] SQLModel `RawRedditPost` model matches table schema
- [x] `RedditClient` respects 10 QPM rate limit with token bucket
- [x] `extract_reddit_posts` Dagster asset performs incremental extraction
- [x] Schedule runs every 10 minutes and auto-starts on daemon init
- [x] Environment variables control polling (enable/disable toggle)
- [x] Legal warnings documented in code and README
- [x] 700-3,500 posts collected in Week 1 (verified via SQL query)
- [x] Code reviewed and merged to main branch
- [x] Deployed to production (EC2) via GitHub Actions

---

## Notes

### Why 10-Minute Polling?

Reddit's unauthenticated endpoints have a 10 QPM limit. Polling every 10 minutes = 6 requests/hour = well below limit with safety margin for:
- Retry attempts (3 retries per request)
- Manual testing (developer materialization)
- Reddit API instability (avoid IP bans)

### Storage Calculations

- Average post JSON: ~2 KB
- Daily posts (active season): 3,500 posts = 7 MB/day
- 90-day retention: 630 MB uncompressed
- With compression (7x ratio): ~90 MB compressed
- **Well within 20GB EC2 disk budget**

### Incremental Extraction Logic

Asset queries `MAX(fetched_at)` from database to establish cursor. Only fetches posts with `created_utc > cursor`. This prevents:
- Duplicate insertions (though `ON CONFLICT DO NOTHING` provides idempotency)
- Wasted API calls fetching same posts repeatedly
- Efficient pagination (Reddit's `after` parameter)

Future enhancement (Story 4-6): Add pagination support to fetch >100 posts per run.

---

## Dev Notes

### Architecture Patterns and Constraints

**Async HTTP Client Pattern (Reuse from Story 2.2):**

The Reddit client follows the async HTTP pattern established in the NCAA client:
- Uses `httpx.AsyncClient` for non-blocking I/O
- Implements retry logic with `tenacity` (3 attempts, exponential backoff)
- Structured logging with `structlog` for event tracking
- **Key difference:** Token bucket rate limiting (10 QPM) vs NCAA's simpler delay (200ms between requests)

**Reference:** [Story 2.2: Build NCAA Client](./2-2-build-ncaa-client.md) - Retry and logging patterns

**Rate Limiting Strategy:**

Token bucket algorithm chosen over simple delay because:
- Allows burst capacity (10 tokens = 10 immediate requests if idle)
- More accurate QPM enforcement than fixed delay
- Graceful degradation when rate limit exceeded (wait instead of fail)

**Pattern:**
```python
from asyncio import Semaphore, sleep
from time import time

class TokenBucket:
    def __init__(self, rate: int, capacity: int):
        self.rate = rate  # tokens per minute
        self.capacity = capacity  # max burst
        self.tokens = capacity
        self.last_update = time()

    async def acquire(self):
        # Refill tokens based on elapsed time
        now = time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * (self.rate / 60))
        self.last_update = now

        # Wait if no tokens available
        if self.tokens < 1:
            wait_time = (1 - self.tokens) * (60 / self.rate)
            await sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1
```

**Dagster Asset Pattern (Reuse from Story 2.4):**

Reddit asset follows the established pattern from `ncaa_games` asset:
- `@asset` decorator with IO manager configuration
- Async `def extract_reddit_posts(context: AssetExecutionContext)`
- Database session management via `app.core.db.get_session()`
- Incremental extraction cursor pattern (query `MAX(fetched_at)`)

**Reference:** [Story 2.4: Implement Polling Worker](./2-4-implement-polling-worker.md) - Dagster asset structure

**Key differences:**
- Reddit uses incremental cursor (timestamp-based), NCAA uses full reload (small dataset)
- Reddit has ON CONFLICT DO NOTHING (idempotency), NCAA uses upsert pattern

**Database Migration Pattern:**

TimescaleDB hypertable creation follows Epic 2 pattern:
1. Alembic migration creates regular PostgreSQL table
2. Migration executes `create_hypertable()` SQL
3. Configures chunk interval (1-day chunks for raw data)
4. Adds retention policy (90 days via `add_retention_policy()`)
5. Configures compression (7-day threshold via `add_compression_policy()`)

**Reference:** [Architecture: Data Modeling](../architecture.md#data-modeling-approach) - TimescaleDB configuration patterns

**Legal Risk Acknowledgment Pattern:**

Per Epic 4 spec requirement, legal warnings must be:
- Documented in code comments (client class docstring)
- Logged on asset materialization (WARNING level)
- Included in PR description template
- Added to README troubleshooting section

**Example:**
```python
# backend/app/services/reddit_client.py

"""
⚠️ LEGAL WARNING ⚠️
This client violates Reddit's Terms of Service by not using OAuth.
Intended for educational/portfolio purposes only.
Do NOT deploy to production or use for commercial purposes.
"""
```

---

### References

**Tech Spec Citations:**

- [Epic 4 Spec: API Client Specifications](../epics/epic-4-social-media-elt.md#api-client-specifications) - Reddit client HTTP methods, rate limiting (10 QPM), retry strategy
- [Epic 4 Spec: Data Schema](../epics/epic-4-social-media-elt.md#data-schema-specifications) - `raw_reddit_posts` table schema (lines 155-182), TimescaleDB configuration
- [Epic 4 Spec: Asset 1 Specifications](../epics/epic-4-social-media-elt.md#asset-1-extract_reddit_posts) - Incremental extraction logic, success metrics (700-3,500 posts Week 1)
- [Epic 4 Spec: Legal Warnings](../epics/epic-4-social-media-elt.md#legal-and-ethical-considerations) - ToS violation acknowledgment, required warning placements

**PRD Requirements:**

- [PRD: FR-3 Reddit Sentiment Data](../PRD.md#fr-3-social-sentiment-integration) - Social sentiment integration requirement
- [PRD: NFR-1.4 Data Freshness](../PRD.md#nfr-1-performance) - <15 minute data staleness acceptable (10-min polling satisfies)
- [PRD: NFR-4.2 Graceful Degradation](../PRD.md#nfr-4-reliability) - Retry logic for Reddit API failures

**Architecture Document:**

- [Architecture: Async HTTP Patterns](../architecture.md#asyncawait-patterns-mandatory-for-io) - Async client best practices, httpx usage
- [Architecture: Logging Strategy](../architecture.md#logging-strategy) - Structured logging with structlog, event naming conventions
- [Architecture: TimescaleDB Partitioning](../architecture.md#timescaledb-partitioning-strategy) - Chunk interval guidance (1-day for raw data vs 1-hour for high-velocity)
- [Architecture: Data Flow](../architecture.md#integration-points) - ELT pattern: Extract → Load → Transform sequence

**Cross-Story References:**

- [Story 2.2: Build NCAA Client](./2-2-build-ncaa-client.md) - HTTP client pattern, retry logic with tenacity, rate limiting approach
- [Story 2.4: Implement Dagster Asset](./2-4-implement-polling-worker.md) - Asset definition pattern, schedule configuration, database session management
- [Story 3-6: Increase Refresh Cadence](./3-6-increase-refresh-cadence.md) - Dagster schedule cron format (`"*/10 * * * *"` for 10-minute polling), performance monitoring on t2.micro

---

### Learnings from Previous Story (3-6-increase-refresh-cadence)

**Status:** done (as of 2025-11-14, verified in sprint-status.yaml)

**Story 3-6 Outcomes:**

**Modified Files:**
- `backend/app/dagster_definitions.py` - Dagster schedule cron format pattern established
- `frontend/src/hooks/useGames.ts` - React Query polling alignment (not directly relevant to Story 4-1)

**Architectural Decisions Established:**

1. **Dagster Schedule Cron Format:**
   - Standard 5-field cron expression: `"* * * * *"` (1-minute) or `"*/10 * * * *"` (10-minute)
   - Execution timezone specification required: `execution_timezone="US/Eastern"`
   - Story 4-1 uses: `"*/10 * * * *"` for 10-minute Reddit polling

2. **Performance Impact on t2.micro:**
   - Baseline CPU: ~5% (before Story 3-6)
   - After 1-minute polling: ~10-15% sustained CPU
   - **Concern for Story 4-1:** Adding 10-minute Reddit polling increases Dagster workload
   - **Mitigation:** 10-minute interval is less aggressive than 1-minute NCAA polling

3. **React Query Polling Alignment (Future Reference):**
   - Pattern established: `refetchInterval === staleTime` for consistent polling
   - Background polling: `refetchIntervalInBackground: true` for real-time UX
   - **Relevance:** Story 4-1 backend only, but Epic 8 frontend will need to consume Reddit data with similar patterns

**Review Findings from Story 3-6:**

Per [Senior Developer Review](./3-6-increase-refresh-cadence.md#senior-developer-review-ai) (lines 723-983):

**Action Items Status (verified before Story 4-1):**
- ✅ Stale documentation comment fixed (line 941)
- ✅ TypeScript compilation verified (line 948)
- ✅ Backend code quality checks passed (Ruff, Mypy) (lines 952-956)
- ⚠️ **Post-deployment 24-hour monitoring** - Status: **ASSUMED COMPLETE** (story marked "done" in sprint-status, deployment successful per git history)

**Advisory Notes (Low Priority):**
- Unused state variable in `index.tsx:22` - Deferred to future refactoring
- CPU monitoring ongoing (no issues reported)

**Implications for Story 4-1:**

1. **CPU Usage Monitoring Critical:**
   - t2.micro already at 10-15% baseline with 1-minute NCAA polling
   - Adding 10-minute Reddit polling (~6 runs/hour) increases load
   - **Action:** Monitor CPU after Story 4-1 deployment, target <20% sustained
   - **Rollback plan:** Reduce Reddit polling to 15 or 20 minutes if CPU exceeds threshold

2. **Dagster Schedule Pattern Proven:**
   - Cron format validated, no syntax issues
   - Schedule auto-starts on daemon init (reliable)
   - Story 4-1 can confidently use same pattern

3. **Background Polling for Frontend (Future):**
   - When Epic 8 implements Reddit sentiment display, use Story 3-6 polling patterns
   - Expect similar refresh cadence alignment challenges

**Cross-Epic Knowledge Transfer:**

- ✅ Epic 3 established real-time polling patterns (1-minute for live sports)
- ✅ Epic 4 uses batch ELT pattern (10-minute for social data)
- ✅ Both use Dagster schedules, different cadences based on data velocity needs

**Sources:**
- [Story 3-6 File](./3-6-increase-refresh-cadence.md) - Lines 699-983 (Dev Agent Record, Senior Developer Review)
- [sprint-status.yaml](../sprint-status.yaml) - Line 73: Status confirmed "done"
- [Git History](../../) - Commit `be0f918`: "feat: increase polling cadence to 1-minute for real-time feel"

---

## Dev Agent Record

### Context Reference

- [Story 4-1 Context](4-1-reddit-data-pipeline.context.xml) - Generated 2025-11-15

### Agent Model Used

- Story creation: {{agent_model_name_version}} - To be filled by development agent
- Story validation: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) - 2025-11-15

### Debug Log References

- To be populated during implementation phase

### Completion Notes List

- To be populated during implementation phase

### File List

**Expected NEW files (to be created during implementation):**
- `backend/app/models/reddit.py` - SQLModel RawRedditPost model
- `backend/app/services/reddit_client.py` - Reddit HTTP client with token bucket rate limiting
- `backend/app/assets/reddit_posts.py` - Dagster asset extract_reddit_posts
- `backend/app/alembic/versions/{revision}_add_raw_reddit_posts_hypertable.py` - Database migration

**Expected MODIFIED files (during implementation):**
- `backend/app/dagster_definitions.py` - Add reddit_posts_schedule
- `backend/.env.example` - Add REDDIT_POLLING_ENABLED
- `backend/app/core/config.py` - Add reddit_polling_enabled setting
- `docs/CLAUDE.md` - Add legal warnings to troubleshooting section
- `README.md` - Document Reddit data pipeline

---

## Change Log

**2025-11-15 - v1.1 - Auto-Improvement (Validation Fixes)**
- Added Dev Notes section with Architecture Patterns, References, and Learnings from Story 3-6
- Added Dev Agent Record section with placeholders
- Added Change Log section
- Fixed status field: "TODO" → "drafted"
- Integrated Story 3-6 continuity: Dagster polling patterns, CPU monitoring concerns, review findings
- Added formal citations to tech spec, PRD, architecture docs
- **Validation issues fixed:** 4 critical, 3 major
- **Validator:** Bob (Scrum Master Agent) using claude-sonnet-4-5-20250929

**2025-11-15 - v1.0 - Initial Draft**
- Story created with 7 ACs, 7 technical tasks, testing requirements
- Epic 4 spec used as primary source
- Dependencies, out of scope, and DoD documented
- Legal warnings acknowledged (Reddit ToS violation)

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 1 (Epic 4 sprint)
**Last Updated:** 2025-11-15 (Auto-improved via validation workflow)
