# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GamePulse is a full-stack web application built with FastAPI (backend) and React (frontend), deployed on AWS EC2 via GitHub Actions CI/CD. The project uses Docker Compose for development and production, with infrastructure managed through Terraform.

**Tech Stack:**

- Backend: FastAPI + SQLModel + PostgreSQL (TimescaleDB extension)
- Orchestration: Dagster (self-hosted) for data pipeline orchestration
- Frontend: React + TypeScript + Vite + TanStack Query/Router + Chakra UI
- Infrastructure: AWS EC2, Terraform modules (VPC, Compute)
- Deployment: GitHub Actions with OIDC authentication to AWS
- Package Management: `uv` (backend), `npm` (frontend)

## Essential Development Commands

### Initial Setup

```bash
# Clone and setup environment
cp .env.example .env
# Edit .env with actual values for SECRET_KEY, POSTGRES_PASSWORD, etc.

# Start full stack with Docker Compose (recommended)
docker compose watch

# Access services:
# Frontend: http://localhost:5173
# Backend API docs: http://localhost:8000/docs
# Adminer (DB): http://localhost:8080
# Traefik UI: http://localhost:8090
# Dagster UI: http://localhost:3000
```

### Backend Development

```bash
cd backend

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run local development server (without Docker)
fastapi dev app/main.py

# Run tests (parallel execution for speed)
uv run pytest -v -n auto

# Run tests sequentially (for debugging)
uv run pytest -v

# Run specific test file
uv run pytest app/tests/api/test_items.py -v

# Run tests by category
uv run pytest -m unit -v           # Unit tests only (fast, no database)
uv run pytest -m integration -v    # Integration tests only (requires database)

# Run tests with coverage (parallel)
uv run coverage run -m pytest -v -n auto
uv run coverage report

# Run tests with coverage (sequential for debugging)
uv run coverage run -m pytest -v
uv run coverage report

# Lint and type check
uv run ruff check .
uv run mypy .

# Database migrations
docker compose exec backend bash
alembic revision --autogenerate -m "Description of change"
alembic upgrade head

# Run tests inside Docker
docker compose exec backend bash scripts/tests-start.sh
# Stop on first error:
docker compose exec backend bash scripts/tests-start.sh -x
```

### Dagster Development (Data Orchestration)

```bash
# Access Dagster UI
# Development: http://localhost:3000
# Production: https://dagster.gamepulse.top

# View asset catalog and lineage
# Navigate to Assets tab in Dagster UI

# Materialize an asset manually (trigger job)
# Option 1: Via UI - Click "Materialize" button on ncaa_games asset
# Option 2: Via CLI
docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games

# View asset materializations and run history
# Navigate to Runs tab in Dagster UI

# Check Dagster logs
docker compose logs -f dagster-daemon
docker compose logs -f dagster-webserver

# Restart Dagster services
docker compose restart dagster-daemon dagster-webserver

# Access Dagster Python shell for debugging
docker compose exec dagster-daemon python
>>> from app.dagster_definitions import defs
>>> from app.assets.ncaa_games import ncaa_games
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run local development server (recommended over Docker for faster reload)
npm run dev

# Build for production
npm run build

# Lint
npm run lint

# Generate API client (after backend OpenAPI schema changes)
# Note: Automatically regenerated on push to main via GitHub Actions

# Manual generation (for local development):
./scripts/generate-client.sh

# Alternative manual method:
# 1. Download http://localhost:8000/api/v1/openapi.json
# 2. Save to frontend/openapi.json
# 3. Run: npm run generate-client

# E2E tests with Playwright
docker compose up -d --wait backend
npx playwright test
npx playwright test --ui  # UI mode
docker compose down -v    # Clean up after tests
```

### Docker Compose Workflows

```bash
# Start with hot reload (development)
docker compose watch

# Stop specific service
docker compose stop frontend  # or backend

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild after dependency changes
docker compose build

# Production build (without dev overrides)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Exec into running container
docker compose exec backend bash
```

### Linting & Formatting

**Backend (Python):**

- **Linter:** Ruff (replaces flake8, isort, pyupgrade)
- **Type Checker:** Mypy
- **Config:** `backend/pyproject.toml`

**Frontend (JavaScript/TypeScript):**

- **Linter & Formatter:** Biome
- **Config:** `frontend/biome.json`

**Pre-commit Hooks:**

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

Pre-commit automatically runs on every commit:

- Check for large files, valid TOML/YAML
- Fix end-of-file and trailing whitespace
- Backend: Ruff lint (`--fix`) + Ruff format
- Frontend: Handled by npm scripts and VSCode (see below)

**VSCode Setup (Recommended):**

Install recommended extensions:

- Python: `ms-python.python`, `charliermarsh.ruff`
- JavaScript/TypeScript: `biomejs.biome`
- Docker: `ms-azuretools.vscode-docker`

VSCode settings (`.vscode/settings.json`) are pre-configured for:

- **Format on save** for all file types
- **Backend:** Ruff as default Python formatter
- **Frontend:** Biome as default JS/TS formatter
- **Auto-organize imports** on save
- **Consistent with CI/CD** linting rules

Manual formatting commands:

