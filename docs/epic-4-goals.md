# Epic 4: Social Media ELT Pipeline - Goals & Requirements

**Epic ID:** Epic 4 (Revised)
**Epic Name:** Social Media Data Ingestion via ELT Pattern
**Owner:** Business Analyst (Mary)
**Date Created:** 2025-11-15
**Status:** Goals Defined - Ready for Architectural Design

---

## Executive Summary

Epic 4 establishes a multi-platform social media data ingestion pipeline using an Extract-Load-Transform (ELT) pattern in Dagster. Unlike the previous Reddit-only batch sentiment approach, this architecture preserves complete raw data from both Reddit and Bluesky in JSONB storage, enabling future ML training while continuing to support Epic 5 excitement scoring requirements.

**Key Strategic Shift:** From targeted sentiment analysis to comprehensive data lake for ML readiness.

---

## Problem Statement

### Business Need

GamePulse requires social sentiment data to calculate game excitement scores (Epic 5 dependency). The original Epic 4 design assumed Reddit OAuth API access for targeted sentiment analysis. However, this approach has three critical limitations:

1. **Single Platform Risk:** Dependency on Reddit's API availability and ToS compliance
2. **Limited Future Value:** Filtered data extraction prevents future ML feature engineering
3. **Missed Opportunities:** Bluesky's rapid growth (10M → 28M users in 3 months) represents untapped signal

### Technical Challenge

**Reddit API Constraints:**
- Official Reddit API OAuth applications not being approved (access blocked)
- Alternative: Use Reddit JSON endpoints (`.json` suffix) without authentication
- **CRITICAL RISK:** Reddit actively litigating against unauthorized scrapers (Oct 2025 lawsuits against SerpApi, Oxylabs, Perplexity AI)
- Unauthenticated access limited to 10 QPM (10 requests per minute - extremely restrictive)
- Terms of Service prohibit automated access without OAuth - **legal exposure exists**
- **Portfolio Context:** Acceptable risk for demo/interview project, NOT recommended for production deployment

**Data Architecture Gap:**
- Current approach (immediate transformation) loses raw API responses
- Schema changes in Reddit/Bluesky APIs would require re-ingestion of historical data
- No mechanism to extract new features from historical posts for ML training

### User Impact

Without social sentiment data:
- Excitement scores (Epic 5) lack real-time community engagement signal
- GamePulse offers only objective stats (scores, rebounds) without subjective "buzz" metric
- Portfolio project misses opportunity to demonstrate ML engineering capabilities

---

## Solution Overview

### ELT Data Pipeline Architecture

**Extract → Load → Transform** pattern implemented in Dagster with daily partitions:

