# Story 2.3: Create Game SQLModel and Database Migration

Status: done

## Story

As a developer,
I want to create the Game SQLModel with proper indexes and database migration,
So that I can store and query NCAA game data efficiently in the database.

## Acceptance Criteria

### AC1: Game SQLModel Created
- [x] File created: `backend/app/models/game.py`
- [x] `Game` SQLModel class includes all required fields from Epic 2 tech spec
- [x] Foreign keys defined: `home_team_id`, `away_team_id` reference `teams.team_id`
- [x] SQLModel includes proper type hints and Field definitions
- [x] Model follows FastAPI/SQLModel patterns from CLAUDE.md

### AC2: Database Indexes Added
- [x] Index created on `game_date` for date-based queries (GET /api/games/today)
- [x] Index created on `game_status` for status filtering (live, scheduled, final)
- [x] Index created on `sport` for multi-sport support
- [x] Index created on `game_type` for tournament classification

### AC3: Alembic Migration Generated and Applied
- [x] Alembic migration generated: `alembic revision --autogenerate -m "Add games table with indexes"`
- [x] Migration file created in `backend/app/alembic/versions/`
- [x] Migration reviewed for correctness (no unintended changes)
- [x] Migration applied: `alembic upgrade head` succeeds
- [x] Database table exists: `\d games` shows correct schema with indexes

### AC4: Model Validation and Testing
- [x] Can create Game instance with valid data
- [x] Foreign key constraint enforced (invalid team_id raises error)
- [x] Can query games using SQLModel ORM patterns
- [x] Model serializes correctly (SQLModel works as Pydantic schema)
- [x] Test game insertion successful in test database

## Tasks / Subtasks

### Task 2.3.1: Create Game SQLModel (AC: #1, #2)
- [x] Create file `backend/app/models/game.py`
- [x] Define `Game` SQLModel class with table=True
- [x] Add primary key: `game_id: str = Field(primary_key=True)`
- [x] Add sport field with index: `sport: str = Field(index=True, default="ncaam")`
- [x] Add game metadata fields: `game_date`, `game_start_time`, `game_end_time`, `venue`
- [x] Add team foreign keys: `home_team_id: str = Field(foreign_key="teams.team_id")`, `away_team_id: str = Field(foreign_key="teams.team_id")`
- [x] Add score fields: `home_score: int = Field(default=0)`, `away_score: int = Field(default=0)`
- [x] Add status tracking: `game_status: Optional[str] = Field(index=True)`, `game_clock: Optional[str]`
- [x] Add game type: `game_type: str = Field(default="regular_season", index=True)`
- [x] Add rivalry factor: `rivalry_factor: Optional[float]`
- [x] Add optional fields: `broadcast_network`, `attendance`
- [x] Add timestamps: `created_at`, `updated_at` with default_factory
- [x] Add proper type imports: `from sqlmodel import Field, SQLModel`, `from datetime import datetime`, `from typing import Optional`

### Task 2.3.2: Generate and Review Alembic Migration (AC: #3)
- [x] Run migration generation: `docker compose exec backend alembic revision --autogenerate -m "Add games table with indexes"`
- [x] Locate migration file in `backend/app/alembic/versions/`
- [x] Review migration for correctness:
  * Verify games table creation with all columns
  * Verify foreign key constraints on home_team_id, away_team_id
  * Verify indexes on sport, game_date, game_status, game_type
  * Check for any unintended changes to other tables
- [x] Edit migration if needed (fix any autogenerate issues)

### Task 2.3.3: Apply Migration and Verify Database Schema (AC: #3)
- [x] Apply migration: `docker compose exec backend alembic upgrade head`
- [x] Verify migration success (check for errors in output)
- [x] Connect to database: `docker compose exec db psql -U gamepulse -d gamepulse`
- [x] Verify table exists: `\d games`
- [x] Verify indexes: `\di` (list indexes, confirm idx_games_date, idx_games_status, idx_games_sport, idx_games_game_type)
- [x] Verify foreign keys: `\d games` (check FOREIGN KEY constraints)
- [x] Exit database: `\q`

