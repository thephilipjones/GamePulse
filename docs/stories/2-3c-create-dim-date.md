# Story 2-3c: Create and Seed dim_date Dimension Table

**Epic**: Epic 2 - Dimensional Foundation + Game Data Ingestion (Batch)
**Status**: Drafted
**Estimated Effort**: 2-3 hours
**Priority**: High (Foundation for time-based dimensional analysis)

## User Story

As a data engineer building a portfolio project,
I want to create a date dimension table with NCAA-specific attributes,
So that GamePulse can support time-based analysis (March Madness trends, weekend vs weekday) and demonstrate understanding of Kimball dimensional modeling date dimensions.

## Context

### Current State
GamePulse uses simple `DATE` or `TIMESTAMP` fields in `fact_game` table for temporal querying. While functional, this approach lacks:
- Pre-computed date attributes (day of week, month name, quarter)
- Domain-specific flags (is_march_madness, tournament_round)
- Efficient time-based GROUP BY operations (no need to extract month/year in queries)

### The Problem
- **No date dimension**: Time-based analysis requires expensive EXTRACT() calls in queries
- **Missing domain metadata**: No way to filter "March Madness games only" or "Sweet 16 weekend" without manual date ranges
- **Portfolio gap**: Date dimensions are a Kimball methodology staple - missing this demonstrates incomplete understanding
- **Query inefficiency**: Repeated date calculations (EXTRACT, date_trunc) instead of pre-computed attributes

### The Solution
Create a `dim_date` dimension table following classic Kimball patterns:
1. **Surrogate key**: `date_key INTEGER` (format: 20250311 for March 11, 2025)
2. **Natural key**: `full_date DATE UNIQUE` (actual calendar date)
3. **Standard attributes**: day_of_week, day_name, month, month_name, quarter, year, is_weekend
4. **Domain-specific attributes**: `is_march_madness BOOLEAN`, `tournament_round VARCHAR(50)`
5. **Seed data**: 2024-01-01 to 2026-12-31 (3 years, ~1,095 rows)

This enables queries like:
```sql
-- Games during March Madness Sweet 16
SELECT * FROM fact_game fg
JOIN dim_date dd ON fg.game_date_key = dd.date_key
WHERE dd.tournament_round = 'Sweet 16';
```

### Relationship to Other Stories
- **Story 2-1** (DONE): Created initial dimensional data structure
- **Story 2-3a** (DONE): Refactored to dimensional model (added FK placeholder `game_date_key`)
- **Story 2-3b** (DONE): Team metadata sync (uses `dim_team`)
- **Story 2-3c** (THIS): Create dim_date dimension table
- **Story 2-4** (NEXT): Dagster worker will populate `fact_game.game_date_key` when inserting games

### What's In Scope
- ✅ Create `dim_date` table schema with surrogate key `date_key`
- ✅ Add standard Kimball date attributes (day, month, quarter, year, day_of_week)
- ✅ Add domain-specific NCAA attributes (is_march_madness, tournament_round)
- ✅ Seed 3 years of dates (2024-2026, ~1,095 rows)
- ✅ Create Python seed script (not Alembic migration - too many rows)
- ✅ SQLModel model for dim_date
- ✅ Alembic migration to create table structure (script populates data)

### What's Out of Scope
- ❌ dim_time table (intraday analysis - Epic 11)
- ❌ Fiscal calendar attributes (fiscal year, fiscal quarter - not needed for NCAA)
- ❌ Holiday flags (not relevant for sports analytics)
- ❌ Populating `fact_game.game_date_key` (Story 2-4 handles this)
- ❌ Historical date backfill beyond 2024-2026

## Acceptance Criteria

### AC1: dim_date Table with Surrogate Key
**GIVEN** the dimensional model refactor from Story 2-3a
**WHEN** running the Alembic migration
**THEN** the system SHALL:
- Create table: `dim_date`
- Add surrogate key: `date_key INTEGER PRIMARY KEY` (format: YYYYMMDD, e.g., 20250311)
- Add natural key: `full_date DATE UNIQUE NOT NULL`
- Add standard Kimball attributes:
  - `day_of_week` INTEGER (1-7, where 1=Monday, 7=Sunday)
  - `day_name` VARCHAR(10) ("Monday", "Tuesday", etc.)
  - `day_of_month` INTEGER (1-31)
  - `month` INTEGER (1-12)
  - `month_name` VARCHAR(10) ("January", "February", etc.)
  - `quarter` INTEGER (1-4)
  - `year` INTEGER (2024, 2025, 2026)
  - `is_weekend` BOOLEAN (TRUE for Saturday/Sunday)