```bash
# Backend
cd backend
uv run ruff check . --fix  # Auto-fix lint issues
uv run ruff format .       # Format code
uv run mypy .              # Type check

# Frontend
cd frontend
npm run lint               # Lint and auto-fix
```

### Infrastructure & Deployment

#### Terraform Infrastructure Management

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply

# View outputs (instance IP, SSH command, etc.)
terraform output

# Get GitHub Actions role ARN (needed for GitHub Secrets)
terraform output -raw github_actions_role_arn

# Connect to EC2 instance via SSH (admin access only)
terraform output -raw ssh_command  # Copy and run the output

# Destroy infrastructure (DANGER)
terraform destroy
```

#### GitHub OIDC Authentication Setup

GamePulse uses GitHub OIDC for zero-secret CI/CD authentication. This eliminates long-lived AWS credentials.

**Initial Setup (One-Time):**

1. **Provision OIDC Infrastructure:**

   ```bash
   cd terraform
   terraform apply
   ```

   This creates:

   - OIDC Identity Provider in AWS
   - IAM role for GitHub Actions with trust policy
   - Least-privilege IAM policies (SSM, EC2 describe, CloudWatch)

2. **Configure GitHub Secrets:**

   - Navigate to GitHub repository → Settings → Secrets and variables → Actions
   - Add the following secrets:
     - `AWS_GITHUB_ACTIONS_ROLE_ARN`: Get from `terraform output github_actions_role_arn`
     - `AWS_EC2_INSTANCE_ID`: Get from `terraform output instance_id`
     - `AWS_DEPLOYMENT_PATH`: Set to `/opt/gamepulse` (standardized deployment location)
     - `DOMAIN_PRODUCTION`: Your production domain (e.g., `gamepulse.top`)
     - `SECRET_KEY`: FastAPI secret key (generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
     - `POSTGRES_PASSWORD`: Database password

3. **How OIDC Works:**
   - GitHub Actions requests OIDC token from GitHub
   - AWS validates token against OIDC provider
   - If valid and repo/branch matches trust policy, AWS issues temporary credentials (15-minute expiry)
   - Workflow uses credentials to authenticate AWS CLI commands
   - Full audit trail captured in CloudTrail

**Security Benefits:**

- ✅ No long-lived credentials in GitHub Secrets
- ✅ Automatic credential expiry (15 minutes)
- ✅ Restricted to specific repo and branches
- ✅ Full CloudTrail audit logging
- ✅ Least-privilege IAM permissions

#### SSM Session Manager Access

AWS Systems Manager Session Manager provides secure shell access without opening SSH ports to the internet.

**Manual Access to EC2 Instance:**

```bash
# Option 1: Via AWS CLI (requires AWS credentials configured locally)
aws ssm start-session --target $(terraform output -raw instance_id)

# Option 2: Via AWS Console
# Go to AWS Systems Manager → Fleet Manager → Select instance → Connect → Session Manager

# Option 3: Traditional SSH (admin IPs only)
terraform output -raw ssh_command
```

**Running Commands via SSM:**

```bash
# Execute deployment commands
aws ssm send-command \
  --instance-ids "i-xxxxx" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cd /opt/gamepulse && git status"]'

# Check command status
aws ssm get-command-invocation \
  --command-id "cmd-xxxxx" \
  --instance-id "i-xxxxx"
```

**SSM Benefits:**

- ✅ No open SSH port to internet
- ✅ Full CloudTrail audit logging of all sessions
- ✅ Centralized access management via IAM
- ✅ Session recording capabilities

#### Production Deployment

**Deployment Location:**

- Standardized deployment path: `/opt/gamepulse`
- Repository must be cloned to this location for automated deployments to work

**Initial Manual Deployment:**

```bash
# 1. SSH to EC2 instance
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<ELASTIC_IP>

# 2. Clone repository to standardized location
sudo mkdir -p /opt
sudo chown ubuntu:ubuntu /opt
cd /opt
git clone https://github.com/thephilipjones/GamePulse.git
cd gamepulse

# 3. Create production .env file
nano .env
# Add required variables (see Environment Variables section below)

# 4. Create external Docker network for Traefik
docker network create traefik-public

# 5. Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 6. Verify deployment
docker compose ps
curl http://localhost:8000/api/v1/utils/health-check/

# 7. Wait for Traefik to provision SSL certificate (~2 minutes)
# Check logs: docker compose logs proxy

# 8. Verify HTTPS access
curl https://api.gamepulse.top/api/v1/utils/health-check/
```

**Automated GitHub Actions Deployment:**

Every push to `main` branch triggers automated deployment (`.github/workflows/deploy.yml`):

1. **Lint** → Backend (ruff, mypy) + Frontend (biome) - runs in parallel
2. **Test** → Backend tests with PostgreSQL service + Frontend tests - runs in parallel
   - Backend test coverage reported in CI logs
3. **Generate Client** → Auto-regenerate TypeScript client from OpenAPI schema (auto-commits if changed)
4. **Build** → Docker images for backend and frontend, push to ECR Public
5. **Deploy** → Connect via SSM, pull latest code, pull images from ECR, restart services
6. **Smoke Test** → Health check with retry logic

The deploy job:

- Authenticates via OIDC (no stored credentials)
- Connects to EC2 via SSM Session Manager
- Executes deployment commands as ubuntu user
- Waits for completion with timeout (10 minutes)
- Reports success/failure with command output

**Environment Variables:**

Required variables in `/opt/gamepulse/.env`:

```bash
# Application
DOMAIN=gamepulse.top
ENVIRONMENT=production
PROJECT_NAME=gamepulse
STACK_NAME=gamepulse-prod

