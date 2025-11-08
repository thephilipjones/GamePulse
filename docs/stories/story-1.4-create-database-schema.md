# Story 1.4: Create Initial Database Schema

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to create the foundational multi-sport database tables (teams, team_groups, team_rivalries, games),
So that I can store game data from multiple sports APIs (NCAAM, NFL, NBA) in a generic, extensible schema.

---

## Acceptance Criteria

**Given** the database is running with TimescaleDB
**When** I create SQLModel models for Team, TeamGroup, TeamRivalry, and Game
**Then** the models include all required fields per architecture schema:

**Team:**
- team_id (PK, format: "{sport}_{team_slug}", e.g., "ncaam_duke")
- sport (e.g., "ncaam", "nfl", "nba")
- team_name
- team_abbr
- team_group_id (FK to team_groups)
- primary_color
- secondary_color
- aliases (PostgreSQL ARRAY for fuzzy matching)
- created_at
- updated_at

**TeamGroup (generic: conferences, divisions, leagues):**
- team_group_id (PK, e.g., "ncaam_acc", "nfl_afc_west")
- team_group_name
- sport
- group_type (e.g., "conference", "division", "league")
- parent_group_id (FK to team_groups, enables nesting)
- level (hierarchy level: 1=top, 2=nested, etc.)
- created_at

**TeamRivalry (many-to-many rivalry mappings):**
- rivalry_id (PK, auto-increment)
- team_a_id (FK to teams)
- team_b_id (FK to teams)
- rivalry_factor (1.0 = normal, 1.5 = heated rivalry)
- rivalry_type (e.g., "historic", "geographic", "playoff")
- notes
- created_at
- updated_at
- UNIQUE constraint on (team_a_id, team_b_id)
- CHECK constraint (team_a_id < team_b_id)

**Game:**
- game_id (PK, format: "{sport}_{api_id}")
- sport (e.g., "ncaam", "nfl", "nba")
- game_date
- home_team_id (FK to teams)
- away_team_id (FK to teams)
- home_score
- away_score
- game_status
- game_clock
- game_start_time
- game_end_time
- venue
- game_type (VARCHAR enum: "regular_season", "postseason", "conference_tournament", "ncaa_tournament", etc.)
- rivalry_factor (cached from team_rivalries for query performance)
- broadcast_network (for BI analysis)
- attendance
- created_at
- updated_at

**And** I generate an Alembic migration: `alembic revision --autogenerate -m "Add multi-sport schema: teams, team_groups, team_rivalries, games"`

**And** I apply the migration: `alembic upgrade head`

**And** the tables exist in the database with correct columns, foreign key constraints, and indexes optimized for BI tools

**And** I can insert test rows into each table successfully (test NCAAM and NFL teams)

**And** TimescaleDB hypertables are prepared for time-series data:
- Create placeholder tables for `excitement_scores` and `betting_odds` (will be populated in Week 2)
- Convert these tables to TimescaleDB hypertables with 1-day chunk intervals
- Add to migration: `SELECT create_hypertable('excitement_scores', 'timestamp', chunk_time_interval => INTERVAL '1 day');`
- Add to migration: `SELECT create_hypertable('betting_odds', 'timestamp', chunk_time_interval => INTERVAL '1 day');`
- Note: These tables support time-series queries for sparkline visualizations

**And** database indexes are created for common query patterns:
- teams: sport, team_group_id
- team_groups: sport, parent_group_id
- games: sport, game_date, game_type, home_team_id, away_team_id

---

## Prerequisites

- Story 1.3 (database with TimescaleDB configured)

---

## Technical Notes

**Create Files:**
- `backend/app/models/team.py` - Team and TeamGroup SQLModel classes
- `backend/app/models/team_rivalry.py` - TeamRivalry SQLModel class
- `backend/app/models/game.py` - Game SQLModel class

