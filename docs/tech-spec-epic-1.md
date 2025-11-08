# Epic Technical Specification: Project Foundation & Infrastructure

Date: 2025-11-07
Author: Philip
Epic ID: 1
Status: Draft

---

## Overview

Epic 1 establishes the production-ready infrastructure foundation for GamePulse using the FastAPI full-stack template. This epic delivers a complete development and deployment pipeline including: Docker Compose orchestration, PostgreSQL 16 with TimescaleDB extension for time-series optimization, GitHub Actions CI/CD automation, and AWS EC2 deployment with Traefik reverse proxy. The template provides a modern, type-safe stack (FastAPI + SQLModel + React + TypeScript) with built-in Alembic migrations and Chakra UI components, saving approximately 8-10 hours of manual configuration work while establishing production-ready patterns.

The epic focuses on creating a deployable infrastructure skeleton before any business logic implementation, enabling rapid iteration with a live public URL available by end of Week 1. By removing unnecessary authentication boilerplate (GamePulse is a public read-only dashboard), the foundation remains minimal yet production-ready.

## Objectives and Scope

**In Scope:**
- Initialize FastAPI full-stack template with proper .env configuration
- **Remove authentication boilerplate FIRST** (users, sessions, auth endpoints) - not needed for public dashboard, cleaner starting point
- **Provision AWS infrastructure using Terraform** (EC2 t2.micro, security groups, Elastic IP, CloudWatch) - Infrastructure as Code for reproducible deployments
- Configure PostgreSQL 16 database with TimescaleDB extension (2.23.0)
- Create initial **multi-sport data schema** with SQLModel ORM and Alembic migrations (teams, team_groups, team_rivalries, games)
- Set up GitHub Actions CI/CD pipeline for automated testing and deployment
- Deploy to AWS EC2 t2.micro (free tier) with Docker Compose and Traefik
- Establish structured logging with structlog for CloudWatch integration
- Verify end-to-end: code push → automated deploy → live accessible URL

**Out of Scope:**
- Business logic implementation (game ingestion, sentiment analysis) - deferred to Epics 2-6
- Frontend UI beyond template baseline - dashboard customization in Epic 8
- Production scaling (multi-instance, load balancing) - deferred to Growth phase
- Advanced monitoring/observability stack (Prometheus, Grafana) - basic health checks only for MVP
- SSL certificate automation - template's Traefik configuration handles automatically

## System Architecture Alignment

Epic 1 establishes the foundational architecture components referenced in the Architecture document:

**Core Infrastructure Decisions:**
- **Starter Template**: FastAPI Full-Stack Template (latest 2025 version) provides Docker Compose orchestration, CI/CD pipeline, and modern tooling - aligns with Architecture decision to save 8-10 hours in Week 1
- **Database**: PostgreSQL 16 + TimescaleDB 2.23.0 for time-series optimization - aligns with Architecture decision favoring learning transferability and production-ready patterns
- **ORM & Migrations**: SQLModel 0.0.23 + Alembic 1.17.1 - keeps template defaults, type-safe database operations
- **Deployment Target**: AWS EC2 t2.micro (1 vCPU, 1GB RAM) within free tier - aligns with NFR-6.1 budget constraint (<$10/month)
- **CI/CD**: GitHub Actions with automated deploy on push to main - aligns with NFR-5.3 deployment automation requirement

**Key Constraints Addressed:**
- Single EC2 instance sufficient for MVP scale (5-10 concurrent games, 10-50 users per NFR-3.1)
- TimescaleDB hypertables enable time-series performance for `excitement_scores` and `betting_odds` tables (Epics 4-5)
- Docker Compose orchestration supports both local development and production deployment
- Traefik reverse proxy provides automatic HTTPS without manual certificate management

## Detailed Design

### Services and Modules

**Infrastructure Modules (Created by Template):**

