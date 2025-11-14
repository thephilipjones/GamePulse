# Epic Technical Specification: Basic API + Dashboard MVP

Date: 2025-11-13
Author: Philip
Epic ID: 3
Status: Draft

---

## Overview

Epic 3 delivers the "Working Demo" milestone by creating a minimal viable web application that displays live NCAA Men's Basketball games on a public URL - achievable by end of Week 1. This epic proves the full stack works end-to-end (data ingestion → database → API → frontend) before adding complexity like excitement scoring, Reddit sentiment, or advanced visualizations. The implementation follows the "functional over pretty" principle: basic FastAPI endpoints serving game data from the dimensional model established in Epic 2, rendered through a simple React dashboard with Chakra UI components and automatic polling refresh.

Epic 3 establishes two critical architectural foundations: (1) the Backend API Layer with CORS-configured endpoints for game data retrieval and health monitoring, and (2) the Frontend Dashboard Layer with React Query-based state management for auto-refresh polling. This architecture enables rapid iteration in later epics - Epic 8 will enhance the same endpoints with excitement scores and sparkline timelines without restructuring the core request/response patterns. The simplified scope deliberately omits Reddit posts, sentiment analysis, and betting odds to maintain Week 1 timeline pressure while Philip actively interviews, prioritizing a shareable live URL over feature completeness. Success criteria: visitors can see today's NCAA games with scores, team names with colors, and auto-refreshing data without manual page reload.

## Objectives and Scope

**In Scope:**

- Create `GET /api/games/today` FastAPI endpoint with Pydantic response schemas querying dimensional model (fact_game + dim_team JOINs)
- Create `GET /api/health` health check endpoint returning system status and database connectivity
- Configure CORS middleware in FastAPI to allow frontend origin (development: localhost:5173, production: gamepulse.top domain)
- Initialize React 18 dashboard application with TypeScript, Vite build tooling, and Chakra UI component library
- Build GameList React component displaying today's games with team names, scores, game status, and team colors
- Implement TanStack Query (React Query) for data fetching with automatic polling refresh every 10-15 minutes
- Basic responsive layout using Chakra UI's responsive props (mobile-friendly design without custom breakpoints)
- Environment-based API URL configuration (VITE_API_URL for local development vs production)
- Error handling for API failures with user-friendly error messages in UI
- Loading states and skeleton screens during initial data fetch

**Out of Scope:**

- Excitement scores and ranking algorithms (Epic 5) - games displayed in chronological order only
- Reddit social sentiment posts and moment detection (Epic 4)
- Sparkline excitement timeline charts (Epic 8 enhancement)
- Advanced filtering/sorting UI beyond basic game status (live, final, scheduled)
- Player-level statistics or box scores - focus on game-aggregate data only
- User authentication or personalization features
- Dark mode theming (Chakra UI default light theme acceptable for MVP)
- Advanced CSS styling and animations - minimal polish acceptable for Week 1 demo
- WebSocket real-time updates - HTTP polling sufficient for 15-minute data cadence
- SEO optimization or meta tags (portfolio demo, not production marketing site)

## System Architecture Alignment

Epic 3 implements the **Backend API Layer** and **Frontend Dashboard Layer** as defined in the Architecture document's module boundaries. This epic creates the first bidirectional communication path between backend and frontend, establishing patterns that later epics will enhance without restructuring.

**Architecture Components Referenced:**

- **Backend Framework**: FastAPI 0.114.2+ async framework with automatic OpenAPI documentation (Architecture section: Technology Stack)
- **Frontend Stack**: React 18 + TypeScript + Vite + Chakra UI 3.8+ (from FastAPI full-stack template, Architecture: Technology Stack)
- **ORM**: SQLModel 0.0.21+ for type-safe database queries joining fact_game with dim_team dimensional tables (Epic 2 schema)
- **State Management**: TanStack Query (React Query) 5.90.7 for API data caching, stale-while-revalidate, and automatic 10-15 min polling (Architecture: Frontend State)
- **HTTP Client**: httpx 0.28.1 (backend internal), native fetch API (frontend to backend)
- **Deployment**: Docker Compose orchestration (backend + frontend + db containers), AWS EC2 t2.micro with Traefik reverse proxy (Epic 1 infrastructure)

**Design Constraints:**

