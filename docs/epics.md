# gamepulse - Epic Breakdown

**Author:** Philip
**Date:** 2025-11-07
**Project Level:** Level 2-3 (Medium Complexity - Data Pipeline + Web App)
**Target Scale:** Portfolio Demo (5-10 concurrent games, 10-50 users)

---

## Overview

This document provides the complete epic breakdown for GamePulse, decomposing the requirements from the [PRD](./PRD.md) into implementable epics and stories.

GamePulse is a real-time sports analytics platform demonstrating modern data engineering patterns: multi-source integration (batch + streaming), time-series analysis, and production-ready cloud deployment.

**Implementation Strategy:** Deploy early, iterate fast. Get a working demo live by end of Week 1, then add intelligence and polish incrementally.

**Stories:** Individual story files are located in [docs/stories/](./stories/)

---

## Phase 1: Foundation + Basic Demo (Week 1 - Working URL ASAP)

### Epic 1: Project Foundation & Infrastructure

**Goal:** Establish production-ready foundation using FastAPI full-stack template with deployment to AWS EC2.

**Value:** Provides the infrastructure foundation for all subsequent development. Live public URL ready for iterative deployment.

**Technical Foundation:**
- FastAPI full-stack template with Docker Compose orchestration
- PostgreSQL 16 + TimescaleDB extension for time-series data
- GitHub Actions CI/CD for automated deployment
- AWS EC2 t2.micro (free tier) with Traefik reverse proxy
- SQLModel ORM with Alembic migrations

**Milestone:** Live public URL infrastructure ready

**Stories:**
1. [Story 1.1: Initialize FastAPI Full-Stack Template](./stories/story-1.1-initialize-fastapi-template.md) - Includes .env configuration
2. [Story 1.2: Configure PostgreSQL with TimescaleDB Extension](./stories/story-1.2-configure-timescaledb.md)
3. [Story 1.3: Create Initial Database Schema](./stories/story-1.3-create-database-schema.md) - Includes TimescaleDB hypertables
4. [Story 1.4: Set Up GitHub Actions CI/CD Pipeline](./stories/story-1.4-setup-github-actions.md)
5. [Story 1.5: Deploy to AWS EC2 with Docker Compose](./stories/story-1.5-deploy-to-aws-ec2.md)
6. [Story 1.6: Remove Authentication Boilerplate](./stories/story-1.6-remove-authentication.md)

---

### Epic 2: Game Data Ingestion (Batch)

**Goal:** Ingest NCAA Men's Basketball game schedules, live scores, and final results via batch polling every 15 minutes.

**Value:** Provides the foundational game data that all other features depend on. Demonstrates batch processing paradigm.

**Technical Stack:**
- NCAA API client using henrygd/ncaa-api (free, self-hostable, 5 req/sec limit)
- httpx for async HTTP requests
- APScheduler for scheduled polling (15-minute intervals)
- SQLModel for database operations
- Alembic migrations for schema management

**Milestone:** Database has game data flowing

**Stories:**
1. [Story 2.1: Create Team and Conference Dimensional Data](./stories/story-2.1-create-dimensional-data.md)
2. [Story 2.2: Build NCAA API Client with httpx](./stories/story-2.2-build-ncaa-client.md)
3. [Story 2.3: Create Game SQLModel and Database Migration](./stories/story-2.3-create-game-model.md)
4. [Story 2.4: Implement Scheduled Polling Worker with APScheduler](./stories/story-2.4-implement-polling-worker.md) - Includes lifecycle integration
5. [Story 2.5: Add Retry Logic and Error Handling](./stories/story-2.5-add-retry-logic.md)

---

### Epic 3: Basic API + Dashboard MVP

**Goal:** Create a minimal working demo with live NCAA games displayed on a web dashboard - achievable by end of Week 1.

**Value:** 🎯 **WORKING DEMO** - Live public URL showing real NCAA games that can be shared in interviews. Proves the full stack works end-to-end before adding complexity.

