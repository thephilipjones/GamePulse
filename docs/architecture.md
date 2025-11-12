# Architecture

**Version Verification Date:** 2025-11-07
**All technology versions verified via WebSearch on November 7, 2025**

## Executive Summary

GamePulse is a data-first web application that combines real-time sports data streaming with batch sentiment analysis to surface the most exciting NCAA basketball games during peak season. The architecture prioritizes data pipeline reliability and time-series performance within AWS free-tier constraints, designed as a portfolio demonstration of modern data engineering patterns.

## Project Initialization

**First implementation story should execute:**

```bash
# Using copier (recommended - handles .env setup):
pipx run copier copy https://github.com/fastapi/full-stack-fastapi-template gamepulse --trust

# Or direct git clone:
git clone https://github.com/fastapi/full-stack-fastapi-template gamepulse
cd gamepulse
```

**This establishes the base architecture with these decisions:**

| Technology | Version | Provided By | Rationale |
|------------|---------|-------------|-----------|
| FastAPI | 0.114.2+ | Starter | Modern async Python framework, auto-generated API docs |
| React + TypeScript | 18.2+ | Starter | Type-safe frontend with modern hooks |
| Vite | Latest | Starter | Fast build tool with HMR |
| PostgreSQL | 12+ (16+ target) | Starter | Relational database with mature ecosystem |
| TimescaleDB | 2.23.0 | Manual Add | Time-series extension for Postgres |
| SQLModel | 0.0.21+ | Starter | Type-safe ORM for FastAPI + Postgres |
| Alembic | 1.12.1+ | Starter | Database migration management |
| uv | Latest | Starter | Modern Python dependency management (100x faster than Poetry) |
| Chakra UI | 3.8+ | Starter | React component library with dark mode |
| Docker Compose | 2.x | Starter | Local development orchestration |
| GitHub Actions | N/A | Starter | CI/CD pipeline |
| Traefik | 3.0+ | Starter | Reverse proxy for automatic HTTPS |

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| **Starter Template** | FastAPI Full-Stack Template | Latest (2025) | All Epics | Production-ready Docker setup, CI/CD pipeline, modern frontend tooling. Saves 8-10 hours in Week 1 vs manual setup. |
| **Database** | PostgreSQL + TimescaleDB | 16.x + 2.23.0 | Epic 2, 3, 4, 5, 6 | PostgreSQL for learning transferability (highly marketable skill). TimescaleDB extension adds time-series optimization. Trade-off: Slightly slower than QuestDB but negligible at GamePulse scale (60MB data). |
| **ORM** | SQLModel | 0.0.21+ | Epic 2, 4, 7 | Type-safe ORM, native FastAPI integration, automatic Pydantic validation. Keep starter template default. |
| **Migrations** | Alembic | 1.12.1+ | All Backend Epics | Standard migration tool for SQLAlchemy/SQLModel. Keep starter template default. |
| **Package Manager** | uv | Latest | All Backend Epics | Modern Python dependency management, 100x faster than Poetry. Template default as of 2025. |
| **Backend Framework** | FastAPI | 0.114.2+ | Epic 7 | Async/await support, automatic OpenAPI docs, high performance. Starter template default. |
| **Frontend Framework** | React + TypeScript + Vite | 18.2+ | Epic 8 | Modern React with type safety, fast builds with Vite. Starter template default. |
| **UI Components** | Chakra UI | 3.8+ | Epic 8 | Pre-built components, dark mode support, responsive design system. Faster than building custom Tailwind components. Keep starter template default. |
| **Deployment** | Docker Compose + AWS EC2 | 2.40.3 + t2.micro | Epic 1 | Starter provides production-ready Docker setup. Deploy to EC2 free tier. |
| **CI/CD** | GitHub Actions | N/A | Epic 1 | Pre-configured in starter template. Auto-deploy on push to main. |
| **Background Jobs** | APScheduler | 3.11.1 | Epic 2, 3, 4 | Lightweight in-process scheduler for polling jobs (15 min intervals). No Redis dependency. Can migrate to Celery + Redis for production scale if needed. |
| **Streaming Infrastructure** | flumine | 2.9.1 | Epic 5 | Purpose-built framework for Betfair WebSocket streaming. Handles auth, reconnection, event callbacks automatically. Saves 2-3 days vs building WebSocket client from scratch. |
| **Time-Series Config** | TimescaleDB Hypertables | 1-day chunks | Epic 4, 5 | Create hypertables for `excitement_scores` and `betting_odds` with 1-day chunk intervals. Compression deferred to Growth phase (data only ~60MB). |
| **HTTP Client** | httpx | 0.28.1 | Epic 2, 3 | Async HTTP client matching FastAPI async architecture. Modern replacement for requests with async/await support. |
| **Sentiment Analysis** | VADER (vaderSentiment) | 3.3.2 | Epic 4 | Rule-based sentiment for social media text. 339x faster than transformers, optimized for Reddit slang/caps/punctuation. Good-enough accuracy for excitement scoring. |
| **Chart Library** | Recharts | 3.3.0 | Epic 8 | React-native declarative charting. Simple API for sparkline timelines. 30-min implementation vs 2-3 days with D3. |
| **Retry Logic** | tenacity | 9.1.2 | Epic 2, 3, 5, 7 | Declarative retry with exponential backoff for external API failures. Graceful degradation per NFR-4.2. |
| **Frontend State** | React Query (TanStack Query) | 5.90.7 | Epic 8 | API data caching, auto-refresh, stale-while-revalidate. Already included in starter template. Perfect for 10-15 min polling. |
| **Logging** | structlog | 25.5.0 | All Backend Epics | Structured JSON logging for CloudWatch integration. Context binding, queryable logs. Matches NFR-4.3 requirement. |

## Project Structure

```
gamepulse/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── games.py           # GET /api/games/today, /api/games/{id}/timeline
│   │   │   │   ├── moments.py         # GET /api/games/{id}/moments
│   │   │   │   └── health.py          # GET /api/health
│   │   │   └── deps.py                # Database session dependencies
│   │   ├── core/
│   │   │   ├── config.py              # Settings, environment variables
│   │   │   ├── db.py                  # Database connection, SQLModel engine
│   │   │   └── security.py            # (Remove auth - not needed for MVP)
│   │   ├── models/
│   │   │   ├── team.py                # Team, Conference SQLModel schemas
│   │   │   ├── game.py                # Game SQLModel schema
│   │   │   ├── reddit.py              # RedditPost SQLModel schema
│   │   │   ├── excitement.py          # ExcitementScore SQLModel schema
│   │   │   └── betting.py             # BettingOdds SQLModel schema
│   │   ├── schemas/
│   │   │   ├── game.py                # Pydantic response models for API
│   │   │   └── health.py              # Health check response models
│   │   ├── services/
│   │   │   ├── ncaa_client.py         # NCAA API polling (batch)
│   │   │   ├── reddit_client.py       # Reddit API polling (batch)
│   │   │   ├── betfair_stream.py      # Betfair WebSocket streaming
│   │   │   ├── excitement_scorer.py   # Excitement algorithm
│   │   │   ├── time_mapper.py         # Wall-clock -> game-clock logic
│   │   │   └── matching.py            # Reddit post -> game matching
│   │   ├── workers/
│   │   │   ├── ncaa_poller.py         # Scheduled job: every 15 min
│   │   │   ├── reddit_poller.py       # Scheduled job: every 15 min
│   │   │   └── excitement_calculator.py # Scheduled job: every 15 min
│   │   ├── alembic/
│   │   │   ├── versions/              # Migration files
│   │   │   └── env.py
│   │   └── main.py                    # FastAPI app entry point
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── pyproject.toml                 # uv dependencies (pyproject.toml standard)
│   ├── Dockerfile                     # Multi-stage build
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── GameCard.tsx           # Game display with excitement badge
│   │   │   ├── ExcitementTimeline.tsx # Sparkline chart
│   │   │   ├── TopMoments.tsx         # Reddit posts list
│   │   │   └── LoadingSkeleton.tsx
│   │   ├── pages/
│   │   │   └── Dashboard.tsx          # Main page
│   │   ├── hooks/
│   │   │   ├── useGames.ts            # React Query for /api/games/today
│   │   │   └── usePolling.ts          # Auto-refresh every 10-15 min
│   │   ├── utils/
│   │   │   ├── api.ts                 # Axios client
│   │   │   └── formatters.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tests/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml                 # Local development orchestration
├── docker-compose.prod.yml            # Production deployment
├── .github/
│   └── workflows/
│       └── deploy.yml                 # CI/CD pipeline
└── README.md
```

## Epic to Architecture Mapping