- Add NCAA-specific attributes:
  - `is_march_madness` BOOLEAN (TRUE for mid-March to early April)
  - `tournament_round` VARCHAR(50) ("First Four", "Round of 64", "Round of 32", "Sweet 16", "Elite 8", "Final Four", "Championship", NULL for non-tournament dates)
- All fields NOT NULL except `tournament_round` (NULL for non-tournament dates)

**Validation**:
- psql `\d dim_date` shows correct schema
- Query: `SELECT COUNT(*) FROM dim_date` = 0 (migration creates table, seed script populates)
- Verify surrogate key format: `SELECT date_key FROM dim_date WHERE full_date = '2025-03-11'` → 20250311

### AC2: Date Dimension Seed Script
**GIVEN** the dim_date table structure exists
**WHEN** running the seed script
**THEN** the system SHALL:
- Generate dates from 2024-01-01 to 2026-12-31 (3 years)
- Insert ~1,095 rows (365 * 3 = 1,095, accounting for leap year)
- Populate all attributes for each date:
  - `date_key`: YYYYMMDD integer format (20240101, 20240102, etc.)
  - `full_date`: DATE value (2024-01-01, 2024-01-02, etc.)
  - Standard attributes calculated from `full_date`
  - NCAA attributes based on tournament schedule rules
- Use batch insert (100 rows per transaction for performance)
- Script is idempotent: Re-running should UPSERT (ON CONFLICT DO NOTHING)

**Validation**:
- Run script: `python backend/app/scripts/seed_dim_date.py`
- Query: `SELECT COUNT(*) FROM dim_date` = 1,095 (or 1,096 if leap year in range)
- Verify March Madness flag: `SELECT * FROM dim_date WHERE is_march_madness = TRUE AND year = 2025` (expect ~25 days, mid-March to early April)
- Verify weekend flag: `SELECT * FROM dim_date WHERE is_weekend = TRUE AND month = 3 AND year = 2025` (expect ~9 Saturdays/Sundays in March)

### AC3: NCAA-Specific Attributes Logic
**GIVEN** the seed script is generating NCAA tournament metadata
**WHEN** calculating `is_march_madness` and `tournament_round`
**THEN** the system SHALL apply these rules:

**March Madness Date Range** (varies by year, approximate):
- Tournament starts: Selection Sunday (mid-March, ~March 13-15)
- Tournament ends: Championship Monday (early April, ~April 5-8)
- `is_march_madness` = TRUE for dates in this range

**Tournament Round Schedule** (typical schedule):
- **First Four**: Tuesday/Wednesday of tournament week (2 days)
- **Round of 64**: Thursday/Friday of tournament week (2 days)
- **Round of 32**: Saturday/Sunday of tournament week (2 days)
- **Sweet 16**: Thursday/Friday of second week (2 days)
- **Elite 8**: Saturday/Sunday of second week (2 days)
- **Final Four**: Saturday of third week (1 day, 2 games)
- **Championship**: Monday of third week (1 day)

**Implementation Strategy**:
For MVP, use hardcoded date ranges per year:
- 2024: March 19 - April 8
- 2025: March 18 - April 7
- 2026: March 17 - April 6

For tournament rounds, use day-of-tournament offset logic (Day 1 = First Four, Day 2-3 = Round of 64, etc.)

**Validation**:
- Query: `SELECT full_date, tournament_round FROM dim_date WHERE year = 2025 AND is_march_madness = TRUE ORDER BY full_date`
- Verify round progression: First Four → Round of 64 → Round of 32 → Sweet 16 → Elite 8 → Final Four → Championship
- Verify gaps between rounds (travel days) have NULL tournament_round but is_march_madness = TRUE

