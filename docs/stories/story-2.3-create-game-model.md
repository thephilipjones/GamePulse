# Story 2.3: Create Game SQLModel and Database Migration

**Epic:** Epic 2 - Game Data Ingestion (Batch)
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to create a Pydantic schema for game creation and update the Game model,
So that I can validate and store NCAA game data in the database.

---

## Acceptance Criteria

**Given** I need to store game data from NCAA API
**When** I create Pydantic schemas for game operations
**Then** I define these schemas in `backend/app/schemas/game.py`:
- `GameCreate`: Input schema for creating games (all required fields)
- `GameUpdate`: Input schema for updating game scores/status (optional fields)
- `GameResponse`: Output schema for API responses (includes team details)

**And** I verify the Game SQLModel from Story 1.3 matches the schema requirements

**And** I add indexes for performance:
- `CREATE INDEX idx_games_date ON games(game_date);`
- `CREATE INDEX idx_games_status ON games(game_status);`

**And** I generate an Alembic migration for indexes: `alembic revision -m "Add indexes to games table"`

**And** I apply the migration: `alembic upgrade head`

**And** I can create and query games using the schemas

---

## Prerequisites

- Story 1.3 (Game model exists)
- Story 2.1 (teams exist)

---

## Technical Notes

**Create File:** `backend/app/schemas/game.py`

**Best Practice:** Pydantic schemas separate from SQLModel (DB models ≠ API schemas)

**Schema Definitions:**

```python
from pydantic import BaseModel
from datetime import datetime

class GameCreate(BaseModel):
    """Input schema for creating games"""
    game_id: str
    home_team_id: str
    away_team_id: str
    game_date: datetime
    game_start_time: datetime

class GameUpdate(BaseModel):
    """Input schema for updating game scores/status"""
    home_score: int | None = None
    away_score: int | None = None
    game_status: str | None = None
    game_clock: str | None = None

class TeamResponse(BaseModel):
    team_id: str
    team_name: str
    primary_color: str | None

    class Config:
        from_attributes = True

class GameResponse(BaseModel):
    """Output schema for API responses"""
    game_id: str
    home_team: TeamResponse
    away_team: TeamResponse
    home_score: int | None
    away_score: int | None
    game_status: str
    game_clock: str | None

    class Config:
        from_attributes = True
```

**Add Indexes for Performance:**
```sql
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_status ON games(game_status);
```

**Rationale:**
- idx_games_date: Improves `GET /api/games/today` (filter by date)
- idx_games_status: Improves filtering by game status (live, scheduled, final)

**Generate Migration:**
```bash
docker-compose exec backend alembic revision -m "Add indexes to games table"
```

**Apply Migration:**
```bash
docker-compose exec backend alembic upgrade head
```

**Verify Indexes:**
```bash
docker-compose exec db psql -U gamepulse -d gamepulse -c "\d games"
```

**Migration File Location:** `backend/app/alembic/versions/`

---

## Definition of Done

- [ ] Schemas file created with GameCreate, GameUpdate, GameResponse
- [ ] TeamResponse schema created for nested team data
- [ ] Game SQLModel verified to match schema requirements
- [ ] Alembic migration generated for indexes
- [ ] Migration applied successfully
- [ ] Indexes verified in database
- [ ] Test game creation with schemas successful
- [ ] Test game query with nested team data successful
- [ ] Code follows architecture patterns
- [ ] Changes committed to git
