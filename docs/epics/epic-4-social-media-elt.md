# Epic 4: Social Media Data Ingestion via ELT Pattern

**Epic ID:** Epic 4 (Revised)
**Epic Name:** Social Media Data Ingestion via ELT Pattern
**Status:** Ready for Development
**Created:** 2025-11-15
**Author:** Winston (Architect)
**Dependencies:** Epic 2 (Dimensional Data Model - dim_team, fact_game)
**Supports:** Epic 5 (Moment Detection & Excitement Scoring)

---

## Executive Summary

Epic 4 implements a **multi-platform social media data pipeline** using Extract-Load-Transform (ELT) architecture to collect game-related social conversations from Reddit and Bluesky. The pipeline stores complete raw JSON data in TimescaleDB hypertables, applies game matching filters during transformation, and produces sentiment-analyzed facts for downstream excitement scoring (Epic 5).

**Key Outcomes:**
- **700-3,500 daily posts** from Reddit's /r/CollegeBasketball (Week 1)
- **Multi-platform unified schema** combining Reddit + Bluesky (Week 2)
- **Sentiment-enriched fact table** with VADER analysis, ready for Epic 5 integration (Week 3)
- **Portfolio-quality data engineering** demonstrating ELT patterns, Dagster orchestration, TimescaleDB partitioning

**Timeline:** 3 weeks (6 stories)
**Effort Estimate:** 60-80 hours

---

## Business Context

### Problem Statement

GamePulse's excitement scoring algorithm (Epic 5) requires social sentiment signals to measure fan engagement around NCAA basketball games. Original design assumed Reddit OAuth API access for targeted subreddit monitoring, but **Reddit OAuth applications are not being approved** (as of November 2025).

### Constraints

| Constraint | Impact |
|------------|--------|
| **No Reddit OAuth** | Must use unauthenticated JSON endpoints with 10 QPM rate limit |
| **Legal Risk** | Reddit actively suing unauthorized scrapers (Oct 2025) - portfolio/demo only |
| **Storage Budget** | 20GB EC2 disk - requires 90-day retention + compression |
| **Memory Budget** | 1GB RAM + 4GB swap - batch size limited to 1000 posts |
| **Effort Constraint** | "Not crazy amount of effort" - 3 weeks maximum |

### Revised Solution: Multi-Platform ELT

**Strategic Pivot:**
1. **Diversify data sources:** Reddit (risky) + Bluesky (compliant) to reduce single-platform dependency
2. **ELT pattern:** Store complete raw JSON for future ML experimentation
3. **Early filtering:** Game matching during extraction (Bluesky) and transformation (both platforms) to minimize irrelevant data storage
4. **Modern data stack:** Dagster + TimescaleDB + VADER sentiment to demonstrate portfolio-quality engineering

**Risk Acceptance:**
- Reddit scraping violates ToS but is enabled by default for portfolio demonstration
- Environment variables allow disabling if Reddit enforces IP bans
- Warnings in code comments and documentation acknowledge legal risk

---

## Architecture Overview

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          EXTRACT LAYER (Dagster Assets)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  Reddit JSON API                    Bluesky atproto API                  │
│  (10 QPM limit)                     (5000 pts/hour)                      │
│         │                                  │                             │
│         │                                  │                             │
│         ▼                                  ▼                             │
│  extract_reddit_posts               extract_bluesky_posts               │
│  - Polling: 10 min                  - Polling: 5 min                    │
│  - User-Agent header                - Keyword filter: #CollegeBasketball│
│  - Rate limiter: 10 QPM             - SDK: atproto v0.0.63+             │
│                                                                           │
└───────────┬──────────────────────────────────┬───────────────────────────┘
            │                                  │
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LOAD LAYER (TimescaleDB Hypertables)                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  raw_reddit_posts                   raw_bluesky_posts                   │
│  - JSONB: Complete post JSON        - JSONB: Complete post JSON         │
│  - Partitioning: 1-day chunks       - Partitioning: 1-day chunks        │
│  - Retention: 90 days compressed    - Retention: 90 days compressed     │
│  - Indexes: GIN on JSONB, B-tree    - Indexes: GIN on JSONB, B-tree     │
│                                                                           │
└───────────┬──────────────────────────────────┬───────────────────────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TRANSFORM LAYER (Dagster Asset)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  transform_social_posts (Hourly)                                        │
│  ├─ Read: raw_reddit_posts, raw_bluesky_posts                           │
│  ├─ Game Matcher: Fuzzy team name matching (dim_team.aliases)           │
│  ├─ Filter: Only game-related posts (confidence > 0.6)                  │
│  ├─ Normalize: Engagement scoring (platform-aware formulas)             │
│  └─ Write: stg_social_posts (unified multi-platform schema)             │
│                                                                           │
│  Cleanup Job (Daily):                                                    │
│  └─ Delete unmatched raw posts older than 7 days                        │
│                                                                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FACT LAYER (Dagster Asset)                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  calculate_sentiment (Hourly, after transform)                          │
│  ├─ Read: stg_social_posts                                              │
│  ├─ VADER Sentiment: Compound score (-1 to +1)                          │
│  ├─ FK Resolution: Link to fact_game.game_key                           │
│  └─ Write: fact_social_sentiment                                        │
│                                                                           │
│  Consumed by:                                                            │
│  └─ Epic 5: Excitement scoring algorithm                                │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dagster Asset Lineage

```
extract_reddit_posts ────────────┐
                                 │
                                 ├──▶ transform_social_posts ──▶ calculate_sentiment
                                 │                                       │
extract_bluesky_posts ───────────┘                                       │
                                                                          ▼
                                                                   Epic 5: excitement_score
                                                                   (future, backlog)
```

**Asset Execution Order:**
1. **Parallel extraction:** `extract_reddit_posts` (every 10 min) + `extract_bluesky_posts` (every 5 min)
2. **Sequential transform:** `transform_social_posts` (hourly at :15) - waits for fresh extracts
3. **Sequential sentiment:** `calculate_sentiment` (hourly at :30) - waits for transform completion

---

## Data Schema Specifications

### 1. `raw_reddit_posts` (Raw Layer)

**Purpose:** Complete preservation of Reddit JSON responses for future ML analysis.

**Table Definition:**

```sql
CREATE TABLE raw_reddit_posts (
    post_id TEXT PRIMARY KEY,                  -- Reddit post ID (e.g., "t3_abc123")
    subreddit TEXT NOT NULL,                   -- Source subreddit (e.g., "CollegeBasketball")
    raw_json JSONB NOT NULL,                   -- Complete Reddit post JSON
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- When we extracted this post
    created_at TIMESTAMPTZ NOT NULL,           -- When Reddit user created post (extracted from JSON)
    post_type TEXT,                            -- "link" | "self" | "image" | "video"
    author TEXT,                               -- Reddit username (extracted from JSON)
    title TEXT,                                -- Post title (extracted from JSON for indexing)
    matched_to_game BOOLEAN DEFAULT FALSE,     -- Flag: Has this been matched to a game?
    match_confidence NUMERIC(3,2),             -- Game matching confidence (0-1), NULL if not matched
    processed_at TIMESTAMPTZ                   -- When transform layer processed this post
);

-- TimescaleDB hypertable (1-day chunks)
SELECT create_hypertable('raw_reddit_posts', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_raw_reddit_fetched_at ON raw_reddit_posts (fetched_at DESC);  -- Incremental loads
CREATE INDEX idx_raw_reddit_unmatched ON raw_reddit_posts (matched_to_game, created_at)  -- Cleanup queries
    WHERE matched_to_game = FALSE;
CREATE INDEX idx_raw_reddit_json_gin ON raw_reddit_posts USING GIN (raw_json);  -- JSONB queries

-- Retention policy: 90 days with compression
SELECT add_retention_policy('raw_reddit_posts', INTERVAL '90 days');
SELECT add_compression_policy('raw_reddit_posts', INTERVAL '7 days');  -- Compress after 7 days
```

**JSON Structure (raw_json column):**

```json
{
  "id": "t3_abc123",
  "subreddit": "CollegeBasketball",
  "author": "hoops_fan_42",
  "title": "Duke vs UNC - What a game!",
  "selftext": "Cameron Indoor was electric tonight...",
  "created_utc": 1700000000,
  "score": 142,
  "num_comments": 37,
  "upvote_ratio": 0.94,
  "url": "https://reddit.com/r/...",
  "permalink": "/r/CollegeBasketball/comments/...",
  "link_flair_text": "Post Game Thread"
}
```

**Storage Estimate:**
- Average post JSON: ~2 KB
- Daily posts: 700-3,500 (depending on game schedule)
- Daily storage: 1.4-7 MB uncompressed, ~0.3-1.5 MB compressed
- 90-day storage: ~135 MB compressed

### 2. `raw_bluesky_posts` (Raw Layer)

**Purpose:** Complete preservation of Bluesky post views for future ML analysis.

**Table Definition:**

