# gamepulse - Epic Breakdown

**Author:** Philip
**Date:** 2025-11-07
**Project Level:** Level 2-3 (Medium Complexity - Data Pipeline + Web App)
**Target Scale:** Portfolio Demo (5-10 concurrent games, 10-50 users)

---

## Overview

This document provides the complete epic breakdown for GamePulse, decomposing the requirements from the [PRD](./PRD.md) into implementable epics and stories.

GamePulse is a real-time sports analytics platform demonstrating modern data engineering patterns: multi-source integration (batch + streaming), time-series analysis, and production-ready cloud deployment.

**Implementation Strategy:** Deploy early, iterate fast. Get a working demo live by end of Week 1, then add intelligence and polish incrementally.

**Stories:** Individual story files are located in [docs/stories/](./stories/)

---

## Phase 1: Foundation + Basic Demo (Week 1 - Working URL ASAP)

### Epic 1: Project Foundation & Infrastructure

**Goal:** Establish production-ready foundation using FastAPI full-stack template with deployment to AWS EC2.

**Value:** Provides the infrastructure foundation for all subsequent development. Live public URL ready for iterative deployment.

**Technical Foundation:**
- FastAPI full-stack template with Docker Compose orchestration
- PostgreSQL 16 + TimescaleDB extension for time-series data
- GitHub Actions CI/CD for automated deployment
- AWS EC2 t2.micro (free tier) with Traefik reverse proxy
- SQLModel ORM with Alembic migrations

**Milestone:** Live public URL infrastructure ready

**Stories:**
1. [Story 1.1: Initialize FastAPI Full-Stack Template](./stories/1-1-initialize-fastapi-template.md)
2. [Story 1.1b: Provision AWS Infrastructure](./stories/1-1b-provision-aws-infrastructure.md)
3. [Story 1.2: Remove Authentication Boilerplate](./stories/1-2-remove-authentication.md)
4. [Story 1.3: Configure TimescaleDB](./stories/1-3-configure-timescaledb.md)
5. [Story 1.4: Create Database Schema](./stories/1-4-create-database-schema.md)
6. [Story 1.5: Setup GitHub Actions](./stories/1-5-setup-github-actions.md)
7. [Story 1.6: Deploy to AWS EC2](./stories/1-6-deploy-to-aws-ec2.md)
8. [Story 1.7: Implement ECR-Based Docker Builds](./stories/1-7-ecr-remote-builds.md)

---

### Epic 2: Dimensional Foundation + Game Data Ingestion (Batch)

**Goal:** Establish Kimball-style dimensional modeling foundation and ingest NCAA Men's Basketball game data via batch polling every 15 minutes.

**Value:** Provides portfolio-ready dimensional data warehouse patterns (surrogate keys, SCD Type 2 readiness, date dimensions) while ingesting foundational game data. Demonstrates understanding of modern data engineering methodology and batch processing paradigm.

**Technical Stack:**
- **Dimensional Modeling:** Kimball star schema with surrogate keys (team_key, game_key, date_key)
- NCAA API client using henrygd/ncaa-api (free, self-hostable, 5 req/sec limit)
- httpx for async HTTP requests
- Dagster (self-hosted) for data orchestration with asset-oriented paradigm (15-minute schedules)
- SQLModel for database operations with dimensional model support
- Alembic migrations for schema management and refactoring

**Dimensional Schema:**
- `dim_team` (surrogate key: team_key, flattened team_group attributes)
- `dim_date` (surrogate key: date_key in YYYYMMDD format, NCAA tournament metadata)
- `fact_game` (surrogate key: game_key, FKs to dim_team and dim_date)

**Milestone:** Database has dimensional model with game data flowing

**Stories:**
1. [Story 2.1: Create Team and Conference Dimensional Data](./stories/story-2.1-create-dimensional-data.md)
2. [Story 2.2: Build NCAA API Client with httpx](./stories/story-2.2-build-ncaa-client.md)
3. [Story 2.3: Create Game SQLModel and Database Migration](./stories/story-2.3-create-game-model.md)
4. **[Story 2-3a: Refactor to Dimensional Model with Surrogate Keys](./stories/2-3a-refactor-dimensional-model.md)** ⬅️ NEW
5. **[Story 2-3b: Sync Team Metadata from NCAA API](./stories/2-3b-sync-team-metadata.md)** ⬅️ NEW
6. **[Story 2-3c: Create and Seed dim_date Dimension Table](./stories/2-3c-create-dim-date.md)** ⬅️ NEW
7. [Story 2.4: Implement Dagster Data Orchestration and NCAA Game Asset](./stories/story-2.4-implement-polling-worker.md)
8. [Story 2.5: Add Retry Logic and Error Handling](./stories/story-2.5-add-retry-logic.md)

---

### Epic 3: Basic API + Dashboard MVP

**Goal:** Create a minimal working demo with live NCAA games displayed on a web dashboard - achievable by end of Week 1.

**Value:** 🎯 **WORKING DEMO** - Live public URL showing real NCAA games that can be shared in interviews. Proves the full stack works end-to-end before adding complexity.

**Simplifications:**
- No excitement scores yet (just show games)
- No Reddit posts or sentiment analysis
- No sparkline charts or fancy visualizations
- Minimal styling (basic Chakra UI components)
- Goal: Functional over pretty - can polish in Epic 8

**Technical Stack:**
- FastAPI endpoints with Pydantic schemas
- React 18 + TypeScript + Chakra UI
- React Query for data fetching and auto-refresh
- Simple responsive layout

**Milestone:** 🎯 WORKING DEMO BY END OF WEEK 1 - Live URL showing NCAA games

**Stories:**
1. [Story 3.1: Create Basic /api/games/today Endpoint](./stories/story-3.1-create-games-endpoint.md) - Includes CORS configuration
2. [Story 3.2: Add Health Check Endpoint](./stories/story-3.2-add-health-endpoint.md)
3. [Story 3.3: Initialize React Dashboard with Chakra UI](./stories/story-3.3-initialize-react-dashboard.md)
4. [Story 3.4: Build Simple Game List Component](./stories/story-3.4-build-game-list.md)
5. [Story 3.5: Add Auto-Refresh Polling with React Query](./stories/story-3.5-add-auto-refresh.md)
6. **Story 3.6: Increase Refresh Cadence to 1 Minute** (Real-Time Feel)

---

#### Story 3.6: Increase Refresh Cadence to 1 Minute (Real-Time Feel)

**Goal:** Transform dashboard from batch-oriented (15-minute updates) to real-time feel (1-minute updates) to match user expectations for live sports.