| Epic | Architecture Components | Database Tables | External APIs | Dependencies |
|------|------------------------|-----------------|---------------|--------------|
| Epic 1: Foundation & Deployment | Docker Compose, AWS EC2, GitHub Actions, TimescaleDB setup | Initial schema | N/A | None |
| Epic 2: Game Data Ingestion | `services/ncaa_client.py`, `workers/ncaa_poller.py`, `models/team.py`, `models/game.py` | `teams`, `conferences`, `games` | NCAA API (henrygd/ncaa-api) | httpx, APScheduler, SQLModel |
| Epic 3: Reddit Social Sentiment | `services/reddit_client.py`, `services/matching.py`, `workers/reddit_poller.py`, `models/reddit.py` | `reddit_posts` | Reddit API (PRAW) | PRAW, httpx, APScheduler |
| Epic 4: Excitement Score Algorithm | `services/excitement_scorer.py`, `workers/excitement_calculator.py`, `models/excitement.py` | `excitement_scores` (hypertable) | N/A | vaderSentiment, APScheduler, reads from Epic 2/3/5 tables |
| Epic 5: Streaming Odds Integration | `services/betfair_stream.py`, `models/betting.py` | `betting_odds` (hypertable) | Betfair WebSocket API | flumine, structlog |
| Epic 6: Time Mapping & Context | `services/time_mapper.py` | Updates `reddit_posts` (game_time_context, estimated_game_clock) | N/A | Depends on Epic 2 (games) and Epic 3 (posts) |
| Epic 7: Backend API Development | `api/routes/games.py`, `api/routes/moments.py`, `api/routes/health.py`, `schemas/game.py`, `schemas/health.py` | All tables (read-only) | N/A | FastAPI, SQLModel, tenacity (for health checks) |
| Epic 8: Frontend Dashboard | `components/GameCard.tsx`, `components/ExcitementTimeline.tsx`, `components/TopMoments.tsx`, `hooks/useGames.ts`, `pages/Dashboard.tsx` | N/A | Backend API (Epic 7) | React Query, Recharts, Chakra UI |
| Epic 9: Testing & Quality | `tests/unit/`, `tests/integration/`, `tests/e2e/` | Test database | Mocked APIs | pytest, pytest-asyncio, httpx (test client) |
| Epic 10: Documentation & Polish | README.md, ADRs, OpenAPI docs | N/A | N/A | None |

**Module Boundaries:**

**Data Ingestion Layer** (Epic 2, 3, 5):
- Owns: External API clients, polling workers, streaming processes
- Writes to: Database tables (games, reddit_posts, betting_odds)
- No direct communication with API layer

**Processing Layer** (Epic 4, 6):
- Owns: Business logic (excitement scoring, time mapping)
- Reads from: Database tables
- Writes to: Database tables (excitement_scores, updates reddit_posts)
- No external API calls

**API Layer** (Epic 7):
- Owns: REST endpoints, Pydantic schemas
- Reads from: Database tables (joins across all tables)
- No writes to database (read-only)
- Serves: Frontend

**Frontend Layer** (Epic 8):
- Owns: React components, UI state management
- Communicates with: API layer only (no direct database access)
- No external API calls

**Integration Points:**

1. **Data Ingestion → Database:**
   - NCAA poller writes to `games` table every 15 min
   - Reddit poller writes to `reddit_posts` table every 15 min
   - Betfair stream writes to `betting_odds` table (real-time)
   - Connection: SQLModel async session

2. **Processing → Database:**
   - Excitement calculator reads `games`, `reddit_posts`, `betting_odds`
   - Writes to `excitement_scores` table every 15 min
   - Time mapper reads `games` and `reddit_posts`, updates `reddit_posts`
   - Connection: SQLModel async session

3. **API → Database:**
   - FastAPI endpoints read via SQLModel ORM
   - Complex queries use JOIN across tables
   - Connection pooling (5-10 connections)

4. **Frontend → API:**
   - React Query fetches JSON over HTTP
   - Polling every 10-15 min (configurable)
   - Auto-retry on failure with exponential backoff

5. **APScheduler → Workers:**
   - In-process scheduler triggers worker functions
   - Shares database connection pool with FastAPI
   - Runs in separate async tasks

6. **flumine → Database:**
   - Long-running WebSocket listener
   - Writes odds updates to `betting_odds` table
   - Independent process from API/workers

## Technology Stack Details

### Core Technologies

**Backend Stack:**
- **FastAPI 0.115+**: Async Python web framework
  - Automatic OpenAPI/Swagger documentation
  - Pydantic validation
  - High performance (comparable to Node.js)
  - Native async/await support

- **PostgreSQL 16 + TimescaleDB**: Relational database with time-series optimization
  - TimescaleDB creates hypertables for `excitement_scores` and `betting_odds`
  - Automatic data partitioning by time
  - Optimized aggregation queries (e.g., sparkline data)

- **SQLModel**: Type-safe ORM
  - Combines SQLAlchemy + Pydantic
  - Automatic API response validation
  - IDE autocomplete for database queries

- **Alembic**: Database migrations
  - Version-controlled schema changes
  - Automatic migration generation from model changes

**Frontend Stack:**
- **React 18 + TypeScript**: Type-safe component library
- **Vite**: Fast build tool with hot module replacement (HMR)
- **Chakra UI**: Component library with dark mode support
- **React Query**: Server state management, automatic caching, polling
- **Recharts**: Sparkline chart library for excitement timelines

**Data Pipeline:**
- **NCAA API Client** (henrygd/ncaa-api): Batch polling every 15 min
- **PRAW** (Python Reddit API Wrapper): Batch polling every 15 min (100 QPM limit)
- **flumine + Betfair API**: Real-time WebSocket streaming for betting odds
- **VADER Sentiment**: Lightweight sentiment analysis (339x faster than transformers)

**DevOps:**
- **Docker + Docker Compose**: Containerization and orchestration
- **GitHub Actions**: CI/CD pipeline (lint, test, build, deploy)
- **AWS EC2 t2.micro**: Free tier deployment target
- **Traefik**: Reverse proxy for automatic HTTPS

### Integration Points

**Data Flow Architecture:**

```
External Sources → Data Ingestion → Database → API → Frontend
```

**1. Data Ingestion Layer:**
- **Batch Sources** (Scheduled workers):
  - NCAA API → `ncaa_poller.py` (every 15 min) → `games` table
  - Reddit API → `reddit_poller.py` (every 15 min) → `reddit_posts` table

- **Streaming Source** (Long-running process):
  - Betfair WebSocket → `betfair_stream.py` (real-time) → `betting_odds` table

**2. Processing Layer:**
- **Excitement Calculator** (Scheduled worker):
  - Reads: `games`, `reddit_posts`, `betting_odds`
  - Calculates: Multi-factor excitement score
  - Writes: `excitement_scores` table (every 15 min)

**3. API Layer:**
- **FastAPI REST endpoints**:
  - `GET /api/games/today` → Queries `games` + `excitement_scores` (JOIN)
  - `GET /api/games/{id}/moments` → Queries `reddit_posts` (filtered by game_id)
  - `GET /api/games/{id}/timeline` → Queries `excitement_scores` (time-series)
  - `GET /api/health` → System status check

**4. Frontend Layer:**
- **React dashboard**:
  - React Query fetches `/api/games/today` every 10-15 min (polling)
  - Displays game cards with Chakra UI components
  - Recharts renders sparkline excitement timelines

**Communication Protocols:**
- Backend ↔ Frontend: REST API over HTTP/HTTPS (JSON)
- Backend ↔ PostgreSQL: SQLModel ORM (connection pooling)
- Backend ↔ External APIs: HTTP polling (NCAA, Reddit) + WebSocket (Betfair)

## Data Modeling Approach

### Overview: Hybrid Dimensional + Time-Series Architecture

GamePulse employs a **modern dimensional modeling approach** combining Kimball star schema patterns with TimescaleDB time-series optimization. This design demonstrates portfolio-ready data warehouse patterns while maintaining pragmatic simplicity for a 60MB dataset.

**Architecture Philosophy:**
- **Dimensional core** (Kimball star schema): dim_team, dim_date, fact_game
- **Time-series facts** (TimescaleDB hypertables): fact_moment, fact_betting_odds
- **Event streams** (semi-structured): event_reddit_post
- **SCD Type 2 readiness**: Future-proof for historical tracking

### Dimensional Schema Design

**1. Dimensions (Slowly Changing Dimensions)**