```
┌─────────────────────────────────────────────────────────────┐
│ EXTRACT LAYER (Dagster Assets)                              │
├─────────────────────────────────────────────────────────────┤
│ extract_reddit_posts     → Reddit JSON endpoint (httpx)     │
│   • Polling: Every 6-10 minutes (10 QPM unauthenticated)    │
│   • Endpoint: https://reddit.com/r/CollegeBasketball.json   │
│   • User-Agent: GamePulse/1.0 (contact info)                │
│   • Capture: Complete post object (~40+ fields)             │
│   • ⚠️ RISK: No OAuth = ToS violation, potential IP ban     │
│                                                              │
│ extract_bluesky_posts    → Raw Bluesky JSON (atproto SDK)   │
│   • Polling: Every 5 minutes (5000 points/hour limit)       │
│   • Target: #CollegeBasketball, #MarchMadness, #NCAAM       │
│   • Capture: Complete post view (~20+ fields)               │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│ LOAD LAYER (TimescaleDB Raw Tables)                         │
├─────────────────────────────────────────────────────────────┤
│ raw_reddit_posts (JSONB)                                    │
│   • post_id, fetched_at, partition_date, raw_json           │
│   • Hypertable: 1-day chunks, GIN index on JSONB            │
│   • Retention: 90 days compressed                           │
│                                                              │
│ raw_bluesky_posts (JSONB)                                   │
│   • post_uri, fetched_at, partition_date, raw_json          │
│   • Hypertable: 1-day chunks, GIN index on JSONB            │
│   • Retention: 90 days compressed                           │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│ TRANSFORM LAYER (Staged + Fact Tables)                      │
├─────────────────────────────────────────────────────────────┤
│ stg_social_posts (Unified Schema)                           │
│   • Common fields: post_text, author, created_at            │
│   • Unified engagement_score (platform-aware formula)       │
│   • source_specific_json (JSONB for platform extras)        │
│   • Transform runs: Hourly (fresh data within 1 hour)       │
│                                                              │
│ fact_social_sentiment (Epic 5 Integration)                  │
│   • Game matching (fuzzy team name algorithm)               │
│   • VADER sentiment analysis (compound score)               │
│   • Engagement metrics for excitement scoring               │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Complete Data Preservation:** Store entire API responses in JSONB before transformation
2. **Platform Agnostic:** Unified schema supports Reddit + Bluesky + future sources
3. **ML Training Ready:** Raw data available for feature engineering without re-ingestion
4. **Incremental Processing:** Daily partitions enable efficient backfills and parallel execution
5. **Observability:** Dagster asset lineage provides clear data flow visibility

---

## Constraints

### Technical Constraints

| Constraint | Description | Impact |
|------------|-------------|--------|
| **TC-1: No Reddit OAuth** | Reddit OAuth applications not being approved. MUST use unauthenticated JSON endpoints. | Severe rate limiting (10 QPM), legal risk, potential IP ban. Portfolio/demo context only. |
| **TC-2: Rate Limits** | Reddit: 10 QPM (unauthenticated), Bluesky: 5000 points/hour | Polling cadence: Reddit 6-10 min, Bluesky 5 min. Conservative usage to avoid ban. |
| **TC-3: Storage Budget** | t2.micro EC2 has 20GB storage (shared with app/dagster DBs) | Raw JSONB: ~4.5GB for 90 days. Requires compression after 7 days. |
| **TC-4: Memory Budget** | t2.micro has 1GB RAM + 4GB swap | Batch size limited to 1000 posts/request. Async processing to avoid memory spikes. |
| **TC-5: Legal Risk** | Reddit ToS prohibits automated access without OAuth. Reddit actively suing scrapers (2025). | **HIGH LEGAL RISK** - Acceptable for portfolio/demo only. Use respectful user-agent, conservative rate limiting. Bluesky uses official SDK (compliant). |

### Business Constraints

| Constraint | Description | Impact |
|------------|-------------|--------|
| **BC-1: Timeline** | Epic 4 must complete within 3 weeks for interview demos | Prioritize MVP (Reddit only Week 1, add Bluesky Week 2). |
| **BC-2: Cost** | Operate within $10/month AWS budget | Use free API tiers. No paid sentiment analysis services. |
| **BC-3: Maintenance** | Solo developer (no 24/7 on-call) | Dagster retry policies, graceful degradation on API failures. |

---

## Requirements

### Functional Requirements

#### FR-1: Multi-Platform Data Extraction
- **FR-1.1:** Extract posts from r/CollegeBasketball subreddit via Reddit JSON endpoint (unauthenticated)
  - Endpoint: `https://www.reddit.com/r/CollegeBasketball/new.json?limit=100`
  - User-Agent: `GamePulse/1.0 (NCAA basketball analytics; contact@gamepulse.top)`
  - Rate limit: 10 QPM maximum (poll every 6-10 minutes conservatively)