**User Story:**
> As a user watching a live game, I want scores and game status to update within 1-2 minutes, so the dashboard feels like a real sports app instead of a delayed summary.

**Business Value:**
- ✅ **Interview Impact:** Demonstrates understanding of real-time data requirements in sports/gaming
- ✅ **User Experience:** 15-minute delays feel broken for live games; 1-minute feels responsive
- ✅ **Portfolio Differentiation:** Shows ability to balance real-time requirements with API constraints
- ✅ **Low Risk, High Impact:** Simple configuration change with dramatic UX improvement

**Technical Approach:**

Story 3.5 implemented the auto-refresh mechanism with 15-minute polling as a conservative starting point. This story tunes the system to 1-minute cadence by updating both backend data ingestion (Dagster) and frontend polling (React Query).

**Backend Changes:**
```python
# backend/app/dagster_definitions.py
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    cron_schedule="* * * * *",  # Every 1 minute (was "*/15 * * * *")
    # ... rest unchanged
)
```

**Frontend Changes:**
```typescript
// frontend/src/hooks/useGames.ts
export function useGames() {
  return useQuery<GameListResponse>({
    queryKey: ["games", "today"],
    queryFn: async () => { /* ... */ },
    refetchInterval: 60000,  // 1 minute (was 900000)
    staleTime: 60000,        // 1 minute (was 900000)
    refetchIntervalInBackground: true,
  });
}
```

**UI Enhancement:**
```typescript
// frontend/src/routes/_layout/index.tsx
// Update "Last updated" display to show seconds for better feedback
<Text fontSize="sm" color="gray.500">
  Last updated {formatDistanceToNow(new Date(data.generated_at), { addSuffix: true })}
</Text>
// Outputs: "Last updated 45 seconds ago" (instead of "less than a minute ago")
```

**API Rate Limit Analysis:**

**Current Usage (15-minute polling):**
- Frequency: 1 request every 15 minutes = 96 requests/day
- Sustained rate: 0.0011 req/sec
- Daily data transfer: ~1.4 MB (96 × 15 KB response size)

**Proposed Usage (1-minute polling):**
- Frequency: 1 request every 1 minute = 1,440 requests/day
- Sustained rate: 0.0167 req/sec
- Daily data transfer: ~21.6 MB (1,440 × 15 KB response size)
- **Increase:** 15x more frequent (still **well below** 5 req/sec burst limit)

**NCAA API Limits (henrygd/ncaa-api wrapper):**
- Documented burst limit: 5 req/sec (enforced with 200ms client-side delay)
- Undocumented QPM/QPD limits: None found in documentation
- Self-hosted wrapper: No centralized rate limiting beyond per-client throttling
- **Risk Assessment:** Low - 1-minute polling is 300x slower than burst limit

**Performance Impact:**

**Backend (Dagster):**
- Current run duration: ~2-3 seconds per execution
- Execution frequency: 60x more frequent (every 1 minute vs every 15 minutes)
- CPU impact: Minimal - Dagster in-process executor with async I/O
- Database impact: ~60 upserts/hour (negligible for PostgreSQL)

**Frontend:**
- Network overhead: 1 request/minute = battery-friendly on mobile
- React Query cache: ~15KB per query (no memory impact)
- Tab visibility API: Polling continues when hidden (user preference for freshness)

**Monitoring and Observability:**

**Add CloudWatch Metrics (Optional - Epic 9):**
```python
# Future enhancement: Track API response codes
context.log.info(f"NCAA API request completed: status={response.status_code}, games={len(raw_games)}")
```

**Manual Monitoring (Immediate):**
- Watch Dagster logs for 429 (rate limit) errors
- Check `/api/v1/health` endpoint response times
- Monitor EC2 instance CPU usage (should remain <10% resting)

**Rollback Plan:**

If rate limiting or performance issues occur:
1. Revert Dagster cron to `"*/5 * * * *"` (5-minute compromise)
2. Revert frontend to `refetchInterval: 300000` (5 minutes)
3. No schema changes required - pure configuration rollback

**Gradual Rollout Strategy (Recommended):**

Instead of jumping directly from 15-minute to 1-minute, consider intermediate testing:

1. **Step 1:** Deploy 5-minute polling (both backend + frontend)
   - Monitor for 24-48 hours
   - Check Dagster logs for errors
   - Verify no API throttling

2. **Step 2:** Deploy 1-minute polling if Step 1 successful
   - Monitor for 24-48 hours
   - If issues arise, rollback to 5-minute

**Why Gradual:**
- De-risks undocumented API rate limits
- Allows performance validation on EC2 t2.micro
- Provides fallback option (5-minute) if 1-minute proves too aggressive

**Alternative: Feature Flag Approach**

For production systems, consider environment-based configuration:

```python
# backend/app/core/config.py
class Settings(BaseSettings):
    DAGSTER_SCHEDULE_INTERVAL: str = "* * * * *"  # Default: 1 minute
    # Override via .env: DAGSTER_SCHEDULE_INTERVAL="*/5 * * * *"
```

**Dependencies:**
- ✅ Story 3.5 completed (auto-refresh mechanism in place)
- ✅ Dagster schedule running and healthy
- ✅ NCAA API client with rate limiting (Story 2.2)

**Acceptance Criteria Hints:**

1. **AC-3.34: Backend Polling Cadence**
   - Dagster schedule updates every 1 minute
   - Dagster logs show successful runs every minute
   - No 429 (rate limit) errors in logs after 24 hours

2. **AC-3.35: Frontend Polling Alignment**
   - React Query refetch interval set to 60000ms
   - Network tab shows API requests every 60 seconds
   - "Last updated" timestamp never exceeds 2 minutes

3. **AC-3.36: Timestamp Display Precision**
   - "Last updated" shows seconds for recency: "45 seconds ago"
   - Updates every 30 seconds via useEffect timer (already implemented in 3.5)

4. **AC-3.37: Monitoring and Validation**
   - Manual verification: Wait 5 minutes, observe 5 API requests in Network tab
   - Dagster UI shows runs every minute (not skipped or failed)
   - EC2 CPU usage remains <15% (CloudWatch or `top` command)

5. **AC-3.38: Error Handling**
   - Existing retry logic from Story 3.5 continues working
   - If API fails, cached data shown with warning banner
   - No regression in error handling behavior

**Risk Assessment:**

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NCAA API rate limiting | Low | Medium | Gradual rollout (5-min → 1-min), monitoring, rollback plan |
| EC2 CPU overload (t2.micro) | Very Low | Medium | CPU metrics monitoring, swap already configured |
| Increased network costs | Very Low | Very Low | 21.6 MB/day well within free tier (15 GB/month) |
| Frontend battery drain | Low | Low | Tab visibility API already pauses polling when hidden |