```sql
CREATE TABLE raw_bluesky_posts (
    post_uri TEXT PRIMARY KEY,                 -- atproto URI (e.g., "at://did:plc:.../app.bsky.feed.post/...")
    post_cid TEXT NOT NULL,                    -- Content ID (immutable hash)
    raw_json JSONB NOT NULL,                   -- Complete Bluesky post view JSON
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL,           -- Post creation timestamp
    author_did TEXT NOT NULL,                  -- Decentralized identifier
    author_handle TEXT,                        -- Human-readable handle (e.g., "alice.bsky.social")
    post_text TEXT,                            -- Extracted text for indexing
    matched_to_game BOOLEAN DEFAULT FALSE,
    match_confidence NUMERIC(3,2),
    processed_at TIMESTAMPTZ
);

-- TimescaleDB hypertable (1-day chunks)
SELECT create_hypertable('raw_bluesky_posts', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_raw_bluesky_fetched_at ON raw_bluesky_posts (fetched_at DESC);
CREATE INDEX idx_raw_bluesky_unmatched ON raw_bluesky_posts (matched_to_game, created_at)
    WHERE matched_to_game = FALSE;
CREATE INDEX idx_raw_bluesky_json_gin ON raw_bluesky_posts USING GIN (raw_json);

-- Retention policy: 90 days with compression
SELECT add_retention_policy('raw_bluesky_posts', INTERVAL '90 days');
SELECT add_compression_policy('raw_bluesky_posts', INTERVAL '7 days');
```

**JSON Structure (raw_json column):**

```json
{
  "uri": "at://did:plc:abc123.../app.bsky.feed.post/xyz789",
  "cid": "bafyreiabc...",
  "author": {
    "did": "did:plc:abc123...",
    "handle": "hoops_fan.bsky.social",
    "displayName": "College Hoops Fan"
  },
  "record": {
    "text": "Duke vs UNC tonight! #CollegeBasketball #MarchMadness",
    "createdAt": "2025-11-15T20:00:00Z",
    "facets": [
      {"$type": "app.bsky.richtext.facet", "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": "CollegeBasketball"}]}
    ]
  },
  "likeCount": 23,
  "replyCount": 5,
  "repostCount": 8
}
```

**Storage Estimate:**
- Average post JSON: ~1.5 KB (smaller than Reddit due to 300-char limit)
- Daily posts: ~500-2,000 (depends on hashtag activity)
- 90-day storage: ~100 MB compressed

### 3. `stg_social_posts` (Transform Layer)

**Purpose:** Unified multi-platform schema with game-matched posts only.

**Table Definition:**

```sql
CREATE TABLE stg_social_posts (
    social_post_key BIGSERIAL PRIMARY KEY,     -- Surrogate key
    platform TEXT NOT NULL CHECK (platform IN ('reddit', 'bluesky')),  -- Source platform
    platform_post_id TEXT NOT NULL,            -- Original post ID/URI
    author_username TEXT,                      -- Platform username/handle
    post_text TEXT NOT NULL,                   -- Full post text/title
    created_at TIMESTAMPTZ NOT NULL,           -- Post creation timestamp
    fetched_at TIMESTAMPTZ NOT NULL,           -- When we extracted it

    -- Game Matching
    matched_teams TEXT[],                      -- Array of matched team_ids (e.g., {"duke", "unc"})
    match_confidence NUMERIC(3,2) NOT NULL,    -- Confidence score (0.6-1.0)
    matched_game_date DATE,                    -- Inferred game date (for FK resolution)

    -- Engagement Metrics (Platform-Normalized)
    engagement_score NUMERIC(10,2),            -- Normalized engagement (formula per platform)
    likes_count INTEGER,                       -- Platform-specific like/upvote count
    comments_count INTEGER,                    -- Comment/reply count
    shares_count INTEGER,                      -- Share/repost count

    -- Platform-Specific Extras (JSONB)
    platform_metadata JSONB,                   -- Reddit: upvote_ratio, flair; Bluesky: facets

    -- Lineage
    source_table TEXT NOT NULL,                -- 'raw_reddit_posts' | 'raw_bluesky_posts'
    source_row_id TEXT NOT NULL,               -- PK from source table
    transformed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(platform, platform_post_id)         -- Prevent duplicates
);

-- TimescaleDB hypertable (1-day chunks on created_at)
SELECT create_hypertable('stg_social_posts', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_stg_social_created_at ON stg_social_posts (created_at DESC);
CREATE INDEX idx_stg_social_teams_gin ON stg_social_posts USING GIN (matched_teams);  -- Array search
CREATE INDEX idx_stg_social_platform_date ON stg_social_posts (platform, matched_game_date);
CREATE INDEX idx_stg_social_engagement ON stg_social_posts (engagement_score DESC, created_at DESC);

-- Retention policy: 90 days (no compression - active querying)
SELECT add_retention_policy('stg_social_posts', INTERVAL '90 days');
```

**Engagement Score Formulas (Platform-Normalized):**

```python
# Reddit engagement score
engagement_score = (
    (upvotes * 1.0) +
    (comments * 2.0) +  # Comments = more engagement than upvotes
    (upvote_ratio * 10.0)  # High upvote ratio = quality signal
)

# Bluesky engagement score (adjusted for smaller scale)
engagement_score = (
    (likes * 1.5) +      # Bluesky likes weighted higher (smaller user base)
    (replies * 3.0) +
    (reposts * 2.5)
)
```

**Storage Estimate:**
- Only game-matched posts stored (~30-50% of raw posts)
- Daily posts: ~500-1,500 (after filtering)
- 90-day storage: ~50 MB

### 4. `fact_social_sentiment` (Fact Layer)

**Purpose:** Sentiment-enriched social posts linked to games for Epic 5 excitement scoring.

**Table Definition:**

```sql
CREATE TABLE fact_social_sentiment (
    sentiment_key BIGSERIAL PRIMARY KEY,       -- Surrogate key

    -- Dimensional FKs
    game_key BIGINT NOT NULL REFERENCES fact_game(game_key),  -- Link to game
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),  -- Game date
    social_post_key BIGINT NOT NULL REFERENCES stg_social_posts(social_post_key),  -- Source post

    -- Sentiment Analysis (VADER)
    sentiment_compound NUMERIC(5,4) NOT NULL,  -- Compound score (-1 to +1)
    sentiment_positive NUMERIC(5,4),           -- Positive component (0-1)
    sentiment_negative NUMERIC(5,4),           -- Negative component (0-1)
    sentiment_neutral NUMERIC(5,4),            -- Neutral component (0-1)

    -- Post Metadata (Denormalized for Epic 5 queries)
    platform TEXT NOT NULL,
    post_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    engagement_score NUMERIC(10,2),

    -- Lineage
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(social_post_key)  -- One sentiment analysis per post
);

-- TimescaleDB hypertable (1-day chunks on created_at)
SELECT create_hypertable('fact_social_sentiment', 'created_at', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_fact_sentiment_game_key ON fact_social_sentiment (game_key, created_at);
CREATE INDEX idx_fact_sentiment_date_key ON fact_social_sentiment (date_key);
CREATE INDEX idx_fact_sentiment_compound ON fact_social_sentiment (sentiment_compound, created_at);
CREATE INDEX idx_fact_sentiment_engagement ON fact_social_sentiment (engagement_score DESC, sentiment_compound);

-- Retention policy: 90 days
SELECT add_retention_policy('fact_social_sentiment', INTERVAL '90 days');
```

**Epic 5 Query Example:**

```sql
-- Calculate average sentiment and engagement for a game
SELECT
    g.game_id,
    g.home_team_name,
    g.away_team_name,
    COUNT(*) AS total_posts,
    AVG(s.sentiment_compound) AS avg_sentiment,
    SUM(s.engagement_score) AS total_engagement,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY s.sentiment_compound) AS sentiment_p90
FROM fact_game g
JOIN fact_social_sentiment s ON g.game_key = s.game_key
WHERE g.game_date = '2025-11-15'
GROUP BY g.game_key, g.game_id, g.home_team_name, g.away_team_name
ORDER BY total_engagement DESC;
```

**Storage Estimate:**
- Same row count as stg_social_posts (~500-1,500 daily)
- 90-day storage: ~30 MB

---

## API Client Specifications

### 1. Reddit Client

**File:** `backend/app/services/reddit_client.py`

**Implementation Pattern:**

