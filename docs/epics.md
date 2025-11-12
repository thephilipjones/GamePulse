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

---

## Phase 2: Data Pipeline Complexity (Week 2 - Add Intelligence)

### Epic 4: Reddit Social Sentiment (Batch)

**Goal:** Track Reddit posts from r/CollegeBasketball and match to games.

**Value:** Social signals available for excitement scoring. Demonstrates event stream data modeling patterns.

**Milestone:** Reddit posts matched to games with confidence scoring

**Schema Design:**
- `event_reddit_post` (event stream, NOT fact table - semi-structured social data)
- Grain: One row per Reddit post
- Partitioned by `post_time` (TimescaleDB hypertable, 1-day chunks)
- Optional FK to `fact_moment` (populated later via heuristic matching in Epic 5.7)

**Table: event_reddit_post**
```sql
event_reddit_post (
  post_key BIGSERIAL PRIMARY KEY,
  post_id VARCHAR(50) UNIQUE NOT NULL,            -- Reddit ID "abc123"
  game_key BIGINT REFERENCES fact_game(game_key),
  moment_key BIGINT,                              -- FK to fact_moment (Epic 5) - NULL if not linked
  post_time TIMESTAMP NOT NULL,
  post_date_key INTEGER REFERENCES dim_date(date_key),
  post_title TEXT,
  post_type VARCHAR(50),                          -- "game_thread", "highlight", "moment"
  post_url TEXT,
  author VARCHAR(100),
  upvotes INTEGER,
  num_comments INTEGER,
  num_awards INTEGER,
  engagement_score DECIMAL(10,2),                 -- upvotes + comments*0.5 + awards*2
  sentiment_score DECIMAL(5,2),                   -- VADER on title (-1 to +1)
  matched_teams TEXT[],                           -- ["Duke", "UNC"]
  match_confidence DECIMAL(3,2),                  -- 0-1 fuzzy match quality
  created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (post_time);
```

**Design Rationale:**
- `event_` prefix signals semi-structured event stream (not traditional fact table)
- Supports future expansion: JSONB fields, nested comment threads, media attachments
- Conceptually distinct from fact tables which measure repeatable business processes

**Stories:** _High-level implementation captured at epic level_
1. Reddit API OAuth authentication
2. Post fetching from r/CollegeBasketball (batch, 15-min polling, 100 QPM limit)
3. Create event_reddit_post table schema
4. Post-to-game matching algorithm (exact → fuzzy team names)
5. Game thread vs moment post classification
6. VADER sentiment analysis on post titles

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

**Stories:** _High-level implementation captured at epic level_
1. Create fact_moment table schema (TimescaleDB hypertable)
2. Reddit velocity calculation (posts/minute in 5-min window)
3. Engagement scoring aggregation (upvotes + comments*0.5 + awards*2.0)
4. Sentiment score integration (from Epic 4 VADER output)
5. Multi-factor excitement algorithm (weighted composite 0-100 scale)
6. Time-series storage and aggregation (TimescaleDB time_bucket)
7. **Link moments to Reddit posts** (heuristic: single high-engagement post within 5-min window → populate source_reddit_post_key)

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
- Epic 3: 5 stories (Basic API + Dashboard MVP)
- **Total: 21 stories for Week 1 working demo**

**Phase 2 (Week 2):** Epic-level schema designs complete ✅
- Epic 4: event_reddit_post schema defined
- Epic 5: fact_moment schema defined (renamed from fact_excitement)
- Epic 6: fact_betting_odds schema defined
- Epic 7: Time mapping (TBD)
- Epic 8: Dimensional query patterns defined

**Phase 3-4:** To be decomposed as Phase 2 nears completion

**Post-MVP:** Epic 11 (Advanced Dimensional Features) - Optional portfolio polish

---

_For detailed story specifications, see individual files in [docs/stories/](./stories/)_
