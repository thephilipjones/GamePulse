# GamePulse Deployment Setup

This document describes the first-time setup process for deploying GamePulse to AWS EC2 with automated CI/CD via GitHub Actions.

## Prerequisites

- AWS EC2 instance provisioned (Story 1.1b - COMPLETE)
- SSH key available at `~/.ssh/gamepulse-key`
- EC2 Public IP: `34.196.105.123`
- Domain: `gamepulse.top` (configured with A records)
- GitHub repository: `https://github.com/thephilipjones/GamePulse.git`

## Architecture Overview

The deployment uses GitHub Actions with 5 sequential jobs:

```
push to main → Lint → Test → Build → Deploy → Smoke Test
```

Each job acts as a quality gate - the pipeline stops if any job fails, preventing broken code from reaching production.

### Job Descriptions

1. **Lint** (<2 min): Runs `ruff`, `mypy`, and `biome` to validate code quality
2. **Test** (<3 min): Runs `pytest` with TimescaleDB service container
3. **Build** (<3 min): Builds Docker images for backend and frontend
4. **Deploy** (<2 min): SSHs to EC2, pulls code, rebuilds containers
5. **Smoke Test** (<1 min): Verifies health endpoint responds correctly

## First-Time EC2 Setup

These commands only need to be run **once** to prepare the EC2 instance for automated deployments.

### Step 1: SSH to EC2 Instance

```bash
ssh -i ~/.ssh/gamepulse-key ubuntu@34.196.105.123
```

### Step 2: Install Git (if not present)

```bash
sudo apt-get update
sudo apt-get install -y git
```

### Step 3: Create Deployment Directory

```bash
# Create directory in /opt (standard for production apps)
sudo mkdir -p /opt/gamepulse

# Change ownership to ubuntu user
sudo chown ubuntu:ubuntu /opt/gamepulse

# Navigate to deployment directory
cd /opt/gamepulse
```

### Step 4: Clone Repository

```bash
git clone https://github.com/thephilipjones/GamePulse.git .
```

**Note:** The trailing `.` clones directly into the current directory.

### Step 5: Create Production Environment File

Create `/opt/gamepulse/.env` with production configuration:

```bash
cat > /opt/gamepulse/.env <<'EOF'
# Domain Configuration
DOMAIN=gamepulse.top
FRONTEND_HOST=https://dashboard.gamepulse.top

# Environment
ENVIRONMENT=production

# Project Identification
PROJECT_NAME=GamePulse
STACK_NAME=gamepulse

# Backend Configuration
BACKEND_CORS_ORIGINS=["https://gamepulse.top","https://dashboard.gamepulse.top","https://api.gamepulse.top","https://www.gamepulse.top"]
SECRET_KEY=CHANGE_ME_GENERATE_SECURE_KEY
FIRST_SUPERUSER=admin@gamepulse.com
FIRST_SUPERUSER_PASSWORD=CHANGE_ME_SECURE_PASSWORD

# Database Configuration
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_DB=gamepulse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD

# Docker Image Names
DOCKER_IMAGE_BACKEND=backend
DOCKER_IMAGE_FRONTEND=frontend

# Optional Services (disabled)
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
EMAILS_FROM_EMAIL=
SENTRY_DSN=
CI=
EOF
```

### Step 6: Generate Secure Secrets

Replace the `CHANGE_ME` placeholders with secure values:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate FIRST_SUPERUSER_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

Edit `.env` and replace:
- `POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD`
- `SECRET_KEY=CHANGE_ME_GENERATE_SECURE_KEY`
- `FIRST_SUPERUSER_PASSWORD=CHANGE_ME_SECURE_PASSWORD`

### Step 7: Initial Deployment

```bash
cd /opt/gamepulse

# Build Docker images
docker compose build

# Start services
docker compose up -d

# Verify services are running
docker compose ps

# Check logs
docker compose logs -f
```

### Step 8: Verify Deployment

```bash
# Check health endpoint
curl https://api.gamepulse.top/api/v1/utils/health-check/
# Expected response: true

# Check API documentation
curl https://api.gamepulse.top/docs
# Should return HTML for Swagger UI

# Check frontend
curl https://dashboard.gamepulse.top/
# Should return HTML for React app
```

## GitHub Repository Configuration

### Configure GitHub Secrets

1. Navigate to: `https://github.com/thephilipjones/GamePulse/settings/secrets/actions`