**Overall Risk:** **LOW** - Well-scoped configuration change with proven rollback path.

**Success Metrics:**

- ✅ Dashboard updates within 1-2 minutes of game events
- ✅ No API rate limit errors after 7 days
- ✅ EC2 CPU usage <15% sustained
- ✅ User perception: "Feels like live sports" vs "Feels delayed"

**Future Enhancements (Out of Scope):**

This story maintains batch polling architecture (1-minute intervals). Future improvements:
- **Epic 6:** WebSocket streaming for sub-second updates (betting odds)
- **Epic 5:** Historical snapshots for tracking score changes between polls
- **Epic 8:** Server-Sent Events (SSE) for push-based updates

**References:**
- NCAA API Client: `backend/app/services/ncaa_client.py` (5 req/sec limit, 200ms delay)
- Dagster Schedule: `backend/app/dagster_definitions.py` (current 15-min schedule)
- React Query Hook: `frontend/src/hooks/useGames.ts` (current 15-min polling)
- Story 3.5 Implementation: Auto-refresh mechanism with stale-while-revalidate

**File Changes Expected:**
- `backend/app/dagster_definitions.py` - Update cron schedule string
- `frontend/src/hooks/useGames.ts` - Update refetchInterval and staleTime
- `frontend/src/routes/_layout/index.tsx` - Optionally enhance timestamp display

**Testing Strategy:**
- **Unit Tests:** No new tests required (configuration change only)
- **Integration Tests:** Verify Dagster schedule triggers every minute
- **Manual Testing:** Monitor dashboard for 5 minutes, count API requests (should be 5)
- **Smoke Test:** Health endpoint response time <500ms under 1-minute polling load

---

## Phase 2: Data Pipeline Complexity (Week 2 - Add Intelligence)

### Epic 4: Social Media Data Ingestion via ELT Pattern

**Goal:** Multi-platform social media data pipeline (Reddit + Bluesky) using Extract-Load-Transform pattern to collect game-related social conversations.

**Value:** Social signals for excitement scoring. Demonstrates ELT patterns, Dagster orchestration, TimescaleDB partitioning, and sentiment analysis.

**Milestone:** Social posts matched to games with sentiment analysis, ready for UI integration

**Technical Stack:**
- Reddit + Bluesky data sources
- TimescaleDB hypertables (90-day retention, 7-day compression)
- Dagster orchestration with auto-materialization policies
- VADER sentiment analysis
- GameMatcher service for team/game resolution

**Epic Documentation:** [Epic 4 Technical Specification](./epics/epic-4-social-media-elt.md)

**Stories:**
1. [Story 4-1: Reddit Data Pipeline](./stories/4-1-reddit-data-pipeline.md) ✅ DONE
2. [Story 4-2: Bluesky Data Pipeline](./stories/4-2-bluesky-data-pipeline.md) ✅ DONE
3. [Story 4-3: Game Matching Service](./stories/4-3-game-matching-service.md) ✅ DONE
4. [Story 4-4: Unified Transform Layer](./stories/4-4-unified-transform-layer.md) ✅ DONE
5. [Story 4-5: Sentiment Analysis Fact Table](./stories/4-5-sentiment-analysis-fact-table.md) ✅ DONE
6. [Story 4-6: Improve Game Matching Quality](./stories/4-6-improve-game-matching-quality.md) ✅ DONE
7. [Story 4-7: Orchestration & Data Management](./stories/4-7-orchestration-data-management.md) ✅ DONE
8. [Story 4-8: Game Matching Post-Processor](./stories/4-8-game-matching-post-processor.md) - READY (Optimization - deferred)
9. **[Story 4-9: Enhanced Game Card UI Design](./stories/4-9-game-card-ui-design.md)** ⬅️ NEW (UX)
10. **[Story 4-10: Social Posts Feed Integration](./stories/4-10-social-posts-feed.md)** ⬅️ NEW (UX)

**Implementation Order:**
- **Week 1:** Stories 4-1 through 4-7 (backend pipeline) ✅ Complete
- **Week 2:** Stories 4-9, 4-10 (UX integration) ⬅️ Next
- **Later:** Story 4-8 (optional optimization)

---

### Epic 5: Moment Detection & Excitement Scoring

**Goal:** Detect exciting moments in games and calculate multi-factor excitement scores.

**Value:** Games ranked by excitement (0-100 scale). Moments linked to specific Reddit posts when identifiable.

**Milestone:** Excitement scores calculated and stored as time-series with optional Reddit post linkage

**Schema Design:**
- `fact_moment` (renamed from fact_excitement - better semantic clarity)
- Grain: One measurement per game per time interval (15 min during batch polling, potentially real-time later)
- Partitioned by `moment_time` (TimescaleDB hypertable, 1-day chunks)
- Optional FK to `event_reddit_post` (links moments to triggering posts)

**Table: fact_moment**
```sql
fact_moment (
  moment_key BIGSERIAL,
  game_key BIGINT REFERENCES fact_game(game_key),
  moment_time TIMESTAMP NOT NULL,                   -- Measurement timestamp
  moment_date_key INTEGER REFERENCES dim_date(date_key),

  -- Measures (excitement components)
  excitement_score DECIMAL(5,2),                    -- 0-100 composite score
  reddit_velocity DECIMAL(8,2),                     -- posts/minute
  reddit_engagement INTEGER,                        -- aggregate engagement
  sentiment_score DECIMAL(5,2),                     -- -1 to +1 (VADER)
  odds_volatility DECIMAL(8,4),                     -- probability shift (Epic 6)

  -- Context
  game_clock VARCHAR(20),                           -- "2:34 2nd Half"
  period VARCHAR(10),                               -- "1st", "2nd", "OT"

  -- Optional link to triggering Reddit post
  source_reddit_post_key BIGINT REFERENCES event_reddit_post(post_key),  -- nullable

  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (game_key, moment_time)
) PARTITION BY RANGE (moment_time);
```

**Design Rationale:**
- `fact_moment` name emphasizes "what happened" vs "how exciting" (more intuitive)
- excitement_score is an attribute of the moment, not a separate fact
- Optional FK to event_reddit_post enables "show me the Reddit post that triggered this moment"
- Heuristic matching (Story 5.7): If single high-engagement post within 5-min window → populate source_reddit_post_key