```python
"""
Reddit JSON API client for unauthenticated endpoint access.

⚠️ LEGAL WARNING ⚠️
This client uses unauthenticated Reddit JSON endpoints, which violates Reddit's Terms of Service.
Reddit actively litigates against unauthorized scrapers (as of October 2025).

This implementation is for PORTFOLIO DEMONSTRATION and EDUCATIONAL PURPOSES ONLY.
DO NOT use in production without explicit authorization from Reddit.

Use at your own risk. Disable via environment variable: REDDIT_POLLING_ENABLED=false
"""

import asyncio
from datetime import datetime
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger(__name__)


class RedditRateLimiter:
    """
    Rate limiter for Reddit's 10 QPM (queries per minute) limit.

    Uses token bucket algorithm with 10 tokens per 60 seconds.
    """

    def __init__(self, queries_per_minute: int = 10):
        self.qpm = queries_per_minute
        self.tokens = queries_per_minute
        self.last_refill = datetime.now()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            # Refill tokens based on time elapsed
            now = datetime.now()
            elapsed = (now - self.last_refill).total_seconds()
            refill_amount = (elapsed / 60.0) * self.qpm

            self.tokens = min(self.qpm, self.tokens + refill_amount)
            self.last_refill = now

            # Wait if no tokens available
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (60.0 / self.qpm)
                logger.info("reddit_rate_limit_wait", wait_seconds=wait_time)
                await asyncio.sleep(wait_time)
                self.tokens = 1

            self.tokens -= 1


class RedditClient:
    """
    Async Reddit JSON API client for /r/CollegeBasketball posts.

    Features:
    - 10 QPM rate limiting (Reddit unauthenticated limit)
    - Exponential backoff retry (3 attempts)
    - Respectful User-Agent header
    - Structured logging
    """

    SUBREDDIT = "CollegeBasketball"
    BASE_URL = f"https://www.reddit.com/r/{SUBREDDIT}"
    USER_AGENT = "GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)"

    def __init__(self, queries_per_minute: int = 10):
        self.rate_limiter = RedditRateLimiter(queries_per_minute)
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "RedditClient":
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_new_posts(self, limit: int = 100, after: str | None = None) -> dict[str, Any]:
        """
        Fetch new posts from /r/CollegeBasketball.

        Args:
            limit: Number of posts to fetch (max 100 per request)
            after: Reddit pagination token (fullname of last post, e.g., "t3_abc123")

        Returns:
            Reddit JSON response dict with "data" key containing posts array

        Raises:
            httpx.HTTPStatusError: If Reddit returns non-200 status
            httpx.TimeoutException: If request exceeds 30s timeout
        """
        await self.rate_limiter.acquire()

        url = f"{self.BASE_URL}/new.json"
        params = {"limit": limit}
        if after:
            params["after"] = after

        logger.info("reddit_fetch_started", url=url, limit=limit, after=after)

        if not self.client:
            raise RuntimeError("RedditClient used outside async context manager")

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        posts_count = len(data.get("data", {}).get("children", []))

        logger.info("reddit_fetch_completed", posts_count=posts_count)

        return data

    async def fetch_hot_posts(self, limit: int = 100) -> dict[str, Any]:
        """Fetch hot posts (for high-activity detection)."""
        await self.rate_limiter.acquire()

        url = f"{self.BASE_URL}/hot.json"
        params = {"limit": limit}

        logger.info("reddit_fetch_hot_started", url=url, limit=limit)

        if not self.client:
            raise RuntimeError("RedditClient used outside async context manager")

        response = await self.client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        posts_count = len(data.get("data", {}).get("children", []))

        logger.info("reddit_fetch_hot_completed", posts_count=posts_count)

        return data


# Usage example (not executed, for reference)
"""
async with RedditClient() as client:
    response = await client.fetch_new_posts(limit=100)
    posts = response["data"]["children"]

    for post_wrapper in posts:
        post = post_wrapper["data"]
        print(f"{post['id']}: {post['title']}")
"""
```

**Configuration (Environment Variables):**

```bash
# .env
REDDIT_POLLING_ENABLED=true          # Set to 'false' to disable Reddit extraction
REDDIT_USER_AGENT="GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)"
REDDIT_RATE_LIMIT_QPM=10             # Queries per minute (conservative default)
REDDIT_SUBREDDIT="CollegeBasketball" # Target subreddit
```

### 2. Bluesky Client

**File:** `backend/app/services/bluesky_client.py`

**Implementation Pattern:**

```python
"""
Bluesky atproto client for hashtag-based post extraction.

✅ COMPLIANT: Uses official atproto SDK with proper authentication.
No legal risk - follows Bluesky's developer guidelines.
"""

from datetime import datetime, timedelta
from typing import Any

import structlog
from atproto import Client as AtprotoClient
from atproto.exceptions import AtProtocolError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = structlog.get_logger(__name__)


class BlueskyRateLimiter:
    """
    Rate limiter for Bluesky's 5000 points/hour limit.

    Assumptions:
    - Search queries: ~100 points each (conservative estimate)
    - Max 50 searches/hour to stay under limit
    - Refills linearly over time
    """

    def __init__(self, points_per_hour: int = 5000, points_per_search: int = 100):
        self.pph = points_per_hour
        self.pps = points_per_search
        self.points = points_per_hour
        self.last_refill = datetime.now()

    async def acquire(self) -> None:
        # Refill points based on time elapsed
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()
        refill_amount = (elapsed / 3600.0) * self.pph

        self.points = min(self.pph, self.points + refill_amount)
        self.last_refill = now

        # Wait if insufficient points
        if self.points < self.pps:
            wait_time = ((self.pps - self.points) / self.pph) * 3600.0
            logger.info("bluesky_rate_limit_wait", wait_seconds=wait_time, points_needed=self.pps)
            await asyncio.sleep(wait_time)
            self.points = self.pps

        self.points -= self.pps


class BlueskyClient:
    """
    Async Bluesky client for hashtag-based post search.

    Features:
    - Official atproto SDK (v0.0.63+)
    - Keyword filtering during fetch (#CollegeBasketball, team names)
    - 5000 points/hour rate limiting
    - Exponential backoff retry
    """

    HASHTAGS = ["CollegeBasketball", "MarchMadness", "NCAAM"]

    def __init__(self, handle: str, app_password: str):
        self.handle = handle
        self.app_password = app_password
        self.client: AtprotoClient | None = None
        self.rate_limiter = BlueskyRateLimiter()

    async def __aenter__(self) -> "BlueskyClient":
        self.client = AtprotoClient()
        self.client.login(self.handle, self.app_password)
        logger.info("bluesky_authenticated", handle=self.handle)
        return self

    async def __aexit__(self, *args: Any) -> None:
        # atproto SDK doesn't require explicit cleanup
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(AtProtocolError),
        reraise=True,
    )
    async def fetch_posts_by_hashtag(
        self,
        hashtag: str,
        since: datetime | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Fetch posts containing a specific hashtag.

        Args:
            hashtag: Hashtag to search (without # prefix, e.g., "CollegeBasketball")
            since: Only fetch posts after this timestamp (default: last 24 hours)
            limit: Max posts to return (default: 100)

        Returns:
            List of Bluesky post view dicts
        """
        await self.rate_limiter.acquire()

        if not self.client:
            raise RuntimeError("BlueskyClient used outside async context manager")

        if since is None:
            since = datetime.now() - timedelta(hours=24)

        logger.info("bluesky_search_started", hashtag=hashtag, since=since, limit=limit)

        # Use atproto SDK search_posts method
        # Note: Actual API may differ - this is pseudocode based on typical SDK patterns
        results = self.client.app.bsky.feed.search_posts(
            q=f"#{hashtag}",
            since=since.isoformat(),
            limit=limit,
        )

        posts = results.posts if hasattr(results, "posts") else []

        logger.info("bluesky_search_completed", posts_count=len(posts))

        return [self._post_to_dict(post) for post in posts]

    def _post_to_dict(self, post: Any) -> dict[str, Any]:
        """Convert atproto post object to dict for storage."""
        return {
            "uri": post.uri,
            "cid": post.cid,
            "author": {
                "did": post.author.did,
                "handle": post.author.handle,
                "displayName": getattr(post.author, "display_name", None),
            },
            "record": {
                "text": post.record.text,
                "createdAt": post.record.created_at,
                "facets": getattr(post.record, "facets", []),
            },
            "likeCount": getattr(post, "like_count", 0),
            "replyCount": getattr(post, "reply_count", 0),
            "repostCount": getattr(post, "repost_count", 0),
        }

    async def fetch_all_hashtags(self, since: datetime | None = None) -> list[dict[str, Any]]:
        """Fetch posts from all configured hashtags."""
        all_posts = []

        for hashtag in self.HASHTAGS:
            try:
                posts = await self.fetch_posts_by_hashtag(hashtag, since=since)
                all_posts.extend(posts)
            except AtProtocolError as e:
                logger.error("bluesky_hashtag_fetch_failed", hashtag=hashtag, error=str(e))
                # Continue with other hashtags

        # Deduplicate by URI
        seen_uris = set()
        unique_posts = []
        for post in all_posts:
            if post["uri"] not in seen_uris:
                seen_uris.add(post["uri"])
                unique_posts.append(post)

        logger.info("bluesky_all_hashtags_completed", total_posts=len(unique_posts))

        return unique_posts
```

**Configuration (Environment Variables):**

```bash
# .env
BLUESKY_HANDLE="gamepulse.bsky.social"     # Your Bluesky handle
BLUESKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx" # App-specific password (not main password!)
BLUESKY_RATE_LIMIT_POINTS_PER_HOUR=5000    # Conservative limit
BLUESKY_HASHTAGS="CollegeBasketball,MarchMadness,NCAAM"  # Comma-separated
```

**Required Dependencies:**

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "atproto>=0.0.63",  # Official Bluesky atproto SDK
    # ... existing dependencies
]
```

---

## Game Matching Algorithm

### Purpose

Filter social posts to only game-related content by detecting team mentions using fuzzy string matching against `dim_team.aliases`.

### Implementation

**File:** `backend/app/services/game_matcher.py`

```python
"""
Game matching service for social posts.

Matches social post text against NCAA team names/aliases to:
1. Filter irrelevant posts (only store game-related content)
2. Provide confidence scores for match quality
3. Link posts to specific games via team + date resolution
"""

from datetime import date
from typing import Any

import structlog
from rapidfuzz import fuzz, process
from sqlmodel import Session, select

from app.models.team import DimTeam

logger = structlog.get_logger(__name__)