- **Single EC2 Instance**: t2.micro (1 vCPU, 1GB RAM) hosts backend API, frontend static assets (via Traefik), database, and Dagster - memory-constrained environment requires lean dependencies
- **CORS Configuration**: Frontend served from separate origin (localhost:5173 dev, https://gamepulse.top prod) requires explicit CORS middleware configuration in FastAPI main.py
- **No Authentication**: Epic 1 removed authentication boilerplate - endpoints are public read-only, acceptable for portfolio demo (NFR-3.1: Public access)
- **Polling Strategy**: 10-15 minute auto-refresh matches Dagster's 15-minute NCAA game ingestion cadence (NFR-1.4: <15 min staleness acceptable)
- **Dimensional Query Patterns**: Queries join fact_game with dim_team using surrogate keys (team_key) to retrieve team names and colors (Epic 2 schema design)

**Integration Points:**

- **Data Flow**: PostgreSQL (fact_game + dim_team) → FastAPI endpoint → JSON response → React Query cache → React components
- **API Contract**: OpenAPI schema auto-generated by FastAPI, consumed by frontend via TypeScript-generated client (generated via scripts/generate-client.sh)
- **Epic 2 Dependency**: Queries read from fact_game table populated by Dagster ncaa_games asset (Story 2.4)
- **Epic 8 Enhancement Path**: GET /api/games/today response schema designed for backward-compatible extension (add excitement_score field later without breaking changes)

## Detailed Design

### Services and Modules

**Epic 3 Module Structure:**

| Module | Responsibility | Location | Inputs | Outputs | Owner |
|--------|---------------|----------|--------|---------|-------|
| **Games API Route** | Expose today's games endpoint with dimensional queries | `backend/app/api/routes/games.py` | Query params (date filter) | JSON list of games with team details | Story 3.1 |
| **Health API Route** | System health check endpoint | `backend/app/api/routes/health.py` | None | JSON health status + DB connectivity | Story 3.2 |
| **Game Response Schema** | Pydantic schema for API response validation | `backend/app/schemas/game.py` | SQLModel query results | Type-safe JSON response | Story 3.1 |
| **CORS Middleware** | Configure allowed origins for frontend access | `backend/app/main.py` (middleware config) | Environment variable BACKEND_CORS_ORIGINS | Configured app instance | Story 3.1 |
| **React Dashboard App** | Main application entry point | `frontend/src/main.tsx` | None | Rendered React app | Story 3.3 |
| **GameList Component** | Display list of games with team info | `frontend/src/components/GameList.tsx` | Array of game objects | Rendered game cards | Story 3.4 |
| **useGamesQuery Hook** | TanStack Query hook for fetching games | `frontend/src/hooks/useGamesQuery.ts` | API endpoint URL | Query result with data/loading/error states | Story 3.5 |
| **API Client** | Auto-generated TypeScript client | `frontend/src/client/` (generated) | OpenAPI schema | Type-safe API methods | Auto-generated |

**Module Interaction Flow:**

```
User Browser
    ↓ (initial page load)
Dashboard.tsx component
    ↓ (calls hook)
useGamesQuery() hook
    ↓ (TanStack Query with refetchInterval: 900000ms = 15 min)
fetch("http://api.gamepulse.top/api/games/today")
    ↓ (HTTP GET with CORS headers)
Traefik Reverse Proxy (port 443)
    ↓ (route to backend container)
FastAPI app.middleware("CORS")
    ↓ (validate origin, add CORS headers)
app.include_router(games_router)
    ↓ (route to /api/games/today)
routes/games.py::get_games_today()
    ↓ (async SQLModel query)
session.exec(
  select(FactGame, DimTeam as home, DimTeam as away)
  .join(home, FactGame.home_team_key == home.team_key)
  .join(away, FactGame.away_team_key == away.team_key)
  .where(FactGame.game_date_key == today_key)
)
    ↓ (transform to Pydantic schema)
GameListResponse(games=[GamePublic(...)])
    ↓ (JSON serialization)
FastAPI JSONResponse with CORS headers
    ↓ (HTTP 200 response)
useGamesQuery() receives data
    ↓ (React Query caches result)
GameList.tsx renders game cards
    ↓ (displays to user)
User sees today's games
```

### Data Models and Contracts

**API Response Schemas (Pydantic):**

**1. GamePublic** - Individual game representation (Story 3.1):
```python
class TeamInfo(BaseModel):
    """Nested team information from dimensional query"""
    team_key: int
    team_id: str              # "ncaam_150" (Duke)
    team_name: str            # "Duke"
    team_group_name: str      # "Atlantic Coast Conference"
    primary_color: str        # "#00539B" (hex color for UI)
    secondary_color: str | None

class GamePublic(BaseModel):
    """Public API representation of a game"""
    game_key: int
    game_id: str              # NCAA API game identifier
    game_date: date           # Date only (2025-11-13)
    game_time: datetime | None  # Scheduled start time (UTC)
    game_status: str          # "scheduled" | "live" | "final"
    home_team: TeamInfo       # Nested team object
    away_team: TeamInfo       # Nested team object
    home_score: int | None    # null if game not started
    away_score: int | None
    game_clock: str | None    # "12:34 2nd" (if live)
    venue: str | None         # Stadium name
    broadcast: str | None     # TV network

class GameListResponse(BaseModel):
    """Response envelope for /api/games/today"""
    games: list[GamePublic]
    total_count: int
    generated_at: datetime     # Response timestamp for cache debugging
```

**2. HealthCheckResponse** - Health endpoint response (Story 3.2):
```python
class HealthCheckResponse(BaseModel):
    """System health status"""
    status: str                # "healthy" | "degraded" | "unhealthy"
    version: str               # API version "1.0.0"
    database: str              # "connected" | "disconnected"
    uptime_seconds: float      # Process uptime
    timestamp: datetime
```

**Database Query Patterns:**

**Query 1: Fetch Today's Games** (dimensional model JOIN pattern):
```python
from sqlmodel import select, Session
from app.models.game import FactGame
from app.models.team import DimTeam
from datetime import date

async def get_today_games(session: Session) -> list[FactGame]:
    """
    Query today's games with team details via dimensional JOINs.
    Uses surrogate key relationships established in Epic 2 schema.
    """
    today_key = int(date.today().strftime("%Y%m%d"))  # 20251113

    # Alias dim_team twice for home/away teams
    home_team = aliased(DimTeam)
    away_team = aliased(DimTeam)

    statement = (
        select(FactGame, home_team, away_team)
        .join(home_team, FactGame.home_team_key == home_team.team_key)
        .join(away_team, FactGame.away_team_key == away_team.team_key)
        .where(FactGame.game_date_key == today_key)
        .where(home_team.is_current == True)  # SCD Type 2 filter
        .where(away_team.is_current == True)
        .order_by(FactGame.game_time.asc())
    )

    results = session.exec(statement).all()
    return results  # Returns tuples (FactGame, DimTeam, DimTeam)
```

**Query 2: Health Check DB Connectivity**:
```python
async def check_database_health(session: Session) -> bool:
    """Simple query to verify database connectivity"""
    try:
        result = session.exec(select(1)).one()
        return result == 1
    except Exception:
        return False
```

**Data Flow Contracts:**

- **PostgreSQL → Backend**: SQLModel ORM returns (FactGame, DimTeam, DimTeam) tuples requiring transformation
- **Backend → Frontend**: Pydantic serializes to JSON with ISO 8601 datetime strings
- **Frontend → Components**: TypeScript interfaces (auto-generated from OpenAPI) enforce compile-time type safety
- **Cache Strategy**: React Query caches responses for 15 minutes (staleTime: 900000ms), matches Dagster ingestion cadence

### APIs and Interfaces

**REST API Endpoints (FastAPI):**

**1. GET /api/games/today** (Story 3.1)

- **Purpose**: Retrieve today's NCAA Men's Basketball games with team details
- **Method**: GET
- **Path**: `/api/games/today`
- **Query Parameters**: None (future: `?date=YYYY-MM-DD` for arbitrary date queries)
- **Request Headers**:
  - `Origin: https://gamepulse.top` (CORS preflight)
- **Response Status Codes**:
  - `200 OK`: Games retrieved successfully
  - `500 Internal Server Error`: Database connectivity failure
- **Response Body** (application/json):
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
- **Error Response** (500):
```json
{
  "detail": "Database connection failed"
}
```

**2. GET /api/health** (Story 3.2)

- **Purpose**: Health check for monitoring and deployment smoke tests
- **Method**: GET
- **Path**: `/api/health`
- **Query Parameters**: None
- **Response Status Codes**:
  - `200 OK`: System healthy
  - `503 Service Unavailable`: Database disconnected or critical failure
- **Response Body** (application/json):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "uptime_seconds": 3600.5,
  "timestamp": "2025-11-13T18:45:00Z"
}
```
- **Use Cases**:
  - GitHub Actions smoke test after deployment (checks HTTP 200 response)
  - AWS health check monitoring (future: CloudWatch alarms)
  - Manual verification during local development

**3. GET /docs** (FastAPI auto-generated)

- **Purpose**: Interactive OpenAPI documentation (Swagger UI)
- **Path**: `/docs`
- **Enabled in**: Development and production (no authentication required for portfolio demo)

**CORS Configuration** (Story 3.1):

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS.split(","),  # ["https://gamepulse.top", "http://localhost:5173"]
    allow_credentials=False,  # No cookies/auth
    allow_methods=["GET"],    # Read-only endpoints
    allow_headers=["*"],
)
```

**Frontend API Client (TypeScript - Auto-generated):**