# Security
SECRET_KEY=<generate-with-python-secrets>
FIRST_SUPERUSER=admin@gamepulse.top
FIRST_SUPERUSER_PASSWORD=<secure-password>

# Database
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=gamepulse
POSTGRES_USER=gamepulse
POSTGRES_PASSWORD=<secure-password>

# Docker Images (ECR Public URLs from terraform output)
DOCKER_IMAGE_BACKEND=public.ecr.aws/REGISTRY_ALIAS/gamepulse/backend
DOCKER_IMAGE_FRONTEND=public.ecr.aws/REGISTRY_ALIAS/gamepulse/frontend
TAG=latest

# Frontend
FRONTEND_HOST=https://gamepulse.top

# CORS (comma-separated origins)
BACKEND_CORS_ORIGINS=https://gamepulse.top,https://api.gamepulse.top

# Email (optional)
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAILS_FROM_EMAIL=noreply@gamepulse.top

# Monitoring (optional)
SENTRY_DSN=
```

#### Rollback Procedure

If a deployment introduces issues:

**Option 1: Git Revert (Recommended)**

```bash
# SSH to EC2 instance
ssh -i ~/.ssh/gamepulse-key.pem ubuntu@<ELASTIC_IP>

# Navigate to deployment directory
cd /opt/gamepulse

# Find the problematic commit
git log --oneline -n 10

# Revert to previous commit
git revert <bad-commit-sha>
# OR reset to known good commit (more aggressive)
git reset --hard <good-commit-sha>

# Rebuild and restart services
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate

# Verify services
docker compose ps
curl http://localhost:8000/api/v1/utils/health-check/
```

**Option 2: Rollback via GitHub Actions**

```bash
# Revert the commit locally
git revert <bad-commit-sha>

# Push to main - this triggers automated deployment
git push origin main

# Monitor deployment in GitHub Actions
# https://github.com/thephilipjones/GamePulse/actions
```

**Option 3: Emergency Manual Restart**

```bash
# If services are crashed but code is fine
cd /opt/gamepulse
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart

# If images are corrupted
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --force-recreate
```

**Emergency Access:**

- Admin SSH access remains available from approved IPs as fallback
- SSM Session Manager provides additional access path
- CloudTrail logs all access for audit purposes

#### ECR Public Lifecycle Policy Configuration (Optional)

ECR Public does not support lifecycle policies via Terraform. To configure lifecycle management for cost optimization:

**Manual Setup via AWS Console:**

1. Navigate to [Amazon ECR Public Gallery Console](https://console.aws.amazon.com/ecr/repositories?region=us-east-1)
2. Select repository: `gamepulse/backend` or `gamepulse/frontend`
3. Go to **Lifecycle policy** tab
4. Click **Create lifecycle policy**
5. Configure policy rules:

**Recommended Policy Rules:**

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 3 tagged images for rollback capability",
      "selection": {
        "tagStatus": "tagged",
        "countType": "imageCountMoreThan",
        "countNumber": 3
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Delete untagged images after 1 day to save storage",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
```

**Alternative: AWS CLI Setup:**

```bash
# Create lifecycle policy file
cat > lifecycle-policy.json <<'EOF'
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 3 tagged images",
      "selection": {
        "tagStatus": "tagged",
        "countType": "imageCountMoreThan",
        "countNumber": 3
      },
      "action": {
        "type": "expire"
      }
    },
    {
      "rulePriority": 2,
      "description": "Delete untagged images after 1 day",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 1
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
EOF

# Apply to backend repository
aws ecr-public put-lifecycle-policy \
  --repository-name gamepulse/backend \
  --lifecycle-policy-text file://lifecycle-policy.json \
  --region us-east-1

# Apply to frontend repository
aws ecr-public put-lifecycle-policy \
  --repository-name gamepulse/frontend \
  --lifecycle-policy-text file://lifecycle-policy.json \
  --region us-east-1
```

**Benefits:**

- Automatic cleanup of old images (saves storage costs)
- Maintains rollback capability (keeps last 3 tagged versions)
- Removes build artifacts (untagged images from failed builds)

**Note:** ECR Public provides 50GB free storage, so lifecycle policies are optional for this project. Recommended for long-term production use.

#### Monitoring and Logs

```bash
# View application logs
cd /opt/gamepulse
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f proxy

# View Docker system status
docker ps
docker stats

# View CloudWatch logs (from local machine with AWS CLI)
aws logs tail /gamepulse/backend --follow
aws logs tail /gamepulse/frontend --follow

# View CloudTrail SSM session logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=StartSession \
  --max-items 10
```

## Architecture & Code Structure

### CI/CD Architecture

**GitHub Actions Workflow:**

Single consolidated workflow (`.github/workflows/deploy.yml`) replaces 11 legacy FastAPI template workflows.

**Workflow Optimization:**

