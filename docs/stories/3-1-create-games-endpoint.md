# Story 3.1: Create Basic /api/games/today Endpoint

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** ready-for-dev
**Assignee:** Claude Code (Dev Agent)
**Sprint:** Week 1
**Story Points:** 5
**Dependencies:** Epic 2 (dim_team, fact_game schema)

---

## User Story

**As a** GamePulse frontend developer
**I want** a REST API endpoint that returns today's NCAA Men's Basketball games with team details
**So that** I can display live game data on the web dashboard with team colors and scores

---

## Business Context

Epic 3 delivers the "Working Demo" milestone - a live public URL showing NCAA games achievable by end of Week 1. Story 3.1 creates the critical backend API contract that bridges the dimensional data model (Epic 2) with the frontend dashboard. This endpoint must handle CORS for cross-origin requests, perform efficient dimensional JOINs using surrogate keys, and return type-safe JSON validated by Pydantic schemas.

**Why This Story Matters:**
- First bidirectional communication between backend and frontend (establishes architectural pattern for Epic 8 enhancements)
- Proves dimensional model works end-to-end (surrogate key JOINs, SCD Type 2 filtering)
- Enables frontend development to proceed in parallel (Story 3.3-3.5)
- Demonstrates FastAPI best practices (Pydantic validation, automatic OpenAPI docs, CORS configuration)

**Impact of Delays:**
- Frontend development blocked (Stories 3.4-3.5 cannot proceed)
- Week 1 demo milestone at risk (need live URL for interviews)
- No integration testing possible until endpoint exists

---

## Acceptance Criteria

### AC-3.1: Games Today Endpoint Functionality

**Given** fact_game table populated with games from Dagster ncaa_games asset (Epic 2)
**When** I send GET request to `/api/games/today`
**Then** response returns HTTP 200 with valid JSON
**And** response contains `games` array and `total_count` integer
**And** each game includes fields: `game_key`, `game_id`, `game_date`, `game_time`, `game_status`, `home_team`, `away_team`, `home_score`, `away_score`
**And** games filtered by today's date (`game_date_key` = YYYYMMDD format of current date)
**And** games ordered chronologically by `game_time` ascending
**And** empty array returned if no games scheduled today (valid response, not error)

**Validation:**
```bash
# Manual API test
curl http://localhost:8000/api/games/today | jq .

# Expected output structure:
{
  "games": [
    {
      "game_key": 12345,
      "game_id": "ncaam_401234567",
      "game_date": "2025-11-13",
      "game_time": "2025-11-13T19:00:00Z",
      "game_status": "scheduled",
      "home_team": { ... },
      "away_team": { ... },
      "home_score": null,
      "away_score": null
    }
  ],
  "total_count": 25,
  "generated_at": "2025-11-13T18:45:00Z"
}
```

---

### AC-3.2: Dimensional Model Integration

**Given** dim_team table with team names, colors, conference names (Epic 2)
**When** endpoint executes database query
**Then** query performs JOINs on `fact_game` with `dim_team` twice (home and away)
**And** uses surrogate key relationships (`home_team_key`, `away_team_key` → `team_key`)
**And** filters `dim_team.is_current = TRUE` to respect SCD Type 2 pattern
**And** team colors (`primary_color`, `secondary_color`) retrieved from dim_team, not hardcoded
**And** conference names (`team_group_name`) included from flattened dim_team fields

**Validation:**
```sql
-- Verify query execution plan uses indexes
EXPLAIN ANALYZE
SELECT fg.*, ht.team_name AS home_name, at.team_name AS away_name
FROM fact_game fg
JOIN dim_team ht ON fg.home_team_key = ht.team_key AND ht.is_current = TRUE
JOIN dim_team at ON fg.away_team_key = at.team_key AND at.is_current = TRUE
WHERE fg.game_date_key = 20251113;

-- Execution time should be <200ms
```

---

### AC-3.3: CORS Configuration

**Given** frontend served from separate origin (localhost:5173 dev, gamepulse.top prod)
**When** browser sends preflight OPTIONS request
**Then** response includes `Access-Control-Allow-Origin` header matching request origin
**And** allowed origins include: `http://localhost:5173`, `https://gamepulse.top`, `https://api.gamepulse.top`
**And** preflight OPTIONS requests return HTTP 204 with proper headers
**And** cross-origin requests from non-whitelisted domains blocked by CORS middleware