| Module | Responsibility | Location | Configuration |
|--------|---------------|----------|---------------|
| **FastAPI Application** | Main web server entry point | `backend/app/main.py` | Exposes REST API, CORS configuration, middleware setup |
| **Database Engine** | SQLModel connection management | `backend/app/core/db.py` | PostgreSQL connection pool (5-10 connections), async session factory |
| **Configuration Management** | Environment variable loading | `backend/app/core/config.py` | Pydantic Settings with .env file support |
| **Alembic Migrations** | Schema version control | `backend/alembic/` | Auto-migration generation from SQLModel changes |
| **Docker Orchestration** | Service composition | `docker-compose.yml` | Backend, frontend, PostgreSQL, Traefik containers |
| **Traefik Proxy** | Reverse proxy + HTTPS | Traefik container | Automatic SSL via Let's Encrypt, route configuration |
| **GitHub Actions** | CI/CD automation | `.github/workflows/` | Lint, test, build, deploy workflow |

**Modules to Remove (Authentication Not Needed):**

| Module | Removal Scope | Rationale |
|--------|--------------|-----------|
| `backend/app/core/security.py` | Delete file | JWT token generation, password hashing - not needed for public dashboard |
| `backend/app/api/routes/login.py` | Delete file | User authentication endpoints - GamePulse has no user accounts |
| `backend/app/api/routes/users.py` | Delete file | User CRUD operations - not needed |
| `backend/app/models/user.py` | Delete file | User SQLModel schema - not needed |
| User-related migrations | Delete migration files | Clean up database schema from auth tables |

**AWS Infrastructure (Terraform IaC):**

| Resource | Purpose | Configuration |
|----------|---------|---------------|
| **EC2 Instance** | Application host | t2.micro (1 vCPU, 1GB RAM), Ubuntu 22.04 LTS, Docker pre-installed |
| **Elastic IP** | Static public IP | Prevents IP changes on instance restart, enables DNS mapping |
| **Security Group** | Firewall rules | Allow SSH (22), HTTP (80), HTTPS (443); restrict SSH to admin IP |
| **IAM Role** | EC2 permissions | CloudWatch Logs write access, Systems Manager Parameter Store read |
| **CloudWatch Log Group** | Centralized logging | `/gamepulse/backend`, `/gamepulse/frontend` log streams |
| **EBS Volume** | Persistent storage | 20GB gp3 (general purpose SSD), auto-backup enabled |

**Terraform Module Structure:**

```
terraform/
├── main.tf          # Main infrastructure definition
├── variables.tf     # Input variables (instance type, region, admin IP)
├── outputs.tf       # Output values (public IP, instance ID)
├── providers.tf     # AWS provider configuration
└── modules/
    ├── ec2/        # EC2 instance + security group
    ├── iam/        # IAM roles and policies
    └── cloudwatch/ # Log groups and metrics
```

**Database Structure Setup:**

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **PostgreSQL 16 Base** | Relational database | Official Docker image with persistent volume |
| **TimescaleDB Extension** | Time-series optimization | `CREATE EXTENSION IF NOT EXISTS timescaledb;` in init script |
| **Connection Pooling** | Efficient DB connections | SQLModel async engine with pool size 5-10 |
| **Migration System** | Schema versioning | Alembic with auto-generation from SQLModel models |

### Data Models and Contracts

**Initial Database Schema (Multi-Sport Data Engineering Foundation):**