- **Parallel execution:** Lint and test jobs run concurrently for speed
- **Dependency caching:** uv (Python) and npm dependencies cached via GitHub Actions
- **Minimal secrets:** OIDC authentication eliminates long-lived AWS credentials
- **Auto-generation:** TypeScript client regenerates automatically on OpenAPI changes

**Workflow Phases:**

```
Phase 1 (Parallel)
├─ lint-backend (ruff, mypy)
├─ lint-frontend (biome)
└─ validate-docker (compose config)

Phase 2 (Parallel, after Phase 1)
├─ test-backend (pytest + coverage)
└─ test-frontend (if configured)

Phase 3 (Sequential, after Phase 2)
└─ generate-client (TypeScript from OpenAPI)
   └─ Auto-commit if changed

Phase 4 (Sequential, after Phase 3)
└─ build (Docker images)
   └─ deploy (to EC2 via SSM)
      └─ smoke-test (health check)
```

**Key Design Decisions:**

- **Single workflow:** Easier to maintain than multiple independent workflows
- **Client generation after tests:** Ensures OpenAPI schema is validated before generation
- **Build after client generation:** Ensures latest client is included in Docker images
- **Coverage in logs only:** No external service required (smokeshow removed)

### Backend Architecture

**Directory Structure:**

```
backend/app/
├── api/              # API routes organized by resource
│   ├── deps.py      # Dependency injection (DB sessions, current user)
│   ├── main.py      # API router aggregation
│   └── routes/      # Route modules (items.py, utils.py, etc.)
├── core/            # Core functionality (config, db, security)
├── models/          # SQLModel models (database tables)
├── crud.py          # CRUD operations (separated from routes)
├── utils.py         # Utility functions
├── tests/           # Pytest test suite
└── alembic/         # Database migrations
```

**Key Patterns:**

- **SQLModel**: Combines Pydantic + SQLAlchemy for unified models
- **Dependency Injection**: `api/deps.py` provides reusable dependencies (DB sessions, auth)
- **CRUD Separation**: Database operations in `crud.py`, business logic in routes
- **Alembic Migrations**: All schema changes go through Alembic (never modify `SQLModel.metadata.create_all`)

**Important Files:**

- `app/main.py`: Application entry point, CORS, middleware setup
- `app/core/config.py`: Settings management (reads from .env)
- `app/core/db.py`: Database session management
- `app/core/security.py`: JWT token generation/verification, password hashing
- `app/models.py`: SQLModel database models
- `app/backend_pre_start.py`: Pre-start checks (DB connectivity)

### Frontend Architecture

**Directory Structure:**

```
frontend/src/
├── client/          # Auto-generated OpenAPI client (DO NOT EDIT)
├── components/      # Reusable React components
├── hooks/           # Custom React hooks
├── routes/          # TanStack Router pages
├── theme/           # Chakra UI theme customization
└── main.tsx         # Application entry point
```

**Key Patterns:**

- **TanStack Router**: File-based routing with type-safe navigation
- **TanStack Query**: Async state management for API calls
- **Auto-generated Client**: OpenAPI TypeScript client provides type-safe API access
- **Chakra UI**: Component library with dark mode support

**Important Notes:**

- NEVER manually edit files in `src/client/` - they're auto-generated
- Always regenerate client after backend API changes
- Use TanStack Query for all API calls (automatic caching, refetching)

### Database & Migrations

**Database Architecture:**
GamePulse uses **two separate PostgreSQL databases** on the same server:

1. **`app` database** - Application data (teams, games, users) managed by Alembic migrations
2. **`dagster` database** - Dagster orchestration metadata (runs, schedules, event logs) managed by Dagster

**Why Separate Databases:**

- Prevents conflicts between Alembic migrations (application) and Dagster schema
- Isolates orchestration metadata from application data
- Allows independent backup/restore and migration strategies

**TimescaleDB Extension:**
The PostgreSQL database includes the TimescaleDB extension for time-series data capabilities.

**Application Database Migration Workflow (Alembic):**

1. Modify SQLModel models in `backend/app/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review generated migration in `backend/app/alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. Commit migration files to git

**NEVER:**

- Uncomment `SQLModel.metadata.create_all(engine)` in production
- Manually modify the database schema
- Skip migrations for schema changes

**Dagster Database Initialization:**

The `dagster` database requires separate initialization from Alembic migrations:

```bash
# Check if dagster database exists
docker compose exec db psql -U postgres -l | grep dagster

# Create database if missing
docker compose exec db psql -U postgres -c "CREATE DATABASE dagster;"

# Initialize Dagster schema (creates ~25 tables)
docker compose exec dagster-daemon dagster instance migrate

# Verify tables created
docker compose exec db psql -U postgres -d dagster -c "\dt" | head -20
```

**Automatic Initialization:**
The `backend/scripts/prestart.sh` script automatically handles Dagster database creation and schema initialization on deployment if `DAGSTER_POSTGRES_DB` environment variable is set to a value different from `POSTGRES_DB`.

**Dimensional Data Seeding:**

GamePulse uses JSON seed files for dimensional data (teams, conferences) that rarely change:

- Seed files location: `backend/app/data/`
  - `conferences.json`: NCAA conferences with group metadata
  - `teams.json`: Team details with colors, aliases for Reddit matching