**Excitement Algorithm (Multi-Factor Weighted)**:
```python
reddit_component = min(reddit_velocity * 4, 40)           # 0-40 scale
sentiment_component = max(0, sentiment_score * 20)        # 0-20 scale (positive only)
odds_component = min(odds_volatility * 600, 30)           # 0-30 scale
base_score = reddit_component + sentiment_component + odds_component  # 0-90
final_score = (base_score * game_context_factor) + rivalry_bonus
# game_context_factor: 1.0 (regular), 1.2 (conference), 1.5 (tournament)
# rivalry_bonus: +10 for rivalry games
excitement_score = min(max(final_score, 0), 100)          # Clamp to 0-100
```

**Stories:**
1. **Story 5.1: Implement Historical Game Snapshots with TimescaleDB** (Foundation - MUST BE FIRST)

**Remaining Stories:** _High-level implementation captured at epic level (to be decomposed after 5.1)_
2. Create fact_moment table schema (TimescaleDB hypertable)
3. Reddit velocity calculation (posts/minute in 5-min window)
4. Engagement scoring aggregation (upvotes + comments*0.5 + awards*2.0)
5. Sentiment score integration (from Epic 4 VADER output)
6. Multi-factor excitement algorithm (weighted composite 0-100 scale)
7. Time-series storage and aggregation (TimescaleDB time_bucket)
8. **Link moments to Reddit posts** (heuristic: single high-engagement post within 5-min window → populate source_reddit_post_key)

---

#### Story 5.1: Implement Historical Game Snapshots with TimescaleDB (Foundation Story)

**Goal:** Create time-series snapshot infrastructure to preserve game state over time, enabling historical analysis and future features (win probability, moment detection, score momentum).

**User Story:**
> As a developer building excitement detection algorithms, I need historical game state data (score progression, game clock) at regular intervals, so I can calculate score momentum, detect swings, and build win probability models.

**Why This Story MUST Be First:**

Epic 5's excitement scoring and moment detection **require historical data that doesn't exist yet**. The current architecture (`fact_game` table) uses **update-in-place** strategy:

```python
# Current behavior (Story 2.4): backend/app/assets/ncaa_games.py
stmt = insert(FactGame).values(fact_game)
stmt = stmt.on_conflict_do_update(
    index_elements=["game_id"],
    set_={
        "home_score": stmt.excluded.home_score,  # Overwrites previous value!
        "away_score": stmt.excluded.away_score,  # No history preserved
        "game_status": stmt.excluded.game_status,
        # ...
    }
)
```

**Problem:** This approach **destroys historical state**. We can't answer:
- "What was the score at 5:32 in the 2nd half?" → Lost, only current score exists
- "How fast did the score change?" → Can't calculate Δ score / Δ time
- "When did momentum shift?" → No baseline to compare against

**Solution:** Implement dual-table architecture:
1. **Keep `fact_game`** (current state table) - Unchanged, fast dashboard queries
2. **Add `fact_game_snapshot`** (historical time-series) - New, enables analytics

**Business Value:**
- ✅ **Unblocks Epic 5:** Excitement algorithms require score deltas (Δ score, Δ time)
- ✅ **Enables Win Probability:** Future model needs score progression to train on
- ✅ **Portfolio Differentiation:** Demonstrates time-series database expertise (TimescaleDB)
- ✅ **Data Foundation:** Accumulates data passively while building other features

**Architectural Pattern: Hybrid Current-State + Snapshot Strategy**

**Table 1: `fact_game` (Existing - NO CHANGES)**
- **Purpose:** Latest game state for dashboard queries
- **Grain:** One row per game
- **Updates:** In-place upserts (current behavior)
- **Queries:** Fast lookups by game_id

**Table 2: `fact_game_snapshot` (New - This Story)**
- **Purpose:** Historical state over time for analytics
- **Grain:** One row per game per snapshot interval
- **Inserts:** Append-only (never update)
- **Queries:** Time-series analysis, win probability, moments

**Schema Design:**

```sql
CREATE TABLE fact_game_snapshot (
  snapshot_key BIGSERIAL,
  game_key BIGINT NOT NULL REFERENCES fact_game(game_key),
  snapshot_time TIMESTAMP NOT NULL,  -- Partition key for TimescaleDB

  -- Snapshot values (denormalized for query performance)
  home_score INT NOT NULL,
  away_score INT NOT NULL,
  game_status VARCHAR(20),           -- "scheduled", "in_progress", "final"
  game_clock VARCHAR(20),            -- "14:32 2nd Half", "Final", "Halftime"
  period VARCHAR(10),                -- "1st", "2nd", "OT", "Final"

  -- Derived measures (computed at snapshot time for query speed)
  score_differential INT,            -- home_score - away_score
  total_score INT,                   -- home_score + away_score

  -- Audit
  created_at TIMESTAMP DEFAULT NOW(),

  PRIMARY KEY (game_key, snapshot_time)
);

-- Convert to TimescaleDB hypertable (automatic partitioning by snapshot_time)
SELECT create_hypertable('fact_game_snapshot', 'snapshot_time',
  chunk_time_interval => INTERVAL '1 day');

-- Add compression policy (90% size reduction after 7 days for old snapshots)
SELECT add_compression_policy('fact_game_snapshot', INTERVAL '7 days');

-- Add index for game_key lookups (queries often filter by specific game)
CREATE INDEX idx_fact_game_snapshot_game_key ON fact_game_snapshot(game_key, snapshot_time DESC);
```

**Design Rationale:**

1. **TimescaleDB Hypertable:** Automatic time-based partitioning (1-day chunks)
   - Efficient inserts: New snapshots append to latest chunk
   - Efficient queries: Time-range queries only scan relevant chunks
   - Compression: Old chunks compressed automatically (90% size reduction)

2. **Denormalized Design:** Store `score_differential` and `total_score` pre-computed
   - Why: Avoids expensive calculations on every query
   - Tradeoff: 8 bytes extra storage per row vs milliseconds saved per query
   - Portfolio win: Shows understanding of dimensional modeling tradeoffs

3. **Composite Primary Key:** `(game_key, snapshot_time)`
   - Prevents duplicate snapshots for same game at same timestamp
   - Efficient for time-series queries (range scans)

**Snapshot Frequency Decision:**

| Frequency | Snapshots/Game (2-hour avg) | Annual Volume | Storage (Compressed) | Use Case |
|-----------|----------------------------|---------------|----------------------|----------|
| **1-minute** | 120 | 660K rows | 13 MB/year | Real-time analytics, win probability |
| **5-minute** | 24 | 132K rows | 3 MB/year | Excitement scoring, general analytics |
| **15-minute** | 8 | 44K rows | 1 MB/year | Archival, cost optimization |