```sql
-- Teams dimensional table (sport-agnostic, supports multi-sport expansion)
CREATE TABLE teams (
    team_id VARCHAR PRIMARY KEY,           -- Format: "{sport}_{team_slug}" e.g., "ncaam_duke", "nfl_chiefs"
    sport VARCHAR NOT NULL,                -- "ncaam", "nfl", "nba" (enables sport-level filtering)
    team_name VARCHAR NOT NULL,            -- e.g., "Duke Blue Devils", "Kansas City Chiefs"
    team_abbr VARCHAR,                     -- e.g., "DU", "KC"
    team_group_id VARCHAR,                 -- FK to team_groups (flexible: conference, division, etc.)
    primary_color VARCHAR,                 -- Hex color for UI (e.g., "#003087")
    secondary_color VARCHAR,               -- Secondary/accent color
    aliases TEXT[],                        -- ["Duke", "Blue Devils", "DU"] for fuzzy matching
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Team groups dimensional table (generic: conferences, divisions, leagues)
-- Supports both flat structure (NCAAM conferences) and nested (NFL conference→division)
CREATE TABLE team_groups (
    team_group_id VARCHAR PRIMARY KEY,     -- e.g., "ncaam_acc", "nfl_afc_west"
    team_group_name VARCHAR NOT NULL,      -- e.g., "ACC", "AFC West"
    sport VARCHAR NOT NULL,                -- "ncaam", "nfl" (for sport-specific queries)
    group_type VARCHAR NOT NULL,           -- "conference", "division", "league" (semantic meaning)
    parent_group_id VARCHAR,               -- FK to team_groups (enables nesting: NFL AFC→AFC West)
    level INTEGER DEFAULT 1,               -- Hierarchy level (1=top, 2=nested, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (parent_group_id) REFERENCES team_groups(team_group_id)
);

-- Team rivalry mapping table (many-to-many, evolving rivalry factors)
CREATE TABLE team_rivalries (
    rivalry_id SERIAL PRIMARY KEY,
    team_a_id VARCHAR NOT NULL REFERENCES teams(team_id),
    team_b_id VARCHAR NOT NULL REFERENCES teams(team_id),
    rivalry_factor DOUBLE PRECISION DEFAULT 1.0,  -- 1.0 = normal, 1.5 = heated rivalry
    rivalry_type VARCHAR,                  -- "historic", "geographic", "playoff", "divisional"
    notes TEXT,                            -- e.g., "Duke-UNC: Tobacco Road rivalry since 1920"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_a_id, team_b_id),          -- Prevent duplicate rivalries
    CHECK (team_a_id < team_b_id)          -- Enforce ordering (prevents A→B and B→A duplicates)
);

-- Games fact table (sport-agnostic, supports basketball, football, baseball, etc.)
CREATE TABLE games (
    game_id VARCHAR PRIMARY KEY,           -- API-provided ID (format: "{sport}_{api_id}")
    sport VARCHAR NOT NULL,                -- "ncaam", "nfl", "nba" (for sport-level queries)
    game_date TIMESTAMPTZ NOT NULL,
    home_team_id VARCHAR REFERENCES teams(team_id),
    away_team_id VARCHAR REFERENCES teams(team_id),
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    game_status VARCHAR,                   -- "scheduled", "live", "halftime", "final", "postponed"
    game_clock VARCHAR,                    -- "2:34 2nd Half", "3rd Quarter 10:23", etc.
    game_start_time TIMESTAMPTZ,           -- Scheduled/actual start time
    game_end_time TIMESTAMPTZ,
    venue VARCHAR,
    game_type VARCHAR DEFAULT 'regular_season',  -- Enum: "regular_season", "postseason", "conference_tournament", "ncaa_tournament", "super_bowl", etc.
    rivalry_factor DOUBLE PRECISION,       -- Cached from team_rivalries for query performance
    broadcast_network VARCHAR,             -- e.g., "ESPN", "CBS" (useful for BI analysis)
    attendance INTEGER,                    -- Actual attendance (if available)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for frequent queries (optimized for BI tools)
CREATE INDEX idx_games_sport ON games(sport);
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_status ON games(game_status);
CREATE INDEX idx_games_type ON games(game_type);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);  -- For rivalry lookups
CREATE INDEX idx_teams_sport ON teams(sport);
CREATE INDEX idx_teams_group ON teams(team_group_id);
```

**SQLModel Schemas (Type-Safe ORM for Multi-Sport Data):**