2. Click **"New repository secret"**

3. Add `AWS_EC2_HOST`:
   - Name: `AWS_EC2_HOST`
   - Value: `34.196.105.123`

4. Add `AWS_SSH_KEY`:
   - Name: `AWS_SSH_KEY`
   - Value: Entire contents of `~/.ssh/gamepulse-key` (include BEGIN/END lines)

To copy the SSH key on macOS:

```bash
cat ~/.ssh/gamepulse-key | pbcopy
```

Then paste into GitHub Secrets.

## Testing the CI/CD Pipeline

### Make a Test Commit

```bash
# On your local machine
cd /Users/Philip/dev/gamepulse

# Make a trivial change
echo "# CI/CD Test" >> docs/deployment-setup.md

# Commit and push to main
git add docs/deployment-setup.md
git commit -m "test: Trigger CI/CD pipeline"
git push origin main
```

### Monitor Workflow Execution

1. Visit: `https://github.com/thephilipjones/GamePulse/actions`
2. Watch the "Deploy to AWS EC2" workflow run
3. Verify all 5 jobs pass (Lint → Test → Build → Deploy → Smoke Test)
4. Check deployment badge on README.md shows "passing"

### Verify Live Deployment

```bash
# Check health endpoint
curl https://api.gamepulse.top/api/v1/utils/health-check/

# Check API docs
open https://api.gamepulse.top/docs

# Check frontend
open https://dashboard.gamepulse.top
```

## Troubleshooting

### Deployment Fails on SSH Connection

**Symptom:** Deploy job fails with "Permission denied (publickey)"

**Solution:**
1. Verify `AWS_SSH_KEY` secret contains full private key with BEGIN/END lines
2. Check key permissions on EC2: `ls -la ~/.ssh/authorized_keys`
3. Verify security group allows SSH from GitHub Actions IPs

### Health Check Fails

**Symptom:** Smoke test fails with "Connection refused" or HTTP 000

**Solutions:**
1. Check services are running: `docker compose ps`
2. Check logs: `docker compose logs backend`
3. Verify Traefik is routing correctly: `docker compose logs traefik`
4. Allow 30 seconds for services to fully start after deployment

### Docker Build Fails

**Symptom:** Build job fails with "Error response from daemon"

**Solutions:**
1. Check Dockerfiles for syntax errors
2. Verify base images are accessible
3. Check disk space on EC2: `df -h`
4. Clean up old images: `docker system prune -af`

### Lint/Test Jobs Fail

**Symptom:** Pipeline stops at Lint or Test job

**Solutions:**
1. Run linters locally: `cd backend && uv run ruff check .`
2. Run tests locally: `cd backend && uv run pytest`
3. Fix issues before pushing to main
4. Use feature branches to test changes before merging

## Continuous Deployment Workflow

After initial setup, every push to `main` automatically:

1. Validates code quality (lint + test)
2. Builds Docker images
3. Deploys to EC2 via SSH
4. Verifies deployment with health check

**No manual steps required** - just push code and it deploys automatically.

## SSL Certificates

Traefik automatically provisions Let's Encrypt SSL certificates for:
- `gamepulse.top`
- `api.gamepulse.top`
- `dashboard.gamepulse.top`
- `www.gamepulse.top`

**First deployment may take 1-2 minutes** while Traefik requests certificates from Let's Encrypt.

Check certificate status:
```bash
docker compose logs proxy | grep -i "cert\|acme"
```

## Future Enhancements

### Custom Domain Migration

If you want to migrate to a different domain later:

1. Update DNS A records to point to `34.196.105.123`
2. Update `.env` on EC2 with new domain
3. Rebuild frontend: `docker compose build frontend`
4. Restart services: `docker compose down && docker compose up -d`
5. Update GitHub Actions workflow smoke test URL

## Related Documentation

- [Story 1.1b - AWS Infrastructure](/docs/stories/1-1b-provision-aws-infrastructure.md)
- [Story 1.3 - TimescaleDB Setup](/docs/stories/1-3-setup-timescaledb.md)
- [Story 1.4 - Database Schema](/docs/stories/1-4-create-database-schema.md)
- [Sprint Status](/docs/sprint-status.yaml)

## Support

For issues with deployment:
1. Check GitHub Actions workflow logs
2. SSH to EC2 and check `docker compose logs`
3. Review this troubleshooting guide
4. Check Story 1.5 acceptance criteria for expected behavior