- **FR-1.2:** Extract posts with basketball hashtags (#CollegeBasketball, #MarchMadness, #NCAAM) via Bluesky atproto SDK
- **FR-1.3:** Support daily partitions for historical backfill capability
- **FR-1.4:** Capture complete API responses (all fields) without filtering

**Acceptance Criteria:**
- Reddit: Fetch 100-500 posts/day from r/CollegeBasketball (rate limit constrained)
- Bluesky: Fetch 500+ posts/day from basketball hashtags
- Extract assets materialize successfully for historical partitions (7+ days)
- No IP bans or rate limit errors over 7-day monitoring period

#### FR-2: Raw Data Persistence
- **FR-2.1:** Store complete Reddit post JSON in `raw_reddit_posts.raw_json` JSONB column
- **FR-2.2:** Store complete Bluesky post JSON in `raw_bluesky_posts.raw_json` JSONB column
- **FR-2.3:** Deduplicate posts using `ON CONFLICT DO NOTHING` (idempotent loads)
- **FR-2.4:** Partition raw tables as TimescaleDB hypertables (1-day chunks)

**Acceptance Criteria:**
- Raw tables contain 3,500-7,000 posts after 1 week of operation (500-1000/day combined)
- JSONB queries execute in <100ms with GIN indexes
- Duplicate posts do not create errors (idempotency verified)

#### FR-3: Unified Schema Transformation
- **FR-3.1:** Transform Reddit posts to `stg_social_posts` with common fields (post_text, author, created_at, engagement_score)
- **FR-3.2:** Transform Bluesky posts to `stg_social_posts` with same common fields
- **FR-3.3:** Calculate unified `engagement_score` using platform-aware formulas:
  - Reddit: `score + (num_comments * 0.5) + (total_awards_received * 2)`
  - Bluesky: `likeCount + (replyCount * 0.5) + (repostCount * 1.5) + (quoteCount * 1.5)`
- **FR-3.4:** Store platform-specific extras in `source_specific_json` JSONB:
  - Reddit: link_flair_text, upvote_ratio, stickied, distinguished
  - Bluesky: facets (mentions/hashtags), embed type, reply context

**Acceptance Criteria:**
- `stg_social_posts` contains both Reddit and Bluesky posts with `source_platform` column
- Engagement scores normalized for cross-platform comparison
- Platform-specific fields queryable via `source_specific_json->>'field_name'`

#### FR-4: Epic 5 Integration (Sentiment & Matching)
- **FR-4.1:** Match posts to games using fuzzy team name algorithm (reuse from old Epic 4)
- **FR-4.2:** Calculate sentiment scores using VADER (compound score -1 to +1)
- **FR-4.3:** Populate `fact_social_sentiment` table with:
  - game_key (foreign key to fact_game)
  - sentiment_score, sentiment_category
  - matched_teams[], match_confidence
  - source_platform
- **FR-4.4:** Enable Epic 5 queries for excitement scoring

**Acceptance Criteria:**
- 70%+ of game-related posts successfully matched to games (match_confidence >= 0.6)
- Sentiment scores correlate with manual spot-checks (positive for wins, negative for losses)
- Epic 5 excitement score formula integrates Reddit + Bluesky signals

#### FR-5: Orchestration & Scheduling
- **FR-5.1:** Reddit extract schedule: every 10 minutes (`*/10 * * * *`)
- **FR-5.2:** Bluesky extract schedule: every 5 minutes (`*/5 * * * *`)
- **FR-5.3:** Transform schedule: hourly at :15 (`15 * * * *`)
- **FR-5.4:** Dagster sensors detect failures and alert via logs

**Acceptance Criteria:**
- Assets materialize automatically per schedule
- 99%+ success rate over 7-day monitoring period
- Failed runs retry 3x with exponential backoff before alerting

### Non-Functional Requirements

#### NFR-1: Risk Mitigation & Respectful Usage
- **Reddit:** Use JSON endpoints with respectful practices (NOT official API - OAuth unavailable)
  - Clear User-Agent with project name and contact info
  - Conservative rate limiting (<80% of 10 QPM limit = poll every 6+ minutes)
  - Monitor for rate limit errors and back off immediately
  - **Accept legal risk** - Portfolio/demo context only, not production
- **Bluesky:** Use official atproto SDK (fully compliant)
- **IP Ban Prevention:** Exponential backoff on errors, logging of all rate limit headers

**Acceptance Criteria:**
- User-Agent header includes: "GamePulse/1.0 (NCAA basketball analytics; contact@gamepulse.top)"
- Reddit polling frequency never exceeds 10 requests/minute (conservative 6-10 min intervals)
- Zero IP bans over 14-day monitoring period
- Rate limit headers logged for every Reddit request
- **Disclaimer:** Document in README that Reddit integration is demo-only, not production-ready

#### NFR-2: Data Quality
- Post deduplication prevents duplicate analysis
- Missing/null fields handled gracefully (COALESCE defaults)
- JSONB schema validation on load (reject malformed JSON)

**Acceptance Criteria:**
- Zero duplicate post_id/post_uri in raw tables
- Transform asset handles missing fields without crashes
- Data quality metrics logged per partition (null counts, avg completeness)

#### NFR-3: Performance
- Extract assets complete within 5 minutes per partition
- Load assets commit batches within 2 minutes
- Transform assets process 10K posts in <10 minutes
- JSONB queries return in <100ms (GIN indexes)

**Acceptance Criteria:**
- Dagster UI shows <10 min total runtime for extract → load → transform
- Database query performance tested with 100K+ post dataset
- No memory OOM errors on t2.micro (1GB RAM + 4GB swap)

#### NFR-4: Observability
- Dagster metadata logs: post counts, avg engagement, execution time
- Structured logging (structlog) for API calls and errors
- Asset lineage visible in Dagster UI

**Acceptance Criteria:**
- Every asset logs metadata visible in Dagster UI
- API errors logged with request/response details
- Asset dependency graph displays Extract → Load → Transform flow

#### NFR-5: Maintainability
- Use official SDKs (PRAW, atproto) - no custom API clients
- SQL transformations (not Python) for data normalization
- Retry policies handle transient failures automatically

**Acceptance Criteria:**
- Code uses PRAW 7.9+ and atproto 0.0.63+ SDKs
- Transform logic implemented as SQL (not Pandas/Python)
- Retry policies tested with mock API failures

---

## Success Criteria

### Minimum Viable Product (MVP)

**Week 1 Complete:**
- ✅ Reddit JSON endpoint client operational (10 QPM unauthenticated, cautious polling)
- ✅ `raw_reddit_posts` table contains 700-3,500 posts (100-500/day × 7 days, rate limited)
- ✅ Extract + Load assets materialize successfully for daily partitions
- ✅ Zero IP bans or rate limit violations

**Week 2 Complete:**
- ✅ `stg_social_posts` table contains unified Reddit + Bluesky posts
- ✅ Transform asset calculates engagement_score correctly (platform-aware)
- ✅ Bluesky integration adds 3,500+ posts (500/day × 7 days)

**Week 3 Complete (Epic 4 Done):**
- ✅ `fact_social_sentiment` table populated with matched posts + sentiment scores
- ✅ Epic 5 excitement scoring query executes successfully
- ✅ Dagster schedules running 99%+ uptime over 7 days

### Portfolio Quality Gates

**Data Quality:**
- 4,000-7,000 posts/week from both platforms combined (rate limit constrained)
- <5% failed API requests (retry policy handles transient errors)
- 70%+ game matching success rate (confidence >= 0.6)
- Bluesky provides majority of volume (Reddit constrained to 10 QPM)

**System Reliability:**
- 99%+ scheduled materialization success rate
- <1 hour latency from post creation to fact table availability
- Zero OOM crashes on t2.micro over 7-day stress test

**Code Quality:**
- httpx for Reddit JSON endpoints (simple HTTP client, no OAuth complexity)
- atproto SDK for Bluesky (official, compliant)
- SQL transformations (maintainable by data analysts)
- Structured logging with correlation IDs and rate limit tracking

**Interview Demo Readiness:**
- Dagster UI shows clear Extract → Load → Transform lineage
- Can explain ELT vs ETL trade-offs
- Can explain technical constraints (Reddit OAuth denied → JSON endpoint pivot)
- Can explain legal risk mitigation strategy (portfolio context, respectful usage)
- Can query JSONB fields on-demand ("show me all stickied posts")
- Epic 5 excitement scores integrate multi-platform signals
- **Transparency:** Acknowledge Reddit approach is demo-only, not production-ready

---

## Data Schema Overview

### Raw Data Tables (JSONB Storage)

```sql
-- Reddit raw posts
CREATE TABLE raw_reddit_posts (
    post_key BIGSERIAL PRIMARY KEY,
    post_id VARCHAR(50) UNIQUE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    partition_date DATE NOT NULL,
    raw_json JSONB NOT NULL,  -- Complete Reddit post "data" object
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('raw_reddit_posts', 'fetched_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_raw_reddit_jsonb ON raw_reddit_posts USING GIN (raw_json);

-- Bluesky raw posts
CREATE TABLE raw_bluesky_posts (
    post_key BIGSERIAL PRIMARY KEY,
    post_uri TEXT UNIQUE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    partition_date DATE NOT NULL,
    raw_json JSONB NOT NULL,  -- Complete Bluesky post view
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('raw_bluesky_posts', 'fetched_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_raw_bluesky_jsonb ON raw_bluesky_posts USING GIN (raw_json);
```

### Staged Data Table (Unified Schema)

```sql
CREATE TABLE stg_social_posts (
    post_key BIGSERIAL PRIMARY KEY,
    source_platform VARCHAR(20) NOT NULL,  -- 'reddit' | 'bluesky'
    post_id TEXT NOT NULL,

    -- Common fields (normalized)
    post_text TEXT NOT NULL,
    post_url TEXT NOT NULL,
    author VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL,

    -- Unified engagement metrics
    engagement_score DECIMAL(10,2),
    upvotes INTEGER,
    comments INTEGER,
    shares INTEGER,

    -- Platform-specific extras (JSONB)
    source_specific_json JSONB,

    partition_date DATE NOT NULL,
    created_at_stg TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (source_platform, post_id)
);

SELECT create_hypertable('stg_social_posts', 'created_at', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_stg_social_platform ON stg_social_posts (source_platform, created_at DESC);
CREATE INDEX idx_stg_social_engagement ON stg_social_posts (engagement_score DESC);
```

### Fact Table (Epic 5 Integration)

```sql
CREATE TABLE fact_social_sentiment (
    sentiment_key BIGSERIAL PRIMARY KEY,
    game_key BIGINT REFERENCES fact_game(game_key),
    post_key BIGINT REFERENCES stg_social_posts(post_key),
    sentiment_date_key INTEGER REFERENCES dim_date(date_key),

    source_platform VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(5,2),
    sentiment_category VARCHAR(20),

    matched_teams TEXT[],
    match_confidence DECIMAL(3,2),
    match_method VARCHAR(50),

    game_time_context VARCHAR(20),
    post_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('fact_social_sentiment', 'post_time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX idx_fact_social_game ON fact_social_sentiment (game_key, post_time DESC);
```

---

## Platform-Specific Details

### Reddit Data (JSON Endpoint Approach)

**Endpoint:** `https://www.reddit.com/r/CollegeBasketball/new.json?limit=100`
**Authentication:** None (unauthenticated)
**Rate Limit:** 10 QPM (requests per minute)
**User-Agent:** `GamePulse/1.0 (NCAA basketball analytics; contact@gamepulse.top)`
**Legal Status:** ⚠️ Violates Reddit ToS - Portfolio/demo use only

**High-Priority Fields (MUST capture):**
- `title` - Primary text for sentiment analysis
- `score` - Upvote count
- `num_comments` - Comment count
- `total_awards_received` - Award count
- `created_utc` - Post timestamp
- `author` - Username
- `permalink` - Post URL
- `link_flair_text` - Post type (e.g., "Game Thread")

**Medium-Priority Fields (useful for ML):**
- `upvote_ratio` - Community sentiment indicator
- `selftext` - Additional text (if self-post)
- `stickied` - Official content indicator
- `distinguished` - Moderator posts

**Storage Strategy:**
- Store complete `post["data"]` object as JSONB
- Extract high-priority fields to typed columns in `stg_social_posts`
- Store medium-priority fields in `source_specific_json`

### Bluesky Data

**High-Priority Fields (MUST capture):**
- `record.text` - Primary text for sentiment analysis
- `likeCount` - Like count
- `replyCount` - Reply count
- `repostCount` - Repost count
- `quoteCount` - Quote post count
- `record.createdAt` - Post timestamp
- `author.handle` - Username
- `uri` - AT Protocol URI

**Medium-Priority Fields (useful for ML):**
- `facets` - Mentions, hashtags (team detection)
- `embed.$type` - Media type classification
- `reply.root` - Thread context

**Storage Strategy:**
- Store complete post view object as JSONB
- Extract high-priority fields to typed columns in `stg_social_posts`
- Store medium-priority fields in `source_specific_json`

---

## Dependencies

### Upstream Dependencies (Epic 4 → Depends On)

| Dependency | Description | Risk |
|------------|-------------|------|
| **Epic 2: NCAA Game Data** | `fact_game` table provides game_key for post matching | ✅ Complete (existing ncaa_games asset) |
| **Reddit Legal Risk Acceptance** | Reddit JSON endpoints violate ToS. Must accept legal risk for portfolio/demo use. | ⚠️ **HIGH RISK** - Portfolio context only. Monitor for Reddit C&D or IP ban. Be prepared to disable Reddit integration. |
| **Bluesky Account** | Need Bluesky account + app password for atproto authentication | ✅ Low risk - Free registration, no approval needed |

### Downstream Dependencies (Depends On → Epic 4)

| Dependency | Description | Impact |
|------------|-------------|--------|
| **Epic 5: Excitement Scoring** | Queries `fact_social_sentiment` for sentiment signal | Must complete Epic 4 Stories 4.1-4.10 before Epic 5 can integrate |
| **Future ML Epic (Epic 11)** | Trains models on raw JSONB data | No immediate blocker - raw data accumulates passively |

---

## Open Questions for Architect

### Technical Design Questions

1. **Q1: Game Matching Algorithm Placement**
   - Should game matching be:
     - **Option A:** Combined in `transform_unified_social_posts` asset (single SQL transform)?
     - **Option B:** Separate `match_posts_to_games` asset (modular, testable)?
   - **Analyst Recommendation:** Option B for better Dagster lineage visibility

2. **Q2: Sentiment Analysis Execution**
   - Should VADER sentiment run:
     - **Option A:** In Python Dagster asset (using vaderSentiment library)?
     - **Option B:** As PostgreSQL function (compile VADER to SQL/PL/pgSQL)?
   - **Analyst Recommendation:** Option A (VADER is Python-native, complex lexicon)

3. **Q3: Incremental Transform Strategy**
   - Should hourly transforms:
     - **Option A:** Re-run full partition (simple, idempotent)?
     - **Option B:** Only transform posts added since last run (complex cursor tracking)?
   - **Analyst Recommendation:** Option B for efficiency (10K posts/day × hourly = only 400 posts/run)

4. **Q4: Raw Data Compression Timing**
   - When to compress raw JSONB chunks:
     - **Option A:** After 7 days (balance access speed vs storage)?
     - **Option B:** After 30 days (longer fast-access window)?
   - **Analyst Recommendation:** Option A (7 days covers active game analysis window)

5. **Q5: Retry Policy Granularity**
   - Should retry policies differ by error type:
     - **Option A:** Single policy (3 retries, exponential backoff) for all failures?
     - **Option B:** Separate policies for rate limits (linear backoff) vs network errors (exponential)?
   - **Analyst Recommendation:** Option B (rate limit backoff should not compound delay)

### Integration Questions

6. **Q6: Epic 5 Fact Table Updates**
   - How should Epic 5 query `fact_social_sentiment`:
     - **Option A:** Join to `stg_social_posts` for latest engagement scores (fresh data)?
     - **Option B:** Denormalize engagement scores into `fact_social_sentiment` (faster queries)?
   - **Analyst Recommendation:** Option B (Epic 5 queries will be high-frequency, optimize for read performance)

7. **Q7: Multi-Platform Engagement Normalization**
   - Should Epic 5 treat Reddit and Bluesky equally:
     - **Option A:** Equal weighting (1:1 ratio)?
     - **Option B:** Platform-specific weights (e.g., Reddit 0.7, Bluesky 0.3 due to smaller community)?
   - **Analyst Recommendation:** Defer to Epic 5 design - Epic 4 provides raw `source_platform` column for flexibility

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **R-1: Reddit Legal Action** | **CRITICAL** (Lawsuit, C&D, DMCA takedown) | **MEDIUM-HIGH** | **Acknowledge risk.** Portfolio/demo context only. Use respectful User-Agent, conservative rate limiting. Monitor for ToS changes. Be prepared to disable Reddit integration immediately if contacted. **Not for production use.** |
| **R-2: Reddit IP Ban** | HIGH (lose Reddit data source entirely) | MEDIUM | Conservative polling (6-10 min = 6-10 requests/hour, well below 10 QPM). Exponential backoff on 429 errors. Monitor X-Ratelimit headers. Fallback to Bluesky-only if banned. |
| **R-3: Insufficient Bluesky Content** | MEDIUM (low post volume reduces Epic 5 signal quality) | MEDIUM | Validate basketball hashtag volume before full implementation. Expand to NBA hashtags if needed. |
| **R-4: Storage Overflow** | HIGH (database crashes, EC2 fills disk) | LOW | Implement 90-day retention policy with compression. Monitor disk usage in CloudWatch. |
| **R-5: API Schema Changes** | LOW (JSONB preserves fields, but breaks typed column extraction) | MEDIUM | Store complete raw JSON. Monitor Reddit/Bluesky changelogs. Add schema validation tests. |
| **R-6: VADER Accuracy** | MEDIUM (poor sentiment scores reduce Epic 5 value) | MEDIUM | Spot-check sentiment scores manually (sample 100 posts). Consider fine-tuning VADER lexicon for sports slang. |

---

## Next Steps

### Immediate Actions (Business Analyst - Mary)

1. **Archive Old Epic 4 Documentation**
   - Move `docs/tech-spec-epic-4.md` to `docs/archive/tech-spec-epic-4-reddit-only.md`
   - Add header note: "ARCHIVED - Replaced by ELT approach in epic-4-goals.md"

2. **Update Sprint Status**
   - Modify `docs/sprint-status.yaml` to reflect Epic 4 revised approach
   - Mark old Story 4-1 (Reddit OAuth Auth) as "superseded by new Epic 4"
   - Add placeholder for new Stories 4.1-4.10 (pending Architect breakdown)

3. **Hand Off to Architect**
   - Trigger `/bmad:bmm:agents:architect` workflow
   - Provide this goals document + complete research report
   - Request: Technical specification for Epic 4 ELT pipeline with story breakdown

### Architect Deliverables (Expected Output)

1. **Technical Specification Document**
   - Database migration scripts (Alembic) for raw/staged/fact tables
   - Dagster asset code patterns (extract/load/transform)
   - Reddit JSON client implementation (httpx with rate limiting)
   - Bluesky client implementation (atproto SDK)
   - Retry policy configurations and exponential backoff
   - Rate limit monitoring and IP ban prevention
   - Logging and monitoring strategy

2. **Story Breakdown**
   - Epic 4 decomposed into 10-12 implementable stories
   - Each story: Description, Acceptance Criteria, Dependencies, Effort Estimate
   - Story sequencing: Week 1 (Reddit), Week 2 (Bluesky + Transform), Week 3 (Sentiment + Epic 5)

3. **Architecture Decision Records (ADRs)**
   - Answers to Open Questions 1-7 above
   - Rationale for technical choices (with trade-off analysis)

---

## Appendix: Research References

### Complete Research Report
- **Location:** Provided in Business Analyst (Mary) research output (2025-11-15)
- **Contents:**
  - Reddit JSON schema (40+ fields documented)
  - Bluesky AT Protocol schema (20+ fields documented)
  - Dagster ELT patterns with code examples
  - TimescaleDB storage strategies
  - Rate limiting calculations
  - Platform comparison matrices

### External Documentation
- **Reddit JSON Endpoints:** https://www.reddit.com/dev/api/ (unauthenticated .json endpoints)
- **httpx Library:** https://www.python-httpx.org/ (async HTTP client for Reddit)
- **Bluesky AT Protocol:** https://docs.bsky.app/
- **atproto SDK:** https://github.com/MarshalX/atproto (Python)
- **Dagster ELT Guide:** https://docs.dagster.io/concepts/assets
- **TimescaleDB Hypertables:** https://docs.timescale.com/use-timescale/latest/hypertables/

### Related GamePulse Documents
- **Epic 2 Tech Spec:** NCAA game data ingestion (ncaa_games Dagster asset)
- **Epic 5 Tech Spec:** Excitement scoring formula (depends on social sentiment)
- **Architecture Documentation:** `docs/architecture.md` (if exists)
- **Sprint Status:** `docs/sprint-status.yaml` (tracking Epic/Story progress)

---

**Document Status:** ✅ Goals Defined - Ready for Architectural Design
**Next Step:** Hand off to Architect for technical specification and story breakdown
**Owner:** Philip (via Business Analyst workflow)
**Last Updated:** 2025-11-15