### AC4: SQLModel Integration
**GIVEN** the dim_date table exists
**WHEN** creating the SQLModel ORM model
**THEN** the system SHALL:
- Create file: `backend/app/models/dim_date.py`
- Define class: `class DimDate(SQLModel, table=True)`
- `__tablename__ = "dim_date"`
- Add all fields matching table schema
- Use `date_key: int = Field(primary_key=True)` (surrogate key, no auto-increment - manually assigned)
- Use `full_date: date = Field(unique=True, index=True)` (natural key)
- Add to `backend/app/models/__init__.py`: `from .dim_date import DimDate`

**Validation**:
- Import test: `python -c "from app.models import DimDate"` succeeds
- Type checking: `mypy backend/app/models/` passes
- SQLModel introspection: `DimDate.__tablename__ == "dim_date"`

### AC5: Foreign Key Integration with fact_game
**GIVEN** Story 2-3a added `game_date_key` column to fact_game
**WHEN** the dim_date table is created
**THEN** the system SHALL:
- Add foreign key constraint: `fact_game.game_date_key REFERENCES dim_date(date_key)`
- Allow NULL values initially (Story 2-4 will populate when inserting games)
- Add index on `fact_game.game_date_key` for join performance

**Validation**:
- psql `\d fact_game` shows FK constraint to dim_date(date_key)
- Test FK: Insert row in dim_date, insert fact_game with matching game_date_key (success)
- Test FK violation: Attempt to insert fact_game with non-existent game_date_key (error)

### AC6: Query Performance Validation
**GIVEN** dim_date is populated with 1,095 rows
**WHEN** executing time-based queries
**THEN** query performance SHALL:
- Simple filter by date_key: <5ms
- JOIN fact_game to dim_date: <50ms (with proper indexes)
- GROUP BY month_name: <10ms
- Filter by is_march_madness: <5ms

**Validation**:
- Run `EXPLAIN ANALYZE` on sample queries
- Verify index usage (should use date_key PK or full_date unique index)
- Verify no sequential scans on dim_date (table is small, but indexes should still be used)

## Implementation Tasks

### Task 1: Create Alembic Migration for dim_date Table
**File**: `backend/app/alembic/versions/XXXX_create_dim_date_table.py`

**Migration**:
```python
def upgrade() -> None:
    op.create_table(
        'dim_date',
        sa.Column('date_key', sa.INTEGER, primary_key=True),
        sa.Column('full_date', sa.DATE, nullable=False, unique=True),
        sa.Column('day_of_week', sa.INTEGER, nullable=False),
        sa.Column('day_name', sa.VARCHAR(10), nullable=False),
        sa.Column('day_of_month', sa.INTEGER, nullable=False),
        sa.Column('month', sa.INTEGER, nullable=False),
        sa.Column('month_name', sa.VARCHAR(10), nullable=False),
        sa.Column('quarter', sa.INTEGER, nullable=False),
        sa.Column('year', sa.INTEGER, nullable=False),
        sa.Column('is_weekend', sa.BOOLEAN, nullable=False),
        sa.Column('is_march_madness', sa.BOOLEAN, nullable=False),
        sa.Column('tournament_round', sa.VARCHAR(50), nullable=True),
    )
    op.create_index('ix_dim_date_full_date', 'dim_date', ['full_date'])
    op.create_index('ix_dim_date_year', 'dim_date', ['year'])
    op.create_index('ix_dim_date_month', 'dim_date', ['year', 'month'])
    op.create_index('ix_dim_date_is_march_madness', 'dim_date', ['is_march_madness'])

    # Add FK constraint from fact_game to dim_date
    op.create_foreign_key(
        'fk_fact_game_date',
        'fact_game',
        'dim_date',
        ['game_date_key'],
        ['date_key']
    )
    op.create_index('ix_fact_game_date_key', 'fact_game', ['game_date_key'])


def downgrade() -> None:
    op.drop_constraint('fk_fact_game_date', 'fact_game', type_='foreignkey')
    op.drop_index('ix_fact_game_date_key', 'fact_game')
    op.drop_table('dim_date')
```

### Task 2: Create DimDate SQLModel
**File**: `backend/app/models/dim_date.py`