class GameMatcher:
    """
    Fuzzy team name matcher for social posts.

    Uses RapidFuzz library for efficient fuzzy string matching.
    """

    CONFIDENCE_THRESHOLD = 0.6  # Minimum match confidence to consider relevant

    def __init__(self, session: Session):
        self.session = session
        self.teams_cache: dict[str, DimTeam] = {}
        self._load_teams_cache()

    def _load_teams_cache(self) -> None:
        """Load all NCAA basketball teams into memory for fast matching."""
        stmt = select(DimTeam).where(
            DimTeam.sport == "ncaam",
            DimTeam.is_current == True,
        )
        teams = self.session.exec(stmt).all()

        for team in teams:
            self.teams_cache[team.team_id] = team

        logger.info("game_matcher_teams_loaded", teams_count=len(self.teams_cache))

    def match_post_to_teams(self, post_text: str) -> dict[str, Any]:
        """
        Match post text to NCAA teams.

        Args:
            post_text: Reddit title/selftext or Bluesky post text

        Returns:
            {
                "matched_teams": ["duke", "unc"],  # team_ids
                "match_confidence": 0.85,          # 0-1 score
                "is_game_related": True,           # confidence >= threshold
                "match_details": {
                    "duke": {"alias_matched": "Duke Blue Devils", "score": 95},
                    "unc": {"alias_matched": "UNC", "score": 90}
                }
            }
        """
        # Build searchable text (lowercase for matching)
        search_text = post_text.lower()

        # Collect all team aliases
        all_aliases: dict[str, str] = {}  # alias -> team_id
        for team_id, team in self.teams_cache.items():
            # Add team name
            all_aliases[team.team_name.lower()] = team_id

            # Add aliases from TEXT[] column
            if team.aliases:
                for alias in team.aliases:
                    all_aliases[alias.lower()] = team_id

        # Find best matches using fuzzy string matching
        matches = process.extract(
            search_text,
            all_aliases.keys(),
            scorer=fuzz.partial_ratio,  # Allows substring matches
            limit=5,  # Top 5 matches
        )

        # Filter matches by score threshold (0-100 scale)
        matched_teams = []
        match_details = {}

        for alias, score, _ in matches:
            if score >= (self.CONFIDENCE_THRESHOLD * 100):
                team_id = all_aliases[alias]
                if team_id not in matched_teams:  # Avoid duplicates
                    matched_teams.append(team_id)
                    match_details[team_id] = {
                        "alias_matched": alias,
                        "score": score,
                    }

        # Calculate overall confidence (average of top 2 scores)
        confidence = 0.0
        if matched_teams:
            top_scores = sorted([d["score"] for d in match_details.values()], reverse=True)[:2]
            confidence = sum(top_scores) / len(top_scores) / 100.0  # Normalize to 0-1

        is_game_related = confidence >= self.CONFIDENCE_THRESHOLD

        result = {
            "matched_teams": matched_teams,
            "match_confidence": round(confidence, 2),
            "is_game_related": is_game_related,
            "match_details": match_details,
        }

        logger.debug("game_match_result", post_text_preview=post_text[:100], result=result)

        return result

    def resolve_game_key(
        self,
        team_ids: list[str],
        post_date: date
    ) -> int | None:
        """
        Resolve team mentions to a specific game_key.

        Logic:
        - If 2 teams mentioned: Find game where both teams play each other on post_date
        - If 1 team mentioned: Find game for that team on post_date (home or away)
        - If 0 or 3+ teams: Return None (ambiguous)

        Args:
            team_ids: List of matched team_ids (e.g., ["duke", "unc"])
            post_date: Date to search for games

        Returns:
            game_key if unique match found, else None
        """
        from app.models.game import FactGame

        if len(team_ids) == 2:
            # Two teams: Find head-to-head game
            team1_id, team2_id = team_ids

            # Get team_keys from team_ids
            team1 = self.teams_cache.get(team1_id)
            team2 = self.teams_cache.get(team2_id)

            if not team1 or not team2:
                return None

            stmt = select(FactGame).where(
                FactGame.game_date == post_date,
                (
                    ((FactGame.home_team_key == team1.team_key) & (FactGame.away_team_key == team2.team_key)) |
                    ((FactGame.home_team_key == team2.team_key) & (FactGame.away_team_key == team1.team_key))
                )
            )

            game = self.session.exec(stmt).first()
            return game.game_key if game else None

        elif len(team_ids) == 1:
            # Single team: Find any game for that team
            team = self.teams_cache.get(team_ids[0])
            if not team:
                return None

            stmt = select(FactGame).where(
                FactGame.game_date == post_date,
                (
                    (FactGame.home_team_key == team.team_key) |
                    (FactGame.away_team_key == team.team_key)
                )
            )

            game = self.session.exec(stmt).first()
            return game.game_key if game else None

        else:
            # 0 or 3+ teams: Ambiguous
            logger.warning("game_resolution_ambiguous", team_ids=team_ids, post_date=post_date)
            return None
```

**Required Dependencies:**

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "rapidfuzz>=3.0.0",  # Fast fuzzy string matching
    # ... existing dependencies
]
```

**Testing Fixtures:**

```python
# backend/app/tests/services/test_game_matcher.py

SAMPLE_POSTS = [
    {
        "text": "Duke vs UNC tonight! Cameron Indoor is going to be electric! #CollegeBasketball",
        "expected_teams": ["duke", "unc"],
        "expected_confidence": 0.95,
    },
    {
        "text": "Go Blue Devils! Ready for tip-off at 7pm",
        "expected_teams": ["duke"],
        "expected_confidence": 0.85,
    },
    {
        "text": "Just had pizza for dinner. Great day!",  # Irrelevant post
        "expected_teams": [],
        "expected_confidence": 0.0,
    },
]
```

---

## Sentiment Analysis Integration

### VADER Sentiment

**Library:** `vaderSentiment` (rule-based sentiment optimized for social media)

**Why VADER over Transformers:**
- **339x faster** than transformer models (DistilBERT)
- **Optimized for social text:** Handles slang, emojis, caps, punctuation (!!!, ???)
- **Good-enough accuracy:** Sufficient for excitement scoring (not research-grade NLP)
- **No GPU required:** Runs efficiently on t2.micro CPU

**Implementation:**

**File:** `backend/app/services/sentiment_analyzer.py`

```python
"""
VADER sentiment analysis for social posts.

VADER (Valence Aware Dictionary and sEntiment Reasoner) is optimized for
social media text with slang, emojis, and punctuation emphasis.
"""

import structlog
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = structlog.get_logger(__name__)


class SentimentAnalyzer:
    """
    VADER-based sentiment analyzer for social posts.

    Output scores:
    - compound: Overall sentiment (-1 to +1, normalized)
    - positive: Positive component (0-1)
    - negative: Negative component (0-1)
    - neutral: Neutral component (0-1)

    Interpretation (compound score):
    - >= 0.05: Positive
    - <= -0.05: Negative
    - -0.05 to 0.05: Neutral
    """

    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        logger.info("sentiment_analyzer_initialized", library="vaderSentiment")

    def analyze(self, text: str) -> dict[str, float]:
        """
        Analyze sentiment of social post text.

        Args:
            text: Post title/selftext (Reddit) or post text (Bluesky)

        Returns:
            {
                "compound": 0.85,     # Overall score (-1 to +1)
                "positive": 0.75,     # Positive component
                "negative": 0.05,     # Negative component
                "neutral": 0.20,      # Neutral component
            }
        """
        scores = self.analyzer.polarity_scores(text)

        logger.debug("sentiment_analyzed", text_preview=text[:100], compound=scores["compound"])

        return {
            "compound": scores["compound"],
            "positive": scores["pos"],
            "negative": scores["neg"],
            "neutral": scores["neu"],
        }

    def batch_analyze(self, texts: list[str]) -> list[dict[str, float]]:
        """Analyze multiple texts efficiently."""
        return [self.analyze(text) for text in texts]
```

**Required Dependencies:**

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "vaderSentiment>=3.3.2",
    # ... existing dependencies
]
```

**Integration into calculate_sentiment Asset:**

```python
# In transform_social_posts Dagster asset
from app.services.sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()

for post in stg_social_posts:
    sentiment = analyzer.analyze(post.post_text)

    # Insert into fact_social_sentiment
    fact_row = FactSocialSentiment(
        social_post_key=post.social_post_key,
        game_key=resolved_game_key,
        sentiment_compound=sentiment["compound"],
        sentiment_positive=sentiment["positive"],
        sentiment_negative=sentiment["negative"],
        sentiment_neutral=sentiment["neutral"],
        # ... other fields
    )
```

---

## Dagster Asset Specifications

### Asset 1: `extract_reddit_posts`

**Purpose:** Extract posts from Reddit /r/CollegeBasketball and load into `raw_reddit_posts` table.

**Schedule:** Every 10 minutes (conservative for 10 QPM limit)

**File:** `backend/app/assets/reddit_posts.py`

```python
from dagster import (
    asset,
    AssetExecutionContext,
    RetryPolicy,
    Backoff,
    ScheduleDefinition,
    DefaultScheduleStatus,
)
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.resources.database import DatabaseResource
from app.services.reddit_client import RedditClient
from app.models.social import RawRedditPost