**SQLModel Pattern (Team):**
```python
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import ARRAY, String
from datetime import datetime

class Team(SQLModel, table=True):
    __tablename__ = "teams"  # Explicit lowercase, plural

    team_id: str = Field(primary_key=True)  # Format: "{sport}_{team_slug}" e.g., "ncaam_duke"
    sport: str = Field(index=True)  # "ncaam", "nfl", "nba"
    team_name: str
    team_abbr: str | None = None
    team_group_id: str | None = Field(default=None, foreign_key="team_groups.team_group_id", index=True)
    primary_color: str | None = None
    secondary_color: str | None = None
    aliases: list[str] = Field(default_factory=list, sa_column=Column(ARRAY(String)))  # PostgreSQL array
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**SQLModel Pattern (TeamGroup):**
```python
class TeamGroup(SQLModel, table=True):
    __tablename__ = "team_groups"

    team_group_id: str = Field(primary_key=True)  # e.g., "ncaam_acc", "nfl_afc_west"
    team_group_name: str
    sport: str = Field(index=True)
    group_type: str  # "conference", "division", "league"
    parent_group_id: str | None = Field(default=None, foreign_key="team_groups.team_group_id", index=True)
    level: int = Field(default=1)  # Hierarchy level: 1=top, 2=nested
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

**SQLModel Pattern (TeamRivalry):**
```python
class TeamRivalry(SQLModel, table=True):
    __tablename__ = "team_rivalries"

    rivalry_id: int | None = Field(default=None, primary_key=True)
    team_a_id: str = Field(foreign_key="teams.team_id")
    team_b_id: str = Field(foreign_key="teams.team_id")
    rivalry_factor: float = Field(default=1.0)  # 1.0 = normal, 1.5 = heated
    rivalry_type: str | None = None  # "historic", "geographic", "playoff", "divisional"
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Note: UNIQUE(team_a_id, team_b_id) and CHECK(team_a_id < team_b_id)
    # should be added in Alembic migration
```

**SQLModel Pattern (Game):**
```python
class Game(SQLModel, table=True):
    __tablename__ = "games"

    game_id: str = Field(primary_key=True)  # Format: "{sport}_{api_id}"
    sport: str = Field(index=True)
    game_date: datetime = Field(index=True)
    home_team_id: str | None = Field(default=None, foreign_key="teams.team_id", index=True)
    away_team_id: str | None = Field(default=None, foreign_key="teams.team_id", index=True)
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    game_status: str | None = None
    game_clock: str | None = None
    game_start_time: datetime | None = None
    game_end_time: datetime | None = None
    venue: str | None = None
    game_type: str = Field(default="regular_season", index=True)  # Enum: regular_season, postseason, etc.
    rivalry_factor: float | None = None  # Cached from team_rivalries
    broadcast_network: str | None = None  # For BI analysis
    attendance: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Key Patterns:**
- Multi-sport support: team_id format `"{sport}_{team_slug}"`, game_id format `"{sport}_{api_id}"`
- PostgreSQL ARRAY type: Use `sa_column=Column(ARRAY(String))` for aliases field
- Foreign Keys: Use `Field(foreign_key="table_name.column_name")` syntax
- Indexes: Add `index=True` to frequently queried fields (sport, dates, foreign keys)
- Timestamps: `Field(default_factory=datetime.utcnow)`
- Nested hierarchies: TeamGroup.parent_group_id enables NFL conference→division or custom structures

**Run Migration:**
```bash
# From backend container
docker-compose exec backend alembic upgrade head
```

**Verify Tables:**
```bash
docker-compose exec db psql -U gamepulse -d gamepulse -c "\dt"
```

---

## Definition of Done

- [ ] SQLModel files created for Team, TeamGroup, TeamRivalry, Game
- [ ] All fields match multi-sport architecture specification
- [ ] team_id uses "{sport}_{team_slug}" format (e.g., "ncaam_duke")
- [ ] aliases field uses PostgreSQL ARRAY type
- [ ] TeamGroup supports hierarchical nesting with parent_group_id
- [ ] TeamRivalry has UNIQUE constraint and CHECK constraint (team_a_id < team_b_id)
- [ ] Game model uses game_type VARCHAR enum instead of is_tournament boolean
- [ ] Foreign key relationships defined correctly
- [ ] Database indexes created for BI tool optimization (sport, dates, foreign keys)
- [ ] Alembic migration generated
- [ ] Migration applied successfully
- [ ] Tables exist in database with correct schema and constraints
- [ ] Test rows inserted into each table (NCAAM and NFL examples)
- [ ] TimescaleDB hypertables created for excitement_scores and betting_odds
- [ ] Code follows architecture import patterns (absolute imports)
- [ ] Changes committed to git