```python
from datetime import date
from sqlmodel import SQLModel, Field

class DimDate(SQLModel, table=True):
    __tablename__ = "dim_date"

    # Surrogate key (manually assigned YYYYMMDD format, not auto-increment)
    date_key: int = Field(primary_key=True)

    # Natural key
    full_date: date = Field(unique=True, index=True)

    # Standard Kimball date attributes
    day_of_week: int  # 1-7 (Monday=1, Sunday=7)
    day_name: str = Field(max_length=10)  # "Monday", "Tuesday", etc.
    day_of_month: int  # 1-31
    month: int  # 1-12
    month_name: str = Field(max_length=10)  # "January", "February", etc.
    quarter: int  # 1-4
    year: int  # 2024, 2025, 2026

    # Standard flags
    is_weekend: bool

    # NCAA-specific attributes
    is_march_madness: bool
    tournament_round: str | None = Field(default=None, max_length=50)
```

### Task 3: Create Date Dimension Seed Script
**File**: `backend/app/scripts/seed_dim_date.py`

```python
from datetime import date, timedelta
from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models import DimDate

def calculate_tournament_round(dt: date) -> tuple[bool, str | None]:
    """
    Calculate if date is in March Madness and what tournament round.

    Returns:
        (is_march_madness, tournament_round)

    Tournament schedule (typical - adjust per year):
        Day 0 (Tue/Wed): First Four
        Day 2-3 (Thu/Fri): Round of 64
        Day 4-5 (Sat/Sun): Round of 32
        Day 7-8 (Thu/Fri): Sweet 16
        Day 9-10 (Sat/Sun): Elite 8
        Day 14 (Sat): Final Four
        Day 16 (Mon): Championship
    """
    # Hardcoded tournament start dates per year (Selection Sunday)
    tournament_starts = {
        2024: date(2024, 3, 19),  # Adjust to actual 2024 schedule
        2025: date(2025, 3, 18),  # Adjust to actual 2025 schedule
        2026: date(2026, 3, 17),  # Adjust to actual 2026 schedule
    }

    if dt.year not in tournament_starts:
        return False, None

    start_date = tournament_starts[dt.year]
    championship_date = start_date + timedelta(days=17)  # ~17 days from start to championship

    if dt < start_date or dt > championship_date:
        return False, None

    # Calculate day offset from tournament start
    day_offset = (dt - start_date).days

    # Map day offset to tournament round
    if day_offset in [0, 1]:  # Tue/Wed
        return True, "First Four"
    elif day_offset in [2, 3]:  # Thu/Fri
        return True, "Round of 64"
    elif day_offset in [4, 5]:  # Sat/Sun
        return True, "Round of 32"
    elif day_offset in [7, 8]:  # Thu/Fri (week 2)
        return True, "Sweet 16"
    elif day_offset in [9, 10]:  # Sat/Sun (week 2)
        return True, "Elite 8"
    elif day_offset == 14:  # Sat (week 3)
        return True, "Final Four"
    elif day_offset == 16:  # Mon (week 3)
        return True, "Championship"
    else:
        # Off days (travel, rest) - still March Madness period, but no games
        return True, None


def seed_dim_date():
    """Seed dim_date table with 2024-2026 dates."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)

    dates_to_insert = []
    current_date = start_date

    while current_date <= end_date:
        # Calculate date attributes
        date_key = int(current_date.strftime("%Y%m%d"))  # 20240101
        day_of_week = current_date.isoweekday()  # 1=Monday, 7=Sunday
        day_name = current_date.strftime("%A")  # "Monday"
        day_of_month = current_date.day
        month = current_date.month
        month_name = current_date.strftime("%B")  # "January"
        quarter = (month - 1) // 3 + 1  # Q1: Jan-Mar, Q2: Apr-Jun, etc.
        year = current_date.year
        is_weekend = day_of_week in [6, 7]  # Saturday=6, Sunday=7

        # Calculate NCAA tournament attributes
        is_march_madness, tournament_round = calculate_tournament_round(current_date)

        # Create DimDate instance
        dim_date = DimDate(
            date_key=date_key,
            full_date=current_date,
            day_of_week=day_of_week,
            day_name=day_name,
            day_of_month=day_of_month,
            month=month,
            month_name=month_name,
            quarter=quarter,
            year=year,
            is_weekend=is_weekend,
            is_march_madness=is_march_madness,
            tournament_round=tournament_round,
        )

        dates_to_insert.append(dim_date)
        current_date += timedelta(days=1)

    # Batch insert (100 rows per transaction for performance)
    with Session(engine) as session:
        for i in range(0, len(dates_to_insert), 100):
            batch = dates_to_insert[i:i + 100]
            for dim_date in batch:
                # Use merge for idempotency (ON CONFLICT DO NOTHING equivalent)
                session.merge(dim_date)
            session.commit()
            print(f"Inserted batch {i // 100 + 1} ({len(batch)} rows)")

    print(f"Seeded {len(dates_to_insert)} dates from {start_date} to {end_date}")


if __name__ == "__main__":
    seed_dim_date()
```

