# Story 1.5: Set Up GitHub Actions CI/CD Pipeline

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** TODO
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want a GitHub Actions workflow that runs tests and deploys to AWS EC2,
So that every push to main branch automatically deploys the latest code.

---

## Acceptance Criteria

**Given** the FastAPI template includes a basic GitHub Actions workflow
**When** I customize the workflow for GamePulse deployment needs
**Then** the workflow includes these jobs:
1. **Lint**: Run ruff, mypy on backend; eslint on frontend
2. **Test**: Run pytest (backend) and vitest (frontend)
3. **Build**: Build Docker images for backend and frontend
4. **Deploy**: SSH to EC2, pull images, restart services

**And** the workflow triggers on push to `main` branch

**And** GitHub secrets are configured:
- AWS_EC2_HOST
- AWS_SSH_KEY
- DOCKER_HUB_USERNAME
- DOCKER_HUB_TOKEN

**And** a test commit triggers the workflow and all jobs pass (deploy will fail until Story 1.6 sets up EC2)

---

## Prerequisites

- Story 1.1 (template with GitHub Actions directory)
- Story 1.4 (database schema created for tests)

---

## Technical Notes

**Modify `.github/workflows/deploy.yml`** (template provides base workflow)

**Jobs to Add:**

1. **Lint Step:**
```yaml
- name: Lint backend
  run: |
    cd backend
    uv run ruff check .
    uv run mypy .
```

2. **Test Step:**
```yaml
- name: Test backend
  run: |
    cd backend
    uv run pytest
```

3. **Docker Build:**
```yaml
- name: Build backend image
  run: docker build -t gamepulse-backend ./backend
```

4. **Deploy Step:**
```yaml
- name: Deploy to EC2
  uses: appleboy/ssh-action@master
  with:
    host: ${{ secrets.AWS_EC2_HOST }}
    username: ubuntu
    key: ${{ secrets.AWS_SSH_KEY }}
    script: |
      cd /home/ubuntu/gamepulse
      git pull
      docker-compose -f docker-compose.prod.yml pull
      docker-compose -f docker-compose.prod.yml up -d
```

**GitHub Secrets Setup:**
- Navigate to repo Settings → Secrets and variables → Actions
- Add each secret with appropriate values
- AWS_SSH_KEY should be the private key content (entire file)

**Note:** Defer smoke test to Story 1.5 (after EC2 is provisioned)

---

## Definition of Done

- [ ] GitHub Actions workflow file modified
- [ ] Lint job added for backend and frontend
- [ ] Test job added for backend and frontend
- [ ] Docker build job added
- [ ] Deploy job template added
- [ ] GitHub secrets configured
- [ ] Test commit triggers workflow
- [ ] Lint and test jobs pass
- [ ] Build job succeeds
- [ ] Deploy job template present (will fail until EC2 exists)
- [ ] Workflow badge added to README
- [ ] Changes committed to git
