# Story 2.1: Create Team and Conference Dimensional Data

Status: ready-for-dev

## Story

As a developer,
I want to create static dimensional data for NCAA Men's Basketball teams and conferences,
So that games can be matched to teams and rivalry detection works correctly.

## Acceptance Criteria

### AC1: JSON Data Files Created

**Given** I need team and conference seed data for the database
**When** I create JSON configuration files
**Then** the following files exist with proper structure:

- [ ] `backend/app/data/teams.json` exists with minimum 20 NCAAM teams
- [ ] Each team has: `team_id`, `team_name`, `team_abbr`, `team_group_id`, `primary_color`, `secondary_color`, `aliases`
- [ ] `backend/app/data/conferences.json` exists with minimum 6 major conferences
- [ ] Each conference has: `team_group_id`, `group_name`, `sport`, `rivalry_factor`
- [ ] Conferences include: ACC, Big 12, SEC, Big Ten, Pac-12, Big East
- [ ] Team IDs follow format: `ncaam_{api_id}` (e.g., `ncaam_150` for Duke)
- [ ] Conference IDs follow format: `ncaam_{abbr}` (e.g., `ncaam_acc`)

### AC2: Data Quality Validation

**Given** I have created JSON data files
**When** I validate data quality
**Then** the data meets quality standards:

- [ ] All 20 teams have valid NCAA API team IDs (matching henrygd/ncaa-api format)
- [ ] All team colors are valid hex codes (e.g., `#003087` for Duke blue)
- [ ] Each team has at least 2 aliases for matching (e.g., ["Duke", "Blue Devils"])
- [ ] All teams belong to one of the 6 conferences (valid `team_group_id`)
- [ ] Rivalry pairs exist: Duke + UNC both have `team_group_id='ncaam_acc'`
- [ ] Conference rivalry factors are 1.2 for strong conferences (ACC, Big Ten, Big 12, SEC)

### AC3: Alembic Migration Created

**Given** I have JSON seed data files
**When** I create an Alembic migration
**Then** the migration is properly configured:

- [ ] Migration file created: `backend/app/alembic/versions/XXXX_seed_dimensional_data.py`
- [ ] Migration reads `backend/app/data/teams.json` and `backend/app/data/conferences.json`
- [ ] Uses upsert logic (INSERT ... ON CONFLICT DO UPDATE) for idempotency
- [ ] Inserts conferences first (parent table)
- [ ] Inserts teams second (child table with foreign key)
- [ ] Migration is reversible (downgrade deletes seeded data)

### AC4: Database Seeded Successfully

**Given** I have created migration
**When** I run `alembic upgrade head`
**Then** the database contains seeded data:

- [ ] Query `SELECT COUNT(*) FROM team_groups WHERE sport = 'ncaam'` returns >= 6
- [ ] Query `SELECT COUNT(*) FROM teams WHERE sport = 'ncaam'` returns >= 20
- [ ] Teams have proper foreign key references: `team_group_id` exists in `team_groups`
- [ ] Sample query works: `SELECT * FROM teams WHERE team_id = 'ncaam_150'` returns Duke
- [ ] Rivalry query works: Duke and UNC both have `team_group_id = 'ncaam_acc'`

## Tasks / Subtasks

### Task 2.1.1: Create Data Directory and JSON Structure (AC: #1)

- [ ] Create directory: `backend/app/data/`
- [ ] Create `.gitkeep` to ensure directory is tracked
- [ ] Create `backend/app/data/teams.json` with empty array structure:
  ```json
  {
    "teams": []
  }
  ```
- [ ] Create `backend/app/data/conferences.json` with empty array structure:
  ```json
  {
    "conferences": []
  }
  ```

**Acceptance:** Directory structure exists, JSON files are valid JSON

---

### Task 2.1.2: Populate Conferences JSON (AC: #1, #2)

- [ ] Add 6 major conferences to `backend/app/data/conferences.json`:
  - ACC (Atlantic Coast Conference) - rivalry_factor: 1.2
  - Big Ten - rivalry_factor: 1.2
  - Big 12 - rivalry_factor: 1.2
  - SEC (Southeastern Conference) - rivalry_factor: 1.2
  - Pac-12 - rivalry_factor: 1.0
  - Big East - rivalry_factor: 1.0