**Usage**:
```bash
cd backend
python -m app.scripts.seed_dim_date
```

### Task 4: Add Seed Script to Docker Entrypoint (Optional)
**File Modified**: `backend/docker-entrypoint.sh` or `backend/prestart.sh`

**Add to prestart script** (runs before FastAPI starts):
```bash
# Seed dim_date if not already seeded
python -m app.scripts.seed_dim_date || true  # Don't fail startup if seeding fails
```

**Alternative**: Manual seeding via docker exec
```bash
docker compose exec backend python -m app.scripts.seed_dim_date
```

### Task 5: Update __init__.py Imports
**File Modified**: `backend/app/models/__init__.py`

```python
from .dim_team import DimTeam
from .fact_game import FactGame
from .dim_date import DimDate  # NEW

__all__ = ["DimTeam", "FactGame", "DimDate"]
```

### Task 6: Add Tests
**File**: `backend/app/tests/models/test_dim_date.py`

```python
from datetime import date
from sqlmodel import Session, select
from app.models import DimDate

def test_create_dim_date(session: Session):
    """Test creating a dim_date record."""
    dim_date = DimDate(
        date_key=20250311,
        full_date=date(2025, 3, 11),
        day_of_week=2,  # Tuesday
        day_name="Tuesday",
        day_of_month=11,
        month=3,
        month_name="March",
        quarter=1,
        year=2025,
        is_weekend=False,
        is_march_madness=False,
        tournament_round=None,
    )
    session.add(dim_date)
    session.commit()

    assert dim_date.date_key == 20250311
    assert dim_date.full_date == date(2025, 3, 11)


def test_march_madness_attributes(session: Session):
    """Test March Madness attributes."""
    # Sweet 16 date (example)
    dim_date = DimDate(
        date_key=20250327,
        full_date=date(2025, 3, 27),
        day_of_week=4,  # Thursday
        day_name="Thursday",
        day_of_month=27,
        month=3,
        month_name="March",
        quarter=1,
        year=2025,
        is_weekend=False,
        is_march_madness=True,
        tournament_round="Sweet 16",
    )
    session.add(dim_date)
    session.commit()

    assert dim_date.is_march_madness == True
    assert dim_date.tournament_round == "Sweet 16"


def test_query_by_tournament_round(session: Session):
    """Test querying dates by tournament round."""
    # Seed multiple dates
    dates = [
        DimDate(date_key=20250327, full_date=date(2025, 3, 27), day_of_week=4, day_name="Thursday",
                day_of_month=27, month=3, month_name="March", quarter=1, year=2025,
                is_weekend=False, is_march_madness=True, tournament_round="Sweet 16"),
        DimDate(date_key=20250328, full_date=date(2025, 3, 28), day_of_week=5, day_name="Friday",
                day_of_month=28, month=3, month_name="March", quarter=1, year=2025,
                is_weekend=False, is_march_madness=True, tournament_round="Sweet 16"),
    ]
    for dim_date in dates:
        session.add(dim_date)
    session.commit()

    # Query Sweet 16 dates
    sweet_16_dates = session.exec(
        select(DimDate).where(DimDate.tournament_round == "Sweet 16")
    ).all()

    assert len(sweet_16_dates) == 2
    assert all(d.is_march_madness for d in sweet_16_dates)
```

