# Story 3.2: Add Health Check Endpoint

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** ready-for-dev
**Assignee:** Claude Code (Dev Agent)
**Sprint:** Week 1
**Story Points:** 3
**Dependencies:** Story 3.1 (Games API endpoint), Epic 2 (Database schema)

---

## User Story

**As a** DevOps engineer deploying GamePulse
**I want** a `/api/health` endpoint that reports system status and database connectivity
**So that** I can monitor application health, validate deployments, and diagnose issues quickly

---

## Business Context

Story 3.2 provides the critical health monitoring endpoint required for the deployment smoke test (Story 1.5 GitHub Actions workflow) and future production monitoring. The GitHub Actions deploy.yml workflow executes `curl /api/health` after deployment to verify the application started successfully before marking the deployment complete. Without this endpoint, deployment failures would go undetected until manual verification.

**Why This Story Matters:**

- Enables automated deployment validation (GitHub Actions smoke test after `docker compose up`)
- Provides real-time system status visibility for troubleshooting
- Establishes observability foundation for future Epic 9 monitoring enhancements
- Demonstrates FastAPI best practices (health check pattern, dependency injection, structured logging)

**Impact of Delays:**

- Deployment automation incomplete (manual health verification required)
- No programmatic way to detect database connectivity issues
- Future Epic 9 monitoring work blocked (health check is prerequisite for CloudWatch alarms)

---

## Acceptance Criteria

### AC-3.4: Health Check Endpoint Functionality

**Given** the application is running with database connectivity
**When** I send GET request to `/api/health`
**Then** response returns HTTP 200 with valid JSON
**And** response includes fields: `status`, `version`, `database`, `uptime_seconds`, `timestamp`
**And** `status` field contains one of: `"healthy"`, `"degraded"`, `"unhealthy"`
**And** `database` field contains one of: `"connected"`, `"disconnected"`
**And** `version` field contains API version string (e.g., "1.0.0")
**And** `uptime_seconds` field contains process runtime as float

**Validation:**

```bash
# Manual API test
curl http://localhost:8000/api/health | jq .

# Expected output:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "uptime_seconds": 3600.5,
  "timestamp": "2025-11-14T18:45:00Z"
}
```

---

### AC-3.5: Database Connectivity Validation

**Given** PostgreSQL database is reachable
**When** health endpoint executes connectivity check
**Then** query executes `SELECT 1` to verify database connection
**And** `database` field returns `"connected"` if query succeeds
**And** `status` field returns `"healthy"` if database connected
**And** response returns HTTP 200

**Given** PostgreSQL database is unreachable (container stopped, network failure)
**When** health endpoint attempts database connectivity check
**Then** exception handler catches database error
**And** `database` field returns `"disconnected"`
**And** `status` field returns `"unhealthy"`
**And** response returns HTTP 503 Service Unavailable

**Validation:**

```bash
# Test healthy database
docker compose up -d db backend
curl http://localhost:8000/api/health
# Expect: HTTP 200, status="healthy", database="connected"

# Test disconnected database
docker compose stop db
curl http://localhost:8000/api/health
# Expect: HTTP 503, status="unhealthy", database="disconnected"
```

---

### AC-3.6: Performance Requirements

**Given** typical workload conditions
**When** health endpoint executes
**Then** P95 response time <100ms (faster than main API endpoints)
**And** database connectivity query executes in <50ms
**And** no expensive aggregations or table scans performed

**Validation:**

```bash
# Load test with 100 concurrent requests
ab -n 1000 -c 100 http://localhost:8000/api/health

# Verify P95 latency from results
# Expected: <100ms for 95th percentile
```

---

### AC-3.7: Structured Logging

**Given** health check endpoint is called
**When** request completes successfully
**Then** structured log emitted with fields: `endpoint="/api/health"`, `status`, `database`, `response_time_ms`
**And** log level is INFO for successful checks