```typescript
// frontend/src/client/services/GamesService.ts (generated)
export class GamesService {
  public static async getGamesToday(): Promise<GameListResponse> {
    const response = await fetch(`${API_URL}/api/games/today`);
    if (!response.ok) throw new Error('Failed to fetch games');
    return response.json();
  }
}

// frontend/src/hooks/useGamesQuery.ts (custom hook)
import { useQuery } from '@tanstack/react-query';
import { GamesService } from '../client';

export const useGamesQuery = () => {
  return useQuery({
    queryKey: ['games', 'today'],
    queryFn: () => GamesService.getGamesToday(),
    refetchInterval: 900000,  // 15 minutes = 900000ms
    staleTime: 900000,        // Consider data fresh for 15 min
    retry: 3,                 // Retry failed requests
  });
};
```

### Workflows and Sequencing

**Workflow 1: Initial Page Load and Data Display**

```
1. User navigates to https://gamepulse.top
   ↓
2. Browser requests index.html from Traefik (frontend container)
   ↓
3. React app bootstraps (main.tsx → App.tsx → Dashboard.tsx)
   ↓
4. Dashboard component renders, calls useGamesQuery() hook
   ↓
5. TanStack Query checks cache (empty on first load)
   ↓
6. Query executes: fetch("https://api.gamepulse.top/api/games/today")
   │  - Sets query status: "loading"
   │  - GameList shows skeleton loading state
   ↓
7. Browser sends HTTP GET with CORS Origin header
   ↓
8. Traefik routes request to backend container (port 8000)
   ↓
9. FastAPI CORS middleware validates origin → adds CORS response headers
   ↓
10. Route handler routes/games.py::get_games_today() executes:
    a. Acquires database session from dependency injection
    b. Constructs SQLModel query with dimensional JOINs
    c. Executes query: SELECT fact_game + dim_team (home) + dim_team (away)
    d. Transforms ORM results to Pydantic GamePublic schemas
    e. Returns GameListResponse JSON
   ↓
11. FastAPI serializes Pydantic to JSON with HTTP 200 response
   ↓
12. TanStack Query receives response:
    - Stores in cache with 15-minute freshness window
    - Updates query status: "success"
    - Triggers React re-render
   ↓
13. GameList.tsx renders game cards:
    - Maps over games array
    - Displays team names, scores, colors
    - Shows game status badges
   ↓
14. User sees today's games displayed
```

**Workflow 2: Automatic Polling Refresh (Every 15 Minutes)**

```
1. Initial page load complete (Workflow 1 finished)
   ↓
2. TanStack Query starts refetchInterval timer (900000ms = 15 min)
   ↓
3. [15 minutes elapse, user still on page]
   ↓
4. React Query triggers background refetch:
   - Does NOT show loading state (uses stale data during fetch)
   - Executes: fetch("https://api.gamepulse.top/api/games/today")
   ↓
5. Backend query re-executes (Steps 7-11 from Workflow 1)
   ↓
6. New data arrives:
   - React Query compares to cached data
   - If different: triggers React re-render (scores updated, new games added)
   - If identical: no re-render (optimization)
   ↓
7. GameList.tsx updates with latest scores
   ↓
8. Timer resets, will refetch again in 15 minutes
   ↓
9. [Repeats until user closes tab]
```

**Workflow 3: Error Handling - Database Connectivity Failure**

```
1. User loads page, useGamesQuery() executes
   ↓
2. Backend receives request, attempts database query
   ↓
3. PostgreSQL connection fails (database container down, network issue)
   ↓
4. SQLModel raises OperationalError
   ↓
5. FastAPI exception handler catches error:
   - Logs structured error with stack trace (structlog)
   - Returns HTTP 500 with { "detail": "Database connection failed" }
   ↓
6. TanStack Query receives 500 response:
   - Updates query status: "error"
   - Initiates retry logic (retry: 3 with exponential backoff)
   ↓
7. Retry 1 (after 1 second):
   - Re-executes fetch
   - If still failing → Retry 2 (after 2 seconds)
   - If still failing → Retry 3 (after 4 seconds)
   ↓
8. All retries exhausted:
   - Query status remains "error"
   - GameList.tsx renders error UI:
     "Failed to load games. Please refresh the page or try again later."
   ↓
9. User sees friendly error message (no stack traces exposed)
```

**Workflow 4: Health Check During Deployment**

```
1. GitHub Actions workflow completes deployment (docker compose up -d)
   ↓
2. Smoke test step executes: curl https://api.gamepulse.top/api/health
   ↓
3. Traefik routes to backend /api/health endpoint
   ↓
4. Health handler checks:
   a. Process uptime (time.time() - start_time)
   b. Database connectivity: session.exec(select(1))
   ↓
5. All checks pass:
   - Returns HTTP 200: { "status": "healthy", "database": "connected", ... }
   ↓
6. GitHub Actions receives 200 response:
   - Deployment marked successful
   - Workflow completes with green checkmark
   ↓
7. If health check returns 503 or times out:
   - GitHub Actions fails deployment
   - Sends notification (deployment failed, manual intervention needed)
```

**Key Timing Constraints:**

- **Initial Page Load**: Target <2 seconds (database query <500ms, network latency <1.5s)
- **Polling Interval**: 900 seconds (15 minutes) - matches Dagster NCAA game ingestion cadence
- **Health Check Timeout**: 10 seconds (GitHub Actions smoke test)
- **API Request Timeout**: 30 seconds (TanStack Query default)
- **Retry Backoff**: 1s, 2s, 4s (exponential, 3 attempts max)

## Non-Functional Requirements

### Performance

**Target Metrics (from PRD NFR-1):**

- **API Response Time (P95)**: <500ms for GET /api/games/today
  - Database query execution: <200ms (dimensional JOIN on indexed surrogate keys)
  - Pydantic serialization: <100ms (typical game list: 20-50 games)
  - Network overhead: <200ms (single EC2 region, no CDN in MVP)
- **Frontend Initial Load**: <2 seconds (P95)
  - React bundle size: <500KB gzipped (Vite code-splitting, tree-shaking)
  - API call: <500ms (measured above)
  - React render: <1 second (minimal component tree, no virtualization needed for <50 games)
- **Database Query Performance**: <200ms for today's games query
  - Indexed on fact_game.game_date_key (B-tree index)
  - Indexed on dim_team.team_key (primary key, clustered)
  - JOIN strategy: nested loop (small result set, <100 rows typical)
- **Polling Overhead**: Negligible (background fetch, no UI blocking)
  - TanStack Query uses stale-while-revalidate (displays cached data during refetch)
  - Network activity: 1 request every 15 minutes = 0.0011 req/sec sustained

**Optimization Strategies:**

- **Database**: Surrogate key JOINs faster than natural key JOINs (integer comparison vs string)
- **Caching**: React Query 15-minute cache reduces unnecessary API calls
- **Bundle Size**: Lazy-load Chakra UI components only used (no full import)
- **Query Optimization**: Single query with JOINs (no N+1 problem)

**Acceptable Trade-Offs for Week 1 MVP:**