- [ ] Use format:
  ```json
  {
    "team_group_id": "ncaam_acc",
    "group_name": "Atlantic Coast Conference",
    "sport": "ncaam",
    "rivalry_factor": 1.2
  }
  ```
- [ ] Validate JSON syntax with `python -m json.tool conferences.json`

**Acceptance:** 6 conferences with proper structure and rivalry factors

---

### Task 2.1.3: Populate Teams JSON with Top 20 NCAA Teams (AC: #1, #2)

- [ ] Research NCAA API team IDs from henrygd/ncaa-api documentation
- [ ] Add 20 NCAA Men's Basketball teams to `backend/app/data/teams.json`:
  - Duke (team_id: ncaam_150, conference: ACC)
  - UNC (team_id: ncaam_153, conference: ACC)
  - Kansas (conference: Big 12)
  - Kentucky (conference: SEC)
  - Gonzaga (conference: WCC - note: add WCC to conferences)
  - UCLA (conference: Pac-12)
  - Villanova (conference: Big East)
  - Michigan State (conference: Big Ten)
  - Arizona (conference: Pac-12)
  - Purdue (conference: Big Ten)
  - (10 more teams from various conferences)
- [ ] Use format:
  ```json
  {
    "team_id": "ncaam_150",
    "team_name": "Duke",
    "team_abbr": "DUKE",
    "sport": "ncaam",
    "team_group_id": "ncaam_acc",
    "primary_color": "#003087",
    "secondary_color": "#FFFFFF",
    "aliases": ["Duke", "Blue Devils", "Duke Blue Devils"]
  }
  ```
- [ ] Find official team colors (hex codes) from team websites or ESPN
- [ ] Add at least 2 aliases per team for Reddit post matching
- [ ] Validate JSON syntax with `python -m json.tool teams.json`

**Acceptance:** 20 teams with valid IDs, colors, and aliases

---

### Task 2.1.4: Create Alembic Migration for Data Seeding (AC: #3)

- [ ] Generate Alembic migration file:
  ```bash
  docker compose exec backend alembic revision -m "seed_dimensional_data"
  ```
- [ ] Update migration file to read JSON files:
  ```python
  import json
  from pathlib import Path

  def upgrade():
      # Read JSON files
      data_dir = Path(__file__).parent.parent.parent / "app" / "data"
      with open(data_dir / "conferences.json") as f:
          conferences = json.load(f)["conferences"]
      with open(data_dir / "teams.json") as f:
          teams = json.load(f)["teams"]

      # Insert conferences (parent table first)
      for conf in conferences:
          op.execute(f"""
              INSERT INTO team_groups (team_group_id, group_name, sport, rivalry_factor)
              VALUES ('{conf['team_group_id']}', '{conf['group_name']}',
                      '{conf['sport']}', {conf['rivalry_factor']})
              ON CONFLICT (team_group_id) DO UPDATE
              SET group_name = EXCLUDED.group_name,
                  rivalry_factor = EXCLUDED.rivalry_factor
          """)

      # Insert teams (child table with FK)
      for team in teams:
          op.execute(f"""
              INSERT INTO teams (team_id, team_name, team_abbr, sport,
                                 team_group_id, primary_color, secondary_color, aliases)
              VALUES ('{team['team_id']}', '{team['team_name']}', '{team['team_abbr']}',
                      '{team['sport']}', '{team['team_group_id']}',
                      '{team['primary_color']}', '{team.get('secondary_color', '')}',
                      ARRAY{team['aliases']})
              ON CONFLICT (team_id) DO UPDATE
              SET team_name = EXCLUDED.team_name,
                  team_abbr = EXCLUDED.team_abbr,
                  team_group_id = EXCLUDED.team_group_id,
                  primary_color = EXCLUDED.primary_color,
                  secondary_color = EXCLUDED.secondary_color,
                  aliases = EXCLUDED.aliases
          """)

  def downgrade():
      op.execute("DELETE FROM teams WHERE sport = 'ncaam'")
      op.execute("DELETE FROM team_groups WHERE sport = 'ncaam'")
  ```
- [ ] Test migration syntax for SQL injection safety (use parameterized queries if possible)

**Acceptance:** Migration file reads JSON and inserts with upsert logic

---

### Task 2.1.5: Run Migration and Validate Database (AC: #4)