**Given** database connectivity fails
**When** health check returns unhealthy status
**Then** structured log emitted with `exc_info=True` (full stack trace)
**And** log includes context: `endpoint`, `database_status`, `error` message
**And** log level is ERROR for failures
**And** no stack traces exposed to API clients (security best practice)

**Validation:**

```python
# Integration test: Capture logs during test
def test_health_endpoint_logging(client, caplog):
    response = client.get("/api/health")
    assert "endpoint" in caplog.records[0].extra
    assert "response_time_ms" in caplog.records[0].extra
```

---

### AC-3.8: GitHub Actions Integration

**Given** GitHub Actions deploy workflow completes `docker compose up -d`
**When** smoke test step executes `curl https://api.gamepulse.top/api/health`
**Then** health endpoint returns HTTP 200 within 10 seconds (deployment timeout)
**And** deployment marked successful in GitHub Actions
**And** workflow logs include health check response

**Given** health endpoint returns HTTP 503 or times out
**When** GitHub Actions smoke test executes
**Then** deployment fails with error message
**And** workflow sends failure notification

**Validation:**

```yaml
# Verify in .github/workflows/deploy.yml smoke test step
- name: Smoke test health endpoint
  run: |
    curl --fail --max-time 10 https://api.gamepulse.top/api/health
```

---

## Tasks / Subtasks

- [ ] **Task 1: Create Pydantic Response Schema** (AC: 3.4)

  - [ ] Create `backend/app/schemas/health.py` file (if not exists from Story 3.1)
  - [ ] Define `HealthCheckResponse` schema with fields: status, version, database, uptime_seconds, timestamp
  - [ ] Add docstring explaining status field values
  - [ ] Add unit test for Pydantic schema validation

- [ ] **Task 2: Implement Health Check Route Handler** (AC: 3.4, 3.5, 3.7)

  - [ ] Create `backend/app/api/routes/health.py` file
  - [ ] Implement `get_health()` function with database connectivity check
  - [ ] Execute `SELECT 1` query to verify database connection
  - [ ] Calculate process uptime (time since application start)
  - [ ] Return `HealthCheckResponse` with HTTP 200 when healthy
  - [ ] Return HTTP 503 when database disconnected
  - [ ] Add structured logging (info on success, error with exc_info=True on failure)
  - [ ] Add explicit context fields: endpoint="/api/health", database_status, response_time_ms

- [ ] **Task 3: Register Router in Main App** (AC: 3.4)

  - [ ] Edit `backend/app/api/main.py`
  - [ ] Import `health.router` from `app.api.routes.health`
  - [ ] Add `app.include_router(health.router, prefix="/api", tags=["health"])`
  - [ ] Verify endpoint accessible at `/api/health`

- [ ] **Task 4: Testing and Validation** (AC: All)

  - [ ] Write integration test: `test_health_endpoint_healthy()` with connected database
  - [ ] Write integration test: `test_health_endpoint_unhealthy()` with mocked database failure
  - [ ] Write integration test: `test_health_endpoint_logging()` with log capture
  - [ ] Manual test: `curl http://localhost:8000/api/health`
  - [ ] Manual test: Stop database, verify HTTP 503 response
  - [ ] Performance test: ab load test (P95 <100ms)
  - [ ] Verify OpenAPI docs at `/docs` include health endpoint

- [ ] **Task 5: GitHub Actions Integration** (AC: 3.8)

  - [ ] Verify `.github/workflows/deploy.yml` smoke test step exists
  - [ ] If missing, add smoke test step after deployment
  - [ ] Test smoke test locally: `curl --fail --max-time 10 http://localhost:8000/api/health`
  - [ ] Document health endpoint in deployment checklist

- [ ] **Task 6: Documentation and Deployment** (AC: All)
  - [ ] Add docstring to `get_health()` function
  - [ ] Document health endpoint usage in CLAUDE.md
  - [ ] Update story file with completion notes
  - [ ] Run pre-commit hooks (ruff, mypy)
  - [ ] Commit changes to git
  - [ ] Update sprint-status.yaml: 3-2-add-health-endpoint = "ready-for-dev" (after story-context)