## Technical Notes

### Surrogate Key Format: YYYYMMDD Integer

**Why integer instead of DATE?**
- Faster JOIN performance (integer comparison vs date comparison)
- Smaller foreign key columns in fact tables (4 bytes vs 8 bytes for timestamp)
- Human-readable: 20250311 is instantly recognizable as March 11, 2025
- Easy to generate: `int(current_date.strftime("%Y%m%d"))`

**Trade-off**: Slightly less intuitive than auto-increment SERIAL keys, but standard Kimball practice

### NCAA Tournament Schedule Variability

**Challenge**: Tournament dates vary by year (Selection Sunday shifts based on Easter, etc.)

**MVP Solution**: Hardcode tournament start dates per year in seed script

**Future Enhancement** (Epic 11):
- Fetch tournament schedule from NCAA API or third-party source
- Update dim_date.tournament_round dynamically
- Add `tournament_year` column to track multi-year history

### Query Examples Using dim_date

**All March Madness games in 2025:**
```sql
SELECT fg.*, ht.team_name AS home_team, at.team_name AS away_team, dd.tournament_round
FROM fact_game fg
JOIN dim_team ht ON fg.home_team_key = ht.team_key
JOIN dim_team at ON fg.away_team_key = at.team_key
JOIN dim_date dd ON fg.game_date_key = dd.date_key
WHERE dd.is_march_madness = TRUE AND dd.year = 2025
ORDER BY dd.full_date, fg.game_start_time;
```

**Games by tournament round:**
```sql
SELECT dd.tournament_round, COUNT(*) AS num_games
FROM fact_game fg
JOIN dim_date dd ON fg.game_date_key = dd.date_key
WHERE dd.tournament_round IS NOT NULL
GROUP BY dd.tournament_round
ORDER BY COUNT(*) DESC;
```

**Weekend vs weekday game distribution:**
```sql
SELECT dd.is_weekend, COUNT(*) AS num_games
FROM fact_game fg
JOIN dim_date dd ON fg.game_date_key = dd.date_key
GROUP BY dd.is_weekend;
```

## Dependencies

### Required Stories (Complete)
- ✅ Story 2-3a: Dimensional model refactor (added game_date_key column)

### Enables Future Stories
- Story 2-4: Dagster worker will populate `fact_game.game_date_key` when inserting games
- Epic 5: Time-based excitement trends ("Which tournament rounds are most exciting?")
- Epic 8: Dashboard filters by tournament round, weekend/weekday

### Blocked By
None - can be implemented immediately after Story 2-3a.

## Testing Strategy

### Unit Tests
- DimDate model validation (date_key format, field types)
- March Madness calculation logic (tournament_round assignment)
- Edge cases (leap year, year boundaries)

### Integration Tests
- Seed script execution (verify 1,095 rows inserted)
- Foreign key constraint (fact_game → dim_date)
- Query performance (EXPLAIN ANALYZE on sample queries)

### Manual Validation
- psql schema inspection (`\d dim_date`)
- Sample queries (tournament round filter, weekend filter)
- Verify March Madness dates align with actual NCAA tournament schedule

## Definition of Done

- [ ] Alembic migration created and tested (create table + FK constraint)
- [ ] `dim_date.py` SQLModel file created
- [ ] `__init__.py` imports updated
- [ ] Seed script `seed_dim_date.py` created and tested
- [ ] All 6 acceptance criteria validated
- [ ] Unit and integration tests passing
- [ ] Type checking passes (`mypy backend/app/models/`)
- [ ] Linting passes (`ruff check backend/app/`)
- [ ] 1,095 dates seeded (2024-2026)
- [ ] March Madness flags verified for 2024-2026
- [ ] Foreign key constraint working (fact_game → dim_date)
- [ ] Query performance validated (<50ms joins)
- [ ] Ready for Story 2-4 (Dagster will populate game_date_key)

## Notes
- This is a classic Kimball date dimension, essential for portfolio demonstrations
- Hardcoded tournament dates for MVP - can be enhanced later with dynamic API fetching
- Seed script is idempotent (can re-run without errors)
- Expected timeline: 2-3 hours for migration + model + seed script + testing
