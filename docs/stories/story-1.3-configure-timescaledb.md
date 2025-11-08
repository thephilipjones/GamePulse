# Story 1.3: Configure PostgreSQL with TimescaleDB Extension

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to add TimescaleDB extension to PostgreSQL,
So that I can optimize time-series queries for excitement_scores and betting_odds tables.

---

## Acceptance Criteria

**Given** the FastAPI template has a base PostgreSQL 16 container
**When** I modify the docker-compose.yml to use timescale/timescaledb:latest-pg16 image
**Then** the database container starts with TimescaleDB extension available

**And** I can connect to the database and verify: `SELECT * FROM pg_extension WHERE extname = 'timescaledb';` returns a row

**And** I create a test hypertable successfully: `SELECT create_hypertable('test_table', 'timestamp');`

---

## Prerequisites

- Story 1.1 (template initialized)
- Story 1.2 (authentication removed)

---

## Technical Notes

**Modify docker-compose.yml db service:**
```yaml
db:
  image: timescale/timescaledb:latest-pg16  # Changed from postgres:16
  environment:
    POSTGRES_USER: gamepulse
    POSTGRES_PASSWORD: ${DB_PASSWORD}
    POSTGRES_DB: gamepulse
```

**TimescaleDB Details:**
- TimescaleDB extension is automatically enabled on database creation
- Version: TimescaleDB 2.23.0 (latest as of 2025-11-07)
- Will create hypertables in Story 5.3 for excitement_scores and betting_odds

**Verify Installation:**
```bash
docker-compose exec db psql -U gamepulse -d gamepulse -c "SELECT * FROM pg_extension;"
```

**Test Hypertable Creation:**
```sql
-- Create test table
CREATE TABLE test_table (
  time TIMESTAMPTZ NOT NULL,
  value DOUBLE PRECISION
);

-- Convert to hypertable
SELECT create_hypertable('test_table', 'time');
```

---

## Definition of Done

- [ ] docker-compose.yml updated with TimescaleDB image
- [ ] Database container starts successfully
- [ ] TimescaleDB extension verified in pg_extension table
- [ ] Test hypertable created successfully
- [ ] Documentation added explaining TimescaleDB choice
- [ ] Changes committed to git