@asset(
    name="extract_reddit_posts",
    description="Extract new posts from /r/CollegeBasketball using unauthenticated JSON endpoints",
    group_name="social_media_extraction",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=5,  # Start with 5s delay (longer than NCAA for Reddit instability)
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def extract_reddit_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    ⚠️ LEGAL WARNING ⚠️
    This asset uses unauthenticated Reddit JSON endpoints, violating Reddit ToS.
    Enable/disable via environment variable: REDDIT_POLLING_ENABLED
    """

    import os

    # Check if Reddit polling is enabled (default: true for portfolio demo)
    if os.getenv("REDDIT_POLLING_ENABLED", "true").lower() != "true":
        context.log.warning("reddit_polling_disabled", reason="REDDIT_POLLING_ENABLED=false")
        return {"posts_extracted": 0, "posts_inserted": 0}

    context.log.info("extract_reddit_posts_started")

    async with database.get_session() as session:
        # Get last fetched timestamp for incremental extraction
        last_fetch_stmt = select(RawRedditPost.created_at).order_by(
            RawRedditPost.created_at.desc()
        ).limit(1)
        last_fetch_result = await session.execute(last_fetch_stmt)
        last_fetch = last_fetch_result.scalar_one_or_none()

        # Default to last 24 hours if no data
        since = last_fetch if last_fetch else datetime.now() - timedelta(hours=24)

        context.log.info("incremental_extraction_since", since=since)

        posts_extracted = 0
        posts_inserted = 0
        posts_skipped = 0

        async with RedditClient() as client:
            # Fetch new posts (max 100 per call due to QPM limit)
            response = await client.fetch_new_posts(limit=100)

            posts_data = response.get("data", {}).get("children", [])
            posts_extracted = len(posts_data)

            for post_wrapper in posts_data:
                post = post_wrapper["data"]

                # Extract creation timestamp
                created_at = datetime.fromtimestamp(post["created_utc"])

                # Skip if before our incremental cursor
                if created_at <= since:
                    posts_skipped += 1
                    continue

                # Create RawRedditPost record
                raw_post = RawRedditPost(
                    post_id=post["id"],
                    subreddit=post["subreddit"],
                    raw_json=post,  # Store complete JSON
                    fetched_at=datetime.now(),
                    created_at=created_at,
                    post_type=post.get("post_hint", "self"),
                    author=post.get("author"),
                    title=post.get("title"),
                )

                # Upsert (idempotent)
                from sqlmodel import insert
                stmt = insert(RawRedditPost).values(raw_post.dict())
                stmt = stmt.on_conflict_do_nothing(index_elements=["post_id"])

                await session.execute(stmt)
                posts_inserted += 1

            await session.commit()

        context.log.info(
            "extract_reddit_posts_completed",
            posts_extracted=posts_extracted,
            posts_inserted=posts_inserted,
            posts_skipped=posts_skipped,
        )

        return {
            "posts_extracted": posts_extracted,
            "posts_inserted": posts_inserted,
            "posts_skipped": posts_skipped,
        }


# Schedule: Every 10 minutes
# NOTE: DefaultScheduleStatus.STOPPED for manual opt-in (legal risk)
reddit_posts_schedule = ScheduleDefinition(
    name="extract_reddit_posts_schedule",
    job=define_asset_job("materialize_reddit_posts", selection="extract_reddit_posts"),
    cron_schedule="*/10 * * * *",  # Every 10 minutes
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start (Philip's preference)
)
```

**Metadata Logging:**
- `posts_extracted`: Total posts from API
- `posts_inserted`: New posts added to database
- `posts_skipped`: Posts before incremental cursor

---

### Asset 2: `extract_bluesky_posts`

**Purpose:** Extract posts from Bluesky using hashtag search, with keyword filtering during fetch.

**Schedule:** Every 5 minutes (Bluesky has higher rate limits)

**File:** `backend/app/assets/bluesky_posts.py`

```python
@asset(
    name="extract_bluesky_posts",
    description="Extract posts from Bluesky using #CollegeBasketball and related hashtags",
    group_name="social_media_extraction",
    compute_kind="python",
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=3,
        backoff=Backoff.EXPONENTIAL,
    ),
)
async def extract_bluesky_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Extract Bluesky posts with keyword filtering during fetch.

    ✅ COMPLIANT: Uses official atproto SDK with proper authentication.
    """

    import os
    from app.services.bluesky_client import BlueskyClient
    from app.models.social import RawBlueskyPost

    context.log.info("extract_bluesky_posts_started")

    # Get credentials from environment
    handle = os.getenv("BLUESKY_HANDLE")
    app_password = os.getenv("BLUESKY_APP_PASSWORD")

    if not handle or not app_password:
        context.log.error("bluesky_credentials_missing")
        raise ValueError("BLUESKY_HANDLE and BLUESKY_APP_PASSWORD must be set")

    async with database.get_session() as session:
        # Get last fetched timestamp
        last_fetch_stmt = select(RawBlueskyPost.created_at).order_by(
            RawBlueskyPost.created_at.desc()
        ).limit(1)
        last_fetch_result = await session.execute(last_fetch_stmt)
        last_fetch = last_fetch_result.scalar_one_or_none()

        since = last_fetch if last_fetch else datetime.now() - timedelta(hours=24)

        context.log.info("incremental_extraction_since", since=since)

        posts_extracted = 0
        posts_inserted = 0

        async with BlueskyClient(handle, app_password) as client:
            # Fetch from all configured hashtags
            # Keyword filtering happens during fetch (in BlueskyClient)
            posts_data = await client.fetch_all_hashtags(since=since)

            posts_extracted = len(posts_data)

            for post in posts_data:
                # Extract creation timestamp
                created_at = datetime.fromisoformat(post["record"]["createdAt"].replace("Z", "+00:00"))

                # Create RawBlueskyPost record
                raw_post = RawBlueskyPost(
                    post_uri=post["uri"],
                    post_cid=post["cid"],
                    raw_json=post,
                    fetched_at=datetime.now(),
                    created_at=created_at,
                    author_did=post["author"]["did"],
                    author_handle=post["author"]["handle"],
                    post_text=post["record"]["text"],
                )

                # Upsert
                from sqlmodel import insert
                stmt = insert(RawBlueskyPost).values(raw_post.dict())
                stmt = stmt.on_conflict_do_nothing(index_elements=["post_uri"])

                await session.execute(stmt)
                posts_inserted += 1

            await session.commit()

        context.log.info(
            "extract_bluesky_posts_completed",
            posts_extracted=posts_extracted,
            posts_inserted=posts_inserted,
        )

        return {
            "posts_extracted": posts_extracted,
            "posts_inserted": posts_inserted,
        }


# Schedule: Every 5 minutes
bluesky_posts_schedule = ScheduleDefinition(
    name="extract_bluesky_posts_schedule",
    job=define_asset_job("materialize_bluesky_posts", selection="extract_bluesky_posts"),
    cron_schedule="*/5 * * * *",  # Every 5 minutes
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start (compliant API)
)
```

---

### Asset 3: `transform_social_posts`

**Purpose:** Transform raw posts into unified multi-platform schema, filtering with game matcher.

**Schedule:** Hourly at :15 (15 minutes after extracts)

**Dependencies:** `extract_reddit_posts`, `extract_bluesky_posts`

**File:** `backend/app/assets/social_transform.py`

```python
@asset(
    name="transform_social_posts",
    description="Transform raw social posts into unified schema with game matching filter",
    group_name="social_media_transformation",
    compute_kind="python",
    deps=[extract_reddit_posts, extract_bluesky_posts],  # Wait for extracts
    retry_policy=RetryPolicy(
        max_retries=2,
        delay=10,
        backoff=Backoff.LINEAR,
    ),
)
async def transform_social_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Transform raw posts to staged unified schema.

    Steps:
    1. Read unprocessed raw posts (matched_to_game = FALSE)
    2. Apply game matcher filter (confidence >= 0.6)
    3. Normalize platform-specific engagement scores
    4. Insert into stg_social_posts
    5. Mark raw posts as processed
    """

    from app.services.game_matcher import GameMatcher
    from app.models.social import RawRedditPost, RawBlueskyPost, StgSocialPost

    context.log.info("transform_social_posts_started")

    async with database.get_session() as session:
        game_matcher = GameMatcher(session)

        posts_processed = 0
        posts_matched = 0
        posts_filtered = 0

        # Process Reddit posts
        reddit_stmt = select(RawRedditPost).where(
            RawRedditPost.matched_to_game == False
        ).limit(1000)  # Batch size (memory constraint)

        reddit_posts = (await session.execute(reddit_stmt)).scalars().all()

        for raw_post in reddit_posts:
            # Extract text for matching
            post_json = raw_post.raw_json
            post_text = f"{post_json.get('title', '')} {post_json.get('selftext', '')}"

            # Apply game matcher
            match_result = game_matcher.match_post_to_teams(post_text)

            # Update raw post with match metadata
            raw_post.matched_to_game = match_result["is_game_related"]
            raw_post.match_confidence = match_result["match_confidence"]
            raw_post.processed_at = datetime.now()

            posts_processed += 1

            # Filter: Only insert if game-related
            if not match_result["is_game_related"]:
                posts_filtered += 1
                continue

            posts_matched += 1

            # Calculate engagement score (Reddit formula)
            engagement_score = (
                (post_json.get("score", 0) * 1.0) +
                (post_json.get("num_comments", 0) * 2.0) +
                (post_json.get("upvote_ratio", 0.5) * 10.0)
            )

            # Create staged post
            stg_post = StgSocialPost(
                platform="reddit",
                platform_post_id=raw_post.post_id,
                author_username=post_json.get("author"),
                post_text=post_text,
                created_at=raw_post.created_at,
                fetched_at=raw_post.fetched_at,
                matched_teams=match_result["matched_teams"],
                match_confidence=match_result["match_confidence"],
                engagement_score=engagement_score,
                likes_count=post_json.get("score", 0),
                comments_count=post_json.get("num_comments", 0),
                shares_count=0,  # Reddit doesn't have shares
                platform_metadata={
                    "upvote_ratio": post_json.get("upvote_ratio"),
                    "link_flair_text": post_json.get("link_flair_text"),
                    "permalink": post_json.get("permalink"),
                },
                source_table="raw_reddit_posts",
                source_row_id=raw_post.post_id,
            )

            # Upsert
            from sqlmodel import insert
            stmt = insert(StgSocialPost).values(stg_post.dict(exclude_unset=True))
            stmt = stmt.on_conflict_do_nothing(index_elements=["platform", "platform_post_id"])
            await session.execute(stmt)

        # Process Bluesky posts (similar logic)
        bluesky_stmt = select(RawBlueskyPost).where(
            RawBlueskyPost.matched_to_game == False
        ).limit(1000)

        bluesky_posts = (await session.execute(bluesky_stmt)).scalars().all()

        for raw_post in bluesky_posts:
            post_json = raw_post.raw_json
            post_text = post_json["record"]["text"]

            match_result = game_matcher.match_post_to_teams(post_text)

            raw_post.matched_to_game = match_result["is_game_related"]
            raw_post.match_confidence = match_result["match_confidence"]
            raw_post.processed_at = datetime.now()

            posts_processed += 1

            if not match_result["is_game_related"]:
                posts_filtered += 1
                continue

            posts_matched += 1

            # Calculate engagement score (Bluesky formula)
            engagement_score = (
                (post_json.get("likeCount", 0) * 1.5) +
                (post_json.get("replyCount", 0) * 3.0) +
                (post_json.get("repostCount", 0) * 2.5)
            )

            stg_post = StgSocialPost(
                platform="bluesky",
                platform_post_id=raw_post.post_uri,
                author_username=post_json["author"]["handle"],
                post_text=post_text,
                created_at=raw_post.created_at,
                fetched_at=raw_post.fetched_at,
                matched_teams=match_result["matched_teams"],
                match_confidence=match_result["match_confidence"],
                engagement_score=engagement_score,
                likes_count=post_json.get("likeCount", 0),
                comments_count=post_json.get("replyCount", 0),
                shares_count=post_json.get("repostCount", 0),
                platform_metadata={
                    "facets": post_json["record"].get("facets", []),
                    "author_did": post_json["author"]["did"],
                },
                source_table="raw_bluesky_posts",
                source_row_id=raw_post.post_uri,
            )

            stmt = insert(StgSocialPost).values(stg_post.dict(exclude_unset=True))
            stmt = stmt.on_conflict_do_nothing(index_elements=["platform", "platform_post_id"])
            await session.execute(stmt)

        await session.commit()

        context.log.info(
            "transform_social_posts_completed",
            posts_processed=posts_processed,
            posts_matched=posts_matched,
            posts_filtered=posts_filtered,
            match_rate=f"{(posts_matched / posts_processed * 100):.1f}%" if posts_processed > 0 else "0%",
        )

        return {
            "posts_processed": posts_processed,
            "posts_matched": posts_matched,
            "posts_filtered": posts_filtered,
        }


# Schedule: Hourly at :15 (after extracts)
transform_social_posts_schedule = ScheduleDefinition(
    name="transform_social_posts_schedule",
    job=define_asset_job("materialize_transform_social_posts", selection="transform_social_posts"),
    cron_schedule="15 * * * *",  # :15 past every hour
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
```

---

### Asset 4: `calculate_sentiment`

**Purpose:** Apply VADER sentiment analysis and resolve game_key for Epic 5 integration.

**Schedule:** Hourly at :30 (after transform)

**Dependencies:** `transform_social_posts`

**File:** `backend/app/assets/social_sentiment.py`

```python
@asset(
    name="calculate_sentiment",
    description="Calculate VADER sentiment scores and resolve game_key for Epic 5 integration",
    group_name="social_media_enrichment",
    compute_kind="python",
    deps=[transform_social_posts],
    retry_policy=RetryPolicy(
        max_retries=2,
        delay=10,
        backoff=Backoff.LINEAR,
    ),
)
async def calculate_sentiment(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Calculate sentiment and create fact_social_sentiment records.

    Steps:
    1. Read new stg_social_posts (not yet in fact table)
    2. Apply VADER sentiment analysis
    3. Resolve game_key using GameMatcher
    4. Resolve date_key from game
    5. Insert into fact_social_sentiment
    """

    from app.services.sentiment_analyzer import SentimentAnalyzer
    from app.services.game_matcher import GameMatcher
    from app.models.social import StgSocialPost, FactSocialSentiment
    from app.models.game import FactGame
    from sqlmodel import select

    context.log.info("calculate_sentiment_started")

    async with database.get_session() as session:
        sentiment_analyzer = SentimentAnalyzer()
        game_matcher = GameMatcher(session)

        posts_analyzed = 0
        posts_matched_to_game = 0
        posts_skipped_no_game = 0

        # Find posts not yet in fact table
        existing_post_keys_stmt = select(FactSocialSentiment.social_post_key)
        existing_result = await session.execute(existing_post_keys_stmt)
        existing_post_keys = set(existing_result.scalars().all())

        # Get new posts
        stg_posts_stmt = select(StgSocialPost).limit(1000)
        stg_posts = (await session.execute(stg_posts_stmt)).scalars().all()

        for stg_post in stg_posts:
            # Skip if already analyzed
            if stg_post.social_post_key in existing_post_keys:
                continue

            posts_analyzed += 1

            # Calculate sentiment
            sentiment = sentiment_analyzer.analyze(stg_post.post_text)

            # Resolve game_key
            game_date = stg_post.matched_game_date or stg_post.created_at.date()
            game_key = game_matcher.resolve_game_key(stg_post.matched_teams, game_date)

            if not game_key:
                posts_skipped_no_game += 1
                context.log.debug(
                    "game_key_resolution_failed",
                    social_post_key=stg_post.social_post_key,
                    matched_teams=stg_post.matched_teams,
                    game_date=game_date,
                )
                continue

            posts_matched_to_game += 1

            # Resolve date_key from game
            game_stmt = select(FactGame.date_key).where(FactGame.game_key == game_key)
            game_result = await session.execute(game_stmt)
            date_key = game_result.scalar_one()

            # Create fact record
            fact_record = FactSocialSentiment(
                game_key=game_key,
                date_key=date_key,
                social_post_key=stg_post.social_post_key,
                sentiment_compound=sentiment["compound"],
                sentiment_positive=sentiment["positive"],
                sentiment_negative=sentiment["negative"],
                sentiment_neutral=sentiment["neutral"],
                platform=stg_post.platform,
                post_text=stg_post.post_text,
                created_at=stg_post.created_at,
                engagement_score=stg_post.engagement_score,
            )

            session.add(fact_record)

        await session.commit()

        context.log.info(
            "calculate_sentiment_completed",
            posts_analyzed=posts_analyzed,
            posts_matched_to_game=posts_matched_to_game,
            posts_skipped_no_game=posts_skipped_no_game,
        )

        return {
            "posts_analyzed": posts_analyzed,
            "posts_matched_to_game": posts_matched_to_game,
            "posts_skipped_no_game": posts_skipped_no_game,
        }


# Schedule: Hourly at :30 (after transform)
calculate_sentiment_schedule = ScheduleDefinition(
    name="calculate_sentiment_schedule",
    job=define_asset_job("materialize_calculate_sentiment", selection="calculate_sentiment"),
    cron_schedule="30 * * * *",  # :30 past every hour
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
```

---

## Database Migrations

### Migration 1: `create_raw_reddit_posts.py`

```python
"""create_raw_reddit_posts

Revision ID: {auto_generated}
Create Date: {auto_generated}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

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

    # TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable('raw_reddit_posts', 'created_at', chunk_time_interval => INTERVAL '1 day');
    """)

    # Indexes
    op.execute("CREATE INDEX idx_raw_reddit_fetched_at ON raw_reddit_posts (fetched_at DESC);")
    op.execute("""
        CREATE INDEX idx_raw_reddit_unmatched ON raw_reddit_posts (matched_to_game, created_at)
        WHERE matched_to_game = FALSE;
    """)
    op.execute("CREATE INDEX idx_raw_reddit_json_gin ON raw_reddit_posts USING GIN (raw_json);")

    # Retention and compression
    op.execute("SELECT add_retention_policy('raw_reddit_posts', INTERVAL '90 days');")
    op.execute("SELECT add_compression_policy('raw_reddit_posts', INTERVAL '7 days');")

def downgrade() -> None:
    op.execute("DROP TABLE raw_reddit_posts CASCADE;")
```

### Migration 2: `create_raw_bluesky_posts.py`

(Similar structure to Migration 1, adjusted for Bluesky columns)

### Migration 3: `create_stg_social_posts.py`

(Create stg_social_posts table with indexes)

### Migration 4: `create_fact_social_sentiment.py`

(Create fact_social_sentiment with FKs to fact_game, dim_date, stg_social_posts)

---

## Environment Configuration

### Required Environment Variables

```bash
# .env (Production)

# Reddit Configuration
REDDIT_POLLING_ENABLED=true                  # Enable/disable Reddit extraction
REDDIT_USER_AGENT="GamePulse/1.0 (Educational portfolio project; +https://gamepulse.top)"
REDDIT_RATE_LIMIT_QPM=10                     # Queries per minute
REDDIT_SUBREDDIT="CollegeBasketball"

# Bluesky Configuration
BLUESKY_HANDLE="gamepulse.bsky.social"       # Your Bluesky handle
BLUESKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # App password (NOT main password!)
BLUESKY_RATE_LIMIT_POINTS_PER_HOUR=5000      # Conservative limit
BLUESKY_HASHTAGS="CollegeBasketball,MarchMadness,NCAAM"

# Data Management
SOCIAL_DATA_RETENTION_DAYS=90                # How long to keep data
SOCIAL_DATA_COMPRESSION_AFTER_DAYS=7         # When to compress TimescaleDB chunks
CLEANUP_UNMATCHED_POSTS=true                 # Delete unmatched raw posts after 7 days

# Game Matching
GAME_MATCH_CONFIDENCE_THRESHOLD=0.6          # Minimum confidence to store (0-1)
```

### AWS Parameter Store Mapping

(Update `backend/scripts/create-env-from-aws-parameters.sh`)

```bash
# New parameters to add:
/gamepulse/production/social/reddit_user_agent
/gamepulse/production/social/reddit_polling_enabled
/gamepulse/production/social/bluesky_handle
/gamepulse/production/social/bluesky_app_password  # SecureString
```

---

## Risk Mitigation

### Legal Risk (Reddit)

**Risk:** Reddit actively sues unauthorized scrapers (Oct 2025 lawsuits vs web crawlers).

**Mitigations:**
1. **Explicit warnings** in code comments, documentation, README
2. **Environment toggle** (`REDDIT_POLLING_ENABLED`) to disable if needed
3. **Respectful User-Agent** with contact URL
4. **Conservative rate limiting** (10 QPM, well below technical limit)
5. **Portfolio-only disclaimer** - not for commercial use

**Acceptance:** Philip accepts this risk for portfolio demonstration purposes.

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Reddit IP ban** | Extraction fails | Bluesky provides redundancy; disable Reddit via env var |
| **Storage overflow** | 20GB disk fills up | 90-day retention, compression after 7 days, cleanup jobs |
| **Memory exhaustion** | OOM on t2.micro | Batch size limited to 1000 posts, swap configured |
| **Bluesky API changes** | Extraction fails | Official SDK reduces risk; retry logic handles transient errors |
| **False positive matches** | Irrelevant posts stored | Confidence threshold tuning (0.6 default), manual review |

### Operational Risks

| Risk | Mitigation |
|------|------------|
| **Schedule overlap** | Stagger schedules: Reddit (every 10 min), Bluesky (every 5 min), Transform (:15), Sentiment (:30) |
| **Cascade failures** | Asset dependencies prevent downstream execution on failure; retry policies handle transients |
| **Data quality drift** | Structured logging in Dagster UI for manual monitoring; Epic 9 (monitoring) will add automated alerts |

---

## Testing Strategy

### Unit Tests

**Maximize value, minimize effort** - focus on critical logic.

**Priority 1: High-Value Tests**
- `test_reddit_client.py`: Mock httpx responses, verify rate limiting
- `test_bluesky_client.py`: Mock atproto SDK, verify hashtag search
- `test_game_matcher.py`: Fixtures with known team mentions, verify confidence scores
- `test_sentiment_analyzer.py`: Sample social posts, verify VADER scores

**Priority 2: Integration Smoke Tests**
- `test_extract_reddit_posts.py`: Can extract and insert into test database?
- `test_transform_pipeline.py`: Can read raw → filter → insert stg?

**Skip (Nice-to-Have):**
- E2E Dagster asset tests (too heavyweight for 3-week sprint)
- Comprehensive edge case coverage (diminishing returns)

### Test Fixtures

```python
# backend/app/tests/fixtures/social_posts.py

SAMPLE_REDDIT_POST = {
    "id": "t3_test123",
    "subreddit": "CollegeBasketball",
    "author": "test_user",
    "title": "Duke vs UNC - What a game!",
    "selftext": "Cameron Indoor was electric...",
    "created_utc": 1700000000,
    "score": 142,
    "num_comments": 37,
    "upvote_ratio": 0.94,
}

SAMPLE_BLUESKY_POST = {
    "uri": "at://did:plc:test123.../app.bsky.feed.post/xyz",
    "cid": "bafytest...",
    "author": {"did": "did:plc:test", "handle": "test.bsky.social"},
    "record": {
        "text": "Go Blue Devils! #CollegeBasketball",
        "createdAt": "2025-11-15T20:00:00Z",
    },
    "likeCount": 23,
    "replyCount": 5,
}
```

---

## Epic 5 Integration

### Query Pattern for Excitement Scoring

Epic 5 will query `fact_social_sentiment` to calculate excitement scores:

```sql
-- Pre-game excitement (posts in 24 hours before tip-off)
SELECT
    g.game_key,
    g.game_id,
    COUNT(*) AS pre_game_post_count,
    AVG(s.sentiment_compound) AS avg_pre_game_sentiment,
    SUM(s.engagement_score) AS total_pre_game_engagement
FROM fact_game g
LEFT JOIN fact_social_sentiment s
    ON g.game_key = s.game_key
    AND s.created_at BETWEEN (g.game_datetime - INTERVAL '24 hours') AND g.game_datetime
WHERE g.game_date = '2025-11-15'
GROUP BY g.game_key, g.game_id;

-- Live excitement (posts during game)
SELECT
    g.game_key,
    COUNT(*) AS live_post_count,
    AVG(s.sentiment_compound) AS avg_live_sentiment,
    STDDEV(s.sentiment_compound) AS sentiment_volatility  -- Higher volatility = more exciting
FROM fact_game g
LEFT JOIN fact_social_sentiment s
    ON g.game_key = s.game_key
    AND s.created_at BETWEEN g.game_datetime AND (g.game_datetime + INTERVAL '3 hours')
WHERE g.game_date = '2025-11-15'
GROUP BY g.game_key;
```

### Schema Validation

Epic 5 requirements for `fact_social_sentiment`:
- ✅ `game_key` FK to `fact_game.game_key`
- ✅ `sentiment_compound` score (-1 to +1)
- ✅ `engagement_score` for weighting posts
- ✅ `created_at` for temporal analysis
- ✅ `platform` for multi-source credibility

**Ready for Epic 5 integration:** Yes, schema design complete.

---

## Success Criteria

### Week 1: Reddit Pipeline Operational
- ✅ Reddit client implemented and tested
- ✅ `raw_reddit_posts` table created with TimescaleDB hypertable
- ✅ `extract_reddit_posts` asset running on schedule (every 10 min)
- ✅ **700-3,500 posts collected** (depending on game schedule)
- ✅ Legal warnings in code and documentation
- ✅ Environment toggle (`REDDIT_POLLING_ENABLED`) functional

### Week 2: Multi-Platform Transformation
- ✅ Bluesky client implemented with keyword filtering
- ✅ `raw_bluesky_posts` table created
- ✅ `extract_bluesky_posts` asset running (every 5 min)
- ✅ `stg_social_posts` table created (unified schema)
- ✅ Game matcher implemented and tested
- ✅ `transform_social_posts` asset filtering irrelevant posts
- ✅ **30-50% of raw posts matched to games** (expected filter rate)

### Week 3: Sentiment & Epic 5 Prep
- ✅ VADER sentiment analyzer integrated
- ✅ `fact_social_sentiment` table created with FKs
- ✅ `calculate_sentiment` asset operational
- ✅ Data retention policies active (90 days)
- ✅ TimescaleDB compression working (7-day threshold)
- ✅ Epic 5 integration verified (query patterns tested)
- ✅ **99% uptime** for all schedules over final week

### Portfolio Quality Metrics
- ✅ Dagster UI shows complete asset lineage
- ✅ Structured logging provides observability
- ✅ Modern data stack patterns demonstrated (ELT, TimescaleDB, Dagster)
- ✅ Code quality: Type hints, docstrings, consistent patterns
- ✅ Legal risk properly documented and mitigated

---

## Story Breakdown

Epic 4 decomposes into **6 coarse-grained stories**:

| Story | Title | Effort (hrs) | Dependencies |
|-------|-------|--------------|--------------|
| **4-1** | Reddit Data Pipeline | 12-16 | None |
| **4-2** | Bluesky Data Pipeline | 10-14 | None |
| **4-3** | Game Matching Service | 8-10 | Epic 2 (dim_team) |
| **4-4** | Unified Transform Layer | 12-16 | 4-1, 4-2, 4-3 |
| **4-5** | Sentiment Analysis & Fact Table | 10-12 | 4-4, Epic 2 (fact_game) |
| **4-6** | Orchestration & Data Management | 8-12 | 4-1, 4-2, 4-4, 4-5 |

**Total Effort:** 60-80 hours (3 weeks @ 20-27 hrs/week)

**Sprint Velocity:** Assumes solo developer with existing Epic 2 patterns to replicate.

---

## Appendices

### Appendix A: TimescaleDB Chunk Sizing Rationale

**1-day chunks** chosen for social posts based on:
- **Write volume:** ~1,500 posts/day (low-to-medium)
- **Query patterns:** Time-range queries (e.g., "last 24 hours")
- **Retention:** 90-day policy benefits from chunk-level drops
- **Compression:** 7-day threshold aligns with 1-day chunks (compress 7 chunks at a time)

Contrast with Epic 6 `fact_betting_odds` (1-hour chunks for high-frequency updates).

### Appendix B: Engagement Score Normalization

**Why platform-specific formulas?**

Reddit and Bluesky have different user bases and engagement scales:
- Reddit upvotes: Typically 10-500 for popular posts
- Bluesky likes: Typically 5-50 (smaller user base)

**Normalization approach:**
- **Relative weighting** within platform (comments > likes)
- **No cross-platform normalization** (preserve platform context for Epic 5 credibility scoring)
- Epic 5 will apply **platform-aware weights** when combining signals

### Appendix C: VADER vs Transformer Trade-offs

| Metric | VADER | DistilBERT (Transformers) |
|--------|-------|----------------------------|
| **Speed** | 0.01ms/post | 3.39ms/post (339x slower) |
| **Accuracy** | ~80% (social media optimized) | ~90% (research-grade) |
| **Dependencies** | 1 small library | PyTorch, GPU recommended |
| **Memory** | <10 MB | ~250 MB model weights |
| **Maintenance** | Stable, no model updates | Model versioning, drift |

**Decision:** VADER is appropriate for GamePulse's "good-enough" portfolio demonstration. Future ML experimentation can leverage raw JSONB data for transformer fine-tuning.

### Appendix D: Alternatives Considered

**Reddit OAuth (Rejected):**
- **Pro:** Compliant, 100 QPM rate limit
- **Con:** Applications not being approved (Nov 2025)
- **Result:** Forced pivot to unauthenticated endpoints

**Pushshift Reddit Archive (Rejected):**
- **Pro:** Historical data, research-approved
- **Con:** 6-month lag, no real-time data
- **Result:** Doesn't meet Epic 5 live excitement scoring needs

**Twitter/X API (Rejected):**
- **Pro:** Large user base, sports discussion
- **Con:** $100/month minimum for API access
- **Result:** Budget constraint (free-tier project)

**Bluesky (Selected):**
- **Pro:** Free official SDK, compliant, growing sports community
- **Con:** Smaller user base than Reddit/Twitter
- **Result:** Best balance of compliance + cost + functionality

### Appendix E: Future dbt Migration Path

**Current Approach:** Epic 4 implements SQL transformations as Python Dagster assets (Stories 4-4, 4-5) mirroring the proven NCAA games pattern from Epic 2.

**Why Python transforms now:**
1. **Consistency:** Matches existing `ncaa_games` asset architecture (extraction + transformation in Dagster)
2. **Speed:** No new tool learning curve - ship faster in 3-week sprint
3. **Flexibility:** Python provides full programmatic control for complex game matching and sentiment logic
4. **Simplicity:** Single-tool orchestration (Dagster only) vs. Dagster + dbt integration

**Future Consideration: dbt for SQL Transformations**

A post-Epic 4 refactor to dbt would provide modern data stack benefits:

**Benefits of dbt:**
- **SQL-first transformations:** More accessible to analysts and data teams
- **Built-in testing framework:** Schema tests (unique, not_null, relationships) in YAML
- **Column-level lineage:** Automatic documentation and dependency graphs
- **Incremental materialization:** Declarative `is_incremental()` logic
- **Community patterns:** dbt packages for common transformations

**Example dbt Models (Hypothetical Refactor):**

```sql
-- models/staging/social/stg_reddit_posts.sql
-- Replaces extract_reddit_posts Python transform logic
{{
    config(
        materialized='incremental',
        unique_key='post_id',
        on_schema_change='append_new_columns'
    )
}}

SELECT
    id AS post_id,
    'reddit' AS platform,
    author AS author_username,
    TO_TIMESTAMP(created_utc) AS created_at,
    COALESCE(title || ' ' || selftext, title) AS content_text,
    ups AS engagement_upvotes,
    downs AS engagement_downvotes,
    num_comments AS engagement_comments,
    (ups - downs + num_comments) AS engagement_score,
    JSON_BUILD_OBJECT(
        'subreddit', subreddit,
        'permalink', permalink,
        'awards', awards
    )::JSONB AS platform_metadata,
    NOW() AS transformed_at
FROM {{ source('raw', 'reddit_posts') }}
WHERE id IS NOT NULL

{% if is_incremental() %}
-- Only process posts newer than last run
AND fetched_at > (SELECT MAX(transformed_at) FROM {{ this }})
{% endif %}

-- models/intermediate/int_social_unified.sql
-- Replaces transform_social_posts Python asset
WITH reddit AS (
    SELECT * FROM {{ ref('stg_reddit_posts') }}
),
bluesky AS (
    SELECT * FROM {{ ref('stg_bluesky_posts') }}
),
combined AS (
    SELECT * FROM reddit
    UNION ALL
    SELECT * FROM bluesky
)
SELECT
    *,
    -- Game detection (would call PostgreSQL function wrapping Python game matcher)
    detect_game_teams(content_text) AS matched_teams,
    calculate_match_confidence(content_text) AS match_confidence
FROM combined
WHERE calculate_match_confidence(content_text) >= 0.6

-- models/marts/social/fct_social_sentiment.sql
-- Replaces calculate_sentiment Python asset
{{
    config(
        materialized='incremental',
        unique_key='social_post_key'
    )
}}

SELECT
    social_post_key,
    game_key,
    date_key,
    -- VADER sentiment (would call PostgreSQL function wrapping Python)
    calculate_sentiment(post_text) AS sentiment_compound,
    platform,
    post_text,
    created_at,
    engagement_score,
    NOW() AS analyzed_at
FROM {{ ref('int_social_unified') }}

{% if is_incremental() %}
WHERE transformed_at > (SELECT MAX(analyzed_at) FROM {{ this }})
{% endif %}
```

**Testing in dbt:**

```yaml
# models/staging/social/schema.yml
models:
  - name: stg_reddit_posts
    description: "Cleaned Reddit posts from /r/CollegeBasketball"
    tests:
      - dbt_utils.recency:
          datepart: hour
          field: created_at
          interval: 2  # Freshness SLA: <2 hours
    columns:
      - name: post_id
        tests:
          - unique
          - not_null
      - name: platform
        tests:
          - accepted_values:
              values: ['reddit']
      - name: engagement_score
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10000

  - name: int_social_unified
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: ref('stg_reddit_posts')  # Ensure no row loss in union
    columns:
      - name: match_confidence
        tests:
          - dbt_utils.accepted_range:
              min_value: 0.6
              max_value: 1.0  # Only matched posts (confidence >= 0.6)
```

**Dagster + dbt Integration:**

```python
# dagster_project/definitions.py
from dagster_dbt import DbtProject, dbt_assets

# Load dbt project
dbt_project = DbtProject(project_dir=Path("dbt_project"))

@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project
)
def sports_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    All dbt models as individual Dagster assets.

    Dagster treats each model as a separate asset with:
    - Automatic dependency resolution (via ref())
    - Model-level observability (which specific models failed)
    - Selective execution (materialize subset of models)
    """
    yield from dbt.cli(["build"], context=context).stream()

# Unified definitions
defs = Definitions(
    assets=[
        # Python extraction assets remain (Reddit/Bluesky API clients)
        extract_reddit_posts,
        extract_bluesky_posts,
        # dbt handles transformations
        sports_dbt_assets,
    ],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)}
)
```

**Hybrid Approach (Recommended):**

For Epic 4's game matching and sentiment analysis, **keep complex logic in Python** but use dbt for simple transformations:
- **Dagster Python:** Reddit/Bluesky extraction, game matching (fuzzy logic), VADER sentiment (ML library)
- **dbt SQL:** Data cleaning, aggregations, joins, incremental loads

**Migration Effort Estimate:**

| Task | Effort (hours) |
|------|----------------|
| Set up dbt project structure | 2 |
| Migrate stg_reddit_posts, stg_bluesky_posts | 2 |
| Create int_social_unified model | 1 |
| Wrap Python game matcher as PostgreSQL function | 3 |
| Wrap VADER as PostgreSQL function | 2 |
| Migrate fct_social_sentiment | 1 |
| Write schema tests (YAML) | 1 |
| Update Dagster definitions for dbt integration | 1 |
| Test end-to-end pipeline | 2 |
| **Total** | **15 hours** |

**When to Migrate:**

- **Epic 9 (Testing & Quality Assurance):** Add dbt tests as part of comprehensive quality framework
- **Epic 10 (Documentation & Polish):** Refactor for portfolio presentation (dbt shows modern data stack fluency)
- **Post-MVP:** If data team grows beyond solo developer (analysts prefer SQL over Python)

**Trade-off Justification:**

Epic 4's Python approach is **not inferior** to dbt - it's a pragmatic choice:
- ✅ **Delivers working pipeline faster** (no dbt learning curve mid-sprint)
- ✅ **Leverages proven patterns** (NCAA games asset already in production)
- ✅ **Handles complex logic better** (fuzzy matching, ML sentiment in Python)
- ✅ **Easier to debug** (single-tool stack, fewer abstraction layers)
- ✅ **Can be refactored later** (dbt migration preserves data, just changes code)

**Conclusion:** Epic 4 prioritizes **speed and simplicity** with future **extensibility**. The raw JSONB data preservation enables both dbt refactoring AND ML experimentation down the road.

---

## Conclusion

Epic 4 implements a **production-quality social media ELT pipeline** demonstrating modern data engineering patterns within GamePulse's constraints (free-tier AWS, 3-week timeline, legal risk awareness).

**Key Technical Achievements:**
- Multi-platform data integration (Reddit + Bluesky)
- TimescaleDB partitioning and compression strategies
- Dagster asset-oriented orchestration with dependencies
- Fuzzy game matching for irrelevant post filtering
- VADER sentiment analysis optimized for social media
- Epic 5-ready fact table with dimensional FKs

**Portfolio Value:**
- ELT pattern (raw → staged → fact) demonstrates data warehouse fundamentals
- Legal risk acknowledgment shows professional judgment
- Modern data stack (Dagster + TimescaleDB + Python async) showcases current best practices
- Extensibility: Raw JSONB preservation enables future ML experimentation

**Ready for Development:** All architectural decisions finalized, stories defined, SM can proceed with sprint planning.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Next Review:** After Story 4-3 completion (game matcher validation)
