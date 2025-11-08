# Story 1.1: Initialize FastAPI Full-Stack Template

**Epic:** Epic 1 - Project Foundation & Infrastructure
**Status:** ready-for-dev
**Assignee:** TBD
**Sprint:** Week 1

---

## User Story

As a developer,
I want to initialize the project using the FastAPI full-stack template,
So that I have a production-ready foundation with Docker, CI/CD, and modern tooling pre-configured.

---

## Acceptance Criteria

**Source:** [Tech Spec Epic 1 - AC-1: Template Initialization](../tech-spec-epic-1.md)

1. **Template Initialized Successfully**
   - [ ] FastAPI full-stack template successfully initialized using copier command
   - [ ] Project structure created with backend/, frontend/, docker-compose.yml, and .github/workflows/
   - [ ] All configuration files present (.env templates, pyproject.toml, package.json)

2. **Environment Configuration Complete**
   - [ ] .env file created in backend/ from .env.example template
   - [ ] PROJECT_NAME set to "gamepulse"
   - [ ] DATABASE_URL configured for PostgreSQL connection
   - [ ] BACKEND_CORS_ORIGINS includes frontend URL (http://localhost:5173)

3. **Docker Services Operational**
   - [ ] Docker Compose starts all services without errors
   - [ ] Can access backend API at http://localhost:8000/docs
   - [ ] Can access frontend at http://localhost:5173

4. **Git Repository Initialized**
   - [ ] Git repository initialized with initial commit
   - [ ] .gitignore configured to exclude .env files

---

## Tasks / Subtasks

### Task 1.1.1: Install Prerequisites (AC: #1)
- [x] Install pipx if not already installed: `brew install pipx` (macOS) or `pip install --user pipx`
- [x] Verify pipx is in PATH: `pipx --version`

### Task 1.1.2: Initialize FastAPI Template (AC: #1)
- [x] Verify template version is 2025 latest by checking GitHub repo
- [x] Run copier command: `pipx run copier copy https://github.com/fastapi/full-stack-fastapi-template gamepulse --trust`
- [x] Answer template prompts with GamePulse-specific values:
  - Project name: gamepulse
  - Project slug: gamepulse
  - Backend port: 8000
  - Frontend port: 5173
  - Database: PostgreSQL 16
- [x] Verify directory structure created: backend/, frontend/, docker-compose.yml, .github/workflows/
- [x] Verify configuration files present: .env.example, pyproject.toml, package.json

### Task 1.1.3: Configure Environment Variables (AC: #2)
- [x] Navigate to backend/ directory
- [x] Copy .env.example to .env: `cp .env.example .env`
- [x] Edit .env file and set:
  - PROJECT_NAME="gamepulse"
  - DATABASE_URL="postgresql://postgres:changethis@db:5432/app"
  - BACKEND_CORS_ORIGINS='["http://localhost:5173"]'
- [x] Document required vs optional variables in .env (add comments)
- [x] Verify CORS origins include frontend URL

### Task 1.1.4: Start Docker Services (AC: #3)
- [x] From project root, run: `docker-compose up -d`
- [x] Wait for all 4 services to start (backend, frontend, db, traefik)
- [x] Verify no errors in docker-compose logs: `docker-compose logs`
- [x] Check service status: `docker-compose ps` (all should show "Up")

### Task 1.1.5: Verify Services Accessible (AC: #3)
- [x] Access backend API docs: http://localhost:8000/docs (Swagger UI should load)
- [x] Access backend health endpoint: http://localhost:8000/api/health
- [x] Access frontend: http://localhost:5173 (React app should load)
- [x] Verify no CORS errors in browser console

### Task 1.1.6: Initialize Git Repository (AC: #4)
- [ ] Initialize git: `git init`
- [ ] Verify .gitignore includes .env files (should be present from template)
- [ ] Add all files: `git add .`
- [ ] Create initial commit: `git commit -m "Initial commit: FastAPI full-stack template"`

### Task 1.1.7: Testing (AC: #1, #2, #3)
- [ ] Run backend tests: `cd backend && poetry run pytest`
- [ ] Verify all template tests pass
- [ ] Test docker-compose restart: `docker-compose down && docker-compose up -d`
- [ ] Verify services restart without errors

---

## Dev Notes

### Architecture Patterns and Constraints

This story establishes the foundational architecture using the FastAPI full-stack template, which provides:

- **Docker Compose Orchestration**: All services containerized for consistent dev/prod environments
- **Async Python Framework**: FastAPI 0.121.0 with async/await support for high performance
- **Type-Safe Stack**: SQLModel ORM + Pydantic validation + TypeScript frontend
- **Modern Frontend**: React 18 + Vite 7.2.2 with hot module replacement
- **Reverse Proxy**: Traefik 3.5.4 for automatic HTTPS (production) and routing
- **CI/CD Ready**: GitHub Actions workflows pre-configured for automated deployment

**Key Constraints:**
- Template version must be latest 2025 release (verified via GitHub before cloning)
- PostgreSQL 16 required (TimescaleDB 2.23.0 extension will be added in Story 1.2)
- CORS must allow frontend URL for local development (http://localhost:5173)
- All services must run on single machine (Docker Compose orchestration)

### Testing Standards Summary

For this infrastructure story:
- **Integration Testing**: Verify docker-compose up succeeds and all services healthy
- **Smoke Testing**: Verify URLs accessible (frontend, backend /docs, backend /health)
- **No Unit Tests Required**: This story is infrastructure setup, not business logic
- **Manual Verification**: Template files, directory structure, .env configuration

### Project Structure Notes

The FastAPI template establishes this structure (from Architecture document):

```
gamepulse/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # API endpoints
│   │   ├── core/             # Config, DB connection
│   │   ├── models/           # SQLModel schemas
│   │   ├── schemas/          # Pydantic response models
│   │   └── main.py           # FastAPI app entry point
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend tests
│   └── pyproject.toml        # Poetry dependencies
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── client/           # API client (auto-generated)
│   │   └── main.tsx          # React entry point
│   ├── package.json          # npm dependencies
│   └── vite.config.ts        # Vite configuration
├── docker-compose.yml        # Service orchestration
└── .github/workflows/        # CI/CD pipelines
```

**Alignment Notes:**
- Template structure matches Architecture document expectations (lines 64-100)
- No conflicts detected - template provides clean starting point
- Authentication modules will be removed in Story 1.2 (not needed for public dashboard)

### References

All technical details sourced from approved project documentation:

- [Source: docs/tech-spec-epic-1.md - AC-1: Template Initialization (lines 548-554)]
- [Source: docs/tech-spec-epic-1.md - Services and Modules section (lines 56-68)]
- [Source: docs/tech-spec-epic-1.md - Dependencies table (lines 510-524)]
- [Source: docs/architecture.md - Project Initialization section (lines 12-38)]
- [Source: docs/architecture.md - Decision Summary table (lines 42-62)]
- [Source: docs/architecture.md - Project Structure (lines 64-100)]
- [Source: docs/epics.md - Epic 1, Story 1.1 (line 40)]

---

## Dev Agent Record

### Context Reference

- [Story Context XML](./1-1-initialize-fastapi-template.context.xml) - Generated 2025-11-07

### Agent Model Used

TBD (will be filled during implementation)

### Debug Log References

TBD

### Completion Notes

- [ ] TBD (Developer will add completion notes here)

### File List

TBD (Developer will list all files created/modified during implementation)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-11-07 | Philip | Initial story draft |
| 2025-11-07 | Bob (SM) | Auto-improved: Added proper structure, citations, and traceability |