- No server-side caching (Redis) - database fast enough for portfolio demo scale (<50 games/day)
- No CDN for static assets - single region acceptable for demo
- No response compression beyond FastAPI defaults (gzip auto-enabled)
- No database query result caching - 15-minute polling means queries run max 4 times/hour

### Security

**Security Posture (from PRD NFR-3):**

- **Authentication**: None (public read-only portfolio demo - NFR-3.1)
  - Endpoints serve public NCAA game data (no user data, no PII)
  - Epic 1 removed authentication boilerplate from starter template
  - Acceptable for portfolio demonstration context
- **CORS Protection**: Explicit origin whitelist in FastAPI middleware
  - Development: `http://localhost:5173` (Vite dev server)
  - Production: `https://gamepulse.top`, `https://api.gamepulse.top`
  - Blocks requests from other origins (prevents embedding in malicious sites)
- **SQL Injection Prevention**: SQLModel parameterized queries
  - ORM prevents raw SQL injection via Pydantic validation
  - All query inputs type-checked (date_key: int, no string interpolation)
- **XSS Protection**: React auto-escapes all content
  - No `dangerouslySetInnerHTML` usage
  - Team names, scores sanitized by Pydantic schemas
- **Rate Limiting**: None in MVP (acceptable for portfolio demo)
  - Future: nginx rate limiting (100 req/min per IP) if abuse detected
  - Current risk: Low (no write endpoints, no auth to brute-force)
- **HTTPS**: Enforced via Traefik Let's Encrypt SSL (Epic 1 infrastructure)
  - All production traffic encrypted in transit
  - Development uses HTTP (localhost acceptable)

**Security Trade-Offs:**

- **No API keys**: Public endpoints acceptable for public NCAA data
- **No input validation beyond types**: Date parameter (future) will use Pydantic date validation
- **No DDoS protection**: t2.micro not critical infrastructure, portfolio demo acceptable downtime
- **Database credentials**: Stored in .env file (Docker Compose secrets sufficient for MVP)

### Reliability/Availability

**Target Availability (from PRD NFR-4):**

- **Uptime Target**: 95% monthly uptime (acceptable for portfolio demo - NFR-4.1)
  - Allows ~36 hours downtime/month (AWS maintenance, deployments, manual restarts)
  - No SLA commitments (not production service)
- **Graceful Degradation**: Frontend displays cached data during backend outages
  - React Query serves stale data up to 15 minutes old if API unreachable
  - User sees last successful data with staleness indicator (future: "Last updated 10 minutes ago")
- **Error Recovery**:
  - **Backend**: FastAPI exception handlers return structured errors (no stack traces to users)
  - **Frontend**: TanStack Query automatic retry (3 attempts, exponential backoff)
  - **Database**: PostgreSQL connection pooling (SQLModel AsyncSession) handles transient failures
- **Deployment Strategy**: Blue-green deployment via Docker Compose
  - `docker compose up -d --force-recreate` rebuilds containers
  - Health check ensures new containers healthy before GitHub Actions marks success
  - Rollback: `git revert` + redeploy (manual intervention, ~5 minutes)

**Failure Modes and Mitigations:**

| Failure Mode | Impact | Mitigation | MTTR |
|--------------|--------|------------|------|
| Database connection failure | API returns 500, frontend shows cached data | TanStack Query retries 3x, displays error after exhaustion | 5-10 min (manual container restart) |
| Backend container crash | API unreachable, frontend degrades to cache | Docker restart policy: `unless-stopped` auto-restarts | 1-2 min (auto) |
| Frontend build failure | Deployment blocked | GitHub Actions fails, previous version remains live | 5-10 min (fix code, redeploy) |
| Traefik SSL certificate expiry | HTTPS fails, HTTP works | Let's Encrypt auto-renewal (Epic 1), monitoring alert | 0 min (auto-renew) |
| t2.micro OOM | All containers killed | 4GB swap configured (Epic 1), Dagster memory limits | 2-5 min (auto-restart) |

**Data Loss Prevention:**

- **Read-Only Endpoints**: Epic 3 has no write operations, zero data loss risk from API failures
- **Database Backups**: Handled by Epic 1 (pg_dump daily), not Epic 3 scope
- **Cache Consistency**: React Query invalidates cache on refetch success (no stale data served after fresh data arrives)

### Observability

**Logging (from PRD NFR-4.3):**

- **Backend Structured Logging**: structlog JSON format for queryable logs
  - Log Level: INFO for requests, ERROR for exceptions
  - Context binding: request_id, endpoint, user_agent, response_time
  - Output: stdout (captured by Docker Compose logs, future: CloudWatch)
  - Example log entry:
    ```json
    {
      "timestamp": "2025-11-13T18:45:00Z",
      "level": "INFO",
      "event": "api_request_completed",
      "endpoint": "/api/games/today",
      "method": "GET",
      "status_code": 200,
      "response_time_ms": 245,
      "games_count": 28,
      "request_id": "abc-123"
    }
    ```
- **Frontend Logging**: Browser console (development), future: Sentry integration
  - React Query dev tools enabled in development (visualize cache state)
  - Error boundary component logs unhandled React errors
- **Database Query Logging**: SQLModel logs slow queries (>1s) in development
  - Production: disabled (performance overhead)

**Monitoring:**

- **Health Check Endpoint**: GET /api/health (200 = healthy, 503 = degraded)
  - GitHub Actions smoke test after deployment (validates backend + database connectivity)
  - Future: CloudWatch synthetic monitoring (5-minute checks)
- **Metrics (Future - Epic 9)**:
  - API response times (P50, P95, P99)
  - Error rates by endpoint
  - Cache hit ratio (React Query)
  - Database connection pool utilization
- **Alerting (Future - Epic 9)**:
  - Health check failures (>3 consecutive)
  - API error rate >5%
  - P95 latency >2 seconds

**Debugging Tools:**

- **FastAPI /docs**: Interactive Swagger UI for manual API testing
- **React Query DevTools**: Visualize cache state, query status, refetch triggers (development only)
- **Docker Logs**: `docker compose logs -f backend frontend` for real-time log streaming
- **Database Queries**: `docker compose exec db psql -U postgres -d app` for manual SQL investigation

**Traceability:**

- **Request IDs**: Unique identifier per API request (middleware-generated UUID)
- **Error Context**: Stack traces in logs (not exposed to users)
- **Git Commit**: Backend /health endpoint returns git SHA (identifies deployed version)
- **Deployment History**: GitHub Actions log preserves deployment timeline with commit links

## Dependencies and Integrations

**Backend Dependencies (Python - pyproject.toml):**