### Task 2.3.4: Test Model Creation and Validation (AC: #4)
- [x] Write unit test in `backend/app/tests/models/test_game.py`
- [x] Test: Create valid Game instance with required fields
- [x] Test: Verify SQLModel works as Pydantic schema (serialization)
- [x] Test: Foreign key constraint enforcement (invalid team_id)
- [x] Test: Default values applied correctly (home_score=0, sport="ncaam")
- [x] Test: Timestamps auto-generated (created_at, updated_at)
- [x] Run tests: `docker compose exec backend uv run pytest app/tests/models/test_game.py -v`
- [x] Verify all tests pass

### Task 2.3.5: Integration Test with Database (AC: #4)
- [x] Write integration test in `backend/app/tests/integration/test_game_model.py`
- [x] Test: Insert test game into database (requires teams from Story 2.1)
- [x] Test: Query game by game_id
- [x] Test: Query games by game_date (test index usage)
- [x] Test: Query games by game_status (test index usage)
- [x] Test: Update game scores (upsert pattern)
- [x] Run integration tests: `docker compose exec backend uv run pytest app/tests/integration/test_game_model.py -v`
- [x] Verify all tests pass

## Dev Notes

### Architecture Alignment

**From Epic 2 Tech Spec (Game Model Section):**
- Game SQLModel schema matches spec lines 328-379
- Multi-sport support via `sport` field (default "ncaam", supports "nfl", "nba" future)
- Rivalry factor field for excitement scoring (Epic 5 dependency)
- Game status enum: "scheduled", "live", "halftime", "final"
- Game type enum: "regular_season", "conference_tournament", "ncaa_tournament"
- Timestamps in UTC (datetime.utcnow())

**SQLModel Pattern (No Separate Pydantic Schemas):**
From Story 2.2 review findings (line 165): "Uses `Game` model directly since SQLModel models work as Pydantic schemas". This means:
- SQLModel `Game` class serves as BOTH database model AND Pydantic schema
- NO separate `GameCreate` / `GameUpdate` / `GameResponse` schemas needed
- Automatic serialization for FastAPI endpoints
- Reduces code duplication and maintains single source of truth

**Database Performance Optimization:**
- **Index on game_date**: Supports Epic 3's `GET /api/games/today` endpoint (filter by CURRENT_DATE)
- **Index on game_status**: Enables efficient filtering for live games dashboard
- **Index on sport**: Supports multi-sport expansion (NCAAM, NFL, NBA)
- **Index on game_type**: Enables tournament-specific queries (March Madness filtering)

### Learnings from Previous Story

**From Story 2-2-build-ncaa-client.md (Status: done)**

- **New Service Created**: `NCAAClient` class at `backend/app/services/ncaa_client.py` - use this for fetching game data
- **API Endpoint**: `https://site.web.api.espn.com/apis/v2/scoreboard/basketball/mens-college-basketball?dates={YYYYMMDD}`
- **Response Structure**: Returns JSON with `events[]` array, each event is a game with home/away teams, scores, status
- **Testing Setup**: Test suite at `backend/app/tests/services/test_ncaa_client.py` demonstrates httpx mocking patterns - follow for Game model tests
- **Architecture Compliance**: All code follows FastAPI/SQLModel patterns from CLAUDE.md (async/await, absolute imports, type hints)
- **SQLModel Pattern Established**: Use SQLModel models directly as Pydantic schemas (no separate schema files)
- **Dependencies Already Added**: httpx and tenacity already in pyproject.toml from Story 2.2

**Pending Review Items (if any)**: None - Story 2.2 approved with zero action items

### Project Structure Notes

**File Locations:**
- Game model: `backend/app/models/game.py` (create new)
- Alembic migrations: `backend/app/alembic/versions/` (autogenerated)
- Unit tests: `backend/app/tests/models/test_game.py` (create new)
- Integration tests: `backend/app/tests/integration/test_game_model.py` (create new)