**dim_team** (Surrogate Key: team_key)
```sql
dim_team (
  team_key INTEGER PRIMARY KEY,              -- Surrogate key (SERIAL, auto-increment)
  team_id VARCHAR(50) UNIQUE NOT NULL,       -- Natural key "ncaam_150"
  sport VARCHAR(20) NOT NULL,                -- "ncaam", "nfl", "nba" (multi-sport)
  team_name VARCHAR(100),
  team_abbr VARCHAR(10),

  -- Flattened team_group (denormalized for query performance)
  team_group_id VARCHAR(50),                 -- "ncaam_acc", "nfl_nfc_east"
  team_group_name VARCHAR(100),              -- "Atlantic Coast Conference"

  -- UI metadata
  primary_color CHAR(7),                     -- Hex color for UI accents
  secondary_color CHAR(7),
  aliases TEXT[],                            -- For Reddit fuzzy matching

  -- SCD Type 2 fields (for future conference realignment tracking)
  is_current BOOLEAN DEFAULT TRUE,
  valid_from TIMESTAMP DEFAULT NOW(),
  valid_to TIMESTAMP DEFAULT NULL,           -- NULL = current version

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

**Design Rationale:**
- **Surrogate key (team_key)**: Enables SCD Type 2 - multiple versions of same team (e.g., Texas in Big 12 vs SEC)
- **Natural key preserved (team_id)**: API integration, external references
- **Flattened team_group**: Only 6 conferences, minimal attributes → no separate dim_conference table (avoids JOIN overhead)
- **Generic naming (team_group)**: Not "conference" - supports NFL divisions, NBA conferences
- **SCD Type 2 ready**: Conference realignment (Texas→SEC, USC→Big Ten) trackable without schema changes

**dim_date** (Surrogate Key: date_key)
```sql
dim_date (
  date_key INTEGER PRIMARY KEY,              -- YYYYMMDD format (20250311)
  full_date DATE UNIQUE NOT NULL,

  -- Standard Kimball attributes
  day_of_week INTEGER,                       -- 1-7 (Monday=1, Sunday=7)
  day_name VARCHAR(10),                      -- "Monday", "Tuesday"
  day_of_month INTEGER,                      -- 1-31
  month INTEGER,                             -- 1-12
  month_name VARCHAR(10),                    -- "January", "February"
  quarter INTEGER,                           -- 1-4
  year INTEGER,                              -- 2024, 2025, 2026
  is_weekend BOOLEAN,

  -- Domain-specific NCAA attributes
  is_march_madness BOOLEAN,                  -- Mid-March to early April
  tournament_round VARCHAR(50)               -- "Sweet 16", "Elite 8", etc.
)
```

**Design Rationale:**
- **Integer surrogate key (YYYYMMDD)**: Faster JOINs than DATE type, human-readable
- **Domain-specific attributes**: March Madness analysis, tournament round filtering
- **Pre-computed**: No EXTRACT() calls in queries - attributes pre-calculated at seed time
- **Seeded 2024-2026**: 1,095 rows, negligible storage, massive query simplification

**2. Fact Tables (Measures + Foreign Keys)**

**fact_game** (Operational Fact - Grain: One game occurrence)
```sql
fact_game (
  game_key BIGSERIAL PRIMARY KEY,            -- Surrogate key
  game_id VARCHAR(50) UNIQUE NOT NULL,       -- Natural key "ncaam_12345"

  -- Dimension foreign keys (surrogate keys, not natural keys)
  game_date_key INTEGER REFERENCES dim_date(date_key),
  home_team_key INTEGER REFERENCES dim_team(team_key),
  away_team_key INTEGER REFERENCES dim_team(team_key),

  -- Degenerate dimensions (no separate dim table)
  sport VARCHAR(20),
  game_status VARCHAR(20),                   -- "scheduled", "live", "final"
  game_type VARCHAR(50),                     -- "regular_season", "tournament"
  venue VARCHAR(200),
  broadcast_network VARCHAR(50),
  game_clock VARCHAR(50),

  -- Measures (numeric facts)
  home_score INTEGER,
  away_score INTEGER,
  attendance INTEGER,
  rivalry_factor DECIMAL(3,2),               -- Cached denormalization (1.0-1.5)

  -- Timestamps (context, not measures)
  game_date DATE NOT NULL,
  game_start_time TIMESTAMP,
  game_end_time TIMESTAMP,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)
