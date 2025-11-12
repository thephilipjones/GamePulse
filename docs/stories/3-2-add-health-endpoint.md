# Story 3.2: Add Health Check Endpoint

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want a `/api/health` endpoint that reports system status,
So that I can monitor the application and diagnose issues.

---

## Acceptance Criteria

**Given** the application has multiple data sources (NCAA API, database)
**When** I create the `/api/health` endpoint
**Then** the endpoint:
- Path: `GET /api/health`
- Returns JSON with overall status: "healthy" | "degraded" | "unhealthy"
- Includes last update timestamp
- Reports status for each data source:
  - `ncaa_api`: Status, last poll timestamp, games tracked count
  - `database`: Connection status, table row counts
- Responds in <100ms

**And** status determination logic:
- **Healthy**: NCAA last poll <20 min ago, database connected
- **Degraded**: NCAA last poll 20-60 min ago (stale data but usable)
- **Unhealthy**: NCAA last poll >60 min ago or database unreachable

**And** I can test the endpoint: `curl http://localhost:8000/api/health` returns valid status

**And** the health check is used by AWS load balancer (if added later) and monitoring

---

## Prerequisites

- Story 2.4 (NCAA poller writes timestamps)
- Story 3.1 (API routes exist)

---

## Technical Notes

**Create File:** `backend/app/api/routes/health.py`

**Health Check Implementation:**
```python
from fastapi import APIRouter, Depends
from sqlmodel import AsyncSession, select, func
from datetime import datetime
from app.api.deps import get_session
from app.models.game import Game
from app.models.team import Team
from app.schemas.health import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_session)):
    """System health check"""

    try:
        # Query most recent game updated_at
        statement = select(func.max(Game.updated_at))
        result = await session.exec(statement)
        last_poll = result.one()

        # Calculate staleness in minutes
        staleness = (datetime.utcnow() - last_poll).total_seconds() / 60

        # Determine status
        if staleness < 20:
            status = "healthy"
        elif staleness < 60:
            status = "degraded"
        else:
            status = "unhealthy"

        # Get row counts
        games_count = await session.scalar(select(func.count(Game.game_id)))
        teams_count = await session.scalar(select(func.count(Team.team_id)))

        return HealthResponse(
            status=status,
            last_update=last_poll,
            sources={
                "ncaa_api": {
                    "status": "ok" if staleness < 20 else "degraded",
                    "last_poll": last_poll,
                    "games_tracked": games_count
                },
                "database": {
                    "status": "ok",
                    "row_counts": {
                        "games": games_count,
                        "teams": teams_count
                    }
                }
            }
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            last_update=None,
            error=str(e)
        )
```

**Create Pydantic Schema:** `backend/app/schemas/health.py`
```python
from pydantic import BaseModel
from datetime import datetime

class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    last_update: datetime | None
    sources: dict | None = None
    error: str | None = None
```

**Include Router:**
Edit `backend/app/api/main.py`:
```python
from app.api.routes import health

app.include_router(health.router, prefix="/api", tags=["health"])
```

**Performance Target:** <100ms response time

**Usage:**
- Story 1.5 deploy script: `curl /api/health` after deployment
- Future: AWS load balancer health checks
- Monitoring dashboards

---

## Definition of Done

- [ ] health.py route file created
- [ ] GET /api/health endpoint implemented
- [ ] Status determination logic correct
- [ ] Last poll timestamp queried
- [ ] Database row counts included
- [ ] HealthResponse schema created
- [ ] Router included in main app
- [ ] curl test returns valid status
- [ ] Response time <100ms verified
- [ ] Error handling for database unreachable
- [ ] Endpoint documented in OpenAPI docs
- [ ] Code follows architecture patterns
- [ ] Changes committed to git