**Validation:**
```bash
# Test CORS preflight from allowed origin
curl -X OPTIONS http://localhost:8000/api/games/today \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Expect: HTTP 204 with Access-Control-Allow-Origin: http://localhost:5173

# Test from disallowed origin
curl -X OPTIONS http://localhost:8000/api/games/today \
  -H "Origin: https://malicious-site.com" \
  -v

# Expect: No Access-Control-Allow-Origin header (browser blocks)
```

---

### AC-3.4: Pydantic Response Schema Validation

**Given** Pydantic schemas defined for `GamePublic` and `GameListResponse`
**When** endpoint returns data
**Then** FastAPI automatically validates response against Pydantic schema
**And** invalid data raises HTTP 422 Unprocessable Entity (schema violation)
**And** OpenAPI schema auto-generated at `/docs` endpoint
**And** TypeScript client can be generated from OpenAPI schema without errors

**Validation:**
```python
# Unit test: Force invalid data to verify Pydantic validation
def test_game_public_schema_validation():
    with pytest.raises(ValidationError):
        GamePublic(
            game_key=123,
            game_id="invalid",
            game_date="not-a-date",  # Should fail validation
            # ... missing required fields
        )
```

---

### AC-3.5: Error Handling and Logging

**Given** database connection failure or query error
**When** endpoint attempts to fetch games
**Then** structured error logged with `exc_info=True` (full stack trace)
**And** response returns HTTP 500 with `{ "detail": "Database connection failed" }`
**And** error log includes context: `endpoint="/api/games/today"`, `request_id=<uuid>`
**And** no stack traces exposed to API clients (security best practice)

**Validation:**
```python
# Integration test: Simulate database failure
def test_games_endpoint_database_error(client, mocker):
    mocker.patch('app.api.deps.get_session').side_effect = OperationalError()
    response = client.get("/api/games/today")
    assert response.status_code == 500
    assert "detail" in response.json()
    # Verify structured log emitted (capture logs in test)
```

---

### AC-3.6: Performance Requirements

**Given** typical workload of 20-50 games per day
**When** endpoint executes query and returns response
**Then** P95 response time <500ms (measured via structlog response_time_ms field)
**And** database query execution time <200ms (measured via PostgreSQL EXPLAIN ANALYZE)
**And** Pydantic serialization time <100ms for 50-game result set

**Validation:**
```bash
# Load test with 100 concurrent requests
ab -n 1000 -c 100 http://localhost:8000/api/games/today

# Verify P95 latency from results
# Expected: <500ms for 95th percentile
```

---

## Tasks / Subtasks

- [ ] **Task 1: Create Pydantic Response Schemas** (AC: 3.4)
  - [ ] Create `backend/app/schemas/game.py` file
  - [ ] Define `TeamInfo` schema with team_key, team_id, team_name, team_group_name, primary_color, secondary_color
  - [ ] Define `GamePublic` schema with all game fields + nested TeamInfo for home/away
  - [ ] Define `GameListResponse` schema with games array, total_count, generated_at
  - [ ] Add unit tests for Pydantic schema validation

