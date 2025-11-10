# Story 1.5: Set Up GitHub Actions CI/CD Pipeline

Status: ready-for-dev

## Story

As a developer,
I want a GitHub Actions workflow that runs tests, builds Docker images, and deploys to AWS EC2,
so that every push to main branch automatically deploys the latest code and validates quality gates.

## Acceptance Criteria

1. **Workflow file created and configured**
   - `.github/workflows/deploy.yml` exists with production-ready configuration
   - Workflow triggers on push to `main` branch
   - Workflow includes 5 sequential jobs: lint, test, build, deploy, smoke-test
   - Job dependencies configured (test depends on lint, build depends on test, etc.)

2. **Lint job validates code quality**
   - Backend: Run `uv run ruff check .` and `uv run mypy .` in backend directory
   - Frontend: Run `npm run lint` in frontend directory
   - Job fails if any linting errors detected (blocking deployment)
   - Execution time: <2 minutes

3. **Test job validates functionality**
   - Backend: Run `uv run pytest` with database service (PostgreSQL container)
   - Frontend: Run `npm run test` (when tests exist)
   - Test database configured via environment variables
   - Job fails if any tests fail (blocking deployment)
   - Execution time: <3 minutes

4. **Build job creates Docker images**
   - Build backend Docker image: `docker build -t gamepulse-backend ./backend`
   - Build frontend Docker image: `docker build -t gamepulse-frontend ./frontend`
   - Images tagged with commit SHA for traceability
   - Optional: Push to Docker Hub or GitHub Container Registry (if configured)
   - Job fails if Docker build errors occur (blocking deployment)

5. **Deploy job updates EC2 instance**
   - SSH to EC2 instance using `appleboy/ssh-action@master`
   - Pull latest code: `git pull origin main`
   - Rebuild and restart services: `docker-compose -f docker-compose.prod.yml up -d --build`
   - Handle secrets via GitHub Secrets (AWS_EC2_HOST, AWS_SSH_KEY)
   - Job fails if deployment script errors occur

6. **Smoke test validates deployment**
   - curl health endpoint: `https://{elastic-ip}/api/health`
   - Verify HTTP 200 response with valid JSON
   - Retry up to 3 times with 10-second delays (allow services to stabilize)
   - Job fails if health check unsuccessful after retries

7. **GitHub Secrets configured**
   - AWS_EC2_HOST: Public IP or domain of EC2 instance
   - AWS_SSH_KEY: Private SSH key content (entire file)
   - Optional: DOCKER_HUB_USERNAME, DOCKER_HUB_TOKEN (if using Docker Hub)
   - Secrets verified by triggering workflow

8. **Workflow visibility and documentation**
   - Workflow badge added to README.md showing build status
   - Workflow runs visible in GitHub Actions tab
   - Clear error messages for debugging failed deployments

## Tasks / Subtasks