**Recommendation: 5-minute snapshots** (middle ground)
- **Why:** Sufficient granularity for excitement detection (score swings visible)
- **Storage:** Only 3 MB/year compressed (negligible on 30 GB EC2 disk)
- **Performance:** 24 snapshots/game = minimal insert overhead
- **Flexibility:** Can switch to 1-minute later if needed (configuration change)

**Implementation Strategy:**

**Phase 1: Create Schema (Migration)**
```bash
# Generate Alembic migration
alembic revision --autogenerate -m "Add fact_game_snapshot for historical tracking"

# Apply migration
alembic upgrade head
```

**Phase 2: Modify Dagster Asset to Insert Snapshots**

```python
# backend/app/assets/ncaa_games.py (modify existing asset)

from app.models.fact_game_snapshot import FactGameSnapshot  # New model

async def ncaa_games(context, database):
    # ... existing upsert logic for fact_game (unchanged) ...

    # NEW: Insert snapshot for games currently in progress
    snapshot_count = 0
    for game_data in raw_games:
        game_state = game_data.get("gameState", "")

        # Only snapshot live games (not scheduled or final)
        if game_state == "live":
            # Retrieve game_key from fact_game upsert
            game_key_result = await session.execute(
                select(FactGame.game_key).where(FactGame.game_id == fact_game.game_id)
            )
            game_key = game_key_result.scalar_one()

            # Create snapshot row
            snapshot = FactGameSnapshot(
                game_key=game_key,
                snapshot_time=datetime.now(UTC),
                home_score=fact_game.home_score,
                away_score=fact_game.away_score,
                game_status=fact_game.game_status,
                game_clock=fact_game.game_clock,
                period=extract_period(game_data),  # Parse from NCAA API
                score_differential=fact_game.home_score - fact_game.away_score,
                total_score=fact_game.home_score + fact_game.away_score,
            )

            # Insert snapshot (no conflict handling needed - composite PK prevents duplicates)
            await session.execute(insert(FactGameSnapshot).values(snapshot))
            snapshot_count += 1

    await session.commit()

    # Add to materialization metadata
    context.log.info(f"Processed {games_processed} games, created {snapshot_count} snapshots")

    return MaterializeResult(
        metadata={
            "games_processed": games_processed,
            "games_inserted": games_inserted,
            "games_updated": games_updated,
            "snapshots_created": snapshot_count,  # NEW metric
        }
    )
```

**Phase 3: Verification Queries**

```sql
-- Check snapshot capture rate
SELECT
  game_key,
  COUNT(*) as num_snapshots,
  MIN(snapshot_time) as first_snapshot,
  MAX(snapshot_time) as last_snapshot,
  MAX(snapshot_time) - MIN(snapshot_time) as game_duration
FROM fact_game_snapshot
GROUP BY game_key
ORDER BY num_snapshots DESC
LIMIT 10;

-- Verify score progression for a specific game
SELECT
  snapshot_time,
  game_clock,
  home_score,
  away_score,
  score_differential
FROM fact_game_snapshot
WHERE game_key = 12345  -- Example game
ORDER BY snapshot_time;

-- Check storage and compression
SELECT
  pg_size_pretty(pg_total_relation_size('fact_game_snapshot')) as total_size,
  pg_size_pretty(pg_relation_size('fact_game_snapshot')) as table_size;
```

**Storage Cost Analysis:**

**Assumptions:**
- NCAA Men's Basketball: ~350 teams, ~30 games/season each
- Annual games: ~5,500 (350 × 30 / 2, accounting for shared games)
- Average game duration: 2 hours
- Snapshot frequency: 5 minutes
- Snapshots per game: ~24 (2 hours × 60 min / 5 min interval)
- Row size: ~200 bytes (8 fields × ~25 bytes avg)

**Storage Calculations:**

**Uncompressed:**
- Snapshots/year: 5,500 games × 24 snapshots = 132,000 rows
- Storage: 132,000 rows × 200 bytes = 26.4 MB/year

**Compressed (TimescaleDB):**
- Compression ratio: ~90% reduction (typical for time-series data)
- Storage: 26.4 MB × 0.10 = **2.6 MB/year compressed**

**5-Year Projection:**
- Total storage: 2.6 MB/year × 5 years = **13 MB total**
- EC2 Free Tier Disk: 30 GB available
- **Usage: <0.05% of available disk** ✅

**Conclusion:** Storage is NOT a constraint, even with 1-minute snapshots (13 MB/year).

**Query Performance Optimization:**

**Use Case 1: Score Progression Chart (Frontend)**
```sql
-- Get last 2 hours of snapshots for game timeline
SELECT
  snapshot_time,
  home_score,
  away_score,
  game_clock
FROM fact_game_snapshot
WHERE game_key = $1
  AND snapshot_time >= NOW() - INTERVAL '2 hours'
ORDER BY snapshot_time;
```

**Performance:** <10ms with TimescaleDB chunk exclusion and index on (game_key, snapshot_time)

**Use Case 2: Score Momentum Calculation (Excitement Scoring)**
```sql
-- Calculate score change velocity over 5-minute window
SELECT
  game_key,
  snapshot_time,
  score_differential,
  score_differential - LAG(score_differential) OVER (
    PARTITION BY game_key ORDER BY snapshot_time
  ) AS score_momentum,
  (snapshot_time - LAG(snapshot_time) OVER (
    PARTITION BY game_key ORDER BY snapshot_time
  )) AS time_delta
FROM fact_game_snapshot
WHERE game_status = 'in_progress'
  AND snapshot_time >= NOW() - INTERVAL '15 minutes';
```

**Use Case 3: Win Probability Model Training (Future)**
```sql
-- Extract training data: score differential and time remaining at each snapshot
SELECT
  fgs.game_key,
  fgs.snapshot_time,
  fgs.score_differential,
  fgs.period,
  fgs.game_clock,
  -- Outcome (did home team win?)
  CASE WHEN fg.home_score > fg.away_score THEN 1 ELSE 0 END as home_team_won
FROM fact_game_snapshot fgs
JOIN fact_game fg ON fgs.game_key = fg.game_key
WHERE fg.game_status = 'final'  -- Only completed games for training
  AND fgs.snapshot_time >= '2024-01-01';
```

**Dependencies:**
- ✅ Story 2.4 completed (Dagster ncaa_games asset exists)
- ✅ Story 2.3a completed (`fact_game` table with surrogate keys)
- ✅ Story 1.3 completed (TimescaleDB extension enabled)
- ✅ Story 3.6 recommended (1-minute Dagster polling for frequent snapshots)