- [ ] Start database: `docker compose up -d db`
- [ ] Run migration: `docker compose exec backend alembic upgrade head`
- [ ] Verify migration success (no errors in output)
- [ ] Connect to database:
  ```bash
  docker compose exec db psql -U gamepulse -d gamepulse
  ```
- [ ] Run validation queries:
  ```sql
  -- Check conference count
  SELECT COUNT(*) FROM team_groups WHERE sport = 'ncaam';
  -- Expected: >= 6

  -- Check team count
  SELECT COUNT(*) FROM teams WHERE sport = 'ncaam';
  -- Expected: >= 20

  -- Verify Duke exists
  SELECT * FROM teams WHERE team_id = 'ncaam_150';

  -- Verify UNC exists
  SELECT * FROM teams WHERE team_id = 'ncaam_153';

  -- Verify rivalry pair (same conference)
  SELECT t.team_name, t.team_group_id
  FROM teams t
  WHERE t.team_id IN ('ncaam_150', 'ncaam_153');
  -- Expected: Both have team_group_id = 'ncaam_acc'

  -- Test foreign key constraint
  SELECT t.team_name, tg.group_name
  FROM teams t
  JOIN team_groups tg ON t.team_group_id = tg.team_group_id
  WHERE t.sport = 'ncaam'
  LIMIT 5;
  ```
- [ ] Verify all queries return expected results
- [ ] Test migration idempotency: Run `alembic upgrade head` again (should succeed with no duplicates)
- [ ] Test downgrade: `alembic downgrade -1` removes data
- [ ] Re-run upgrade: `alembic upgrade head` restores data

**Acceptance:** Database has 20 teams, 6 conferences, rivalry pairs validated

---

### Task 2.1.6: Document Data Loading Process (AC: #4)

- [ ] Update CLAUDE.md with data seeding instructions:
  ```markdown
  ## Data Seeding

  ### Initial Setup
  Dimensional data (teams, conferences) is seeded via Alembic migration.

  ### Re-run Data Seeding
  If you need to refresh dimensional data:
  ```bash
  # Downgrade to remove data
  docker compose exec backend alembic downgrade -1

  # Re-upgrade to restore data
  docker compose exec backend alembic upgrade head
  ```

  ### Update Frequency
  - Run once during Epic 2 deployment
  - Update occasionally for roster/conference changes (rare)
  ```
- [ ] Commit changes with message: "feat: Add NCAA team and conference dimensional data"

**Acceptance:** CLAUDE.md documents data seeding process

---

## Dev Notes

### Architecture Alignment

**Tech Spec Reference:**
- [Source: docs/tech-spec-epic-2.md - Lines 74-79: Dimensional Data Seed module]
- [Source: docs/tech-spec-epic-2.md - Lines 884-891: AC-1 Dimensional Data Seeding requirements]

**Database Schema Reference:**
- [Source: docs/architecture.md - Lines 489-510: Teams and conferences dimensional tables]
- Tables created in Story 1.4: `teams`, `team_groups`

**Alembic Migration Pattern:**
- Use upsert logic (INSERT ... ON CONFLICT DO UPDATE) for idempotency
- Migration can be run multiple times safely
- Downgrade removes only seeded data (WHERE sport = 'ncaam')

### Data Sources

**NCAA Team IDs:**
- Source: henrygd/ncaa-api team ID format (e.g., Duke = 150)
- Team IDs must match NCAA API responses for game matching to work
- Format: `ncaam_{api_id}` to namespace by sport

**Team Colors:**
- Primary source: Official team websites (athletics.duke.edu, etc.)
- Secondary source: ESPN team pages
- Format: Hex codes (e.g., `#003087` for Duke blue)

**Conference Rivalry Factors:**
- Strong conferences (ACC, Big Ten, Big 12, SEC): 1.2
- Other conferences: 1.0
- Future Epic 5 may add explicit rivalry pairs (e.g., Duke-UNC = 1.5)

### Project Structure Notes

**New Files Created:**
```
backend/app/data/
├── .gitkeep
├── teams.json              ← 20 NCAA teams with colors, aliases
└── conferences.json        ← 6 conferences with rivalry factors
```

**Files Modified:**
```
backend/app/alembic/versions/
└── XXXX_seed_dimensional_data.py   ← New migration
```