```python
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import ARRAY, String
from datetime import datetime
from typing import Optional, List

class Team(SQLModel, table=True):
    __tablename__ = "teams"

    team_id: str = Field(primary_key=True)  # Format: "{sport}_{slug}"
    sport: str = Field(index=True)  # Enables sport-level filtering
    team_name: str
    team_abbr: Optional[str] = None
    team_group_id: Optional[str] = Field(foreign_key="team_groups.team_group_id")
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    aliases: List[str] = Field(sa_column=Column(ARRAY(String)))  # PostgreSQL array
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TeamGroup(SQLModel, table=True):
    __tablename__ = "team_groups"

    team_group_id: str = Field(primary_key=True)
    team_group_name: str
    sport: str = Field(index=True)
    group_type: str  # "conference", "division", "league"
    parent_group_id: Optional[str] = Field(foreign_key="team_groups.team_group_id")
    level: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TeamRivalry(SQLModel, table=True):
    __tablename__ = "team_rivalries"

    rivalry_id: Optional[int] = Field(default=None, primary_key=True)
    team_a_id: str = Field(foreign_key="teams.team_id")
    team_b_id: str = Field(foreign_key="teams.team_id")
    rivalry_factor: float = Field(default=1.0)
    rivalry_type: Optional[str] = None  # "historic", "geographic", etc.
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Game(SQLModel, table=True):
    __tablename__ = "games"

    game_id: str = Field(primary_key=True)  # Format: "{sport}_{api_id}"
    sport: str = Field(index=True)
    game_date: datetime = Field(index=True)
    home_team_id: str = Field(foreign_key="teams.team_id")
    away_team_id: str = Field(foreign_key="teams.team_id")
    home_score: int = Field(default=0)
    away_score: int = Field(default=0)
    game_status: Optional[str] = Field(index=True)
    game_clock: Optional[str] = None
    game_start_time: Optional[datetime] = None
    game_end_time: Optional[datetime] = None
    venue: Optional[str] = None
    game_type: str = Field(default="regular_season", index=True)
    rivalry_factor: Optional[float] = None  # Cached from team_rivalries
    broadcast_network: Optional[str] = None
    attendance: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Data Engineering Considerations:**

This schema is optimized for:
- **Multi-sport expansion**: `sport` field enables filtering, team_id namespacing prevents collisions
- **BI tool compatibility**: Indexed fields for common analytical queries (sport, date, status, type)
- **Flexible hierarchies**: `team_groups` supports both flat (NCAAM conferences) and nested (NFL conference→division)
- **Rivalry evolution**: `team_rivalries` table allows rivalry factors to evolve over time, cached on `games` for query performance
- **Game type semantics**: `game_type` enum supports various tournament structures across sports
- **Broadcast/attendance data**: Additional fields for richer BI analysis (viewership patterns, stadium capacity utilization)

**TimescaleDB Hypertable Setup (Deferred to Epics 4-5):**

```sql
-- Execute AFTER creating excitement_scores table (Epic 4)
SELECT create_hypertable('excitement_scores', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');

-- Execute AFTER creating betting_odds table (Epic 5)
SELECT create_hypertable('betting_odds', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');
```

### APIs and Interfaces

**Initial API Endpoints (Minimal for Epic 1):**

```python
# Health Check Endpoint (Story 1.1)
GET /api/health
Response: {
    "status": "healthy",
    "database": "connected",
    "timestamp": "2025-11-07T20:00:00Z",
    "version": "0.1.0"
}

# Root Endpoint (Template Default)
GET /
Response: {
    "message": "GamePulse API",
    "docs": "/docs"
}

# OpenAPI Documentation (Auto-Generated)
GET /docs          # Swagger UI
GET /redoc         # ReDoc UI
GET /openapi.json  # OpenAPI schema
```

**CORS Configuration:**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public dashboard, no auth restrictions
    allow_credentials=False,
    allow_methods=["GET"],  # Read-only API
    allow_headers=["*"],
)
```

**Response Schema (Pydantic):**

```python
from pydantic import BaseModel
from datetime import datetime

class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    database: str  # "connected" | "disconnected"
    timestamp: datetime
    version: str
```

### Workflows and Sequencing

**1. Initial Setup Workflow (Story 1.1):**

```
Developer → copier template → Answer prompts → .env file created
    ↓
Template generates:
    - backend/ (FastAPI + SQLModel + Alembic)
    - frontend/ (React + TypeScript + Vite + Chakra)
    - docker-compose.yml
    - .github/workflows/
    ↓
Manual configuration:
    - Update .env with PROJECT_NAME=gamepulse
    - Configure PostgreSQL credentials
    - Set CORS origins
    ↓
Verify: docker-compose up → Access http://localhost:8080
```

**2. Database Migration Workflow (Story 1.3):**

```
Developer: Define SQLModel schema (Team, Conference, Game)
    ↓
Generate migration: alembic revision --autogenerate -m "Add initial schema"
    ↓
Review migration file: backend/alembic/versions/xxx_add_initial_schema.py
    ↓
Apply migration: alembic upgrade head
    ↓
Verify: psql → \dt (list tables) → Confirm teams, conferences, games exist
    ↓
Seed dimensional data: Load teams.json, conferences.json → INSERT INTO tables
```

**3. CI/CD Deployment Workflow (Stories 1.4 + 1.5):**

```
Developer: git push origin main
    ↓
GitHub Actions Trigger:
    Step 1: Lint (black, pylint, eslint)
    Step 2: Test (pytest, jest)
    Step 3: Build (Docker images for backend + frontend)
    Step 4: Deploy to EC2
        - SSH to EC2 instance
        - Pull latest Docker images
        - docker-compose down && docker-compose up -d
    Step 5: Smoke Test
        - curl https://gamepulse.example.com/api/health
        - Verify HTTP 200 response
    ↓
Deployment Complete: Live URL accessible
    ↓
Rollback if failure: Keep last 3 Docker images, manual rollback via SSH
```

**4. TimescaleDB Extension Activation (Story 1.2):**

```
docker-compose up postgres (start PostgreSQL 16)
    ↓
Connect: docker exec -it gamepulse-postgres psql -U postgres
    ↓
Execute: CREATE EXTENSION IF NOT EXISTS timescaledb;
    ↓
Verify: SELECT extname FROM pg_extension WHERE extname = 'timescaledb';
    ↓
Confirm: extname = 'timescaledb' (version 2.23.0)
```

**5. Authentication Removal Workflow (Story 1.6):**

```
Identify auth-related files:
    - backend/app/core/security.py
    - backend/app/api/routes/login.py
    - backend/app/api/routes/users.py
    - backend/app/models/user.py
    ↓
Delete files + references in main.py router imports
    ↓
Remove user table migration: Delete alembic version files
    ↓
Test: pytest → Confirm no broken imports
    ↓
Commit: "Remove auth boilerplate - public dashboard"
```

## Non-Functional Requirements

### Performance

**Database Performance Targets:**
- Schema migration execution: <10 seconds for initial schema creation
- Database connection pool initialization: <2 seconds
- Health check endpoint response time: <100ms (p95)
- Query performance baseline (no data yet): <50ms for simple SELECT queries

**Deployment Performance:**
- Docker Compose startup (all services): <60 seconds
- GitHub Actions CI/CD pipeline: <5 minutes end-to-end (lint, test, build, deploy)
- Terraform apply (infrastructure provisioning): <3 minutes for initial deployment

**Performance is not critical for Epic 1** - focus is on establishing working infrastructure. Query optimization and time-series performance will be addressed in Epics 4-5 when data volume increases.

### Security

**Infrastructure Security:**
- EC2 security group: SSH access restricted to admin IP only (no 0.0.0.0/0)
- HTTPS enforced via Traefik + Let's Encrypt (automatic cert renewal)
- PostgreSQL: Not publicly exposed, only accessible within Docker network
- IAM role: Principle of least privilege (CloudWatch write, Parameter Store read only)

**Application Security:**
- No authentication system = no credential storage vulnerabilities
- CORS configured for public read-only access (appropriate for portfolio demo)
- Secrets management: Environment variables via .env (local) + AWS Parameter Store (production)
- Docker images: Official base images only (FastAPI, PostgreSQL, Node), scanned for vulnerabilities in CI

**Data Security:**
- All data is public sports data (no PII, no sensitive information)
- Database credentials stored in .env (gitignored) and AWS Parameter Store
- No user-generated content = no injection attack surface

### Reliability/Availability

**Target Uptime:** 95% during demo periods (Week 1 onwards)

**Single Point of Failure Accepted:**
- Single EC2 instance (no load balancing/auto-scaling in MVP)
- Single database instance (no replication/failover)
- Rationale: Portfolio demo scale, not production traffic

**Graceful Degradation Strategy:**
- If PostgreSQL fails: API returns HTTP 503 with clear error message
- If Docker Compose crashes: systemd auto-restart (configured via user-data script)
- Rollback capability: Keep last 3 Docker images for manual rollback

**Data Durability:**
- EBS volume snapshots: Daily automated backups (7-day retention)
- Database persistence: Docker volume mapped to EBS storage
- Acceptable data loss window: 24 hours (daily backups sufficient for MVP)

### Observability

**Logging Strategy:**
- Structured JSON logs (structlog) written to stdout
- Docker captures stdout → forwarded to CloudWatch Logs
- Log retention: 7 days (sufficient for debugging recent issues)
- Log groups: `/gamepulse/backend`, `/gamepulse/frontend`, `/gamepulse/postgres`

**Health Monitoring:**
- `/api/health` endpoint checks:
  - Database connectivity (SELECT 1 query)
  - Application status
  - Timestamp for freshness verification
- External monitoring: UptimeRobot (free tier) - ping /api/health every 5 minutes

**Metrics (Basic MVP):**
- CloudWatch metrics: EC2 CPU%, memory%, disk%
- Application metrics: Request count, error rate (logged, not visualized yet)
- **Deferred to Growth:** Prometheus + Grafana dashboards, detailed query metrics

**Deployment Observability:**
- GitHub Actions logs: Visible in Actions tab (lint, test, build, deploy steps)
- Terraform state: Stored in S3 with state locking (DynamoDB table)
- Deployment verification: Automated smoke test (curl /api/health) in CI/CD pipeline

## Dependencies and Integrations

**External Dependencies:**

| Dependency | Version | Purpose | Installation Method |
|------------|---------|---------|-------------------|
| FastAPI | 0.114.2+ | Web framework | uv (from template) |
| SQLModel | 0.0.21+ | Type-safe ORM | uv (from template) |
| Alembic | 1.12.1+ | Database migrations | uv (from template) |
| PostgreSQL | 12+ (16+ target) | Database | Docker image |
| TimescaleDB | 2.23.0 | Time-series extension | PostgreSQL extension |
| React | 18.2+ | Frontend framework | npm (from template) |
| TypeScript | 5.x | Type safety | npm (from template) |
| Vite | Latest | Build tool | npm (from template) |
| Chakra UI | 3.8+ | UI components | npm (from template) |
| Docker Compose | 2.x | Orchestration | Binary install |
| Traefik | 3.0+ | Reverse proxy | Docker image |
| Terraform | 1.9+ | Infrastructure as Code | Binary install |
| structlog | 25.5.0 | Structured logging | uv (manual add) |

**AWS Service Dependencies:**
- EC2 (t2.micro free tier)
- EBS (20GB gp3 storage)
- CloudWatch Logs (log aggregation)
- Systems Manager Parameter Store (secrets management)
- S3 (Terraform state storage)
- DynamoDB (Terraform state locking)

**Integration Points:**
- GitHub → GitHub Actions (CI/CD trigger)
- GitHub Actions → AWS EC2 (SSH deployment)
- Docker Compose → PostgreSQL (database connection)
- FastAPI → PostgreSQL (SQLModel ORM)
- React → FastAPI (HTTP API calls)
- Traefik → FastAPI (reverse proxy)
- Traefik → Let's Encrypt (SSL certificates)
- structlog → CloudWatch Logs (log shipping)

**No External APIs in Epic 1** - NCAA, Reddit, Betfair integrations deferred to Epics 2-5

## Acceptance Criteria (Authoritative)

**AC-1: Template Initialization**
- [ ] FastAPI full-stack template successfully initialized using copier
- [ ] .env file generated with PROJECT_NAME=gamepulse
- [ ] Docker Compose starts all services without errors
- [ ] Can access backend API at http://localhost:8000/docs
- [ ] Can access frontend at http://localhost:3000

**AC-2: Authentication Removal (Story moved before database setup)**
- [ ] Deleted files: `security.py`, `login.py`, `users.py`, `user.py`
- [ ] Removed user-related router imports from `main.py`
- [ ] Deleted user table migration files
- [ ] pytest passes with no broken imports
- [ ] API docs (Swagger) show no auth endpoints

**AC-3: AWS Infrastructure Provisioning**
- [ ] Terraform modules created: ec2, iam, cloudwatch
- [ ] `terraform plan` executes without errors
- [ ] `terraform apply` provisions EC2 t2.micro successfully
- [ ] Elastic IP allocated and associated with EC2 instance
- [ ] Security group configured: SSH (admin IP only), HTTP, HTTPS
- [ ] CloudWatch log groups created: `/gamepulse/backend`, `/gamepulse/frontend`
- [ ] Can SSH to EC2 instance using provided key pair

**AC-4: TimescaleDB Configuration**
- [ ] PostgreSQL 16 Docker container starts successfully
- [ ] TimescaleDB extension (2.23.0) installed and verified
- [ ] Query `SELECT extname FROM pg_extension` returns 'timescaledb'
- [ ] Can connect to database from backend container

**AC-5: Multi-Sport Database Schema**
- [ ] SQLModel models created: Team, TeamGroup, TeamRivalry, Game
- [ ] Alembic migration generated with `alembic revision --autogenerate`
- [ ] Migration applied successfully: `alembic upgrade head`
- [ ] Tables exist: teams, team_groups, team_rivalries, games
- [ ] Indexes created: sport, date, status, type, team lookups
- [ ] Sample data seeded: 5 NCAAM teams, 2 conferences, 1 rivalry

**AC-6: GitHub Actions CI/CD**
- [ ] Workflow file created: `.github/workflows/deploy.yml`
- [ ] Push to main triggers workflow
- [ ] Workflow steps: lint → test → build → deploy → smoke test
- [ ] Deployment SSH to EC2, pull Docker images, restart services
- [ ] Smoke test: curl https://{elastic-ip}/api/health returns HTTP 200

**AC-7: Production Deployment**
- [ ] Docker Compose production config (`docker-compose.prod.yml`) created
- [ ] Traefik configured with Let's Encrypt for HTTPS
- [ ] SSL certificate obtained automatically
- [ ] Live URL accessible: https://{domain or elastic-ip}
- [ ] `/api/health` returns valid JSON response
- [ ] Logs visible in CloudWatch Logs

**AC-8: End-to-End Verification**
- [ ] Local development: docker-compose up works
- [ ] Code push to main → GitHub Actions succeeds → Live site updated
- [ ] Health check endpoint responsive (<100ms)
- [ ] Database migrations apply cleanly
- [ ] Rollback test: revert to previous Docker image successfully

## Traceability Mapping

| Acceptance Criteria | PRD Requirement | Architecture Component | Story | Test Coverage |
|---------------------|----------------|------------------------|-------|---------------|
| AC-1: Template Init | FR-8.1: Deployment automation | Docker Compose, FastAPI, React | 1.1 | Integration test: docker-compose up |
| AC-2: Auth Removal | NFR-5.1: Code maintainability | Security module cleanup | 1.6 → **1.2 (reordered)** | Unit test: no auth imports |
| AC-3: AWS Infra | NFR-6.1: Cost constraints, FR-8.1 | EC2, Terraform IaC | **New: 1.1b** | Manual: terraform plan/apply |
| AC-4: TimescaleDB | Architecture: Time-series storage | PostgreSQL + extension | 1.3 → **1.4 (reordered)** | Integration test: SELECT extname |
| AC-5: Multi-Sport Schema | FR-1.2: Team dimensional data | SQLModel, Alembic | 1.3 → **1.5 (reordered)** | Integration test: query teams table |
| AC-6: CI/CD Pipeline | NFR-5.3: Deployment automation | GitHub Actions | 1.4 → **1.6 (reordered)** | E2E test: push → deploy → verify |
| AC-7: Production Deploy | FR-8.1: Live demo URL | EC2 + Traefik + Docker | 1.5 → **1.7 (reordered)** | Manual: curl health endpoint |
| AC-8: End-to-End | Success Criteria: Week 1 milestone | Full stack integration | All stories | E2E test: full deployment cycle |

**Story Reordering Note:**
- **Original:** 1.1 (Template) → 1.2 (TimescaleDB) → 1.3 (Schema) → 1.4 (CI/CD) → 1.5 (Deploy) → 1.6 (Auth Removal)
- **Revised:** 1.1 (Template) → **1.1b (Terraform)** → **1.2 (Auth Removal)** → 1.3 (TimescaleDB) → 1.4 (Schema) → 1.5 (CI/CD) → 1.6 (Deploy)
- **Rationale:** Remove auth early for cleaner working environment; provision AWS before deployment stories

## Risks, Assumptions, Open Questions

**Risks:**

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| FastAPI template breaking changes | High - entire foundation | Low | Pin template to specific commit hash, not "latest" |
| TimescaleDB extension incompatible with PostgreSQL 16 | High - time-series performance | Low | Verified compatibility (TimescaleDB 2.23.0 supports PG16) |
| AWS free tier limits exceeded | Medium - cost overrun | Medium | CloudWatch billing alarm at $8/month threshold |
| Terraform state corruption | High - infrastructure lost | Low | S3 backend with versioning + DynamoDB locking |
| Let's Encrypt rate limits | Medium - HTTPS unavailable | Low | Use staging environment for testing, production certs once |
| Multi-sport schema over-engineered | Low - simpler structure sufficient | Medium | Start with minimal viable schema, refactor in Epic 2 if needed |

**Assumptions:**

- FastAPI full-stack template is stable and production-ready (verified by community usage)
- AWS EC2 t2.micro sufficient for Week 1 (no traffic yet, just infrastructure validation)
- PostgreSQL + TimescaleDB in Docker performs adequately for MVP scale (<60MB data)
- Multi-sport schema design won't require major refactoring when adding NFL/NBA
- GitHub Actions minutes sufficient for CI/CD (2,000 free minutes/month)
- Traefik auto-SSL works reliably (Let's Encrypt widely used in production)

**Open Questions:**

1. **Domain name:** Use Elastic IP directly or register domain (e.g., gamepulse.dev)? Decision: Start with IP, add domain in Week 2 if needed
2. **Terraform state storage:** Use local file or S3 backend immediately? Decision: S3 backend from start (prevents state loss)
3. **Database backup frequency:** Daily sufficient or need hourly? Decision: Daily for MVP, upgrade to hourly if data becomes critical
4. **Multi-sport team ID collision:** How to handle "chiefs" (NFL) vs "chiefs" (hypothetical NCAA)? Decision: Always prefix with sport (ncaam_chiefs, nfl_chiefs)
5. **Team group hierarchy depth:** Support unlimited nesting or limit to 2 levels? Decision: Limit to 2 levels for MVP (conference→division), add recursion if needed later

**Data Engineering Considerations:**

- Schema must support BI tools (Tableau, Metabase, Superset) → Ensured via indexed fields, semantic naming
- Rivalry factors should be time-aware (rivalries evolve) → team_rivalries table supports updated_at timestamp
- Game types should be extensible (playoffs, championships, All-Star games) → VARCHAR enum allows new types without schema changes

## Test Strategy Summary

**Epic 1 Testing Focus:** Infrastructure validation, not business logic testing

**Unit Tests (Minimal for Epic 1):**
- SQLModel schema validation (Team, TeamGroup, Game models serialize correctly)
- Health check endpoint returns valid JSON
- **Coverage Target:** 30% (low because Epic 1 is mostly infrastructure, not logic)

**Integration Tests:**
- Docker Compose starts all services successfully
- PostgreSQL connection from FastAPI backend
- TimescaleDB extension query succeeds
- Alembic migrations apply without errors
- CORS middleware configured correctly

**End-to-End Tests:**
- Full deployment cycle: git push → GitHub Actions → EC2 update → live URL
- Health check endpoint accessible via public URL
- SSL certificate valid (HTTPS works)
- Logs visible in CloudWatch

**Manual Testing:**
- Terraform plan/apply (infrastructure provisioning)
- SSH access to EC2 instance
- Docker commands on EC2
- Database connection via psql
- Browser access to live URL

**Test Execution:**
- **Local:** pytest (backend unit + integration), npm test (frontend)
- **CI:** GitHub Actions runs tests on every push
- **Deployment:** Automated smoke test (curl /api/health) after deploy

**Test Data:**
- Sample teams: 5 NCAAM teams (Duke, UNC, Kansas, Kentucky, Villanova)
- Sample conferences: ACC, Big 12
- Sample rivalry: Duke-UNC (rivalry_factor=1.5, type="historic")
- No real game data yet (Epic 2)

**Success Criteria for Epic 1 Testing:**
- [ ] All GitHub Actions workflows pass (green checkmarks)
- [ ] Live URL returns HTTP 200 for /api/health
- [ ] Database schema matches SQLModel definitions
- [ ] Can manually verify infrastructure via AWS console
- [ ] Rollback tested (revert to previous Docker image successfully)