- Migration: `7a8f23177a57_seed_dimensional_data.py` loads seed files on upgrade
- Upsert logic: Migration uses `ON CONFLICT DO UPDATE` for idempotency (can run multiple times safely)

**Re-seeding Data:**

If you need to update dimensional data after initial deployment:

```bash
# Option 1: Edit JSON files and re-run migration (idempotent)
# 1. Edit backend/app/data/teams.json or conferences.json
# 2. Migration automatically updates on container restart (if not yet applied)

# Option 2: Manually re-apply data changes
docker compose exec backend python
>>> from pathlib import Path
>>> import json
>>> from sqlmodel import Session, create_engine, select
>>> from app.core.config import settings
>>> from app.models.team import Team, TeamGroup
>>> engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
>>> # Load and upsert data manually using session.merge() or raw SQL
```

**Validation Queries:**

```bash
# Check seeded data
docker compose exec backend python -c "
from sqlmodel import Session, create_engine, select
from app.core.config import settings
from app.models.team import Team, TeamGroup

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
with Session(engine) as session:
    conferences = session.exec(select(TeamGroup).where(TeamGroup.sport == 'ncaam')).all()
    teams = session.exec(select(Team).where(Team.sport == 'ncaam')).all()
    print(f'Conferences: {len(conferences)}, Teams: {len(teams)}')
    for conf in conferences:
        print(f'  - {conf.team_group_name} ({conf.team_group_id})')
"
```

### AWS Deployment Architecture

**Infrastructure (Terraform):**

```
VPC (10.1.0.0/16)
├── Public Subnet (10.1.1.0/24) - EC2 instance, Elastic IP
└── Private Subnet (10.1.2.0/24) - Reserved for future RDS
```

**Terraform Modules:**

- `modules/vpc/`: VPC, subnets, Internet Gateway, route tables
- `modules/compute/`: EC2 instance, security groups, IAM roles, CloudWatch

**Security:**

- SSH: Restricted to specific IPs (admin_ip_cidrs + tailscale_device_ips in terraform.tfvars)
- HTTP/HTTPS: Open to internet (0.0.0.0/0)
- GitHub Actions: OIDC authentication (no long-lived credentials)
- EC2 Instance: Ubuntu 24.04 with Docker, Docker Compose, Tailscale pre-installed

**Memory Management (t2.micro optimization):**

- **Swap Space:** 4GB swap file automatically created during instance provisioning
- **Location:** `/swapfile` with 600 permissions (root only)
- **Persistence:** Configured in `/etc/fstab` for automatic mounting on reboot
- **Swappiness:** Tuned to `vm.swappiness=10` (optimized for server workloads)
  - Default is 60 (aggressive swapping)
  - 10 = only swap when necessary, prioritize RAM for better performance
- **Why needed:** t2.micro has only 1GB RAM; 4GB swap prevents OOM (Out of Memory) crashes
- **Automatic setup:** Configured in `terraform/modules/compute/user_data.sh`
- **Idempotent:** Safe to run multiple times, checks if swap already exists

**Verify swap status:**

```bash
# Check swap is enabled
swapon --show

# View memory and swap usage
free -h

# Check swappiness setting
cat /proc/sys/vm/swappiness
```

**Deployment Process:**

1. Push to `main` triggers GitHub Actions workflow
2. Lint (ruff, mypy, biome) → Test (pytest, npm test) → Build (Docker images)
3. OIDC auth to AWS → SSM send-command to EC2 instance
4. EC2 pulls latest code, rebuilds images, restarts services
5. Smoke test hits health endpoint to verify deployment

## Important Conventions

### Secret Management

GamePulse uses **AWS Systems Manager Parameter Store** for centralized secret management with the following architecture:

**Benefits:**

- ✅ **FREE** (vs $30-54/year for Secrets Manager)
- ✅ KMS encryption at rest for sensitive values
- ✅ CloudTrail audit logging of all parameter access
- ✅ Automated secret injection during deployment
- ✅ Version tracking and rollback capability
- ✅ No secrets in Terraform state or GitHub

**Parameter Hierarchy:**

```
/gamepulse/
├── production/
│   ├── app/ (secret_key, first_superuser, domain, etc.)
│   ├── database/ (password, name, user, server, port)
│   ├── docker/ (backend_image, frontend_image, tag)
│   └── email/ (smtp credentials - optional)
└── shared/
    └── infrastructure/
        └── tailscale_authkey
```

**Initial Setup (One-Time):**

1. **Provision infrastructure:**

   ```bash
   cd terraform
   terraform apply
   ```

   This creates:

   - KMS key for encryption (alias: `gamepulse-secrets`)
   - Parameter Store entries with placeholder values
   - IAM policies for EC2 to read parameters

2. **Populate actual secret values:**

   ```bash
   ./scripts/populate-parameters.sh production
   ```

   This script will:

   - Generate secure random values for `SECRET_KEY` and `POSTGRES_PASSWORD`
   - Prompt for admin password and Tailscale auth key
   - Write encrypted secrets to Parameter Store
   - Verify parameters were created successfully

3. **Verify parameters:**

   ```bash
   # List all production parameters
   aws ssm get-parameters-by-path \
     --path '/gamepulse/production/' \
     --recursive \
     --region us-east-1

   # Get specific parameter (with decryption)
   aws ssm get-parameter \
     --name '/gamepulse/production/app/secret_key' \
     --with-decryption \
     --region us-east-1
   ```