---

## Dev Notes

### Architecture Patterns from Epic 3 Tech Spec

**Health Check Design** (from Tech Spec [APIs and Interfaces section](../tech-spec-epic-3.md#apis-and-interfaces)):

- Simple database connectivity validation: `SELECT 1` query (not expensive aggregations)
- Target response time: <100ms (faster than main API endpoints)
- HTTP status codes: 200 (healthy), 503 (unhealthy)
- Used by: GitHub Actions smoke test, future AWS health check monitoring
- No authentication required (public read-only endpoint)

**Error Handling Pattern** (from Tech Spec [Reliability section](../tech-spec-epic-3.md#reliability-availability)):

- Structured logging with `structlog` (JSON output for queryable logs)
- Context binding: `endpoint`, `database_status`, `response_time_ms`
- Stack traces in logs (`exc_info=True`), not exposed to clients
- HTTP 503 with generic message: `{ "status": "unhealthy", "database": "disconnected" }`

**Performance Optimization** (from Tech Spec [Performance section](../tech-spec-epic-3.md#performance)):

- Target: P95 <100ms (health check should be faster than main API)
- Simple query: `SELECT 1` (no table scans or aggregations)
- No caching needed (health check must reflect current state)

### Project Structure Alignment

**FastAPI Template Structure** (from Epic 1):

```
backend/app/
├── api/
│   ├── deps.py        # Dependency injection (get_session) - REUSE
│   ├── main.py        # Router aggregation - MODIFY (add health router)
│   └── routes/        # Route modules by resource
│       ├── games.py   # EXISTING (Story 3.1)
│       └── health.py  # NEW - This story creates this file
├── schemas/           # Pydantic API schemas
│   ├── game.py        # EXISTING (Story 3.1)
│   └── health.py      # NEW - This story creates this file (if not exists)
└── tests/api/routes/
    ├── test_games.py  # EXISTING (Story 3.1)
    └── test_health.py # NEW - This story creates this file
```

**Story 3.2 follows template convention:**

- `schemas/health.py` for API contract (separate from database models)
- `api/routes/health.py` for health check route
- `api/deps.py` provides `get_session` dependency (already exists from Story 3.1)

### Learnings from Previous Story (3-1-create-games-endpoint)

**From Story 3-1 Completion Notes:**

- ✅ **Use `exc_info=True` in error logging** - Applied in this story's error handler
- ✅ **Structured logging with explicit context fields** - Adding `endpoint`, `database_status`, `response_time_ms`
- ✅ **Specific exception handling** - Catch `(OperationalError, DatabaseError)` not generic `Exception`
- ✅ **FastAPI dependency override for testing** - Use for mocking database failures in tests
- ✅ **Performance validation script** - Health check requires <100ms (even faster than games endpoint)

**Testing Patterns from Story 3-1:**

- Integration tests with FastAPI TestClient preferred over complex mocking
- Use dependency override pattern for mocking database failures
- Manual curl tests for smoke testing
- Load testing with Apache Bench (ab) for performance validation
- Avoid greenlet dependency issues (use standard pytest fixtures)

**Files to Reuse (Story 3.1 artifacts):**

- `backend/app/api/deps.py::get_session` - Database session dependency injection
- `backend/app/api/main.py` - Router registration pattern (same as games router)
- `backend/app/tests/conftest.py` - Test fixtures for database and client
- Testing patterns: FastAPI TestClient, dependency override, log capture

**Code Quality from Story 3-1 Code Review:**

- Specific database exceptions: `from sqlalchemy.exc import OperationalError, DatabaseError`
- Explicit log context fields: endpoint, request_id (from query param)
- Pydantic schema validation unit tests with `pytest.raises(ValidationError)`
- Performance validation bash script for CI/CD integration

### Code Examples from Tech Spec

**Health Check Implementation** (from Tech Spec [APIs section](../tech-spec-epic-3.md#apis-and-interfaces)):

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import OperationalError, DatabaseError
from datetime import datetime
from app.api.deps import get_session
from app.schemas.health import HealthCheckResponse
import time
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Store application start time for uptime calculation
APP_START_TIME = time.time()

@router.get("/health", response_model=HealthCheckResponse)
async def get_health(
    session: Session = Depends(get_session),
    request_id: str | None = None
) -> HealthCheckResponse:
    """
    System health check endpoint.

    Validates database connectivity and returns system status.
    Used by GitHub Actions smoke test and future monitoring.

    Returns:
        HealthCheckResponse: System health status with database connectivity

    Raises:
        HTTPException: 503 if database unreachable
    """
    start_time = time.time()

    try:
        # Simple database connectivity check
        result = session.exec(select(1)).one()
        database_status = "connected" if result == 1 else "disconnected"
        overall_status = "healthy" if database_status == "connected" else "unhealthy"

        uptime = time.time() - APP_START_TIME
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        logger.info(
            "health_check_completed",
            extra={
                "endpoint": "/api/health",
                "status": overall_status,
                "database": database_status,
                "response_time_ms": response_time,
                "request_id": request_id or "unknown"
            }
        )

        return HealthCheckResponse(
            status=overall_status,
            version="1.0.0",
            database=database_status,
            uptime_seconds=uptime,
            timestamp=datetime.utcnow()
        )

    except (OperationalError, DatabaseError) as e:
        uptime = time.time() - APP_START_TIME
        response_time = (time.time() - start_time) * 1000

        logger.error(
            "health_check_failed",
            exc_info=True,
            extra={
                "endpoint": "/api/health",
                "database_status": "disconnected",
                "response_time_ms": response_time,
                "error": str(e),
                "request_id": request_id or "unknown"
            }
        )

        raise HTTPException(
            status_code=503,
            detail="Service unavailable - database connection failed"
        )
```

**Expected Response Example** (from Tech Spec [APIs section](../tech-spec-epic-3.md#apis-and-interfaces)):

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "uptime_seconds": 3600.5,
  "timestamp": "2025-11-14T18:45:00Z"
}
```

**Error Response Example** (HTTP 503):

```json
{
  "detail": "Service unavailable - database connection failed"
}
```

### References

**Tech Spec Sections:**

- [APIs and Interfaces](../tech-spec-epic-3.md#apis-and-interfaces) - Health endpoint specification, response schema
- [Workflows and Sequencing](../tech-spec-epic-3.md#workflows-and-sequencing) - Workflow 4 (Health Check During Deployment)
- [Observability](../tech-spec-epic-3.md#observability) - Structured logging, monitoring requirements
- [Reliability/Availability](../tech-spec-epic-3.md#reliability-availability) - Graceful degradation, error recovery
- [Traceability Mapping](../tech-spec-epic-3.md#traceability-mapping) - AC-3.4 test strategies

**PRD Requirements:**

- [NFR-4.3](../PRD.md#nfr-4-reliability) - Monitoring and observability requirements
- [NFR-4.1](../PRD.md#nfr-4-reliability) - 95% uptime target requires health monitoring

**Architecture Document:**

- [API Contracts](../architecture.md#api-contracts) - Health endpoint specification
- [Logging Strategy](../architecture.md#logging-strategy) - Structured logging with structlog

**Previous Story:**

- [Story 3.1](./3-1-create-games-endpoint.md#dev-agent-record) - Error handling patterns, structured logging, testing approach

**GitHub Actions Deployment:**

- `.github/workflows/deploy.yml` - Smoke test step uses health endpoint

---

## Dev Agent Record

### Context Reference

- [Story Context XML](./3-2-add-health-endpoint.context.xml)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