**No Conflicts:**
- Story 1.4 created `teams` and `team_groups` tables (schema exists)
- Story 2.1 populates those tables with seed data (no schema changes)

### Testing Strategy

**Unit Tests:** Not applicable (data seeding is integration-level)

**Integration Tests:**
- Test migration idempotency (run twice, verify no duplicates)
- Test downgrade (removes data cleanly)
- Test foreign key constraints (teams reference conferences)
- Test query patterns (JOIN teams + team_groups)

**Manual Validation:**
- Visual inspection of JSON data (valid hex codes, proper aliases)
- Database query validation (counts, foreign keys, rivalry pairs)

### Learnings from Previous Story

**From Story 1-7-ecr-remote-builds (Status: review)**

Story 1-7 completed the Epic 1 infrastructure foundation by implementing ECR-based remote Docker builds. Key context for Story 2.1:

**Infrastructure Available:**
- ✅ Docker Compose orchestration operational
- ✅ PostgreSQL 16 database running with TimescaleDB extension
- ✅ Alembic migrations working (tested in Stories 1.3, 1.4)
- ✅ GitHub Actions CI/CD pipeline operational
- ✅ ECR Public repository for backend container images

**Database Schema:**
- ✅ `teams` table exists (Story 1.4) - ready for data
- ✅ `team_groups` table exists (Story 1.4) - ready for data
- ✅ Foreign key relationship configured: `teams.team_group_id` → `team_groups.team_group_id`

**Development Environment:**
- ✅ Backend container accessible: `docker compose exec backend bash`
- ✅ Database container accessible: `docker compose exec db psql -U gamepulse -d gamepulse`
- ✅ Alembic commands working: `docker compose exec backend alembic upgrade head`

**No Breaking Changes:**
- Story 2.1 only **adds data**, does not modify schema
- No conflicts with Story 1-7's ECR infrastructure changes
- Migration pattern consistent with Story 1.4's database setup

**Files to Reference:**
- [backend/app/models/team.py](../../backend/app/models/team.py) - Team and TeamGroup SQLModel schemas
- [backend/app/alembic/env.py](../../backend/app/alembic/env.py) - Alembic configuration
- [docker-compose.yml](../../docker-compose.yml) - Database service configuration

[Source: docs/stories/1-7-ecr-remote-builds.md - Lines 980-1151: Completion notes and file list]

### References

**Primary Sources:**
- [Source: docs/tech-spec-epic-2.md - Epic 2 Technical Specification]
- [Source: docs/architecture.md - Lines 489-510: Database dimensional tables]
- [Source: docs/epics.md - Lines 51-72: Epic 2 overview and stories]

**External Documentation:**
- [henrygd/ncaa-api Documentation](https://github.com/henrygd/ncaa-api) - Team ID format
- [Alembic Migration Operations](https://alembic.sqlalchemy.org/en/latest/ops.html)
- [PostgreSQL INSERT ... ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT)

## Definition of Done

- [ ] All acceptance criteria met and verified
- [ ] All tasks completed with passing validation
- [ ] JSON files created with 20 teams and 6 conferences
- [ ] Team colors are official hex codes
- [ ] Aliases arrays populated for Reddit matching
- [ ] Alembic migration created with upsert logic
- [ ] Migration executed successfully (no errors)
- [ ] Database verified: 20 teams and 6+ conferences exist
- [ ] Foreign key relationships validated (teams → conferences)
- [ ] Rivalry pairs exist (Duke + UNC both in ACC)
- [ ] Migration idempotency tested (can run twice safely)
- [ ] Documentation updated (CLAUDE.md)
- [ ] Changes committed to git
- [ ] Story reviewed and approved by Product Owner

---

## Dev Agent Record

### Context Reference

- [Story Context](./2-1-create-dimensional-data.context.xml) - Generated 2025-11-11

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

<!-- Debug logs will be added during implementation -->

### Completion Notes List

<!-- Completion notes will be added after implementation -->

### File List

<!-- File list will be added after implementation -->

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-11 | Bob (SM) | Story created from existing draft, updated with Tech Spec AC-1 requirements, architectural context from Epic 2, and learnings from Story 1-7. Renamed file from story-2.1-* to 2-1-* format per naming convention. Status: drafted |
