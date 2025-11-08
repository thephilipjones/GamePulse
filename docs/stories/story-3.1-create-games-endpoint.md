# Story 3.1: Create Basic /api/games/today Endpoint

**Epic:** Epic 3 - Basic API + Dashboard MVP
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want a FastAPI endpoint that returns today's games,
So that the frontend dashboard can display game data.

---

## Acceptance Criteria

**Given** games exist in the database from the NCAA poller
**When** I create the `/api/games/today` endpoint
**Then** the endpoint:
- Path: `GET /api/games/today`
- Returns JSON array of today's games (game_date = current date)
- Includes team details (home_team and away_team nested objects)
- Response schema matches `GamesResponse` from Story 2.3
- Sorts games by game_date ascending (chronological order)
- Supports optional query param: `?limit=10` (default 10 games)

**And** the endpoint joins the games, teams tables to fetch team names and colors

**And** the endpoint responds in <500ms (performance target)

**And** I can test the endpoint:
- `curl http://localhost:8000/api/games/today` returns valid JSON
- `curl http://localhost:8000/api/games/today?limit=5` returns max 5 games

**And** the endpoint is documented in auto-generated FastAPI OpenAPI docs at `/docs`

**And** CORS configuration is set up for frontend-backend communication:
- Configure FastAPI CORS middleware in main.py
- Allow origins from `BACKEND_CORS_ORIGINS` environment variable (set in Story 1.1)
- Set `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`
- Verify frontend can successfully call API from http://localhost:5173
- Note: This prevents CORS errors when React dashboard calls backend API

---

## Prerequisites

- Story 2.4 (games exist in database)
- Story 2.3 (schemas exist)

---

## Technical Notes

**Create File:** `backend/app/api/routes/games.py`

**Endpoint Implementation:**
```python
from fastapi import APIRouter, Depends
from sqlmodel import AsyncSession, select
from datetime import date
from app.api.deps import get_session
from app.models.game import Game
from app.models.team import Team
from app.schemas.game import GamesResponse, GameResponse

router = APIRouter()

@router.get("/games/today", response_model=GamesResponse)
async def get_todays_games(
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
):
    """Fetch today's games with team details"""

    statement = (
        select(Game, Team.alias("home_team"), Team.alias("away_team"))
        .join(Team, Game.home_team_id == Team.team_id, isouter=False)
        .join(Team, Game.away_team_id == Team.team_id, isouter=False)
        .where(Game.game_date >= date.today())
        .order_by(Game.game_date)
        .limit(limit)
    )

    results = await session.exec(statement)
    games = results.all()

    return GamesResponse(
        games=[GameResponse.from_orm(game) for game in games],
        updated_at=datetime.utcnow()
    )
```

**Include Router in Main App:**
Edit `backend/app/api/main.py`:
```python
from app.api.routes import games

app.include_router(games.router, prefix="/api", tags=["games"])
```

**Response Model:**
```python
class GamesResponse(BaseModel):
    games: List[GameResponse]
    updated_at: datetime
```

**CORS Configuration:**
Ensure FastAPI CORS middleware allows frontend origin (add to backend/app/main.py):
```python
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,  # From .env: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Note:** `BACKEND_CORS_ORIGINS` was configured in Story 1.1 as environment variable

**Test with:**
- Swagger UI: `http://localhost:8000/docs`
- curl: `curl http://localhost:8000/api/games/today`

**Performance Target:** <500ms response time

---

## Definition of Done

- [ ] games.py route file created
- [ ] GET /api/games/today endpoint implemented
- [ ] Endpoint joins games and teams tables
- [ ] Response includes nested team details
- [ ] Query param limit works correctly
- [ ] Router included in main app
- [ ] CORS configured for frontend origin
- [ ] Endpoint documented in OpenAPI docs
- [ ] curl test returns valid JSON
- [ ] Response time <500ms verified
- [ ] Code follows architecture patterns (async/await, absolute imports)
- [ ] Changes committed to git