**Acceptance Criteria Hints:**

1. **AC-5.1: Schema Creation**
   - `fact_game_snapshot` table created via Alembic migration
   - TimescaleDB hypertable configured with 1-day chunk interval
   - Compression policy enabled (7-day retention for uncompressed data)
   - Primary key on `(game_key, snapshot_time)` enforced
   - Foreign key to `fact_game(game_key)` enforced

2. **AC-5.2: Snapshot Capture Logic**
   - Dagster asset inserts snapshots only for games with `game_status = 'in_progress'`
   - Snapshots NOT created for scheduled or final games (avoids wasted storage)
   - Derived measures (`score_differential`, `total_score`) calculated and stored
   - Dagster metadata includes `snapshots_created` count

3. **AC-5.3: Data Quality Validation**
   - No duplicate snapshots: Primary key constraint prevents same `(game_key, snapshot_time)`
   - Score consistency: Snapshot scores match `fact_game` current scores (within 1-minute lag)
   - Temporal ordering: Snapshots for each game ordered chronologically
   - No orphan snapshots: All `game_key` values exist in `fact_game` table

4. **AC-5.4: Query Performance**
   - Score progression query (<game_key, last 2 hours>) returns in <50ms
   - Index on `(game_key, snapshot_time DESC)` exists and used by query planner
   - TimescaleDB chunk exclusion visible in EXPLAIN plan

5. **AC-5.5: Storage Verification**
   - Annual snapshot volume: ~132K rows for 5-minute snapshots (or ~660K for 1-minute)
   - Compressed size: <5 MB/year for 5-minute snapshots
   - Compression policy active (verify with `SELECT * FROM timescaledb_information.compression_settings`)

6. **AC-5.6: Monitoring and Observability**
   - Dagster run logs include snapshot metrics: `"Created 42 snapshots for 7 live games"`
   - No errors in Dagster logs related to snapshot insertion
   - PostgreSQL disk usage remains <5% of 30 GB after 30 days

**Risk Assessment:**

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Storage growth exceeds estimates | Low | Low | Compression reduces by 90%, retention policy deletes >90 days |
| Insert performance degrades | Very Low | Low | TimescaleDB optimized for high-velocity inserts, 24-60 inserts/hour trivial |
| Query performance impacts dashboard | Very Low | Medium | Snapshots use separate table, `fact_game` queries unchanged |
| Snapshot logic bugs (duplicates, missing) | Medium | Low | Primary key prevents duplicates, validation queries catch missing |

**Overall Risk:** **LOW** - Well-understood TimescaleDB patterns, no changes to existing queries.

**Rollback Plan:**

If issues arise:
1. Disable snapshot insertion logic (comment out in Dagster asset)
2. `fact_game` queries unaffected (no dependency on snapshots)
3. Drop `fact_game_snapshot` table if needed (no foreign key from other tables)

**Success Metrics:**

- ✅ Historical data accumulating: 24 snapshots/game for 2-hour games
- ✅ Storage growth linear: ~2.6 MB/year compressed
- ✅ No Dagster errors: 100% successful snapshot insertions
- ✅ Query speed: Score progression chart renders in <100ms
- ✅ Future-ready: Data foundation for Epic 5 excitement algorithms

**Future Enhancements (Out of Scope):**

- **Continuous Aggregates:** Pre-compute hourly score averages using TimescaleDB
- **Retention Policy:** Auto-delete snapshots >90 days old (keep disk usage bounded)
- **Snapshot API Endpoint:** `GET /api/games/{id}/timeline` (Epic 8)
- **Win Probability Model:** Train on snapshot data (Epic 5.9 or Epic 11)

**Why This Story Unlocks Epic 5:**

Without snapshots, Epic 5 stories **cannot be implemented**:
- ❌ Story 5.5 (Multi-factor excitement algorithm): Needs score momentum = Δ(score_differential) / Δt
- ❌ Story 5.6 (Time-series aggregation): Needs historical measurements to aggregate
- ❌ Future win probability: Needs score progression to train Bayesian model

With snapshots:
- ✅ Score momentum calculable: Compare snapshot N to snapshot N-1
- ✅ Excitement detection possible: Identify rapid score swings (>6 points in 5 min)
- ✅ Data foundation ready: Accumulate 1-2 months of data for modeling

**Recommended Timeline:**

1. **Week 2 Start:** Implement Story 5.1 (snapshots)
2. **Week 2-3:** Let snapshots accumulate passively while building Epic 4 (Reddit)
3. **Week 3 End:** Decompose remaining Epic 5 stories (now have historical data to work with)

