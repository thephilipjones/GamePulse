# Story 4-2: Bluesky Data Pipeline

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-2
**Status:** TODO
**Estimated Effort:** 10-14 hours
**Priority:** High (Week 1-2 - blocks 4-4)
**Dependencies:** Epic 2 (dim_team, fact_game completed)

---

## User Story

**As a** data engineer,
**I want** to extract NCAA basketball posts from Bluesky using hashtag search with keyword filtering during fetch,
**So that** I have compliant, multi-platform social media data for game excitement scoring and reduce Reddit dependency risk.

---

## Context

Bluesky provides a **compliant alternative** to Reddit's ToS-violating unauthenticated endpoints. This story implements extraction using the official `atproto` Python SDK with:

- ✅ **No legal risk** - Official SDK with proper authentication (app password)
- ✅ **Keyword filtering during fetch** - Search by hashtags (#CollegeBasketball, #MarchMadness, #NCAAM)
- ✅ **Higher rate limits** - 5000 points/hour vs Reddit's 10 QPM
- ✅ **Growing sports community** - NCAA basketball fans migrating from Twitter/X

This story implements the **extraction and loading** components for Bluesky, mirroring Story 4-1's architecture but with platform-specific differences (atproto SDK vs httpx, hashtag search vs subreddit polling).

---

## Acceptance Criteria

### 1. Bluesky Client Implementation

✅ **GIVEN** a Bluesky client authenticated with app password
**WHEN** I call `fetch_posts_by_hashtag(hashtag="CollegeBasketball", limit=100)`
**THEN** it searches Bluesky for posts containing the hashtag
**AND** respects the 5000 points/hour rate limit
**AND** only returns posts from the last 24 hours (incremental extraction)
**AND** retries up to 3 times with exponential backoff on atproto errors
**AND** logs structured events (search_started, search_completed, rate_limit_wait)

### 2. Keyword Filtering During Fetch

✅ **GIVEN** configured hashtags: `["CollegeBasketball", "MarchMadness", "NCAAM"]`
**WHEN** I call `fetch_all_hashtags()`
**THEN** client searches all 3 hashtags
**AND** deduplicates posts by URI (same post can have multiple hashtags)
**AND** only returns posts containing game-related keywords
**AND** filters out irrelevant posts at fetch time (before database insertion)

### 3. Database Table & Migration

✅ **GIVEN** Alembic migrations are run
**WHEN** I check the database schema
**THEN** `raw_bluesky_posts` table exists with columns:
- `post_uri` TEXT PRIMARY KEY (atproto URI)
- `post_cid` TEXT NOT NULL (content ID - immutable hash)
- `raw_json` JSONB NOT NULL (complete Bluesky post view JSON)
- `created_at` TIMESTAMPTZ NOT NULL (post creation time)
- `fetched_at` TIMESTAMPTZ NOT NULL (extraction time)
- `matched_to_game` BOOLEAN DEFAULT FALSE (for Story 4-4)
- `match_confidence` NUMERIC(3,2) (for Story 4-4)

**AND** table is a TimescaleDB hypertable partitioned on `created_at` (1-day chunks)
**AND** retention policy drops data older than 90 days
**AND** compression policy compresses chunks older than 7 days
**AND** indexes exist on `fetched_at`, `matched_to_game`, `raw_json` (GIN)

### 4. Dagster Asset - extract_bluesky_posts

✅ **GIVEN** the Dagster daemon is running and Bluesky credentials are set
**WHEN** the `extract_bluesky_posts` asset materializes
**THEN** it fetches posts from all configured hashtags
**AND** inserts them into `raw_bluesky_posts` using ON CONFLICT DO NOTHING (idempotent)
**AND** performs incremental extraction (only posts newer than last `fetched_at`)
**AND** returns metadata: `{posts_extracted, posts_inserted}`
**AND** logs structured events visible in Dagster UI

### 5. Dagster Schedule - Every 5 Minutes

✅ **GIVEN** the Dagster daemon is running
**WHEN** I view schedules in Dagster UI
**THEN** `extract_bluesky_posts_schedule` exists with:
- Cron: `*/5 * * * *` (every 5 minutes)
- Status: `RUNNING` (auto-starts on daemon init)
- Timezone: `America/New_York`

**AND** schedule triggers asset materialization every 5 minutes
**AND** schedule respects rate limits (max 12 searches/hour = within 5000 points/hour limit)

### 6. Environment Configuration

✅ **GIVEN** environment variables are set
**WHEN** I start the Dagster daemon
**THEN** the following variables are respected:
- `BLUESKY_HANDLE` (e.g., "gamepulse.bsky.social")
- `BLUESKY_APP_PASSWORD` (app-specific password, NOT main password)
- `BLUESKY_RATE_LIMIT_POINTS_PER_HOUR=5000` (configurable limit)
- `BLUESKY_HASHTAGS="CollegeBasketball,MarchMadness,NCAAM"` (comma-separated)

**AND** if credentials are missing, asset raises ValueError with clear error message

### 7. Week 1-2 Success Metric

✅ **GIVEN** the schedule has run for 7 days
**WHEN** I query `SELECT COUNT(*) FROM raw_bluesky_posts WHERE created_at > NOW() - INTERVAL '7 days'`
**THEN** result is between 500-2,000 posts (depending on hashtag activity)
**AND** no data loss (all fetched posts successfully inserted)
**AND** no authentication errors (app password valid)

---

## Technical Tasks

### Task 1: Database Migration - raw_bluesky_posts Table

**File:** `backend/app/alembic/versions/{timestamp}_create_raw_bluesky_posts.py`

**Implementation:**
```python
def upgrade() -> None:
    # Create table
    op.execute("""
        CREATE TABLE raw_bluesky_posts (
            post_uri TEXT PRIMARY KEY,
            post_cid TEXT NOT NULL,
            raw_json JSONB NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL,
            author_did TEXT NOT NULL,
            author_handle TEXT,
            post_text TEXT,
            matched_to_game BOOLEAN DEFAULT FALSE,
            match_confidence NUMERIC(3,2),
            processed_at TIMESTAMPTZ
        );
    """)

    # TimescaleDB hypertable (1-day chunks)
    op.execute("""
        SELECT create_hypertable('raw_bluesky_posts', 'created_at',
                                 chunk_time_interval => INTERVAL '1 day');
    """)

    # Indexes
    op.execute("CREATE INDEX idx_raw_bluesky_fetched_at ON raw_bluesky_posts (fetched_at DESC);")
    op.execute("""
        CREATE INDEX idx_raw_bluesky_unmatched ON raw_bluesky_posts (matched_to_game, created_at)
        WHERE matched_to_game = FALSE;
    """)
    op.execute("CREATE INDEX idx_raw_bluesky_json_gin ON raw_bluesky_posts USING GIN (raw_json);")

    # Retention and compression policies
    op.execute("SELECT add_retention_policy('raw_bluesky_posts', INTERVAL '90 days');")
    op.execute("SELECT add_compression_policy('raw_bluesky_posts', INTERVAL '7 days');")

def downgrade() -> None:
    op.execute("DROP TABLE raw_bluesky_posts CASCADE;")
```

**Verification:**
```bash
# Generate migration
docker compose exec backend alembic revision --autogenerate -m "create_raw_bluesky_posts"

# Apply migration
docker compose exec backend alembic upgrade head

# Verify table
docker compose exec db psql -U postgres -d app -c "\d raw_bluesky_posts"
docker compose exec db psql -U postgres -d app -c "SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'raw_bluesky_posts';"
```

---

### Task 2: SQLModel - RawBlueskyPost Model

**File:** `backend/app/models/social.py` (modify, add to existing file from Story 4-1)

**Implementation:**
```python
class RawBlueskyPost(SQLModel, table=True):
    """
    Raw Bluesky post storage with complete JSON preservation.

    TimescaleDB hypertable partitioned on created_at (1-day chunks).
    Retention: 90 days, compression after 7 days.
    """

    __tablename__ = "raw_bluesky_posts"

    post_uri: str = Field(
        primary_key=True,
        description="atproto URI (e.g., 'at://did:plc:.../app.bsky.feed.post/...')"
    )
    post_cid: str = Field(description="Content ID (immutable hash)")
    raw_json: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
        description="Complete Bluesky post view JSON"
    )
    fetched_at: datetime = Field(default_factory=datetime.now, description="When we extracted this post")
    created_at: datetime = Field(description="When Bluesky user created post")
    author_did: str = Field(description="Decentralized identifier (DID)")
    author_handle: str | None = Field(default=None, description="Human-readable handle (e.g., 'alice.bsky.social')")
    post_text: str | None = Field(default=None, description="Post text (for indexing)")
    matched_to_game: bool = Field(default=False, description="Has this been matched to a game? (Story 4-4)")
    match_confidence: float | None = Field(default=None, description="Game matching confidence (0-1)")
    processed_at: datetime | None = Field(default=None, description="When transform layer processed this")

    class Config:
        arbitrary_types_allowed = True
```

---

### Task 3: Bluesky Client - atproto SDK Integration

**File:** `backend/app/services/bluesky_client.py` (new file)

**Implementation:** See Epic 4 spec (docs/epics/epic-4-social-media-elt.md), section "API Client Specifications > Bluesky Client"

**Key Features:**
- `BlueskyRateLimiter` class (5000 points/hour budget)
- `BlueskyClient` async context manager using `atproto.Client`
- `fetch_posts_by_hashtag()` method with keyword filtering
- `fetch_all_hashtags()` with deduplication
- Structured logging (structlog)

**Dependencies to add:**
```toml
# backend/pyproject.toml
[project]
dependencies = [
    "atproto>=0.0.63",  # Official Bluesky atproto SDK
    # ... existing dependencies
]
```

**Installation:**
```bash
cd backend
uv add atproto
uv sync
```

**Verification:**
```python
# Manual test (requires valid credentials)
import asyncio
from app.services.bluesky_client import BlueskyClient
import os

async def test_bluesky():
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_APP_PASSWORD")

    async with BlueskyClient(handle, password) as client:
        posts = await client.fetch_posts_by_hashtag("CollegeBasketball", limit=10)
        print(f"Fetched {len(posts)} posts")
        for post in posts:
            print(f"  - {post['uri']}: {post['record']['text'][:60]}...")

asyncio.run(test_bluesky())
```

---

### Task 4: Dagster Asset - extract_bluesky_posts

**File:** `backend/app/assets/bluesky_posts.py` (new file)

**Implementation:** See Epic 4 spec, section "Dagster Asset Specifications > Asset 2: extract_bluesky_posts"

**Key Features:**
- `@asset` decorator with retry policy (3 attempts, exponential backoff)
- Incremental extraction (query last `fetched_at`)
- Credential validation (raise error if missing)
- Upsert using `ON CONFLICT DO NOTHING` (idempotent)
- Structured logging with metadata

**Verification:**
```bash
# Manual materialization
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions extract_bluesky_posts

# Check Dagster UI
# Navigate to http://localhost:3000 → Assets → extract_bluesky_posts → View materializations

# Verify data inserted
docker compose exec db psql -U postgres -d app -c "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM raw_bluesky_posts;"
```

---

### Task 5: Dagster Schedule - extract_bluesky_posts_schedule

**File:** `backend/app/dagster_definitions.py` (modify existing file)

**Implementation:**
```python
# Add to imports
from app.assets.bluesky_posts import extract_bluesky_posts, bluesky_posts_schedule

# Add to assets list
from app.assets import bluesky_posts as bluesky_posts_module

all_assets = load_assets_from_modules([
    ncaa_games_module,
    reddit_posts_module,
    bluesky_posts_module,  # Add this
])

# Add to schedules list
all_schedules = [
    ncaa_games_schedule,
    reddit_posts_schedule,
    bluesky_posts_schedule,  # Add this
]
```

**Schedule Definition (in bluesky_posts.py):**
```python
from dagster import ScheduleDefinition, DefaultScheduleStatus, define_asset_job

bluesky_posts_job = define_asset_job(
    name="materialize_bluesky_posts",
    selection="extract_bluesky_posts",
)

bluesky_posts_schedule = ScheduleDefinition(
    name="extract_bluesky_posts_schedule",
    job=bluesky_posts_job,
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start (compliant API)
)
```

**Verification:**
```bash
# Restart Dagster daemon
docker compose restart dagster-daemon dagster-webserver

# Check Dagster UI → Schedules
# Verify "extract_bluesky_posts_schedule" shows status: RUNNING
# Wait 5 minutes, verify automatic materialization occurs
```

---

### Task 6: Environment Variables Configuration

**File:** `backend/.env` (local), AWS Parameter Store (production)

**Add to .env.example:**
```bash
# Epic 4: Bluesky Data Pipeline
BLUESKY_HANDLE="your-handle.bsky.social"
BLUESKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"  # App password from Bluesky settings
BLUESKY_RATE_LIMIT_POINTS_PER_HOUR=5000
BLUESKY_HASHTAGS="CollegeBasketball,MarchMadness,NCAAM"
```

**Create Bluesky App Password:**
1. Log in to Bluesky → Settings → Privacy and Security → App Passwords
2. Create new app password named "GamePulse Production"
3. Copy password (format: `xxxx-xxxx-xxxx-xxxx`)
4. Store in environment variables

**Add to AWS Parameter Store (Production):**
```bash
# Run locally with AWS credentials
aws ssm put-parameter \
  --name '/gamepulse/production/social/bluesky_handle' \
  --value 'gamepulse.bsky.social' \
  --type String \
  --region us-east-1

aws ssm put-parameter \
  --name '/gamepulse/production/social/bluesky_app_password' \
  --value 'xxxx-xxxx-xxxx-xxxx' \
  --type SecureString \
  --region us-east-1

aws ssm put-parameter \
  --name '/gamepulse/production/social/bluesky_hashtags' \
  --value 'CollegeBasketball,MarchMadness,NCAAM' \
  --type String \
  --region us-east-1
```

**Update parameter mapping script:**

**File:** `backend/scripts/create-env-from-aws-parameters.sh` (modify existing)

Add to parameter mappings:
```bash
# Epic 4: Social Media (add to existing section from Story 4-1)
BLUESKY_HANDLE=$(get_parameter "/gamepulse/${ENV}/social/bluesky_handle")
BLUESKY_APP_PASSWORD=$(get_parameter "/gamepulse/${ENV}/social/bluesky_app_password")
BLUESKY_HASHTAGS=$(get_parameter "/gamepulse/${ENV}/social/bluesky_hashtags")
```

---

### Task 7: Keyword Filtering Logic

**Implementation Note:** Keyword filtering happens during fetch in `BlueskyClient.fetch_posts_by_hashtag()`.

**Hashtag Search Query:**
```python
# In BlueskyClient.fetch_posts_by_hashtag()
results = self.client.app.bsky.feed.search_posts(
    q=f"#{hashtag}",  # Query: #CollegeBasketball
    since=since.isoformat(),  # Only posts after timestamp
    limit=limit,
)
```

**Deduplication Logic:**
```python
# In BlueskyClient.fetch_all_hashtags()
seen_uris = set()
unique_posts = []

for post in all_posts:
    if post["uri"] not in seen_uris:
        seen_uris.add(post["uri"])
        unique_posts.append(post)
```

**Future Enhancement (Story 4-6):**
Add team name keywords to hashtag list for broader coverage:
```python
KEYWORDS = [
    "#CollegeBasketball",
    "#MarchMadness",
    "#NCAAM",
    "Duke Blue Devils",  # Team-specific
    "UNC Tar Heels",
]
```

---

## Testing Requirements

### Unit Tests

**File:** `backend/app/tests/services/test_bluesky_client.py`

**Test Cases:**
1. `test_rate_limiter_respects_points_limit()` - Verify 5000 points/hour budget
2. `test_fetch_posts_by_hashtag_success()` - Mock atproto SDK response, verify parsing
3. `test_fetch_all_hashtags_deduplication()` - Verify duplicate URIs removed
4. `test_authentication_error_handling()` - Mock invalid credentials, verify error

**Priority:** Medium (nice-to-have for Week 2, can defer to Week 3)

### Integration Tests

**File:** `backend/app/tests/assets/test_extract_bluesky_posts.py`

**Test Cases:**
1. `test_extract_bluesky_posts_inserts_data()` - Use test database, verify upsert
2. `test_incremental_extraction()` - Verify only new posts extracted
3. `test_missing_credentials_raises_error()` - Unset credentials, verify ValueError

**Priority:** Low (defer to Week 3)

### Manual Testing Checklist

- [ ] Create Bluesky app password, add to `.env`
- [ ] Run `alembic upgrade head`, verify table created
- [ ] Manually materialize asset in Dagster UI, verify data inserted
- [ ] Wait 5 minutes, verify schedule triggers automatically
- [ ] Check logs for structured events (search_started, search_completed)
- [ ] Query database: `SELECT COUNT(*) FROM raw_bluesky_posts;` - verify posts exist
- [ ] Verify deduplication: Query for duplicate `post_uri` (should be 0)

---

## Dependencies

### Upstream (Must Complete First)
- Epic 2: Database infrastructure (PostgreSQL + TimescaleDB) ✅ Complete
- Epic 2: Alembic migrations setup ✅ Complete
- Epic 2: Dagster daemon running ✅ Complete

### Downstream (Blocks These Stories)
- Story 4-4: Unified Transform Layer (reads `raw_bluesky_posts`)
- Story 4-6: Orchestration & Data Management (schedules depend on this asset)

### External Dependencies
- Bluesky API availability (beta service, can be unstable)
- Network connectivity from EC2 to Bluesky
- Valid app password (must be rotated if compromised)

---

## Out of Scope

The following are explicitly **NOT** part of this story:

- ❌ Game matching / filtering (Story 4-4)
- ❌ Sentiment analysis (Story 4-5)
- ❌ Reddit integration (Story 4-1)
- ❌ Advanced keyword expansion (team names, player names) - basic hashtags sufficient
- ❌ Bluesky API monitoring / alerting (Epic 9)

---

## Definition of Done

- [x] Alembic migration creates `raw_bluesky_posts` TimescaleDB hypertable
- [x] SQLModel `RawBlueskyPost` model matches table schema
- [x] `BlueskyClient` authenticates with app password and searches by hashtag
- [x] `extract_bluesky_posts` Dagster asset performs incremental extraction
- [x] Schedule runs every 5 minutes and auto-starts on daemon init
- [x] Environment variables provide Bluesky credentials
- [x] Keyword filtering during fetch (hashtag search)
- [x] Deduplication logic prevents duplicate post URIs
- [x] 500-2,000 posts collected in Week 1-2 (verified via SQL query)
- [x] Code reviewed and merged to main branch
- [x] Deployed to production (EC2) via GitHub Actions

---

## Notes

### Why 5-Minute Polling?

Bluesky has higher rate limits (5000 points/hour) compared to Reddit (10 QPM). Polling every 5 minutes = 12 requests/hour = ~1200 points/hour (assuming 100 points per search), leaving ample buffer for:
- Multiple hashtag searches (3 hashtags × 12 runs = 36 searches/hour)
- Retry attempts
- Manual testing

### atproto SDK Stability

The atproto Python SDK is in early development (v0.0.x). Expect:
- Breaking API changes in minor versions
- Sparse documentation (rely on source code examples)
- Active community support on Bluesky Developer Discord

Pin to specific version (`atproto==0.0.63`) and test upgrades carefully.

### Storage Calculations

- Average post JSON: ~1.5 KB (smaller than Reddit due to 300-char post limit)
- Daily posts (active season): 2,000 posts = 3 MB/day
- 90-day retention: 270 MB uncompressed
- With compression (7x ratio): ~40 MB compressed
- **Well within 20GB EC2 disk budget**

### Hashtag Coverage

Initial hashtags target broad NCAA basketball conversation:
- `#CollegeBasketball` - General discussion
- `#MarchMadness` - Tournament-specific
- `#NCAAM` - NCAA Men's Basketball abbreviation

Future expansion (Story 4-6):
- Conference hashtags: `#ACC`, `#BigTen`, `#SEC`
- Team-specific: `#GoDuke`, `#GoHeels`
- Player hashtags: `#ZionWilliamson` (if trending)

### Incremental Extraction Logic

Asset queries `MAX(fetched_at)` from database to establish cursor. Only fetches posts with `created_at > cursor`. Bluesky SDK's `since` parameter provides native incremental support (unlike Reddit's pagination).

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 1-2 (Epic 4 sprint)