**Dependencies (Already Satisfied):**
- SQLModel: Already configured in Epic 1
- Alembic: Already configured in Epic 1
- PostgreSQL with teams table: Created in Stories 1.4 and 2.1
- Team dimensional data: Seeded in Story 2.1 (Duke, UNC, etc.)

**Migration Strategy:**
- Use `alembic revision --autogenerate` for migration generation
- Always review autogenerated migrations before applying
- Alembic detects SQLModel table changes automatically
- Foreign key constraints will be created automatically

### References

- [Epic 2 Tech Spec: Game Model Section](../tech-spec-epic-2.md#data-models-and-contracts) (lines 328-379)
- [Epic 2 Tech Spec: AC-3 Game Model Requirements](../tech-spec-epic-2.md#acceptance-criteria-authoritative) (lines 903-913)
- [Story 2.2: NCAA API Client](./2-2-build-ncaa-client.md) - SQLModel pattern established
- [Story 2.1: Dimensional Data](./2-1-create-dimensional-data.md) - Teams table for foreign keys
- [CLAUDE.md: Database Migrations](../CLAUDE.md#database--migrations) - Alembic workflow
- [Architecture: Database Schema](../architecture.md) - Overall schema design

## Definition of Done

- [x] Game SQLModel created with all required fields
- [x] Foreign keys defined for home_team_id, away_team_id
- [x] Database indexes created (game_date, game_status, sport, game_type)
- [x] Alembic migration generated and reviewed
- [x] Migration applied successfully (alembic upgrade head)
- [x] Database schema verified (\d games shows correct structure)
- [x] Unit tests written and passing (model creation, validation)
- [x] Integration tests written and passing (database operations)
- [x] Foreign key constraints enforced (tested with invalid team_id)
- [x] Code follows architecture patterns (SQLModel, type hints, async)
- [x] Changes committed to git

## Dev Agent Record

### Context Reference

- [Story Context XML](./2-3-create-game-model.context.xml) - Generated 2025-11-11

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

No blocking issues encountered.

### Completion Notes List

**Implementation Summary:**
- Game SQLModel and database migration were already complete from previous work
- Added comprehensive test coverage (6 unit tests + 8 integration tests)
- All tests passing (100% success rate)

**Key Findings:**
1. **Python 3.10 Compatibility Fix**: Updated Game model to use `datetime.utcnow` instead of `datetime.now(UTC)` for Python 3.10.19 compatibility
2. **Test Infrastructure**: Created `backend/app/tests/models/` and `backend/app/tests/integration/` directories with proper fixtures
3. **Database Indexes Verified**: Confirmed all required indexes exist (game_date, game_status, sport, game_type, composite teams)
4. **Foreign Key Constraints Tested**: Verified database enforces referential integrity for team_id foreign keys

**Test Coverage:**
- **Unit Tests** (`test_game.py`): 6 tests covering model instantiation, serialization, defaults, field types, and timestamps
- **Integration Tests** (`test_game_model.py`): 8 tests covering database insert/query, foreign key enforcement, index usage, and updates

**Technical Notes:**
- PostgreSQL stores timestamps as naive datetimes (TIMESTAMP WITHOUT TIME ZONE)
- Tests use transaction rollback for isolation (no test data persists)
- Sample team fixtures handle both seeded data and test data creation

### File List

**Created Files:**
- `backend/app/tests/models/test_game.py` (177 lines) - Unit tests for Game model
- `backend/app/tests/integration/test_game_model.py` (347 lines) - Integration tests for database operations
- `backend/app/tests/models/__init__.py` - Module marker
- `backend/app/tests/integration/__init__.py` - Module marker

**Modified Files:**
- `backend/app/models/game.py` - Fixed Python 3.10 compatibility (datetime.utcnow)
- `docs/stories/2-3-create-game-model.md` - Updated status to "done", marked all tasks complete