**How Secrets are Loaded:**

1. **During Deployment (Automated):**

   - GitHub Actions triggers deployment on push to `main`
   - Deployment script runs `backend/scripts/load-secrets.sh production .env` on EC2
   - Script fetches all parameters from `/gamepulse/production/` via AWS CLI
   - Parameters are mapped to `.env` format and written to disk
   - Docker Compose reads `.env` and starts services
   - `.env` is deleted after deployment for security

2. **Local Testing (Manual):**
   ```bash
   # On EC2 or locally with AWS credentials
   cd /opt/gamepulse
   bash backend/scripts/load-secrets.sh production .env
   cat .env  # Verify contents
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

**Rotating Secrets:**

```bash
# Rotate a specific secret
aws ssm put-parameter \
  --name '/gamepulse/production/database/password' \
  --value 'new-secure-password' \
  --type SecureString \
  --overwrite

# View parameter history
aws ssm get-parameter-history \
  --name '/gamepulse/production/database/password'

# Trigger redeployment to apply new secrets
git push origin main  # Or manually restart on EC2
```

**Tailscale Auto-Connection:**

Tailscale auth key is stored in Parameter Store and automatically used during EC2 instance provisioning:

- Parameter: `/gamepulse/shared/infrastructure/tailscale_authkey`
- User data script fetches key and runs `tailscale up --authkey=...`
- New EC2 instances automatically join Tailscale network on boot

**Security Best Practices:**

1. **Never commit secrets to git** - Use Parameter Store instead
2. **Rotate secrets regularly** - Use `aws ssm put-parameter --overwrite`
3. **Delete .env files** - After deployment, remove local copies
4. **Use SecureString** - All sensitive parameters encrypted with KMS
5. **Audit access** - Review CloudTrail logs for parameter access
6. **Least privilege** - EC2 can only read, not write parameters

### Environment Variables

**Note:** In production, environment variables are automatically generated from Parameter Store (see Secret Management section above). For local development, create `.env` manually:

**Required in .env (Local Development):**

- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`: Initial admin account
- `POSTGRES_PASSWORD`: Database password
- `DOMAIN`: `localhost` for dev, actual domain for production
- `ENVIRONMENT`: `local` / `staging` / `production`

**Frontend (.env):**