- [ ] **Task 2: Implement API Route Handler** (AC: 3.1, 3.2, 3.5)
  - [ ] Create `backend/app/api/routes/games.py` file
  - [ ] Implement `get_games_today()` function with dimensional query pattern
  - [ ] Use `aliased()` for home/away team JOINs
  - [ ] Filter by `game_date_key` (today's date in YYYYMMDD format)
  - [ ] Filter by `is_current = TRUE` for SCD Type 2
  - [ ] Order by `game_time` ascending
  - [ ] Transform query results to `GamePublic` schemas
  - [ ] Add structured logging (info on success, error with exc_info=True on failure)
  - [ ] Add error handling with HTTP 500 response

- [ ] **Task 3: Configure CORS Middleware** (AC: 3.3)
  - [ ] Edit `backend/app/main.py`
  - [ ] Add CORS middleware with `allow_origins=settings.BACKEND_CORS_ORIGINS.split(",")`
  - [ ] Set `allow_credentials=False`, `allow_methods=["GET"]`, `allow_headers=["*"]`
  - [ ] Verify `BACKEND_CORS_ORIGINS` environment variable in `.env`
  - [ ] Test CORS preflight from allowed origin

- [ ] **Task 4: Register Router in Main App** (AC: 3.1)
  - [ ] Edit `backend/app/main.py`
  - [ ] Import `games.router` from `app.api.routes.games`
  - [ ] Add `app.include_router(games.router, prefix="/api/games", tags=["games"])`
  - [ ] Verify endpoint accessible at `/api/games/today`

- [ ] **Task 5: Testing and Validation** (AC: All)
  - [ ] Write integration test: `test_get_games_today_empty_result()`
  - [ ] Write integration test: `test_get_games_today_with_games()` with dimensional data
  - [ ] Write integration test: `test_cors_headers_allowed_origin()`
  - [ ] Write integration test: `test_database_error_handling()`
  - [ ] Manual test: `curl http://localhost:8000/api/games/today`
  - [ ] Manual test: Verify OpenAPI docs at `/docs`
  - [ ] Performance test: ab load test (P95 <500ms)
  - [ ] Verify TypeScript client generation works

- [ ] **Task 6: Documentation and Deployment** (AC: All)
  - [ ] Add docstring to `get_games_today()` function
  - [ ] Document `BACKEND_CORS_ORIGINS` in `.env.example`
  - [ ] Update story file with completion notes
  - [ ] Run pre-commit hooks (ruff, mypy)
  - [ ] Commit changes to git
  - [ ] Update sprint-status.yaml: 3-1-create-games-endpoint = "done"

---

## Dev Notes

### Architecture Patterns from Epic 3 Tech Spec

**Dimensional Query Pattern** (from Tech Spec [Data Models section](../tech-spec-epic-3.md#data-models-and-contracts)):
- Use surrogate keys (`team_key`, `game_key`, `date_key`) for JOINs (faster than natural keys)
- Filter `is_current = TRUE` to respect SCD Type 2 pattern
- Alias `dim_team` twice for home/away teams using SQLAlchemy `aliased()`
- Order by `game_time` ascending (chronological display)
- Calculate `game_date_key` as `int(date.today().strftime("%Y%m%d"))` for filtering

**CORS Configuration** (from Tech Spec [Security section](../tech-spec-epic-3.md#security)):
- Whitelist specific origins (no wildcard `*` for security)
- Environment variable `BACKEND_CORS_ORIGINS` comma-separated list
- Development: `http://localhost:5173` (Vite dev server)
- Production: `https://gamepulse.top`, `https://api.gamepulse.top`
- Read-only endpoints: `allow_methods=["GET"]` (no POST/PUT/DELETE)
- No cookies/auth needed: `allow_credentials=False`

**Error Handling Pattern** (from Tech Spec [Reliability section](../tech-spec-epic-3.md#reliability-availability)):
- Structured logging with `structlog` (JSON output for queryable logs)
- Context binding: `endpoint`, `games_count`, `response_time_ms`
- Stack traces in logs (`exc_info=True`), not exposed to clients
- HTTP 500 with generic message: `{ "detail": "Database connection failed" }`
- No user-facing stack traces (security best practice)

**Performance Optimization** (from Tech Spec [Performance section](../tech-spec-epic-3.md#performance)):
- Target: P95 <500ms (database <200ms, serialization <100ms, network <200ms)
- Use indexed surrogate keys for JOINs (integer comparison faster than string)
- Single query with JOINs (avoid N+1 problem)
- No server-side caching needed (database fast enough for <50 games/day)

### Project Structure Alignment

**FastAPI Template Structure** (from Epic 1):
```
backend/app/
├── api/
│   ├── deps.py        # Dependency injection (get_session)
│   ├── main.py        # Router aggregation, CORS middleware
│   └── routes/        # Route modules by resource
│       └── games.py   # NEW - This story creates this file
├── core/
│   ├── config.py      # Settings (BACKEND_CORS_ORIGINS)
│   └── db.py          # Database session management
├── models/            # SQLModel database models
│   ├── game.py        # EXISTING - FactGame (Epic 2, Story 2-3a)
│   └── team.py        # EXISTING - DimTeam (Epic 2, Story 2-3b)
└── schemas/           # Pydantic API schemas (separate from models)
    └── game.py        # NEW - This story creates this file
```

**Story 3.1 follows template convention:**
- `schemas/game.py` for API contracts (not in `models/` which is for SQLModel/database)
- `api/routes/games.py` for resource-specific routes
- `api/deps.py` provides `get_session` dependency (already exists from Epic 1)

### Learnings from Previous Story (2-5-add-retry-logic)

**From Story 2-5 Completion Notes:**
- ✅ **Use `exc_info=True` in error logging** - Applied in this story's error handler
- ✅ **Structured logging with context fields** - Adding `endpoint`, `games_count` fields
- ✅ **Daemon resilience patterns** - Backend API should also never crash on errors

**Testing Patterns from Story 2-5:**
- Manual Dagster UI validation preferred over complex async tests (Story 2-5 lesson)
- Integration tests with FastAPI TestClient more reliable than mocking deep database calls
- Seed test data explicitly in tests (don't rely on Dagster ingestion during test runs)
- Avoid greenlet dependency for CI stability (Story 2-5 encountered greenlet issues)

**Files to Reuse (Epic 2 artifacts):**
- `backend/app/models/game.py::FactGame` - SQLModel with game_key, game_date_key, home_team_key, away_team_key (Story 2-3a)
- `backend/app/models/team.py::DimTeam` - SQLModel with team_key, team_name, primary_color, team_group_name, is_current (Stories 2-1, 2-3b)
- `backend/app/api/deps.py::get_session` - Dependency injection for database session (Epic 1)

**Technical Debt from Story 2-5:**
- Story 2-5 deferred health check documentation to this epic (Story 3.2)
- No action needed for this story (health endpoint is separate story)

### Code Examples from Tech Spec

**Query Pattern Example** (from Tech Spec [Data Models section](../tech-spec-epic-3.md#data-models-and-contracts)):
```python
from sqlmodel import select, Session, and_
from sqlalchemy.orm import aliased
from datetime import date

today_key = int(date.today().strftime("%Y%m%d"))  # 20251113

# Alias dim_team twice for home/away teams
home_team = aliased(DimTeam)
away_team = aliased(DimTeam)

statement = (
    select(FactGame, home_team, away_team)
    .join(home_team, and_(
        FactGame.home_team_key == home_team.team_key,
        home_team.is_current == True
    ))
    .join(away_team, and_(
        FactGame.away_team_key == away_team.team_key,
        away_team.is_current == True
    ))
    .where(FactGame.game_date_key == today_key)
    .order_by(FactGame.game_time.asc())
)

results = session.exec(statement).all()  # Returns tuples (FactGame, DimTeam, DimTeam)
```

**Expected Response Example** (from Tech Spec [APIs section](../tech-spec-epic-3.md#apis-and-interfaces)):
```json
{
  "games": [
    {
      "game_key": 12345,
      "game_id": "ncaam_401234567",
      "game_date": "2025-11-13",
      "game_time": "2025-11-13T19:00:00Z",
      "game_status": "scheduled",
      "home_team": {
        "team_key": 150,
        "team_id": "ncaam_150",
        "team_name": "Duke",
        "team_group_name": "Atlantic Coast Conference",
        "primary_color": "#00539B",
        "secondary_color": "#FFFFFF"
      },
      "away_team": {
        "team_key": 153,
        "team_id": "ncaam_153",
        "team_name": "North Carolina",
        "team_group_name": "Atlantic Coast Conference",
        "primary_color": "#7BAFD4",
        "secondary_color": "#FFFFFF"
      },
      "home_score": null,
      "away_score": null,
      "game_clock": null,
      "venue": "Cameron Indoor Stadium",
      "broadcast": "ESPN"
    }
  ],
  "total_count": 25,
  "generated_at": "2025-11-13T18:45:00Z"
}
```

### References

**Tech Spec Sections:**
- [APIs and Interfaces](../tech-spec-epic-3.md#apis-and-interfaces) - Response schemas, CORS config, endpoint specification
- [Data Models and Contracts](../tech-spec-epic-3.md#data-models-and-contracts) - Pydantic schemas, dimensional query patterns
- [Workflows and Sequencing](../tech-spec-epic-3.md#workflows-and-sequencing) - Workflow 1 (Initial Page Load and Data Display)
- [Performance](../tech-spec-epic-3.md#performance) - P95 <500ms target, query optimization
- [Security](../tech-spec-epic-3.md#security) - CORS configuration, SQL injection prevention
- [Traceability Mapping](../tech-spec-epic-3.md#traceability-mapping) - AC-3.1, AC-3.2, AC-3.3 test strategies

**PRD Requirements:**
- [FR-6.1](../PRD.md#fr-6-backend-api) - Backend API for game data retrieval
- [NFR-1.1](../PRD.md#nfr-1-performance) - API response time <500ms (P95)
- [NFR-3.2](../PRD.md#nfr-3-security) - CORS protection for frontend access

**Architecture Document:**
- Backend API Layer design
- FastAPI + SQLModel + Pydantic stack
- Dimensional model query patterns with surrogate keys

**Previous Story:**
- [Story 2-5](./2-5-add-retry-logic.md#dev-agent-record) - Retry logic patterns, structured logging with exc_info=True

---

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-1-create-games-endpoint.context.xml)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