- [ ] Task 1.5.1: Create GitHub Actions Workflow File (AC: #1)
  - [ ] Create `.github/workflows/deploy.yml` with basic structure
  - [ ] Configure workflow trigger: on push to main branch
  - [ ] Define 5 jobs: lint, test, build, deploy, smoke-test
  - [ ] Set job dependencies: lint → test → build → deploy → smoke-test

- [ ] Task 1.5.2: Implement Lint Job (AC: #2)
  - [ ] Add Python lint step: `uv run ruff check .` and `uv run mypy .`
  - [ ] Add frontend lint step: `npm run lint`
  - [ ] Configure to run in parallel (backend and frontend independent)
  - [ ] Verify lint job fails on linting errors

- [ ] Task 1.5.3: Implement Test Job (AC: #3)
  - [ ] Add PostgreSQL service container for backend tests
  - [ ] Configure backend test step: `uv run pytest`
  - [ ] Configure frontend test step: `npm run test` (skip if no tests yet)
  - [ ] Set environment variables for test database connection
  - [ ] Verify test job fails on test failures

- [ ] Task 1.5.4: Implement Build Job (AC: #4)
  - [ ] Add Docker build step for backend image
  - [ ] Add Docker build step for frontend image
  - [ ] Tag images with commit SHA: `${GITHUB_SHA:0:7}`
  - [ ] Optional: Add Docker Hub push step (if using registry)
  - [ ] Verify build job fails on Docker build errors

- [ ] Task 1.5.5: Implement Deploy Job (AC: #5)
  - [ ] Add SSH action using `appleboy/ssh-action@master`
  - [ ] Configure SSH connection with secrets: AWS_EC2_HOST, AWS_SSH_KEY
  - [ ] Add deployment script: git pull, docker-compose rebuild, restart services
  - [ ] Add error handling: exit on any command failure
  - [ ] Verify deploy job only runs after successful build

- [ ] Task 1.5.6: Implement Smoke Test Job (AC: #6)
  - [ ] Add curl step to check `/api/health` endpoint
  - [ ] Parse JSON response and verify `status: "healthy"`
  - [ ] Implement retry logic: 3 attempts with 10-second delays
  - [ ] Verify smoke test fails if endpoint unreachable or unhealthy

- [ ] Task 1.5.7: Configure GitHub Secrets (AC: #7)
  - [ ] Navigate to repo Settings → Secrets and variables → Actions
  - [ ] Add AWS_EC2_HOST secret (EC2 public IP from Story 1.1b Terraform output)
  - [ ] Add AWS_SSH_KEY secret (private key content from Story 1.1b key pair)
  - [ ] Optional: Add DOCKER_HUB_USERNAME and DOCKER_HUB_TOKEN
  - [ ] Verify secrets by triggering test workflow run

- [ ] Task 1.5.8: Add Workflow Badge and Documentation (AC: #8)
  - [ ] Add workflow status badge to README.md
  - [ ] Document workflow structure in project documentation
  - [ ] Add troubleshooting guide for common deployment failures
  - [ ] Verify badge displays correctly on GitHub

- [ ] Task 1.5.9: End-to-End Workflow Validation
  - [ ] Make test commit and push to main branch
  - [ ] Verify all workflow jobs pass (lint, test, build, deploy, smoke-test)
  - [ ] Verify live site updated with latest changes
  - [ ] Check workflow execution time (<10 minutes total)

## Dev Notes

### Architecture Patterns and Constraints

**CI/CD Pipeline Philosophy:**

GamePulse uses GitHub Actions for continuous deployment following the "deploy early, iterate fast" principle from the PRD. The pipeline is designed to validate code quality (lint), ensure functionality (test), package application (build), deploy to production (deploy), and verify deployment success (smoke-test) in a single automated workflow.

**Key Design Principles:**

1. **Sequential Quality Gates**: Each job depends on the previous job's success, preventing broken code from reaching production
2. **Fast Feedback Loops**: Total pipeline execution <10 minutes to support rapid iteration during active development
3. **Fail-Fast Philosophy**: Lint runs first (fastest check) to catch syntax errors before expensive test/build jobs
4. **Production Parity**: Same Docker images used in CI are deployed to production (no "works on my machine" issues)

**GitHub Actions Workflow Structure:**

```yaml
Trigger: push to main
├── Job 1: Lint (parallel: backend + frontend) - <2 min
│   └── Blocks on: ruff, mypy, eslint errors
├── Job 2: Test (depends on: lint) - <3 min
│   └── Blocks on: pytest failures, test database connection issues
├── Job 3: Build (depends on: test) - <3 min
│   └── Blocks on: Docker build errors, missing dependencies
├── Job 4: Deploy (depends on: build) - <2 min
│   └── Blocks on: SSH failures, docker-compose errors
└── Job 5: Smoke Test (depends on: deploy) - <1 min
    └── Blocks on: health endpoint unreachable, unhealthy status
```

**Deployment Strategy:**

- **Blue-Green Deployment Approximation**: Docker Compose's `up -d --build` rebuilds containers with zero-downtime rolling updates
- **Rollback Strategy**: If deployment fails, manually SSH to EC2 and run `git checkout <previous-commit>` + `docker-compose up -d --build`
- **State Management**: Docker volumes persist database data across deployments (no data loss)

**Secrets Management:**

- AWS_EC2_HOST: Public IP from Terraform output (Story 1.1b)
- AWS_SSH_KEY: Private key generated in Story 1.1b (entire file content, including `-----BEGIN/END-----` markers)
- Never commit secrets to git - GitHub Secrets provides secure storage and injection at runtime

### Testing Standards Summary

**CI/CD Pipeline Testing:**

- **Workflow Syntax Validation**: Use GitHub's workflow validator or `actionlint` CLI tool
- **Lint Job Testing**: Intentionally introduce linting error, verify job fails (red X in Actions tab)
- **Test Job Testing**: Intentionally break a test, verify job fails and blocks deployment
- **Build Job Testing**: Introduce Docker syntax error, verify job fails
- **Deploy Job Testing**: Use invalid SSH key, verify job fails with clear error message
- **Smoke Test Testing**: Stop backend service on EC2, verify smoke test fails and reports unhealthy

**End-to-End Validation:**

1. Make trivial code change (update README or add comment)
2. Commit and push to main: `git commit -m "test: validate CI/CD pipeline" && git push`
3. Monitor GitHub Actions tab: All jobs should pass (green checkmarks)
4. Verify live site updated: Check commit SHA in deployment logs or API response header

**Troubleshooting Common Failures:**

- **SSH Connection Failed**: Verify AWS_SSH_KEY secret includes newlines correctly, check EC2 security group allows SSH from GitHub Actions IPs
- **Docker Build Timeout**: Increase timeout in workflow file, optimize Dockerfile (multi-stage builds, layer caching)
- **Smoke Test Fails**: Allow 30-60 seconds for services to stabilize after deployment, increase retry count or delay

**Test Coverage Impact:**

- Story 1.5 does not require new unit tests (infrastructure configuration)
- Integration tests in future stories will be executed by the test job
- Epic 9 will add comprehensive test suite to validate code quality gates

### Project Structure Notes

**Files Created:**
```
.github/workflows/deploy.yml              ✨ NEW (GitHub Actions CI/CD pipeline)
README.md                                  ✏️ MODIFIED (add workflow badge)
```

**Files Modified:**
```
(None - this story only adds CI/CD infrastructure)
```

**Alignment with Tech Spec:**

This story implements Tech Spec Epic 1 - AC-6: "GitHub Actions CI/CD"
- [Tech Spec lines 585-591](../tech-spec-epic-1.md#L585-591): AC-6 requirements
- [Tech Spec lines 373-392](../tech-spec-epic-1.md#L373-392): CI/CD deployment workflow
- [Architecture lines 52-53](../architecture.md#L52-53): GitHub Actions decision rationale

**Story Sequencing:**
- **Prerequisites**: Story 1.1b (AWS infrastructure provisioned, SSH key available), Story 1.4 (database schema exists for tests)
- **Successor**: Story 1.6 (deploy to AWS EC2 - uses CI/CD pipeline)
- **Enables**: All future stories can use automated deployment (push to main → live in <10 min)

### Learnings from Previous Story

**From Story 1-4-create-database-schema (Status: review)**

Story 1.4 successfully created the multi-sport database schema using SQLModel and Alembic, establishing the data foundation for GamePulse. All acceptance criteria met with comprehensive testing via PostgreSQL queries.

**Key Learnings Applicable to Story 1.5:**

1. **Docker Compose Workflow Established**: Story 1.4 demonstrated reliable `docker-compose exec` commands - Story 1.5's test job will use same pattern for database connectivity

2. **Migration Strategy Confirmed**: Alembic `upgrade head` executes cleanly in Docker environment - CI/CD test job should run migrations before pytest to ensure test database schema is current

3. **Test Database Setup Required**: Story 1.5's test job needs dedicated test database (separate from dev database) - configure via environment variable override in GitHub Actions

4. **SQLModel Import Patterns**: Story 1.4 restructured models into `backend/app/models/` package - ensure mypy type checking in lint job validates new import structure

5. **Idempotent Operations**: Story 1.4's seed script demonstrated SELECT-before-INSERT pattern - CI/CD deployment should be idempotent (safe to run multiple times)

**Files to Validate in CI/CD:**
- `backend/app/models/*.py` - Ensure mypy type checking passes for new models package
- `backend/app/alembic/versions/*.py` - Migrations apply cleanly in test database
- `backend/app/data/seed_data.py` - Seed script executes successfully (for test data setup)

**No Conflicts Detected:**
- GitHub Actions workflow won't modify existing code structure
- CI/CD pipeline enhances existing Docker Compose setup
- Test database isolated from development database

[Source: stories/1-4-create-database-schema.md#Completion-Notes]

### References

All technical details sourced from approved project documentation:

- [Source: docs/tech-spec-epic-1.md - AC-6: GitHub Actions CI/CD (lines 585-591)]
- [Source: docs/tech-spec-epic-1.md - CI/CD Deployment Workflow (lines 373-392)]
- [Source: docs/architecture.md - GitHub Actions Decision (lines 52-53)]
- [Source: docs/architecture.md - DevOps Stack (lines 251-256)]
- [Source: docs/PRD.md - Success Criteria: Working Demo Within 2-3 Weeks (lines 89-93)]
- [Source: docs/PRD.md - NFR-5.3: Deployment Automation (referenced in Tech Spec)]

## Dev Agent Record

### Context Reference

- [docs/stories/1-5-setup-github-actions.context.xml](1-5-setup-github-actions.context.xml)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-10 | Bob (SM) | Created story following BMM template with full context from Tech Spec Epic 1 AC-6, architecture CI/CD patterns, and Story 1.4 learnings. Renamed from story-1.5-setup-github-actions.md to 1-5-setup-github-actions.md (new naming convention). |