**References:**
- Current Architecture: `backend/app/assets/ncaa_games.py` (upsert-only, no snapshots)
- TimescaleDB Docs: [Hypertables](https://docs.timescale.com/use-timescale/latest/hypertables/)
- TimescaleDB Docs: [Compression](https://docs.timescale.com/use-timescale/latest/compression/)
- PRD Section: NFR-1.5 (Data retention: 90 days for time-series metrics)

**File Changes Expected:**
- `backend/app/models/fact_game_snapshot.py` - New SQLModel class
- `backend/app/alembic/versions/XXX_add_game_snapshots.py` - New migration
- `backend/app/assets/ncaa_games.py` - Modify to insert snapshots
- `backend/app/models/__init__.py` - Import new model

**Testing Strategy:**
- **Unit Tests:** Snapshot model validation (required fields, derived measures)
- **Integration Tests:** Dagster asset inserts snapshots for live games, not final games
- **Manual Testing:** Run Dagster asset 3x over 15 minutes, verify 3 snapshots created
- **Query Tests:** Validate score progression query returns chronological results

---

### Epic 6: Streaming Betting Odds Integration

**Goal:** Demonstrate WebSocket streaming with Betfair.

**Value:** Portfolio shows dual paradigms (batch + streaming). High-velocity time-series writes.

**Milestone:** Real-time betting odds streaming demonstrated with odds_volatility integrated into fact_moment

**Schema Design:**
- `fact_betting_odds` (time-series fact table)
- Grain: One odds snapshot per game per time per bookmaker per market type
- Partitioned by `odds_time` (TimescaleDB hypertable, 1-hour chunks for high-velocity writes)
- Optional dim_bookmaker table (deferred to Epic 11 - single bookmaker "Betfair" for MVP)

**Table: fact_betting_odds**
```sql
fact_betting_odds (
  odds_key BIGSERIAL,
  game_key BIGINT REFERENCES fact_game(game_key),
  odds_time TIMESTAMP NOT NULL,
  odds_date_key INTEGER REFERENCES dim_date(date_key),

  -- Measures
  home_odds DECIMAL(10,4),                          -- Decimal odds (e.g., 1.85)
  away_odds DECIMAL(10,4),
  home_implied_prob DECIMAL(5,4),                   -- Derived: 1 / home_odds
  away_implied_prob DECIMAL(5,4),
  market_margin DECIMAL(5,4),                       -- Overround/vig

  -- Degenerate dimensions (no separate dim table for MVP)
  bookmaker VARCHAR(50),                            -- "Betfair" for MVP
  market_type VARCHAR(50),                          -- "moneyline" for MVP

  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (game_key, odds_time, bookmaker, market_type)
) PARTITION BY RANGE (odds_time);
```

**Design Rationale:**
- TimescaleDB partitioning: 1-hour chunks (optimized for high write volume from WebSocket)
- Degenerate dimensions (bookmaker, market_type): No separate dim table for MVP (single bookmaker)
- Future enhancement (Epic 11): Create dim_bookmaker if multiple bookmakers added
- Odds volatility derived: Calculate 5-min probability shifts for fact_moment integration

**Stories:** _High-level implementation captured at epic level_
1. Betfair WebSocket API + flumine framework integration
2. Create fact_betting_odds table schema (TimescaleDB hypertable)
3. Real-time odds → implied win probability calculation
4. Odds volatility calculation (5-min probability shifts)
5. Integration with fact_moment (populate odds_volatility measure)

---

### Epic 7: Time Mapping & Narrative Context

**Goal:** Convert timestamps to game-clock context.

**Value:** Moments show "10:00 1st Half" instead of UTC timestamps.

**Milestone:** Time mapping implemented with confidence scoring

**Stories:** _To be decomposed in Phase 2_

---

## Phase 3: Enhanced Dashboard (Week 2 - Full Features)

### Epic 8: Enhanced API + Dashboard

**Goal:** Transform basic dashboard into polished, feature-complete experience using dimensional queries.

**Value:** Interview-ready polished dashboard with full feature set. Demonstrates dimensional query patterns.

**Milestone:** Enhanced dashboard with excitement scores, sparklines, Reddit moments using dimensional model

**Dimensional Query Patterns:**

**1. Top 10 Exciting Games Today** (Primary Dashboard Query):
```sql
SELECT
  fg.game_key,
  fg.game_id,
  fg.game_status,
  fg.game_clock,
  ht.team_name AS home_team,
  ht.primary_color AS home_color,
  at.team_name AS away_team,
  at.primary_color AS away_color,
  fg.home_score,
  fg.away_score,
  latest_moment.excitement_score,
  dd.tournament_round
FROM fact_game fg
JOIN dim_team ht ON fg.home_team_key = ht.team_key AND ht.is_current = TRUE
JOIN dim_team at ON fg.away_team_key = at.team_key AND at.is_current = TRUE
JOIN dim_date dd ON fg.game_date_key = dd.date_key
LEFT JOIN LATERAL (
  SELECT excitement_score, reddit_velocity
  FROM fact_moment
  WHERE game_key = fg.game_key
  ORDER BY moment_time DESC
  LIMIT 1
) latest_moment ON TRUE
WHERE dd.full_date = CURRENT_DATE
ORDER BY latest_moment.excitement_score DESC NULLS LAST
LIMIT 10;
```

**2. Excitement Timeline (Sparkline Data)**:
```sql
SELECT
  time_bucket('5 minutes', moment_time) AS bucket,
  AVG(excitement_score) AS avg_excitement,
  MAX(reddit_velocity) AS peak_velocity
FROM fact_moment fm
JOIN fact_game fg ON fm.game_key = fg.game_key
WHERE fg.game_id = $1
  AND fm.moment_time >= NOW() - INTERVAL '4 hours'
GROUP BY bucket
ORDER BY bucket;
```

**3. Top Moments with Linked Reddit Posts**:
```sql
SELECT
  fm.moment_time,
  fm.excitement_score,
  fm.game_clock,
  erp.post_title,
  erp.post_url,
  erp.engagement_score
FROM fact_moment fm
JOIN fact_game fg ON fm.game_key = fg.game_key
LEFT JOIN event_reddit_post erp ON fm.source_reddit_post_key = erp.post_key
WHERE fg.game_id = $1
ORDER BY fm.excitement_score DESC
LIMIT 10;
```

**4. March Madness Tournament Round Analysis**:
```sql
SELECT
  dd.tournament_round,
  COUNT(*) AS num_games,
  AVG(fm.excitement_score) AS avg_excitement,
  MAX(fm.excitement_score) AS peak_excitement
FROM fact_game fg
JOIN dim_date dd ON fg.game_date_key = dd.date_key
JOIN fact_moment fm ON fg.game_key = fm.game_key
WHERE dd.tournament_round IS NOT NULL
  AND dd.year = 2025
GROUP BY dd.tournament_round
ORDER BY avg_excitement DESC;
```

**API Endpoints:**
- `GET /api/games/today` → Use query pattern #1
- `GET /api/games/{game_id}/timeline` → Use query pattern #2
- `GET /api/games/{game_id}/moments` → Use query pattern #3
- `GET /api/analysis/tournament-rounds` → Use query pattern #4 (new endpoint)

**Stories:** _High-level implementation captured at epic level_
1. Refactor GET /api/games/today to use dimensional queries (surrogate key JOINs)
2. Create GET /api/games/{id}/timeline endpoint (TimescaleDB time_bucket aggregation)
3. Create GET /api/games/{id}/moments endpoint (link to Reddit posts)
4. Add tournament round filter to dashboard (dim_date.tournament_round)
5. Implement sparkline charts with Recharts (time-series visualization)
6. Add top moments expandable sections (show Reddit post titles/links)
7. Mobile-responsive design with Chakra UI

---

## Phase 4: Quality & Documentation (Week 3)

### Epic 9: Testing & Quality Assurance

**Goal:** >70% test coverage, professional code quality.

**Value:** Demonstrates engineering rigor.

**Milestone:** Professional test coverage and code quality

**Stories:** _To be decomposed in Phase 4_

---

### Epic 10: Documentation & Polish

**Goal:** Complete portfolio artifact.

**Value:** Interview-ready documentation.

**Milestone:** Complete portfolio artifact ready for interviews

**Stories:** _To be decomposed in Phase 4_

---

### Epic 11: Advanced Dimensional Features (Post-MVP)

**Goal:** Implement advanced dimensional modeling patterns for portfolio polish.

**Value:** Demonstrates deep understanding of dimensional modeling beyond basics. SCD Type 2, advanced time dimensions, materialized aggregates.

**Milestone:** Production-ready dimensional enhancements with historical tracking and performance optimization

**Optional Features (Portfolio Polish):**

**1. SCD Type 2 for Conference Realignment**
- Track when teams change conferences (Texas/Oklahoma → SEC, USC/UCLA → Big Ten)
- Use `is_current`, `valid_from`, `valid_to` fields already in dim_team schema
- Generate historical conference lineups for past seasons

**Example SCD Type 2 Implementation:**
```sql
-- Texas moves to SEC in 2024
UPDATE dim_team
SET is_current = FALSE,
    valid_to = '2024-07-01'
WHERE team_id = 'ncaam_251'
  AND is_current = TRUE;

INSERT INTO dim_team (
  team_id, team_name, team_group_id, team_group_name,
  is_current, valid_from, valid_to,
  primary_color, secondary_color, aliases
)
VALUES (
  'ncaam_251', 'Texas', 'ncaam_sec', 'Southeastern Conference',
  TRUE, '2024-07-01', NULL,
  '#BF5700', '#FFFFFF', ARRAY['Texas', 'Longhorns', 'UT']
);

-- Query: "Which conference was Texas in during 2023 season?"
SELECT team_group_name
FROM dim_team
WHERE team_id = 'ncaam_251'
  AND '2023-12-01' BETWEEN valid_from AND COALESCE(valid_to, '9999-12-31');
-- Result: "Big 12 Conference"
```

**2. dim_time Table (Intraday Analysis)**
- Create time dimension for intraday analysis (00:00:00 to 23:59:59)
- Attributes: hour, minute, period_of_day ("Morning", "Afternoon", "Prime Time")
- Enable "when do exciting moments happen?" analysis (8pm ET = peak excitement)

**Table: dim_time**
```sql
dim_time (
  time_key INTEGER PRIMARY KEY,              -- 143000 = 14:30:00
  full_time TIME UNIQUE,
  hour INTEGER,                              -- 0-23
  minute INTEGER,                            -- 0-59
  period_of_day VARCHAR(20),                 -- "Morning", "Afternoon", "Evening", "Prime Time"
  is_prime_time BOOLEAN,                     -- 19:00-23:00 ET
  is_business_hours BOOLEAN                  -- 09:00-17:00 ET
)
```

**3. dim_tournament Table**
- NCAA tournament metadata: regions, seedings, bracket structure
- Link to fact_game via tournament_id
- Enable "tournament excitement trends" analysis

**Table: dim_tournament**
```sql
dim_tournament (
  tournament_key INTEGER PRIMARY KEY,
  tournament_id VARCHAR(50) UNIQUE,
  tournament_name VARCHAR(100),              -- "NCAA Men's Basketball Tournament"
  year INTEGER,
  region VARCHAR(50),                        -- "East", "West", "South", "Midwest"
  seed_line INTEGER,                         -- 1-16 (for team seeding)
  bracket_structure JSONB                    -- Full bracket metadata
)
```

**4. Pre-Aggregated Rollups (Performance Optimization)**
- Materialize common aggregations (daily excitement averages, conference rankings)
- Use TimescaleDB continuous aggregates for automatic maintenance

**Continuous Aggregate Example:**
```sql
CREATE MATERIALIZED VIEW daily_excitement_summary
WITH (timescaledb.continuous) AS
SELECT
  game_key,
  time_bucket('1 day', moment_time) AS day,
  AVG(excitement_score) AS avg_excitement,
  MAX(excitement_score) AS peak_excitement,
  COUNT(*) AS num_moments
FROM fact_moment
GROUP BY game_key, day;

-- Refresh policy (automatic maintenance)
SELECT add_continuous_aggregate_policy('daily_excitement_summary',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour');
```

**5. dim_bookmaker Table (Multi-Bookmaker Support)**
- If multiple bookmakers added beyond Betfair
- Normalize bookmaker attributes from fact_betting_odds degenerate dimension

**Table: dim_bookmaker**
```sql
dim_bookmaker (
  bookmaker_key INTEGER PRIMARY KEY,
  bookmaker_id VARCHAR(50) UNIQUE,
  bookmaker_name VARCHAR(100),
  country VARCHAR(50),
  is_active BOOLEAN
)
```

**Implementation Priority:**
| Feature | Priority | Estimated Effort | Value |
|---------|----------|------------------|-------|
| SCD Type 2 | High | 4-6 hours | Portfolio differentiation (advanced dimensional modeling) |
| dim_time | Medium | 3-4 hours | Enables intraday trend analysis |
| dim_tournament | Medium | 4-5 hours | Bracket analysis, seeding insights |
| Continuous Aggregates | Low | 3-4 hours | Performance optimization (data already small) |
| dim_bookmaker | Low | 2-3 hours | Only if multiple bookmakers added |

**Stories:** _To be decomposed post-MVP_
1. Implement SCD Type 2 logic for dim_team
2. Create dim_time table and seed 1,440 rows (minutes in a day)
3. Create dim_tournament table and integrate with fact_game
4. Implement TimescaleDB continuous aggregates for performance
5. Create dim_bookmaker (if multi-bookmaker support added)

---

## Implementation Status

**Phase 1 (Week 1):** Stories defined ✅
- Epic 1: 8 stories (Foundation + Infrastructure)
- Epic 2: 8 stories (**3 NEW** - Dimensional Foundation: 2-3a, 2-3b, 2-3c)
- Epic 3: **6 stories** (Basic API + Dashboard MVP) - **+1 NEW: Story 3.6 (1-Minute Refresh)**
- **Total: 22 stories for Week 1 working demo**

**Phase 2 (Week 2):** Epic-level schema designs complete ✅
- Epic 4: event_reddit_post schema defined
- Epic 5: **Story 5.1 defined** (fact_game_snapshot - Foundation story) + fact_moment schema defined (renamed from fact_excitement)
- Epic 6: fact_betting_odds schema defined
- Epic 7: Time mapping (TBD)
- Epic 8: Dimensional query patterns defined

**New Stories (Architecture-Driven):**
- ✅ **Story 3.6:** Increase Refresh Cadence to 1 Minute (Epic 3 extension - real-time feel)
- ✅ **Story 5.1:** Implement Historical Game Snapshots with TimescaleDB (Epic 5 foundation - MUST BE FIRST)

**Phase 3-4:** To be decomposed as Phase 2 nears completion

**Post-MVP:** Epic 11 (Advanced Dimensional Features) - Optional portfolio polish

---

_For detailed story specifications, see individual files in [docs/stories/](./stories/)_