| Package | Version | Purpose | Epic 3 Usage |
|---------|---------|---------|--------------|
| fastapi[standard] | >=0.115.0 | Web framework with automatic OpenAPI docs | API routes, Pydantic validation, CORS middleware |
| sqlmodel | >=0.0.22 | Type-safe ORM (Pydantic + SQLAlchemy) | Database queries with dimensional JOINs |
| pydantic | >=2.9.0 | Data validation and serialization | Response schemas (GamePublic, HealthCheckResponse) |
| httpx | >=0.27.0 | Async HTTP client | Not used in Epic 3 (future: external API calls) |
| structlog | >=24.0.0 | Structured JSON logging | Request/error logging with context binding |
| alembic | >=1.13.0 | Database migrations | Not modified in Epic 3 (uses Epic 2 schema) |
| psycopg[binary] | >=3.2.0 | PostgreSQL driver | Database connectivity |
| sentry-sdk[fastapi] | >=2.0.0 | Error tracking (optional) | Future: Epic 9 monitoring |

**Frontend Dependencies (JavaScript - package.json):**

| Package | Version | Purpose | Epic 3 Usage |
|---------|---------|---------|--------------|
| react | ^18.2.0 | UI library | Component rendering |
| react-dom | ^18.2.0 | React DOM renderer | Browser rendering |
| @chakra-ui/react | ^3.8.0 | Component library | GameList UI components, skeleton loaders |
| @tanstack/react-query | ^5.28.14 | Server state management | API data fetching, caching, auto-refresh polling |
| @tanstack/react-router | 1.19.1 | Type-safe routing | Dashboard routing (minimal in MVP) |
| axios | 1.7.4 | HTTP client | Auto-generated API client requests |
| react-error-boundary | ^4.0.13 | Error handling | Catch React render errors |
| @emotion/react | ^11.14.0 | CSS-in-JS (Chakra dependency) | Chakra UI styling engine |
| next-themes | ^0.4.4 | Theme management | Future: dark mode (Epic 8) |

**Dev Dependencies:**

| Package | Version | Purpose |
|---------|---------|---------|
| vite | ^5.4.14 | Build tool (fast HMR, optimized bundles) |
| typescript | ^5.2.2 | Type checking |
| @hey-api/openapi-ts | ^0.57.0 | TypeScript client generation from OpenAPI schema |
| @biomejs/biome | 1.6.1 | Linter/formatter |
| pytest | >=8.3.0 | Backend testing framework |
| mypy | >=1.11.0 | Python static type checker |
| ruff | >=0.7.0 | Python linter/formatter |

**External Service Integrations:**

| Service | Purpose | Epic 3 Integration | Authentication |
|---------|---------|-------------------|----------------|
| PostgreSQL + TimescaleDB | Relational database with time-series extensions | Queries fact_game + dim_team tables | Connection string in .env (POSTGRES_PASSWORD) |
| AWS EC2 | Hosting infrastructure | Traefik routes traffic to containers | SSH key (admin only), SSM Session Manager |
| Traefik | Reverse proxy + SSL termination | Routes https://api.gamepulse.top → backend container | Let's Encrypt SSL cert (auto-renewed) |
| Docker Compose | Container orchestration | Manages backend, frontend, db, Dagster containers | Local Docker socket |
| GitHub Actions | CI/CD pipeline | Runs tests, builds images, deploys to EC2, smoke test | OIDC authentication to AWS |

**Internal Service Integrations:**

| From Service | To Service | Protocol | Data Flow | Epic 3 Changes |
|--------------|------------|----------|-----------|----------------|
| Frontend (React) | Backend (FastAPI) | HTTP/HTTPS | GET /api/games/today → JSON response | New endpoint + component |
| Frontend (React) | Backend (FastAPI) | HTTP/HTTPS | GET /api/health → JSON response | New health endpoint |
| Backend (FastAPI) | PostgreSQL | PostgreSQL protocol (asyncpg) | SELECT query via SQLModel ORM | New dimensional query |
| Browser | Traefik | HTTPS (port 443) | Static assets + API proxy | CORS configuration |
| GitHub Actions | Backend (EC2) | HTTPS | Health check smoke test | New /api/health validation |

**Version Constraints and Compatibility:**

- **Python**: >=3.10 (FastAPI requires modern type hints)
- **Node**: >=18.0 (Vite requires ES modules support)
- **PostgreSQL**: 16.x (TimescaleDB 2.23.0 compatibility)
- **Docker Compose**: >=2.40.3 (watch mode support for hot reload)

**No New External Dependencies Added in Epic 3:**

Epic 3 uses existing dependencies from Epic 1 (FastAPI full-stack template) and Epic 2 (dimensional schema). Only new code: API routes, React components, TanStack Query hooks.

## Acceptance Criteria (Authoritative)

**From PRD Requirements FR-6 (Backend API) and FR-7 (Frontend Dashboard):**

**AC-3.1: Games Today Endpoint Functionality**
- GET /api/games/today endpoint returns HTTP 200 with valid JSON response
- Response contains list of games with game_key, game_id, game_date, game_time, game_status fields
- Each game includes nested home_team and away_team objects with team_name, primary_color, secondary_color
- Games filtered by today's date (game_date_key = YYYYMMDD format of current date)
- Games ordered chronologically by game_time ascending
- Response includes total_count field matching number of games in array
- Empty array returned if no games scheduled for today (valid response, not error)

**AC-3.2: Dimensional Model Integration**
- Query executes JOINs on fact_game with dim_team (twice: home and away)
- Uses surrogate key relationships (home_team_key, away_team_key → team_key)
- Filters dim_team.is_current = TRUE to respect SCD Type 2 pattern
- Team colors (primary_color, secondary_color) retrieved from dim_team, not hardcoded
- Conference names (team_group_name) included from flattened dim_team fields

**AC-3.3: CORS Configuration**
- CORS middleware configured in FastAPI main.py with explicit origin whitelist
- Development origin http://localhost:5173 allowed (Vite dev server)
- Production origins https://gamepulse.top and https://api.gamepulse.top allowed
- Preflight OPTIONS requests return HTTP 204 with proper Access-Control headers
- Cross-origin requests from non-whitelisted domains return HTTP 403 or blocked by browser

**AC-3.4: Health Check Endpoint**
- GET /api/health endpoint returns HTTP 200 when system healthy
- Response includes status field ("healthy" | "degraded" | "unhealthy")
- Response includes database field ("connected" | "disconnected")
- Database connectivity validated via SELECT 1 query before responding
- Returns HTTP 503 if database connection fails
- Response includes uptime_seconds (process runtime) and timestamp fields

**AC-3.5: Frontend Game List Display**
- React Dashboard component renders without errors on page load
- GameList component displays all games returned from API
- Each game card shows home team name and away team name
- Team colors applied as background or border styling (visual verification)
- Game status badge displays "scheduled" | "live" | "final" appropriately
- Scores displayed when available (home_score, away_score), "vs" shown when null
- Loading skeleton displayed while initial API request in progress

**AC-3.6: Auto-Refresh Polling**
- TanStack Query hook configured with refetchInterval: 900000ms (15 minutes)
- Background refetch occurs every 15 minutes while page remains open
- No loading spinner shown during background refetch (stale-while-revalidate pattern)
- UI updates automatically when new data arrives (scores changed, new games added)
- Polling stops when user navigates away from page (cleanup on unmount)