**Simplifications:**
- No excitement scores yet (just show games)
- No Reddit posts or sentiment analysis
- No sparkline charts or fancy visualizations
- Minimal styling (basic Chakra UI components)
- Goal: Functional over pretty - can polish in Epic 8

**Technical Stack:**
- FastAPI endpoints with Pydantic schemas
- React 18 + TypeScript + Chakra UI
- React Query for data fetching and auto-refresh
- Simple responsive layout

**Milestone:** 🎯 WORKING DEMO BY END OF WEEK 1 - Live URL showing NCAA games

**Stories:**
1. [Story 3.1: Create Basic /api/games/today Endpoint](./stories/story-3.1-create-games-endpoint.md) - Includes CORS configuration
2. [Story 3.2: Add Health Check Endpoint](./stories/story-3.2-add-health-endpoint.md)
3. [Story 3.3: Initialize React Dashboard with Chakra UI](./stories/story-3.3-initialize-react-dashboard.md)
4. [Story 3.4: Build Simple Game List Component](./stories/story-3.4-build-game-list.md)
5. [Story 3.5: Add Auto-Refresh Polling with React Query](./stories/story-3.5-add-auto-refresh.md)

---

## Phase 2: Data Pipeline Complexity (Week 2 - Add Intelligence)

### Epic 4: Reddit Social Sentiment (Batch)

**Goal:** Track Reddit posts from r/CollegeBasketball and match to games.

**Value:** Social signals available for excitement scoring.

**Milestone:** Reddit posts matched to games with confidence scoring

**Stories:** _To be decomposed in Phase 2_

---

### Epic 5: Excitement Score Algorithm

**Goal:** Calculate multi-factor excitement scores.

**Value:** Games ranked by excitement (0-100 scale).

**Milestone:** Excitement scores calculated and stored as time-series

**Stories:** _To be decomposed in Phase 2_

---

### Epic 6: Streaming Betting Odds Integration

**Goal:** Demonstrate WebSocket streaming with Betfair.

**Value:** Portfolio shows dual paradigms (batch + streaming).

**Milestone:** Real-time betting odds streaming demonstrated

**Stories:** _To be decomposed in Phase 2_

---

### Epic 7: Time Mapping & Narrative Context

**Goal:** Convert timestamps to game-clock context.

**Value:** Moments show "10:00 1st Half" instead of UTC timestamps.

**Milestone:** Time mapping implemented with confidence scoring

**Stories:** _To be decomposed in Phase 2_

---

## Phase 3: Enhanced Dashboard (Week 2 - Full Features)

### Epic 8: Enhanced API + Dashboard

**Goal:** Transform basic dashboard into polished, feature-complete experience.

**Value:** Interview-ready polished dashboard with full feature set.

**Milestone:** Enhanced dashboard with excitement scores, sparklines, Reddit moments

**Stories:** _To be decomposed in Phase 3_

---

## Phase 4: Quality & Documentation (Week 3)

### Epic 9: Testing & Quality Assurance

**Goal:** >70% test coverage, professional code quality.

**Value:** Demonstrates engineering rigor.

**Milestone:** Professional test coverage and code quality

**Stories:** _To be decomposed in Phase 4_

---

### Epic 10: Documentation & Polish

**Goal:** Complete portfolio artifact.

**Value:** Interview-ready documentation.

**Milestone:** Complete portfolio artifact ready for interviews

**Stories:** _To be decomposed in Phase 4_

---

## Implementation Status

**Phase 1 (Week 1):** Stories defined ✅
- Epic 1: 6 stories
- Epic 2: 5 stories
- Epic 3: 5 stories
- **Total: 17 stories for Week 1 working demo**

**Phase 2-4:** To be decomposed as Phase 1 nears completion

---

_For detailed story specifications, see individual files in [docs/stories/](./stories/)_