```

**Design Rationale:**
- **Surrogate key**: Enables future expansion (same game played multiple times in tournament scenarios)
- **Degenerate dimensions**: sport, game_status, venue - low cardinality, no separate dim table
- **Cached rivalry_factor**: Denormalized from team_group match - query performance optimization
- **Indexes on**: game_date, game_status, sport, game_type (hot path queries)

**fact_moment** (Time-Series Fact - Grain: One measurement per game per time interval)
```sql
fact_moment (
  moment_key BIGSERIAL,
  game_key BIGINT REFERENCES fact_game(game_key),
  moment_time TIMESTAMP NOT NULL,
  moment_date_key INTEGER REFERENCES dim_date(date_key),

  -- Measures (excitement components)
  excitement_score DECIMAL(5,2),             -- 0-100 composite
  reddit_velocity DECIMAL(8,2),              -- posts/minute
  reddit_engagement INTEGER,                 -- upvotes + comments*0.5 + awards*2
  sentiment_score DECIMAL(5,2),              -- -1 to +1 (VADER)
  odds_volatility DECIMAL(8,4),              -- probability shift

  -- Context
  game_clock VARCHAR(20),                    -- "2:34 2nd Half"
  period VARCHAR(10),                        -- "1st", "2nd", "OT"

  -- Optional link to triggering Reddit post
  source_reddit_post_key BIGINT REFERENCES event_reddit_post(post_key),

  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (game_key, moment_time)
) PARTITION BY RANGE (moment_time);
```

**TimescaleDB Hypertable Configuration:**
```sql
SELECT create_hypertable('fact_moment', 'moment_time', chunk_time_interval => INTERVAL '1 day');
```

**Design Rationale:**
- **Grain precision**: One row per measurement snapshot (15 min during batch, potentially real-time later)
- **TimescaleDB partitioning**: 1-day chunks (low write volume, batch polling)
- **Optional FK to event_reddit_post**: Links moments to specific triggering posts (heuristic matching)
- **Query optimization**: TimescaleDB time_bucket for sparkline aggregations

**fact_betting_odds** (High-Velocity Time-Series Fact - Grain: One odds snapshot per game per time per bookmaker)
```sql
fact_betting_odds (
  odds_key BIGSERIAL,
  game_key BIGINT REFERENCES fact_game(game_key),
  odds_time TIMESTAMP NOT NULL,
  odds_date_key INTEGER REFERENCES dim_date(date_key),

  -- Measures
  home_odds DECIMAL(10,4),                   -- Decimal odds (1.85)
  away_odds DECIMAL(10,4),
  home_implied_prob DECIMAL(5,4),            -- 1 / home_odds
  away_implied_prob DECIMAL(5,4),
  market_margin DECIMAL(5,4),                -- Overround/vig

  -- Degenerate dimensions (MVP - single bookmaker)
  bookmaker VARCHAR(50),                     -- "Betfair"
  market_type VARCHAR(50),                   -- "moneyline"

  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (game_key, odds_time, bookmaker, market_type)
) PARTITION BY RANGE (odds_time);
```

**TimescaleDB Hypertable Configuration:**
```sql
SELECT create_hypertable('fact_betting_odds', 'odds_time', chunk_time_interval => INTERVAL '1 hour');
```

**Design Rationale:**
- **Partitioning strategy**: 1-hour chunks (high write volume from WebSocket streaming)
- **Degenerate dimensions**: bookmaker, market_type - no separate dim_bookmaker for MVP (single bookmaker)
- **Future normalization**: Epic 11 - create dim_bookmaker if multiple bookmakers added

**3. Event Tables (Semi-Structured Event Streams)**

**event_reddit_post** (Event Stream - NOT a traditional fact table)
```sql
event_reddit_post (
  post_key BIGSERIAL PRIMARY KEY,
  post_id VARCHAR(50) UNIQUE NOT NULL,       -- Reddit ID "abc123"
  game_key BIGINT REFERENCES fact_game(game_key),
  moment_key BIGINT,                         -- FK to fact_moment (nullable, populated via heuristic)
  post_time TIMESTAMP NOT NULL,
  post_date_key INTEGER REFERENCES dim_date(date_key),

  -- Event attributes
  post_title TEXT,
  post_type VARCHAR(50),                     -- "game_thread", "highlight", "moment"
  post_url TEXT,
  author VARCHAR(100),

  -- Measures (for aggregation)
  upvotes INTEGER,
  num_comments INTEGER,
  num_awards INTEGER,
  engagement_score DECIMAL(10,2),            -- Calculated measure
  sentiment_score DECIMAL(5,2),              -- VADER on title

  -- Matching metadata
  matched_teams TEXT[],                      -- ["Duke", "UNC"]
  match_confidence DECIMAL(3,2),             -- 0-1 fuzzy match quality

  created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (post_time);
```

**Design Rationale:**
- **event_ prefix**: Signals semi-structured event stream, NOT traditional fact table
- **Conceptual distinction**: Events that happened vs measurements of business processes
- **Future expansion**: JSONB fields, nested comment threads, media attachments
- **Query patterns**: Full-text search, JSONB queries - different from fact table aggregations

### Why Kimball Dimensional Modeling?

**Portfolio Value:**
- Demonstrates understanding of industry-standard dimensional modeling methodology
- Shows ability to make pragmatic trade-offs (when to normalize vs denormalize)
- SCD Type 2 readiness proves forward-thinking design

**Query Performance Benefits:**
1. **Pre-computed attributes**: dim_date.is_march_madness, dim_date.tournament_round (no EXTRACT() in queries)
2. **Strategic denormalization**: team_group flattened into dim_team (6 groups, avoids JOIN)
3. **Surrogate key JOINs**: Integer comparison faster than VARCHAR natural keys
4. **TimescaleDB optimization**: time_bucket aggregations on partitioned data

**Example: Dimensional Query Pattern**
```sql
-- Top 10 Exciting Games Today (Primary Dashboard Query)
SELECT
  fg.game_key,
  fg.game_id,
  fg.game_status,
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

**Query Benefits:**
- Surrogate key JOINs (team_key, date_key) - faster than natural keys
- SCD Type 2 filter (is_current = TRUE) - gets current team version
- Pre-computed tournament_round - no date extraction logic
- TimescaleDB lateral JOIN - efficient latest moment lookup

### When NOT to Use Dimensional Modeling

**Reddit Posts → event_reddit_post (event stream)**
- Semi-structured social data with variable attributes
- May need JSONB fields, nested structures
- Query patterns: full-text search, not traditional aggregations
- Use event_ prefix to signal conceptual difference

**Operational Tables → fact_game (hybrid approach)**
- Updated frequently during live games (score changes, status transitions)
- Supports both OLTP (real-time updates) and OLAP (analytical queries)
- Compromise: operational fact table with dimensional FK relationships

### SCD Type 2 Strategy (Epic 11 - Post-MVP)

**Use Case: Conference Realignment Tracking**

Example: Texas moves from Big 12 to SEC in 2024

**Current State (Big 12):**
```sql
team_key: 42
team_id: "ncaam_251"
team_name: "Texas"
team_group_id: "ncaam_b12"
team_group_name: "Big 12 Conference"
is_current: TRUE
valid_from: 2020-01-01
valid_to: NULL
```

**After Conference Change:**
```sql
-- Old version (expire)
UPDATE dim_team
SET is_current = FALSE, valid_to = '2024-07-01'
WHERE team_key = 42;

-- New version (insert)
INSERT INTO dim_team (
  team_id, team_name, team_group_id, team_group_name,
  is_current, valid_from, valid_to, ...
)
VALUES (
  'ncaam_251', 'Texas', 'ncaam_sec', 'Southeastern Conference',
  TRUE, '2024-07-01', NULL, ...
);
```

**Historical Query:**
```sql
-- "Which conference was Texas in during 2023 season?"
SELECT team_group_name
FROM dim_team
WHERE team_id = 'ncaam_251'
  AND '2023-12-01' BETWEEN valid_from AND COALESCE(valid_to, '9999-12-31');
-- Result: "Big 12 Conference"
```

**Benefits:**
- Historical accuracy preserved (games played in Big 12 vs SEC)
- No cascade updates to fact tables
- Temporal queries: "Show all SEC teams for 2024 season"

### TimescaleDB Partitioning Strategy

**fact_moment: 1-day chunks**
- Write volume: Low (batch polling every 15 min = ~100 writes/day per game)
- Query pattern: Recent data (last 4 hours for sparklines)
- Retention: Keep all data (60MB total for full season)

**fact_betting_odds: 1-hour chunks**
- Write volume: High (WebSocket streaming = ~100 ticks per game)
- Query pattern: Recent volatility calculations (5-min windows)
- Retention: Keep all data for MVP, compress older data in Epic 11

**Compression (Deferred to Epic 11):**
```sql
-- Compress data older than 7 days
ALTER TABLE fact_moment SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'game_key'
);

SELECT add_compression_policy('fact_moment', INTERVAL '7 days');
```

### Schema Evolution Pattern

**Phase 1 (Epic 2): Normalized → Dimensional Refactor**
- Story 2-3a: Add surrogate keys, flatten team_groups, add SCD Type 2 fields
- Migration preserves all data, no downtime

**Phase 2 (Epic 4-6): Add Time-Series Facts**
- Create fact_moment, fact_betting_odds as hypertables
- Partitioning strategy optimized per write volume

**Phase 3 (Epic 11): Advanced Features**
- Implement SCD Type 2 logic for conference changes
- Add dim_time, dim_tournament
- Create continuous aggregates for performance

### Interview Talking Points

**"Why hybrid dimensional + time-series?"**
> "GamePulse has dual requirements: operational queries for the real-time dashboard (which game is exciting RIGHT NOW) and analytical queries for trending analysis (which teams generated the most excitement this tournament). Pure Kimball would over-engineer the operational queries, but pure normalized OLTP would make the time-series analysis inefficient. I used TimescaleDB hypertables for high-velocity measurements while keeping a dimensional core for slicing by team, conference, and time."

**"Why flatten team_group instead of separate dim_conference table?"**
> "With only 6 major conferences and minimal attributes (just name and type), normalizing to a separate dim_conference table adds JOIN overhead without providing value. However, I kept the team_group_id for potential future expansion - if we add NFL with 8 divisions and complex hierarchies, we can denormalize to a proper dimension table with SCD Type 2 without changing the fact tables. It's pragmatic dimensional modeling - Kimball patterns where they add value, denormalization where they don't."

**"Why event_ prefix for Reddit data?"**
> "Reddit posts are semi-structured events with JSONB-friendly attributes, not traditional business process measurements. The schema signals this is an event stream that might evolve to include nested comment threads, media attachments, or real-time CDC from Reddit's API. It's conceptually distinct from fact tables which measure repeatable business processes. This naming convention makes the architectural intent clear to future developers."

---

## Implementation Patterns

### Naming Conventions

**Database:**
- Table names: Lowercase, plural (e.g., `games`, `reddit_posts`, `excitement_scores`)
- Column names: Snake_case (e.g., `game_id`, `home_score`, `created_at`)
- Foreign keys: `{table}_id` format (e.g., `team_id`, `game_id`)

**Backend (Python):**
- Files: Snake_case (e.g., `excitement_scorer.py`, `ncaa_client.py`)
- Classes: PascalCase (e.g., `ExcitementScore`, `RedditClient`)
- Functions: Snake_case (e.g., `calculate_excitement()`, `match_post_to_game()`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_GAMES`, `POLLING_INTERVAL`)

**Frontend (TypeScript/React):**
- Components: PascalCase (e.g., `GameCard.tsx`, `ExcitementTimeline.tsx`)
- Hooks: camelCase with `use` prefix (e.g., `useGames.ts`, `usePolling.ts`)
- Utilities: camelCase (e.g., `formatTimestamp()`, `getTeamColor()`)
- Files: Match component/hook name (e.g., `GameCard.tsx` exports `GameCard`)

**API Endpoints:**
- REST pattern: `/api/{resource}/{id?}/{action?}`
- Examples: `/api/games/today`, `/api/games/{game_id}/moments`
- Lowercase with hyphens for multi-word (e.g., `/api/game-threads`)

### Code Organization

**Backend Organization:**
- **models/**: SQLModel database schemas (one file per domain entity)
- **schemas/**: Pydantic API response models (separate from DB models)
- **api/routes/**: FastAPI endpoint definitions (one file per resource)
- **services/**: Business logic, external API clients (reusable functions)
- **workers/**: Scheduled background jobs (polling, calculations)
- **core/**: Cross-cutting concerns (config, database, security)

**Frontend Organization:**
- **components/**: Reusable UI components (one file per component)
- **pages/**: Top-level page components (match routes)
- **hooks/**: Custom React hooks for data fetching, state
- **utils/**: Pure utility functions (formatting, validation)

**Test Organization:**
- **tests/unit/**: Pure function tests (excitement calculation, matching logic)
- **tests/integration/**: API endpoint tests with mocked database
- **tests/e2e/**: Full pipeline tests with test database

### Error Handling

**Backend Error Strategy:**

**Retry Logic (External APIs):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60)
)
async def fetch_ncaa_games():
    # Retries 3 times with exponential backoff: 2s, 4s, 8s
    response = await ncaa_client.get_games()
    return response
```

**Graceful Degradation:**
- NCAA API down → Serve cached game data, show stale data warning
- Reddit API down → Show games without social sentiment data
- Betfair stream disconnects → Auto-reconnect, continue with last known odds
- Database unreachable → Return HTTP 503 with error message

**Error Response Format:**
```json
{
  "detail": "NCAA API temporarily unavailable",
  "error_code": "EXTERNAL_API_ERROR",
  "retry_after": 60
}
```

**Frontend Error Handling:**
- API failures → Show cached data + yellow banner "Last updated X min ago"
- Network errors → Display offline indicator, retry automatically
- No games today → Show empty state "No games scheduled"

### Date/Time Handling

**Timezone Convention:**
```python
from datetime import datetime, timezone

# ALWAYS use UTC internally
utc_now = datetime.now(timezone.utc)

# Store as TIMESTAMPTZ in PostgreSQL (preserves timezone)
# API responses: ISO 8601 format
api_timestamp = utc_now.isoformat()  # "2025-11-07T20:00:00+00:00"
```

**Wall-Clock → Game-Clock Mapping:**
- Input: Reddit post timestamp (UTC), game start time (UTC)
- Processing: Calculate elapsed time, account for halftime
- Output: Estimated game clock ("10:00 1st Half"), confidence score
- Location: `services/time_mapper.py`

**Rule**: All timestamps stored as UTC, converted only for display.

### API Response Format

**Success Response:**
```json
{
  "games": [...],
  "updated_at": "2025-11-07T20:00:00Z"
}
```

**Error Response:**
```json
{
  "detail": "NCAA API temporarily unavailable",
  "error_code": "EXTERNAL_API_ERROR",
  "retry_after": 60
}
```

**Pydantic Schema Enforcement:**
```python
from pydantic import BaseModel
from datetime import datetime

class GamesResponse(BaseModel):
    games: List[GameSchema]
    updated_at: datetime
```

### Testing Strategy

**Test Organization:**
- `tests/unit/`: Pure functions (excitement calculation, matching, time mapping)
- `tests/integration/`: API endpoints with mocked database
- `tests/e2e/`: Full pipeline with test database

**Coverage Target**: >70% for core logic

**pytest Fixtures:**
- Database sessions (test DB)
- Mocked external APIs (NCAA, Reddit, Betfair)
- Sample game data for testing

### Logging Strategy

**Structured Logging (JSON format):**
```python
import logging
import structlog

logger = structlog.get_logger()

# Example log output:
logger.info(
    "excitement_score_calculated",
    game_id="401234567",
    score=94.5,
    reddit_velocity=12.3,
    sentiment=0.82,
    duration_ms=45
)
```

**Log Levels:**
- **DEBUG**: Detailed diagnostic info (local development only)
- **INFO**: General operational events (API requests, job completions)
- **WARNING**: Degraded performance, retries, stale data served
- **ERROR**: API failures, exceptions, data quality issues

**Log Destinations:**
- Local dev: stdout (colored, human-readable)
- Production: stdout → Docker logs → CloudWatch Logs (JSON)

**Key Metrics Logged:**
- API response times (middleware logs all requests)
- Polling job completion (games fetched, posts matched, scores calculated)
- External API failures (NCAA, Reddit, Betfair errors)
- Data quality metrics (match confidence, missing data)

## Data Architecture

### Database Schema (PostgreSQL + TimescaleDB)

**Dimensional Tables:**

```sql
-- Teams (slow-changing dimension)
CREATE TABLE teams (
    team_id VARCHAR PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    team_abbr VARCHAR,
    conference_id VARCHAR,
    primary_color VARCHAR,
    aliases TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conferences
CREATE TABLE conferences (
    conference_id VARCHAR PRIMARY KEY,
    conference_name VARCHAR NOT NULL,
    sport VARCHAR DEFAULT 'NCAA_MBB',
    rivalry_factor FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Fact Tables (High-Frequency):**

```sql
-- Games (updated every 15 min during live games)
CREATE TABLE games (
    game_id VARCHAR PRIMARY KEY,
    game_date TIMESTAMPTZ NOT NULL,
    home_team_id VARCHAR REFERENCES teams(team_id),
    away_team_id VARCHAR REFERENCES teams(team_id),
    home_score INT,
    away_score INT,
    game_status VARCHAR,  -- scheduled, live, halftime, final
    game_clock VARCHAR,   -- "2:34 2nd Half"
    game_start_time TIMESTAMPTZ,
    game_end_time TIMESTAMPTZ,
    venue VARCHAR,
    is_rivalry BOOLEAN,
    is_tournament BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reddit posts (batch ingested every 15 min)
CREATE TABLE reddit_posts (
    post_id VARCHAR PRIMARY KEY,
    game_id VARCHAR REFERENCES games(game_id),
    post_type VARCHAR,  -- game_thread, moment, pre_game, post_game
    title TEXT NOT NULL,
    author VARCHAR,
    upvotes INT,
    comments_count INT,
    awards_count INT,
    post_time TIMESTAMPTZ NOT NULL,
    game_time_context VARCHAR,
    estimated_game_clock VARCHAR,
    time_mapping_confidence FLOAT,
    url TEXT,
    match_method VARCHAR,
    match_confidence FLOAT,
    is_game_thread BOOLEAN DEFAULT FALSE,
    engagement_score FLOAT,
    sentiment_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Excitement scores (time-series hypertable)
CREATE TABLE excitement_scores (
    game_id VARCHAR NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    score FLOAT NOT NULL,
    reddit_velocity FLOAT,
    reddit_engagement INT,
    sentiment_score FLOAT,
    odds_volatility FLOAT,
    game_context_factor FLOAT,
    rivalry_bonus FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('excitement_scores', 'timestamp');

-- Betting odds (streaming, time-series hypertable)
CREATE TABLE betting_odds (
    game_id VARCHAR NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    market_type VARCHAR,  -- moneyline, spread, total
    home_odds FLOAT,
    away_odds FLOAT,
    implied_home_prob FLOAT,
    implied_away_prob FLOAT,
    volume INT,
    odds_shift_5min FLOAT,
    odds_volatility_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('betting_odds', 'timestamp');
```

**Indexes for Performance:**

```sql
-- Games lookup by date
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_status ON games(game_status);

-- Reddit posts by game and time
CREATE INDEX idx_reddit_posts_game ON reddit_posts(game_id, post_time);
CREATE INDEX idx_reddit_posts_engagement ON reddit_posts(engagement_score DESC);

-- Excitement scores time-series queries (TimescaleDB auto-creates on timestamp)
CREATE INDEX idx_excitement_game ON excitement_scores(game_id, timestamp DESC);

-- Betting odds time-series queries
CREATE INDEX idx_betting_odds_game ON betting_odds(game_id, timestamp DESC);
```

### Data Relationships

**Primary Relationships:**
- `games.home_team_id` → `teams.team_id` (Many-to-One)
- `games.away_team_id` → `teams.team_id` (Many-to-One)
- `reddit_posts.game_id` → `games.game_id` (Many-to-One)
- `excitement_scores.game_id` → `games.game_id` (Many-to-One, time-series)
- `betting_odds.game_id` → `games.game_id` (Many-to-One, time-series)

**Key Queries:**

**Dashboard "Games Today" Query:**
```sql
SELECT
    g.*,
    ht.team_name AS home_team_name,
    ht.primary_color AS home_color,
    at.team_name AS away_team_name,
    at.primary_color AS away_color,
    e.score AS excitement_score,
    e.timestamp AS excitement_updated_at
FROM games g
JOIN teams ht ON g.home_team_id = ht.team_id
JOIN teams at ON g.away_team_id = at.team_id
LEFT JOIN LATERAL (
    SELECT score, timestamp
    FROM excitement_scores
    WHERE game_id = g.game_id
    ORDER BY timestamp DESC
    LIMIT 1
) e ON TRUE
WHERE g.game_date >= CURRENT_DATE
  AND g.game_date < CURRENT_DATE + INTERVAL '1 day'
ORDER BY e.score DESC NULLS LAST
LIMIT 10;
```

**Sparkline Timeline Query:**
```sql
SELECT timestamp, score
FROM excitement_scores
WHERE game_id = $1
  AND timestamp >= NOW() - INTERVAL '4 hours'
ORDER BY timestamp ASC;
```

**Top Moments Query:**
```sql
SELECT *
FROM reddit_posts
WHERE game_id = $1
  AND post_type IN ('moment', 'game_thread')
ORDER BY engagement_score DESC
LIMIT 10;
```

## API Contracts

### REST API Specification

**Base URL:** `http://localhost:8000/api` (dev), `https://gamepulse.example.com/api` (prod)

**Endpoints:**

**1. GET /api/games/today**

Fetch today's games with excitement scores.

**Query Parameters:**
- `limit` (optional, default=10): Max games to return
- `sort` (optional, default=excitement_desc): Sort order

**Response:**
```json
{
  "games": [
    {
      "game_id": "401234567",
      "home_team": {
        "id": "du",
        "name": "Duke",
        "color": "#003087"
      },
      "away_team": {
        "id": "unc",
        "name": "UNC",
        "color": "#7BAFD4"
      },
      "home_score": 78,
      "away_score": 81,
      "status": "final",
      "game_clock": null,
      "excitement_score": 94.5,
      "is_rivalry": true,
      "excitement_trend": [
        {"timestamp": "2025-11-07T19:00:00Z", "score": 45},
        {"timestamp": "2025-11-07T19:15:00Z", "score": 58},
        {"timestamp": "2025-11-07T19:30:00Z", "score": 72}
      ]
    }
  ],
  "updated_at": "2025-11-07T20:00:00Z"
}
```

**2. GET /api/games/{game_id}/moments**

Fetch top Reddit posts for a game.

**Query Parameters:**
- `type` (optional): Filter by post_type (all | moment | game_thread)

**Response:**
```json
{
  "game_id": "401234567",
  "game_thread": {
    "post_id": "xyz",
    "title": "[Game Thread] Duke vs UNC",
    "url": "https://reddit.com/r/CollegeBasketball/...",
    "comments_count": 1247
  },
  "moments": [
    {
      "post_id": "abc123",
      "title": "Duke opens with 12-0 run, crowd silenced",
      "upvotes": 342,
      "comments_count": 87,
      "game_time_context": "1st_half",
      "estimated_game_clock": "10:00 1st Half",
      "time_mapping_confidence": 0.85,
      "url": "https://reddit.com/..."
    }
  ]
}
```

**3. GET /api/games/{game_id}/timeline**

Fetch excitement score time-series for sparkline chart.

**Response:**
```json
{
  "game_id": "401234567",
  "timeline": [
    {"timestamp": "2025-11-07T19:00:00Z", "score": 45},
    {"timestamp": "2025-11-07T19:15:00Z", "score": 58}
  ]
}
```

**4. GET /api/health**

System health check.

**Response:**
```json
{
  "status": "healthy",
  "last_update": "2025-11-07T20:00:00Z",
  "sources": {
    "ncaa_api": {
      "status": "ok",
      "last_poll": "2025-11-07T19:58:00Z",
      "games_tracked": 8
    },
    "reddit_api": {
      "status": "ok",
      "rate_limit_remaining": 87,
      "posts_ingested": 342
    },
    "betfair": {
      "status": "connected",
      "lag_ms": 150
    }
  },
  "database": {
    "status": "ok",
    "row_counts": {
      "games": 5000,
      "reddit_posts": 12000,
      "excitement_scores": 50000
    }
  }
}
```

## Security Architecture

**Authentication:**
- **MVP**: No user authentication required (public read-only dashboard)
- **Remove from starter template**: JWT auth endpoints, user models, password hashing

**API Security:**
- **External API credentials**: Stored in environment variables (.env files, gitignored)
- **Rate limiting**: Respect upstream API limits (Reddit 100 QPM, NCAA 5 req/s)
- **CORS**: FastAPI CORS middleware configured for frontend origin

**Data Privacy:**
- No personal user data collected
- Public Reddit data only (usernames, post content)
- No analytics cookies or tracking

**Dependency Security:**
- Run `poetry audit` in CI/CD pipeline
- Pin dependency versions in `pyproject.toml`
- Dependabot auto-updates for security patches

## Performance Considerations

**Database Optimization:**
- TimescaleDB hypertables for `excitement_scores` and `betting_odds`
- Automatic time-based partitioning (PARTITION BY DAY implied)
- SYMBOL columns in QuestDB → VARCHAR with indexes in Postgres
- Connection pooling via SQLAlchemy (default 5-10 connections)

**API Performance:**
- Response time target: <500ms for `/api/games/today`
- Caching: React Query caches API responses (10-15 min stale time)
- Database query optimization: Use LATERAL JOINs for latest excitement scores

**Frontend Performance:**
- Code splitting: React.lazy for non-critical components
- Bundle size budget: <500KB gzipped (enforced in Vite config)
- Image lazy loading for team logos
- React.memo for GameCard components (prevent re-renders)

**Scalability:**
- **MVP scale**: 5-10 concurrent games, 200 posts/day, 10-50 users
- **EC2 t2.micro capacity**: 1 vCPU, 1GB RAM (sufficient for MVP)
- **Upgrade path**: Vertical scale to t3.small (2 vCPU, 2GB) if needed

## Deployment Architecture

**Local Development (Docker Compose):**

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: gamepulse
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    command: uvicorn app.main:app --reload --host 0.0.0.0
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://gamepulse:${DB_PASSWORD}@db:5432/gamepulse

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
    ports:
      - "5173:5173"
    depends_on:
      - backend

volumes:
  postgres_data:
```

**Production Deployment (AWS EC2 t2.micro):**

**Infrastructure:**
- **EC2 Instance**: t2.micro (1 vCPU, 1GB RAM, free tier)
- **Storage**: 20GB EBS volume (GP2, free tier)
- **Networking**: Elastic IP, Security Group (ports 80, 443, 22)
- **Reverse Proxy**: Traefik for automatic HTTPS (Let's Encrypt)

**Deployment Process:**

1. **GitHub Actions Workflow** (`.github/workflows/deploy.yml`):
   - Trigger: Push to `main` branch
   - Steps:
     - Run linters (ruff, mypy, eslint)
     - Run tests (pytest, vitest)
     - Build Docker images (backend, frontend)
     - Push images to Docker Hub
     - SSH to EC2, pull images
     - Run `docker-compose -f docker-compose.prod.yml up -d`
     - Smoke test: `curl https://gamepulse.example.com/api/health`

2. **Production Docker Compose** (`docker-compose.prod.yml`):
   - Traefik reverse proxy with HTTPS
   - PostgreSQL with persistent volume
   - Backend API container
   - Frontend static files served by Nginx
   - All containers on Docker network

**Environment Variables:**
- **Local**: `.env` file (gitignored)
- **Production**: AWS Systems Manager Parameter Store (loaded at container start)

## Development Environment

### Prerequisites

**Required:**
- Git
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- pipx (for copier)

**Optional but Recommended:**
- VSCode with extensions: Python, ESLint, Prettier
- Postman or Insomnia (API testing)

### Setup Commands

**Initial Project Setup:**

```bash
# 1. Clone the FastAPI full-stack template
pipx run copier copy https://github.com/fastapi/full-stack-fastapi-template gamepulse --trust

cd gamepulse

# 2. Add TimescaleDB to PostgreSQL Dockerfile
# Edit backend/Dockerfile, add after FROM postgres:16:
# RUN apt-get update && apt-get install -y timescaledb-2-postgresql-16

# 3. Create .env files (template generates these)
# Edit backend/.env with your credentials

# 4. Start local development environment
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Create TimescaleDB hypertables
docker-compose exec db psql -U gamepulse -d gamepulse -c "
  SELECT create_hypertable('excitement_scores', 'timestamp');
  SELECT create_hypertable('betting_odds', 'timestamp');
"

# 7. Access services:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API docs: http://localhost:8000/docs
```

**Daily Development:**

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm test

# Stop services
docker-compose down
```

**Database Operations:**

```bash
# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Add excitement_scores table"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1

# Access PostgreSQL CLI
docker-compose exec db psql -U gamepulse -d gamepulse
```

## Architecture Decision Records (ADRs)

### ADR-001: PostgreSQL + TimescaleDB over QuestDB

**Context:** GamePulse requires time-series storage for excitement scores and betting odds with high query performance.

**Decision:** Use PostgreSQL 16 with TimescaleDB extension instead of QuestDB.

**Rationale:**
- **Learning value**: PostgreSQL knowledge is highly transferable (top 3 databases in industry)
- **Ecosystem maturity**: SQLModel ORM, Alembic migrations, extensive tutorials
- **Starter template fit**: FastAPI full-stack template already configured for Postgres
- **Performance acceptable**: At GamePulse scale (60MB total data, ~100 writes/min), TimescaleDB queries are sub-100ms
- **Trade-off acknowledged**: QuestDB would be 6x faster for time-series aggregations, but speed difference negligible at this scale

**Consequences:**
- SQLModel ORM can be used (type-safe queries)
- Alembic manages schema migrations
- Slightly higher memory footprint (~500MB vs ~300MB for QuestDB)
- Single database handles both dimensional and time-series data

### ADR-002: FastAPI Full-Stack Starter Template

**Context:** GamePulse has a 2-3 week MVP timeline requiring rapid setup.

**Decision:** Use official FastAPI full-stack template as project foundation.

**Rationale:**
- **Time savings**: 8-10 hours saved in Week 1 vs manual Docker/CI setup
- **Production patterns**: Pre-configured Docker Compose, GitHub Actions, automatic HTTPS
- **Modern tooling**: Vite, React Query, TypeScript, uv already integrated
- **Best practices**: Follows FastAPI recommendations for project structure

**Consequences:**
- Must remove authentication boilerplate (~30 min)
- Locked into template's opinions (uv, Chakra UI) - decided to keep these
- Slightly more complex than minimal setup, but comprehensive

### ADR-003: uv for Package Management

**Context:** Modern Python package managers include Poetry (mature) and uv (new, 100x faster). As of 2025, the FastAPI full-stack template has migrated to uv as the default.

**Decision:** Use uv (starter template default) for dependency management.

**Rationale:**
- **Template default**: FastAPI template v0.8.0 (Feb 2025) uses uv by default
- **Performance**: 100x faster than Poetry for dependency resolution and installation
- **Modern tooling**: Written in Rust, actively maintained by Astral (creators of ruff)
- **Zero migration cost**: Template already configured with uv
- **Compatibility**: Fully compatible with pyproject.toml standard

**Consequences:**
- Extremely fast dependency installs (seconds vs minutes)
- Newer tool with smaller ecosystem than Poetry, but rapidly growing adoption
- Template handles all configuration, no manual setup required

### ADR-004: Chakra UI over Tailwind CSS

**Context:** Frontend needs dark theme, responsive design, and component library.

**Decision:** Keep Chakra UI (starter template default) instead of swapping to Tailwind CSS.

**Rationale:**
- **Pre-built components**: Button, Card, Modal already implemented (saves time)
- **Dark mode built-in**: `useColorMode()` hook trivial to implement
- **Responsive design system**: Breakpoints and spacing already configured
- **Time cost of migration**: Swapping CSS frameworks is 4-6 hours of non-portfolio-value work

**Consequences:**
- Larger bundle size than Tailwind (~50KB extra gzipped)
- More opinionated styling (less low-level control)
- Can customize Chakra theme to match mockups

### ADR-005: Batch Polling + WebSocket Streaming (Dual Paradigms)

**Context:** GamePulse needs to demonstrate both batch and streaming data processing for portfolio value.

**Decision:**
- **Batch processing**: NCAA API (15 min polling), Reddit API (15 min polling)
- **Streaming**: Betfair WebSocket for betting odds (real-time)

**Rationale:**
- **Portfolio demonstration**: Shows understanding of when to use each paradigm
- **API constraints**: Reddit (100 QPM), NCAA (5 req/s) are polling-only
- **Cost efficiency**: Betfair delayed API is free, provides real WebSocket streaming
- **Interview narrative**: "I chose batch for rate-limited APIs and streaming for real-time data"

**Consequences:**
- Data freshness: 10-15 min lag for games/Reddit, <3 sec for betting odds
- Dual architecture: Scheduled workers (batch) + long-running stream process
- Complexity increase: Must handle both paradigms in codebase

### ADR-006: Reddit Post-Level Tracking (Not Comments)

**Context:** Reddit provides both posts and comments. Comments have richer data but API limits are strict.

**Decision:** Track posts only for MVP, defer comments to Growth phase.

**Rationale:**
- **API efficiency**: 100 QPM limit sufficient for ~100 posts/hour, but not for 1000s of comments
- **Signal quality**: Post titles capture key moments ("BUZZER BEATER"), comments add detail but not core value
- **Time constraints**: Comment ingestion adds 2-3 days of implementation time

**Consequences:**
- MVP excitement algorithm based on post engagement only
- Game thread comments not analyzed for sentiment
- Can add comment tracking in Growth phase without architecture changes

### ADR-007: Dagster for Data Orchestration (Asset-Oriented)

**Context:** GamePulse requires workflow orchestration for batch data ingestion (NCAA API polling every 15 minutes, Reddit sentiment analysis) and needs to demonstrate modern data engineering practices for targeting data solutions architect roles. Initial consideration was APScheduler (simple in-process scheduling), with alternatives including Prefect (flow-oriented) and Airflow (mature but complex).

**Decision:** Use Dagster (self-hosted) for data pipeline orchestration.

**Rationale:**
- **Asset-oriented paradigm**: Dagster treats data as first-class citizens (assets) rather than tasks, aligning with data platform architecture thinking required for data solutions architect roles
- **Built-in lineage**: Visual asset catalog shows how excitement_scores depend on ncaa_games + reddit_posts + betting_odds, demonstrating data flow understanding
- **Portfolio differentiation**: Modern tool gaining traction in data engineering (vs ubiquitous Airflow), shows awareness of industry trends
- **Interview narrative**: Asset lineage graphs are visually impressive demo material: "excitement scores depend on these three upstream assets..."
- **Real dependencies**: GamePulse has genuine orchestration complexity (NCAA → Reddit matching → excitement calculation + streaming Betfair integration), not just simple scheduled tasks
- **Self-hosted deployment**: Dagster Cloud costs $200-600/month for MVP usage (14K-28K credits), self-hosted on existing EC2 costs $0 and demonstrates infrastructure skills
- **Async support**: Full support for `async def` asset definitions, works seamlessly with FastAPI patterns and httpx client
- **Migration strategy**: Start with 30-day Dagster Cloud trial for fast learning and branch deployments, then migrate to self-hosted before trial ends

**Alternatives Considered:**
- **APScheduler**: Simple in-process scheduling, sufficient for MVP scale, but lacks observability UI and doesn't demonstrate modern data platform thinking
- **Prefect**: Flow-oriented with excellent async support, free cloud tier, but task-paradigm less impressive than asset-paradigm for data architect roles
- **Airflow**: Industry standard with massive ecosystem, but complex deployment (requires Redis/Celery), Jinja templates less Pythonic than Dagster's pure Python

**Consequences:**
- **Learning curve**: +1-2 days implementation vs APScheduler (3-4 days vs 2 days), but asset paradigm requires mindset shift
- **Infrastructure**: Dagster webserver + daemon containers added to Docker Compose, uses existing PostgreSQL for metadata storage
- **Portfolio value**: Visual asset lineage graph for interview demos, demonstrates understanding of data lineage and asset dependencies
- **Cost optimization**: Migrating from Cloud trial to self-hosted saves $200-600/month, shows cost-conscious architecture decisions
- **No dbt needed**: Dagster assets can handle SQL transformations directly for GamePulse's simple aggregation needs (excitement score calculations)
- **Deployment**: Two additional containers (dagster-webserver on port 3000, dagster-daemon for schedules), Traefik routing for dagster.gamepulse.top subdomain

---

## Extended Implementation Patterns (Agent Consistency)

### Import Patterns (CRITICAL - Prevents Module Errors)

**Python - ALWAYS Use Absolute Imports:**
```python
✅ from app.models.game import Game
✅ from app.services.ncaa_client import fetch_games
✅ from app.core.db import get_session

❌ from ..models.game import Game  # Relative imports forbidden
❌ from models.game import Game  # Missing app prefix
```

**TypeScript - Use Path Aliases:**
```typescript
✅ import { GameCard } from '@/components/GameCard';
✅ import { useGames } from '@/hooks/useGames';

❌ import { GameCard } from '../../components/GameCard';  # Relative forbidden
```

### File Location Patterns (WHERE Things Go)

**Backend Structure:**
```
app/models/{domain}.py          → SQLModel database models (Team, Game, RedditPost)
app/schemas/{domain}.py         → Pydantic API response schemas (GameSchema, GamesResponse)
app/api/routes/{resource}.py    → FastAPI endpoints (games.py, moments.py, health.py)
app/services/{logic}.py         → Business logic (excitement_scorer, time_mapper)
app/services/{api}_client.py    → External API clients (ncaa_client, reddit_client)
app/workers/{job}_poller.py     → Background jobs (ncaa_poller, reddit_poller)
app/core/{concern}.py           → Cross-cutting (config, db, logging)
```

**Frontend Structure:**
```
src/components/{Component}.tsx   → Reusable UI (GameCard, ExcitementTimeline)
src/pages/{Page}.tsx             → Top-level pages (Dashboard)
src/hooks/{useSomething}.ts      → Custom hooks (useGames, usePolling)
src/utils/{utility}.ts           → Pure functions (formatters, colors)
```

### Async/Await Patterns (MANDATORY for I/O)

**Python - ALL I/O Operations Must Be Async:**
```python
✅ async def fetch_games() -> List[Game]:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

✅ async def get_game(session: AsyncSession, game_id: str):
    result = await session.exec(select(Game).where(Game.game_id == game_id))
    return result.one()

❌ def fetch_games():  # Missing async - BLOCKS event loop
    response = requests.get(url)  # Sync I/O forbidden in FastAPI
```

**TypeScript - React Query Pattern:**
```typescript
✅ const { data } = useQuery({
    queryKey: ['games'],
    queryFn: async () => {
      const res = await fetch('/api/games/today');
      return res.json();
    }
  });

❌ fetch('/api/games').then(...)  # Use async/await, not .then()
```

### SQLModel Schema Patterns

**Database Model (table=True):**
```python
from sqlmodel import SQLModel, Field
from datetime import datetime

class Game(SQLModel, table=True):
    __tablename__ = "games"  # Explicit name (plural, lowercase)

    game_id: str = Field(primary_key=True)
    home_team_id: str = Field(foreign_key="teams.team_id")
    home_score: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**API Response Schema (Pydantic):**
```python
from pydantic import BaseModel

class GameSchema(BaseModel):
    game_id: str
    home_team: TeamSchema  # Nested schema
    excitement_score: float

    class Config:
        from_attributes = True  # Allow ORM conversion
```

### Logging Patterns (structlog)

**Event Naming (snake_case, past tense):**
```python
logger.info(
    "excitement_calculated",  # NOT "calculate_excitement"
    game_id="401234567",
    score=94.5,
    duration_ms=45
)

logger.error(
    "api_fetch_failed",  # NOT "fetch_api_failure"
    api="ncaa",
    status_code=500,
    retry_attempt=2
)
```

### APScheduler Job Pattern

**Interval-Based Polling:**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

scheduler.add_job(
    poll_ncaa_games,  # async function
    'interval',
    seconds=900,  # 15 minutes
    id='ncaa_poller',
    replace_existing=True
)

async def poll_ncaa_games():
    logger.info("ncaa_poll_started")
    games = await fetch_ncaa_games()
    await save_games(games)
    logger.info("ncaa_poll_completed", count=len(games))
```

### Configuration Pattern

**Environment Variables (Pydantic Settings):**
```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDDIT_API_KEY: str
    BETFAIR_API_KEY: str
    POLLING_INTERVAL: int = 900

    class Config:
        env_file = ".env"

settings = Settings()
```

## Novel Patterns

GamePulse implements two custom patterns that don't have standard off-the-shelf solutions. These patterns are critical for AI agent consistency and require explicit implementation guidance.

### Pattern 1: Excitement Score Calculation

**Purpose:** Multi-factor algorithm combining Reddit velocity, sentiment, betting odds volatility, and game context to score game excitement from 0-100.

**Implementation Location:** `backend/app/services/excitement_scorer.py`

**Database Target:** Writes to `excitement_scores` hypertable every 15 min

**Inputs:**
- `reddit_velocity`: Posts per 15-min window (float, 0-∞)
- `sentiment_score`: VADER compound sentiment -1 to 1 (float)
- `odds_volatility`: 5-min odds shift magnitude (float, 0-1)
- `rivalry_bonus`: 0 (no) or 10 (rivalry game) (int)
- `game_context_factor`: Tournament multiplier 1.0-1.5 (float)

**Algorithm Steps:**

1. **Normalize Reddit Velocity** (0-40 scale):
   ```python
   reddit_component = min(reddit_velocity * 4, 40)
   # 0 posts = 0, 10+ posts = 40
   ```

2. **Convert Sentiment Score** (0-20 scale):
   ```python
   sentiment_component = max(0, sentiment_score * 20)
   # Only positive sentiment counts: -1 to 1 → 0 to 20
   ```

3. **Normalize Odds Volatility** (0-30 scale):
   ```python
   odds_component = min(odds_volatility * 600, 30)
   # 0.05+ shift = 30 (5% price movement is highly volatile)
   ```

4. **Calculate Base Score**:
   ```python
   base_score = reddit_component + sentiment_component + odds_component
   # Range: 0-90
   ```

5. **Apply Multipliers and Bonuses**:
   ```python
   final_score = (base_score * game_context_factor) + rivalry_bonus
   # game_context_factor: 1.0 (regular), 1.2 (conference), 1.5 (tournament)
   # rivalry_bonus: +10 for rivalry games (Duke vs UNC, etc.)
   ```

6. **Clamp to Valid Range**:
   ```python
   excitement_score = min(max(final_score, 0), 100)
   ```

**Edge Cases:**

| Scenario | Handling | Rationale |
|----------|----------|-----------|
| No Reddit posts for game | Use `odds_volatility` + `game_context` only | Betting market still signals excitement |
| Reddit API down | Set `reddit_velocity = 0`, calculate with remaining factors | Graceful degradation per NFR-4.2 |
| No betting odds available | Exclude `odds_component`, scale other factors proportionally | Early-season games may lack betting data |
| Negative sentiment dominant | `sentiment_component = 0` (only positive sentiment counts) | Controversy ≠ exciting gameplay |
| Post-game posts | Timestamp filter: only posts during live game window | Avoid post-game analysis skewing scores |

**Output Schema:**
```python
class ExcitementScore(SQLModel, table=True):
    game_id: str
    timestamp: datetime  # UTC
    score: float  # 0-100
    reddit_velocity: float
    reddit_engagement: int  # Total upvotes + comments
    sentiment_score: float
    odds_volatility: float
    game_context_factor: float
    rivalry_bonus: float
```

**States and Transitions:**

```
[Calculating] → [Current] → [Stale]
    ↓             ↓           ↓
   15min       <10min      >20min
```

- **Calculating**: Worker actively computing score
- **Current**: Score calculated <10 min ago, safe to display
- **Stale**: Score >20 min old, show "Last updated X min ago" warning

**Testing Strategy:**
- Unit tests: Mock Reddit/betting data, verify score ranges
- Edge case tests: Zero values, missing data, extreme values
- Integration tests: End-to-end with test database

---

### Pattern 2: Wall-Clock to Game-Clock Time Mapping

**Purpose:** Convert Reddit post timestamps (UTC wall-clock) to estimated game clock (e.g., "10:34 2nd Half") for contextualizing moments.

**Implementation Location:** `backend/app/services/time_mapper.py`

**Database Target:** Updates `reddit_posts.game_time_context`, `reddit_posts.estimated_game_clock`, `reddit_posts.time_mapping_confidence`

**Inputs:**
- `post_time`: Reddit post timestamp UTC (datetime)
- `game_start_time`: Scheduled game start UTC (datetime)
- `game_status`: scheduled | live | halftime | final (str)
- `actual_game_clock` (optional): Real game clock from NCAA API if available (str)

**Algorithm Steps:**

1. **Calculate Elapsed Time**:
   ```python
   elapsed_seconds = (post_time - game_start_time).total_seconds()
   elapsed_min = elapsed_seconds / 60
   ```

2. **Apply Halftime Adjustment**:
   ```python
   HALFTIME_DURATION = 15  # minutes
   FIRST_HALF_DURATION = 20  # minutes

   if elapsed_min > FIRST_HALF_DURATION + HALFTIME_DURATION:
       # Post is in 2nd half, subtract halftime
       game_elapsed_min = elapsed_min - HALFTIME_DURATION
   else:
       game_elapsed_min = elapsed_min
   ```

3. **Determine Period and Clock**:
   ```python
   if game_elapsed_min < 0:
       context = "pre_game"
       clock = None
   elif game_elapsed_min <= 20:
       context = "1st_half"
       clock_remaining = 20 - game_elapsed_min
       clock = f"{int(clock_remaining):02d}:{int((clock_remaining % 1) * 60):02d} 1st Half"
   elif game_elapsed_min <= 40:
       context = "2nd_half"
       clock_remaining = 40 - game_elapsed_min
       clock = f"{int(clock_remaining):02d}:{int((clock_remaining % 1) * 60):02d} 2nd Half"
   else:
       context = "post_game"
       clock = "Final"
   ```

4. **Calculate Confidence Score**:
   ```python
   if game_status == "live" and 0 <= game_elapsed_min <= 55:
       confidence = 0.9  # High confidence during typical game window
   elif game_status == "scheduled":
       confidence = 0.3  # Pre-game posts, low confidence
   elif game_elapsed_min > 55:
       confidence = 0.5  # Post-game, medium confidence
   else:
       confidence = 0.7  # Default

   # Boost confidence if actual game clock available from NCAA API
   if actual_game_clock:
       confidence = min(confidence + 0.1, 1.0)
   ```

**Edge Cases:**

| Scenario | Handling | Confidence | Rationale |
|----------|----------|------------|-----------|
| Post before game start | `context = "pre_game"`, `clock = None` | 1.0 | Exact classification |
| Post >2 hours after start | `context = "post_game"` | 0.8 | Likely post-game analysis |
| Game status "scheduled" but post exists | `context = "pre_game"` | 1.0 | Pre-game discussion |
| Overtime game | Extend 2nd half clock beyond 20:00 | 0.6 | Less predictable timing |
| Delayed game start | Use NCAA API `actual_start_time` if available | 0.9 | Corrected for real start |

**Output Schema:**
```python
# Updates to reddit_posts table
game_time_context: str  # pre_game, 1st_half, halftime, 2nd_half, post_game
estimated_game_clock: str | None  # "15:30 2nd Half" or None
time_mapping_confidence: float  # 0.0-1.0
```

**Context Categories:**

| Context | Description | Typical Use Case |
|---------|-------------|------------------|
| `pre_game` | Post before tipoff | Hype, predictions, lineup discussions |
| `1st_half` | 0:00-20:00 game time | Early game moments, hot starts |
| `halftime` | Between halves | Score reactions, adjustment discussions |
| `2nd_half` | 20:00-40:00 game time | Late-game drama, buzzer beaters |
| `post_game` | After final buzzer | Recap, highlights, analysis |

**States and Transitions:**

```
[Pre-Game] → [1st Half] → [Halftime] → [2nd Half] → [Post-Game]
   ↓            ↓            ↓            ↓             ↓
 t < 0      0-20 min    20-35 min    35-55 min     t > 55 min
```

**Integration with Excitement Scoring:**
- Time-mapped posts enable period-specific excitement trends
- "2nd Half" posts weighted higher (clutch moments more exciting)
- Pre-game posts excluded from excitement velocity calculations

**Testing Strategy:**
- Unit tests: Known timestamps → expected game clock outputs
- Edge case tests: Pre-game, overtime, delayed starts
- Confidence validation: Assert confidence scores in expected ranges

---

_Generated by BMAD Decision Architecture Workflow v1.3.2_
_Date: 2025-11-07_
_For: Philip (GamePulse Project)_
