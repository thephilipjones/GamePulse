# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GamePulse is a full-stack web application built with FastAPI (backend) and React (frontend), deployed on AWS EC2 via GitHub Actions CI/CD. The project uses Docker Compose for development and production, with infrastructure managed through Terraform.

**Tech Stack:**
- Backend: FastAPI + SQLModel + PostgreSQL (TimescaleDB extension)
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

# Run tests
uv run pytest -v

# Run specific test
uv run pytest app/tests/api/test_items.py -v

# Run tests with coverage
uv run coverage run -m pytest
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
# Option 1 (automatic - requires backend venv):
./scripts/generate-client.sh

# Option 2 (manual):
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

### Pre-commit Hooks

```bash
# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
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
git clone https://github.com/PhilipTrauner/gamepulse.git
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

Every push to `main` branch triggers automated deployment:

1. **Lint** → Backend (ruff, mypy) + Frontend (biome)
2. **Test** → Backend tests with PostgreSQL service
3. **Build** → Docker images for backend and frontend
4. **Deploy** → Connect via SSM, pull latest code, rebuild images, restart services
5. **Smoke Test** → Health check with retry logic

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
# https://github.com/PhilipTrauner/gamepulse/actions
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

**TimescaleDB Extension:**
The PostgreSQL database includes the TimescaleDB extension for time-series data capabilities.

**Migration Workflow:**
1. Modify SQLModel models in `backend/app/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review generated migration in `backend/app/alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. Commit migration files to git

**NEVER:**
- Uncomment `SQLModel.metadata.create_all(engine)` in production
- Manually modify the database schema
- Skip migrations for schema changes

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

**Deployment Process:**
1. Push to `main` triggers GitHub Actions workflow
2. Lint (ruff, mypy, biome) → Test (pytest, npm test) → Build (Docker images)
3. OIDC auth to AWS → SSM send-command to EC2 instance
4. EC2 pulls latest code, rebuilds images, restarts services
5. Smoke test hits health endpoint to verify deployment

## Important Conventions

### Environment Variables

**Required in .env:**
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`: Initial admin account
- `POSTGRES_PASSWORD`: Database password
- `DOMAIN`: `localhost` for dev, actual domain for production
- `ENVIRONMENT`: `local` / `staging` / `production`

**Frontend (.env):**
- `VITE_API_URL`: Backend API URL (defaults to http://localhost:8000)

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

**Development:**
```bash
docker compose watch  # Uses base + override
```

**Production:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Git Workflow

**Branches:**
- `main`: Production branch (deploys to EC2 on push)

**Secrets (GitHub Actions):**
- `AWS_GITHUB_ACTIONS_ROLE_ARN`: IAM role for OIDC
- `AWS_EC2_INSTANCE_ID`: Target EC2 instance
- Other secrets: `DOMAIN_PRODUCTION`, `SECRET_KEY`, `POSTGRES_PASSWORD`, etc.

## Common Development Tasks

### Adding a New API Endpoint

1. Define route in `backend/app/api/routes/<resource>.py`
2. Add CRUD operation in `backend/app/crud.py` (if needed)
3. Add tests in `backend/app/tests/api/test_<resource>.py`
4. Regenerate frontend client: `./scripts/generate-client.sh`
5. Use generated client in frontend React components

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

**Issue: GitHub Actions deployment fails**
- Check GitHub Actions logs for specific error
- Verify AWS EC2 instance is running: `aws ec2 describe-instances --instance-ids <id>`
- SSH to instance and check Docker logs: `docker compose logs`

**Issue: Terraform apply fails**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify terraform.tfvars has correct IP addresses
- Check SSH key exists: `ls -l ~/.ssh/gamepulse-key*`