- `VITE_API_URL`: Backend API URL (defaults to http://localhost:8000)

**Production:**

- Environment variables are stored in AWS Parameter Store
- Automatically loaded via `backend/scripts/load-secrets.sh` during deployment
- Never manually create `.env` files in production

### Testing Patterns

**Backend Tests:**

- Use pytest fixtures from `conftest.py`
- Test database is automatically created/torn down
- Use `client` fixture for API endpoint testing
- Test files mirror app structure: `app/api/routes/items.py` → `app/tests/api/test_items.py`

**Frontend Tests:**

- Playwright for E2E tests
- Requires backend running (`docker compose up -d --wait backend`)
- Clean up with `docker compose down -v` after tests

### Docker Compose Files

**Three compose files:**

1. `docker-compose.yml`: Base configuration (all environments)
2. `docker-compose.override.yml`: Development overrides (auto-loaded, volume mounts, hot reload)
3. `docker-compose.prod.yml`: Production overrides (explicit, no dev tools)

**Important: Override File Behavior**

- Docker Compose **automatically** loads `docker-compose.override.yml` unless you explicitly specify `-f` flags
- This means `docker compose up` loads both `docker-compose.yml` + `docker-compose.override.yml`
- The override file configures development mode: `fastapi run --reload` (WatchFiles auto-reloader)
- In production, this causes high CPU usage as WatchFiles constantly polls the filesystem

**Development:**

```bash
docker compose watch  # Uses base + override (development mode)
```

**Production (CRITICAL - must use explicit -f flags):**

```bash
# Correct: Explicitly loads prod config, excludes override file
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# WRONG: Auto-loads override file, runs in development mode
docker compose up -d
```

**Production Configuration:**

- Backend: `fastapi run --workers 1 app/main.py` (no `--reload` flag)
- Worker count: 1 (optimized for t2.micro single vCPU)
- Healthchecks: 30-second intervals (vs 10s in development)

### Git Workflow

**Branches:**

- `main`: Production branch (auto-deploys to EC2 on every push)

**GitHub Actions Workflow:**

Single workflow file: `.github/workflows/deploy.yml`

Every push to `main` triggers:

1. **Parallel Phase 1:**
   - Lint backend (ruff, mypy)
   - Lint frontend (biome)
   - Validate Docker Compose config
2. **Parallel Phase 2:**
   - Test backend (pytest + coverage)
   - Test frontend (if configured)
3. **Sequential Phase 3:**
   - Generate TypeScript client from OpenAPI
   - Auto-commit if schema changed
4. **Sequential Phase 4:**
   - Build Docker images
   - Push to ECR Public
   - Deploy to EC2 via SSM
   - Smoke test health endpoint

**GitHub Secrets Required:**

- `AWS_GITHUB_ACTIONS_ROLE_ARN`: IAM role for OIDC authentication
- `AWS_EC2_INSTANCE_ID`: Target EC2 instance ID
- `ECR_BACKEND_URL`: ECR Public URL for backend image
- `ECR_FRONTEND_URL`: ECR Public URL for frontend image

**Note:** Application secrets (passwords, keys) are stored in Parameter Store, not GitHub Secrets. See Secret Management section for details.

## Common Development Tasks

### Adding a New API Endpoint

1. Define route in `backend/app/api/routes/<resource>.py`
2. Add CRUD operation in `backend/app/crud.py` (if needed)
3. Add tests in `backend/app/tests/api/test_<resource>.py`
4. Commit and push to `main`
5. TypeScript client automatically regenerates via GitHub Actions
6. Use generated client in frontend React components

**Manual client generation (for local dev):**

```bash
./scripts/generate-client.sh
```

### Adding a New Database Model

1. Create SQLModel class in `backend/app/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Add <model>"`
3. Review migration in `backend/app/alembic/versions/`
4. Apply: `alembic upgrade head`
5. Add CRUD operations in `backend/app/crud.py`
6. Commit migration files

### Updating Dependencies

**Backend:**

```bash
# Add new package
uv add <package-name>

# Update existing
uv sync --upgrade-package <package-name>

# After changes, rebuild Docker
docker compose build backend
```

**Frontend:**

```bash
npm install <package-name>
npm install <package-name> --save-dev  # Dev dependency

# After changes, rebuild Docker
docker compose build frontend
```

### Debugging in Docker

**Backend:**

```bash
# Option 1: View logs
docker compose logs -f backend

# Option 2: Exec into container
docker compose exec backend bash
# Then run: fastapi run --reload app/main.py

# Option 3: Run Python interpreter
docker compose exec backend python
```

**Database:**

```bash
# Access Adminer UI: http://localhost:8080
# System: PostgreSQL
# Server: db
# Username: postgres (from .env)
# Password: (from .env)
# Database: app
```

### Infrastructure Updates

1. Modify `terraform/*.tf` or `terraform/modules/**/*.tf`
2. Review plan: `terraform plan`
3. Apply changes: `terraform apply`
4. Commit Terraform state changes (if using local state)

**Note:** This project uses local Terraform state. For production, consider remote state (S3 + DynamoDB).

## Troubleshooting

**Issue: "Module not found" in backend**

- Solution: Ensure you're in activated venv or use `docker compose exec backend`

**Issue: Frontend can't reach backend**

- Check `VITE_API_URL` in `frontend/.env`
- Verify backend is running: `curl http://localhost:8000/docs`

**Issue: Database migration conflicts**

- Never manually edit applied migrations
- Create new migration to fix issues
- Use `alembic downgrade` cautiously (data loss risk)

**Issue: Docker build fails**

- Clear build cache: `docker compose build --no-cache`
- Remove old containers: `docker compose down -v`

**Issue: GitHub Actions workflow fails**

- Check GitHub Actions logs for specific error
- **Linting failures:** Pre-commit hooks should catch these locally
  - Backend: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy .`
  - Frontend: `cd frontend && npm run lint`
- **Test failures:** Run tests locally first
  - Backend: `cd backend && uv run pytest -v`
  - Frontend: `cd frontend && npm test` (if configured)
- **Deployment failures:**
  - Verify AWS EC2 instance is running: `aws ec2 describe-instances --instance-ids <id>`
  - SSH to instance and check Docker logs: `docker compose logs`

**Issue: Pre-commit hooks failing**

- Ensure hooks are installed: `uv run pre-commit install`
- Run manually to see errors: `uv run pre-commit run --all-files`
- Common fixes:
  - Ruff formatting: `cd backend && uv run ruff format .`
  - Fix end-of-file/trailing whitespace issues (auto-fixed by pre-commit)

**Issue: VSCode not formatting on save**

- Install recommended extensions (VSCode will prompt)
  - Python: `charliermarsh.ruff`
  - JavaScript/TypeScript: `biomejs.biome`
- Check VSCode settings are loaded: `.vscode/settings.json` should be present
- Reload VSCode window: Cmd+Shift+P → "Developer: Reload Window"

**Issue: Terraform apply fails**

- Check AWS credentials: `aws sts get-caller-identity`
- Verify terraform.tfvars has correct IP addresses
- Check SSH key exists: `ls -l ~/.ssh/gamepulse-key*`

**Issue: Dagster services won't start or in restart loop**

- **Symptom:** Dagster webserver/daemon containers constantly restarting
- **Common causes:**
  1. Missing `dagster` database - Check if database exists:
     ```bash
     docker compose exec db psql -U postgres -l | grep dagster
     ```
  2. Database exists but schema not initialized - Verify tables exist:
     ```bash
     docker compose exec db psql -U postgres -d dagster -c "\dt" | head -20
     ```
- **Solution:**

  ```bash
  # Create database if missing
  docker compose exec db psql -U postgres -c "CREATE DATABASE dagster;"

  # Initialize Dagster schema
  docker compose exec dagster-daemon dagster instance migrate

  # Restart services
  docker compose restart dagster-daemon dagster-webserver
  ```

- **Prevention:** The `prestart.sh` script should handle this automatically in future deployments

**Issue: High CPU usage from Dagster or ssm-worker processes**

- **Symptom:** EC2 instance slow, high CPU usage visible in `top` or CloudWatch
- **Root cause:** Dagster services in infinite retry loop trying to connect to uninitialized database
- **Solution:** Follow "Dagster services won't start" steps above - CPU should normalize within 1-2 minutes
- **Verification:**

  ```bash
  # Check CPU before fix
  top -bn1 | grep -E "Cpu|dagster|ssm"

  # After fix, verify Dagster is healthy
  docker compose exec dagster-daemon dagster instance info

  # Check CPU normalized
  top -bn1 | grep -E "Cpu|dagster|ssm"
  ```

**Issue: Dagster UI shows "Instance misconfigured" or connection errors**

- **Symptom:** Dagster UI loads but shows configuration errors
- **Check environment variables:**
  ```bash
  docker compose config | grep DAGSTER
  ```
- **Verify all required variables are set:**
  - `DAGSTER_POSTGRES_URL` - Should point to `dagster` database (not `app`)
  - `DAGSTER_POSTGRES_DB=dagster` - Separate database name
  - `DAGSTER_HOME=/tmp/dagster_home` - Dagster runtime directory
- **Verify database connection:**
  ```bash
  docker compose exec dagster-daemon python -c "
  import os
  from dagster_postgres.run_storage import PostgresRunStorage
  print(f'DB URL: {os.getenv(\"DAGSTER_POSTGRES_URL\")}')
  "
  ```

**Issue: Dagster schedule not running (ncaa_games_schedule)**

- **Check schedule status in Dagster UI:**
  - Navigate to **Schedules** tab
  - Verify `ncaa_games_schedule` shows status **Running** (not **Stopped**)
- **If stopped, start it:**
  - Click toggle to enable schedule
  - Schedule runs every 15 minutes (cron: `*/15 * * * *`)
- **Check daemon is processing schedules:**
  ```bash
  docker compose logs dagster-daemon | grep -i schedule
  # Should see: "Checking for new runs for schedule: ncaa_games_schedule"
  ```
- **Manual test:**
  ```bash
  # Trigger manual materialization
  docker compose exec dagster-daemon dagster asset materialize -m app.dagster_definitions ncaa_games
  ```

**Issue: Dagster asset materialization fails**

- **Check logs for specific error:**
  ```bash
  docker compose logs dagster-daemon | grep -A 20 "ncaa_games"
  ```
- **Common causes:**
  1. **Database connection issues** - Check `POSTGRES_*` env vars
  2. **NCAA API timeout** - Network connectivity issue
  3. **Missing teams in dim_team** - Run seed migration: `alembic upgrade head`
- **Verify database tables exist:**
  ```bash
  docker compose exec db psql -U postgres -d app -c "\dt" | grep -E "dim_team|fact_game"
  ```

**Issue: High CPU usage / Credit Bankruptcy on t2.micro (28% resting CPU)**

- **Symptom:** EC2 instance consistently using 25-30% CPU at rest, burning through CPU credits faster than they accumulate
- **Root cause:** Backend running in development mode with `--reload` flag (WatchFiles auto-reloader) + aggressive 10-second healthchecks
- **Why this happens:**
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` automatically loads `docker-compose.override.yml` unless explicitly excluded
  - Override file sets `command: fastapi run --reload app/main.py` (development mode)
  - WatchFiles constantly polls filesystem for changes (significant CPU overhead)
  - Healthchecks running every 10 seconds add 5-10% CPU overhead on t2.micro
- **Solution:** The production command override in `docker-compose.prod.yml` fixes this by:
  1. Using `fastapi run --workers 1 app/main.py` (removes `--reload` flag)
  2. Optimizing worker count for single-vCPU t2.micro
  3. Relaxing healthcheck intervals from 10s to 30s (70% reduction)
- **Expected result:** CPU should drop from 28% to 5-10% after redeployment
- **Verification:**

  ```bash
  # On EC2 instance, check current CPU usage
  top -bn1 | head -15

  # Verify backend is running in production mode (no WatchFiles)
  docker compose logs backend | grep -i "watch\|reload"
  # Should see: "Started server process [X]" (NOT "Started reloader process")

  # Check healthcheck intervals
  docker compose ps --format json | jq '.[].Health'
  ```

- **Prevention:** Always use explicit `-f` flags when deploying to production to exclude override file

**Issue: Out of Memory (OOM) errors or containers being killed**

- **Symptom:** Docker containers randomly exit, `dmesg` shows OOM killer messages, services restart unexpectedly
- **Root cause:** t2.micro has only 1GB RAM, insufficient for running multiple Docker containers
- **Solution:** 4GB swap space is automatically configured during instance provisioning via `user_data.sh`
- **Verify swap is enabled:**

  ```bash
  # Check swap status
  swapon --show
  # Should show: /swapfile with 4G size

  # View memory and swap usage
  free -h

  # Check for OOM killer events
  dmesg | grep -i "killed process"
  ```

- **Manual setup (if swap missing):**

  ```bash
  # Create 4GB swap file
  sudo fallocate -l 4G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile

  # Make persistent across reboots
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

  # Optimize swappiness for servers
  echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
  sudo sysctl -w vm.swappiness=10
  ```

- **Prevention:** Swap is automatically configured on new EC2 instances. For existing instances, run manual setup above.