**AC-3.7: Error Handling and Resilience**
- Frontend displays user-friendly error message when API returns 500
- TanStack Query retries failed requests 3 times with exponential backoff (1s, 2s, 4s)
- Cached data remains visible during temporary API outages (up to 15 min staleness)
- Error boundary catches unhandled React errors and displays fallback UI
- Backend logs errors with structlog (stack trace, request context) but doesn't expose to users

**AC-3.8: Performance Requirements**
- API response time <500ms (P95) for GET /api/games/today measured via logs
- Frontend initial page load <2 seconds (P95) measured via browser DevTools
- Database query execution <200ms for today's games query (via PostgreSQL explain analyze)
- React bundle size <500KB gzipped (measured via Vite build output)

**AC-3.9: API Contract and Type Safety**
- OpenAPI schema auto-generated at /docs endpoint (Swagger UI accessible)
- TypeScript client generated from OpenAPI schema (no manual edits to frontend/src/client/)
- Pydantic response schemas enforce type validation (invalid data raises 422 errors)
- Frontend TypeScript compilation passes with no type errors

**AC-3.10: Deployment and Integration**
- GitHub Actions workflow deploys successfully after push to main
- Smoke test validates GET /api/health returns HTTP 200 after deployment
- CORS configuration works in production (browser console shows no CORS errors)
- Frontend can fetch games from production backend (https://api.gamepulse.top)
- Traefik routes traffic correctly (https://gamepulse.top → frontend, https://api.gamepulse.top → backend)

## Traceability Mapping

**Mapping: Acceptance Criteria → Tech Spec Sections → Components → Test Strategy**

| AC ID | PRD Requirement | Spec Section(s) | Component(s) | Test Idea |
|-------|----------------|----------------|--------------|-----------|
| AC-3.1 | FR-6.1 (Backend API - Game Data) | APIs and Interfaces, Data Models | `backend/app/api/routes/games.py::get_games_today()`, `backend/app/schemas/game.py::GameListResponse` | Integration test: Mock database with 5 games, call endpoint, assert 200 status, validate JSON schema matches Pydantic model |
| AC-3.2 | FR-6.1, Epic 2 Dimensional Model | Data Models (Query 1), System Architecture Alignment | `backend/app/api/routes/games.py` (dimensional JOIN query), `backend/app/models/game.py::FactGame`, `backend/app/models/team.py::DimTeam` | Unit test: Execute query with SQLite fixture, verify JOIN uses team_key surrogate keys, assert is_current filter applied |
| AC-3.3 | FR-7.2 (Frontend-Backend Integration), NFR-3.2 (CORS) | Security, APIs and Interfaces | `backend/app/main.py::CORSMiddleware` configuration | Integration test: Send OPTIONS preflight from allowed origin, assert 204 response with Access-Control-Allow-Origin header; Test rejected origin returns 403 |
| AC-3.4 | FR-6.2 (Health Check), NFR-4.3 (Monitoring) | APIs and Interfaces, Observability | `backend/app/api/routes/health.py::get_health()` | Integration test: Mock database connection success → assert 200 + "healthy"; Mock database failure → assert 503 + "unhealthy" |
| AC-3.5 | FR-7.1 (Frontend Display) | Services and Modules, Data Models | `frontend/src/components/GameList.tsx`, `frontend/src/hooks/useGamesQuery.ts` | E2E test (Playwright): Start backend, seed 3 games, load dashboard, assert 3 game cards rendered with team names visible |
| AC-3.6 | FR-7.3 (Auto-Refresh), NFR-1.4 (Data Freshness <15 min) | Workflows and Sequencing (Workflow 2), APIs and Interfaces | `frontend/src/hooks/useGamesQuery.ts` (refetchInterval: 900000) | Unit test (React Testing Library): Mock useQuery with fake timer, advance 15 min, assert refetch called; E2E: Load page, wait 15 min, verify network request made |
| AC-3.7 | FR-7.4 (Error Handling), NFR-4.2 (Graceful Degradation) | Reliability/Availability, Workflows (Workflow 3) | `frontend/src/hooks/useGamesQuery.ts` (retry: 3), `frontend/src/components/ErrorBoundary.tsx` | Unit test: Mock API failure, assert 3 retries with exponential backoff (1s, 2s, 4s); E2E: Stop backend, verify error message displayed, restart backend, verify recovery |
| AC-3.8 | NFR-1.1 (API Latency <500ms), NFR-1.2 (Page Load <2s) | Performance | Backend route handler, React bundle optimization | Performance test: Load test with 100 concurrent requests → measure P95 latency; Lighthouse CI for page load time |
| AC-3.9 | FR-6.3 (API Documentation), FR-7.5 (Type Safety) | APIs and Interfaces, Dependencies | OpenAPI schema generation, TypeScript client (`frontend/src/client/`), Pydantic schemas | Integration test: Generate OpenAPI schema, validate against JSON Schema spec; Type check: Run `tsc --noEmit` in CI, assert zero errors |
| AC-3.10 | NFR-5.1 (CI/CD Automation), NFR-4.1 (95% Uptime) | Reliability/Availability (Deployment Strategy), External Service Integrations | GitHub Actions workflow (`.github/workflows/deploy.yml`), Traefik reverse proxy | E2E deployment test: Push to main, monitor GitHub Actions logs, curl health endpoint, verify 200 response; Manual verification: Load https://gamepulse.top in browser |

**PRD Requirements Coverage:**

- **FR-6 (Backend API)**: Covered by AC-3.1, AC-3.2, AC-3.4, AC-3.9
- **FR-7 (Frontend Dashboard)**: Covered by AC-3.5, AC-3.6, AC-3.7, AC-3.9
- **NFR-1 (Performance)**: Covered by AC-3.8
- **NFR-3 (Security)**: Covered by AC-3.3
- **NFR-4 (Reliability)**: Covered by AC-3.4, AC-3.7, AC-3.10
- **NFR-5 (Deployment)**: Covered by AC-3.10

**Test Coverage Strategy:**

- **Unit Tests (pytest, React Testing Library)**: AC-3.2, AC-3.6, AC-3.7 (50% of ACs)
- **Integration Tests (FastAPI TestClient)**: AC-3.1, AC-3.3, AC-3.4, AC-3.9 (40% of ACs)
- **E2E Tests (Playwright)**: AC-3.5, AC-3.6, AC-3.7, AC-3.10 (40% of ACs)
- **Performance Tests (Load testing)**: AC-3.8 (10% of ACs)
- **Manual Verification**: AC-3.10 production HTTPS access (5% of ACs)

**Story-to-AC Mapping:**

- **Story 3.1 (Create /api/games/today endpoint)**: AC-3.1, AC-3.2, AC-3.3
- **Story 3.2 (Add health check endpoint)**: AC-3.4
- **Story 3.3 (Initialize React dashboard)**: AC-3.5 (partial)
- **Story 3.4 (Build game list component)**: AC-3.5
- **Story 3.5 (Add auto-refresh polling)**: AC-3.6, AC-3.7 (error handling)
- **All Stories**: AC-3.8 (performance), AC-3.9 (type safety), AC-3.10 (deployment)

## Risks, Assumptions, Open Questions

**Risks:**

| Risk ID | Risk Description | Impact (H/M/L) | Probability (H/M/L) | Mitigation Strategy |
|---------|-----------------|----------------|--------------------|--------------------|
| R-3.1 | CORS misconfiguration blocks production frontend access | High | Medium | Test CORS in staging environment before production deployment; Document CORS headers in deployment checklist; Fallback: temporarily allow all origins (*) if blocked, then fix quickly |
| R-3.2 | Database query performance degrades with 50+ games/day | Medium | Low | Monitor query execution times in logs; Add composite index on (game_date_key, game_time) if slow; Acceptable: Query still <500ms with 100 games based on Epic 2 testing |
| R-3.3 | t2.micro memory exhaustion crashes containers during high traffic | Medium | Medium | Rely on 4GB swap from Epic 1; Docker restart policy auto-recovers; Monitor with `docker stats`; Upgrade to t2.small ($18/mo) if persistent OOM |
| R-3.4 | No NCAA games during development (off-season testing) | Low | High (if developing June-October) | Use seed data SQL script with 10-20 fake games for testing; Dagster ingestion tested separately; Production launch timed for November (season start) |
| R-3.5 | TypeScript client generation fails after OpenAPI schema changes | Low | Low | CI workflow catches failures before merge; Rollback schema changes if generation breaks; Manual fix: edit openapi.json, regenerate |
| R-3.6 | React Query cache staleness confuses users (scores don't update) | Low | Medium | Display "Last updated" timestamp (deferred to Epic 8); Document 15-min refresh interval in user testing; Manual refresh always available (browser reload) |

**Assumptions:**

| Assumption ID | Assumption Description | Validation Strategy | Impact if Invalid |
|--------------|----------------------|---------------------|-------------------|
| A-3.1 | Epic 2 completed successfully: fact_game + dim_team tables exist and populated | Query database schema before starting Epic 3; Run `\dt` in psql to verify tables | **BLOCKER** - Cannot proceed without dimensional model; Must complete Epic 2 first |
| A-3.2 | Dagster NCAA game ingestion working and populating data every 15 minutes | Check Dagster UI for successful runs; Query fact_game for recent games | **BLOCKER** - No data to display; Epic 3 becomes untestable; Must fix Dagster first |
| A-3.3 | FastAPI template includes CORS middleware by default | Review starter template main.py file | Low impact - Add CORS manually in 5 minutes if missing |
| A-3.4 | Chakra UI provides sufficient components for basic game list (no custom CSS needed) | Prototype GameList component in Story 3.4 | Low impact - Fall back to basic HTML/CSS if Chakra insufficient; Defer polish to Epic 8 |
| A-3.5 | NCAA Men's Basketball season active during development (November-April) | Check NCAA calendar; November 2025 = season start | Medium impact - Use seed data for testing; Production launch delayed until season starts |
| A-3.6 | Production domain gamepulse.top DNS and SSL already configured (Epic 1) | Verify `curl https://gamepulse.top` returns 200 or redirects correctly | Medium impact - Configure DNS/SSL before Epic 3 deployment; 1-2 hour delay |
| A-3.7 | TanStack Query sufficient for all caching/polling needs (no custom polling logic) | Review React Query docs; Prototype auto-refresh in Story 3.5 | Low impact - React Query widely adopted, proven solution; Edge case: write custom polling with setInterval if needed |

**Open Questions:**

| Question ID | Question | Decision Maker | Status | Impact |
|-------------|----------|---------------|--------|--------|
| Q-3.1 | Should Epic 3 include basic dark mode toggle or defer to Epic 8? | Product Owner (Philip) | **RESOLVED** - Defer to Epic 8 (Out of scope per Objectives) | Low - Week 1 timeline constraint; Light mode acceptable for MVP |
| Q-3.2 | Is mobile responsiveness required for Epic 3 or Epic 8 enhancement? | Product Owner (Philip) | **RESOLVED** - Basic responsiveness in Epic 3 using Chakra UI responsive props (In scope per Objectives) | Medium - Portfolio interviews may demo on mobile; Chakra provides responsive out-of-box |
| Q-3.3 | Should filtering by conference be included in Epic 3 game list? | Product Owner (Philip) | **RESOLVED** - Out of scope (per Objectives: "chronological order only") | Low - Filtering deferred to Epic 8; Chronological display sufficient for MVP |
| Q-3.4 | What happens if no games scheduled today? Display message vs empty list? | UX Designer / SM | **OPEN** - Recommend: "No games scheduled for today. Check back tomorrow!" message | Low - Edge case (rare during season); Empty list acceptable fallback |
| Q-3.5 | Should health endpoint include Dagster status check or just database? | Architect / SM | **RESOLVED** - Database only (per AC-3.4); Dagster monitoring deferred to Epic 9 | Low - Health check proves API functional; Dagster separate concern |
| Q-3.6 | Auto-refresh interval: 10 minutes vs 15 minutes? | Product Owner / Architect | **RESOLVED** - 15 minutes (per Objectives + Architecture: matches Dagster cadence) | Low - Alignment with data ingestion frequency; More frequent polling wastes bandwidth |

**Decisions Requiring Validation:**

1. **CORS Origins** - Confirm production domain before deployment (Q: https://gamepulse.top or https://www.gamepulse.top?)
2. **Error Message Copy** - Finalize user-facing error messages in Story 3.4/3.5 (currently placeholders)
3. **Game Status Badge Colors** - Visual design for "scheduled" (gray), "live" (green), "final" (blue) badges
4. **Loading Skeleton Design** - Number of skeleton cards to show (recommend: 6 cards matching typical game count)

## Test Strategy Summary

**Testing Pyramid for Epic 3:**

```
         /\
        /  \  E2E Tests (10% - Critical paths)
       /    \
      /------\  Integration Tests (40% - API contracts)
     /        \
    /----------\  Unit Tests (50% - Business logic)
```

**1. Unit Tests (Backend - pytest)**

**Target Coverage:** 80% code coverage for new modules

| Test Suite | Scope | Key Tests | Tools |
|------------|-------|-----------|-------|
| Query Logic Tests | `backend/app/api/routes/games.py` | - Test dimensional JOIN with mock data<br>- Verify date_key filtering (today vs tomorrow)<br>- Assert is_current filter applied<br>- Test empty result set handling | pytest, SQLModel in-memory database |
| Schema Validation Tests | `backend/app/schemas/game.py` | - Valid GamePublic serialization<br>- Invalid data raises ValidationError<br>- Nested TeamInfo validation<br>- Null handling (optional fields) | pytest, Pydantic |
| Health Check Tests | `backend/app/api/routes/health.py` | - Database connected returns "healthy"<br>- Database error returns "unhealthy"<br>- Uptime calculation accurate | pytest, mock database connection |

**Sample Unit Test:**
```python
def test_get_today_games_filters_by_date(db_session):
    """Verify query only returns games matching today's date_key"""
    today_key = int(date.today().strftime("%Y%m%d"))
    tomorrow_key = today_key + 1

    # Insert games for today and tomorrow
    create_test_game(db_session, date_key=today_key)
    create_test_game(db_session, date_key=tomorrow_key)

    # Query should only return today's game
    results = get_today_games(db_session)
    assert len(results) == 1
    assert results[0].game_date_key == today_key
```

**2. Integration Tests (Backend - FastAPI TestClient)**

**Target Coverage:** All API endpoints with realistic request/response cycles

| Test Suite | Scope | Key Tests | Tools |
|------------|-------|-----------|-------|
| Games Endpoint Tests | GET /api/games/today | - HTTP 200 with valid JSON schema<br>- Response includes all required fields<br>- Total_count matches array length<br>- Empty array when no games | FastAPI TestClient, pytest fixtures |
| CORS Tests | CORS middleware | - Allowed origin returns Access-Control-Allow-Origin header<br>- OPTIONS preflight returns 204<br>- Rejected origin blocks request | TestClient, custom headers |
| Health Endpoint Tests | GET /api/health | - Returns 200 when healthy<br>- Returns 503 when database down<br>- Response includes all required fields | TestClient, mock database |

**Sample Integration Test:**
```python
def test_games_today_endpoint_returns_valid_schema(client, db_with_games):
    """Verify GET /api/games/today returns expected JSON structure"""
    response = client.get("/api/games/today")
    assert response.status_code == 200

    data = response.json()
    assert "games" in data
    assert "total_count" in data
    assert len(data["games"]) == data["total_count"]

    # Validate first game has required fields
    game = data["games"][0]
    assert all(key in game for key in ["game_key", "home_team", "away_team"])
```

**3. Integration Tests (Frontend - React Testing Library)**

**Target Coverage:** All React hooks and component interactions

| Test Suite | Scope | Key Tests | Tools |
|------------|-------|-----------|-------|
| useGamesQuery Hook Tests | `frontend/src/hooks/useGamesQuery.ts` | - Query fetches data on mount<br>- Refetch interval set to 900000ms<br>- Retry logic triggers on error<br>- Cache persists for 15 minutes | React Testing Library, jest fake timers, MSW (Mock Service Worker) |
| GameList Component Tests | `frontend/src/components/GameList.tsx` | - Renders loading skeleton initially<br>- Displays games after load<br>- Shows error message on failure<br>- Team colors applied correctly | React Testing Library, jest |

**Sample Frontend Test:**
```typescript
test('useGamesQuery refetches every 15 minutes', async () => {
  jest.useFakeTimers();
  const { result } = renderHook(() => useGamesQuery());

  // Wait for initial load
  await waitFor(() => expect(result.current.isSuccess).toBe(true));

  // Fast-forward 15 minutes
  jest.advanceTimersByTime(900000);

  // Verify refetch triggered
  await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
});
```

**4. End-to-End Tests (Playwright)**

**Target Coverage:** Critical user journeys from browser to database

| Test Suite | Scope | Key Tests | Execution Environment |
|------------|-------|-----------|----------------------|
| Happy Path Workflow | Full stack | 1. User loads https://gamepulse.top<br>2. Page loads within 2 seconds<br>3. Game list displays with team names<br>4. Auto-refresh works after 15 min (use setInterval mock) | Docker Compose (backend + frontend + db) |
| Error Recovery Workflow | Full stack | 1. User loads page<br>2. Backend stops mid-session<br>3. Error message displays<br>4. Backend restarts<br>5. Page recovers on next refetch | Docker Compose with controlled container stops |
| CORS Verification | Full stack | 1. Load frontend from production domain<br>2. Verify API requests succeed<br>3. Check browser console for CORS errors | Production-like environment (separate origins) |

**Sample E2E Test:**
```typescript
test('user sees games on dashboard', async ({ page }) => {
  // Seed database with test games
  await seedDatabase([
    { home_team: 'Duke', away_team: 'UNC', game_status: 'scheduled' }
  ]);

  // Navigate to dashboard
  await page.goto('http://localhost:5173');

  // Wait for game list to load
  await page.waitForSelector('[data-testid="game-card"]');

  // Verify game displayed
  await expect(page.locator('text=Duke')).toBeVisible();
  await expect(page.locator('text=UNC')).toBeVisible();
});
```

**5. Manual Testing Checklist**

| Test Case | Steps | Expected Result | Priority |
|-----------|-------|----------------|----------|
| Production HTTPS Access | 1. Open https://gamepulse.top in Chrome<br>2. Check SSL certificate | Green padlock, no warnings | **CRITICAL** |
| Mobile Responsiveness | 1. Open on iPhone/Android<br>2. Verify layout adapts | Game cards stack vertically, text readable | High |
| Cross-Browser Compatibility | 1. Test in Chrome, Firefox, Safari<br>2. Verify rendering consistent | No layout bugs, API calls work | Medium |
| Empty State Display | 1. Set system date to June (off-season)<br>2. Load dashboard | Empty list or "No games" message | Low |

**6. Performance Testing**

**Approach:** Load testing with k6 or Apache JMeter

- **Target:** 100 concurrent requests to GET /api/games/today
- **Success Criteria:** P95 latency <500ms, zero 5xx errors
- **Execution:** Local Docker Compose or staging environment
- **Frequency:** Before each deployment to production

**7. Continuous Integration (GitHub Actions)**

**Test Execution in CI:**

```yaml
# .github/workflows/deploy.yml (test job)
test-backend:
  runs-on: ubuntu-latest
  steps:
    - name: Run backend tests
      run: |
        cd backend
        uv run pytest -v --cov=app --cov-report=term
        uv run mypy .
        uv run ruff check .

test-frontend:
  runs-on: ubuntu-latest
  steps:
    - name: Run frontend tests
      run: |
        cd frontend
        npm run lint
        npm test
        tsc --noEmit  # Type check
```

**Test Execution Timeline:**

- **Local Development:** Unit tests run on file save (watch mode)
- **Pre-Commit:** Linting + type checking via pre-commit hooks
- **CI Pipeline:** Full test suite on every push to main
- **Deployment:** E2E smoke test after production deployment

**Coverage Goals:**

- **Unit Tests:** 80% code coverage (measured by pytest-cov)
- **Integration Tests:** 100% endpoint coverage (all routes tested)
- **E2E Tests:** 100% critical path coverage (happy path + error recovery)

**Test Data Management:**

- **Unit/Integration Tests:** Pytest fixtures with in-memory SQLite database
- **E2E Tests:** Seed SQL script creates 10-20 realistic games with known teams
- **Production:** No test data - uses live Dagster ingestion from NCAA API

**Deferred to Epic 9 (Testing & Quality):**

- Load testing with realistic traffic patterns
- Security testing (penetration testing, OWASP top 10 verification)
- Accessibility testing (WCAG compliance)
- Cross-browser compatibility matrix (currently manual verification only)
