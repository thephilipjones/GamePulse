# Epic 2 Retrospective: Dimensional Foundation + Game Data Ingestion

**Date**: 2025-11-13
**Facilitator**: Bob (Scrum Master)
**Participants**: Philip (Project Lead), Alice (Product Owner), Charlie (Senior Dev), Dana (QA Engineer), Elena (Junior Dev), Winston (Architect)
**Epic**: Epic 2 - Dimensional Foundation + Game Data Ingestion
**Stories Completed**: 8/8 (100%)

---

## Epic Overview

Epic 2 established the dimensional data warehouse foundation for GamePulse, implementing Kimball-style dimensional modeling with surrogate keys, SCD Type 2 readiness, and Dagster orchestration for NCAA game data ingestion. The epic successfully delivered a production-ready data pipeline with comprehensive retry logic and automatic team discovery, all operating under severe infrastructure constraints (t2.micro with 1GB RAM).

### Key Deliverables
- ✅ Dimensional data warehouse with surrogate keys (Stories 2-1, 2-3a)
- ✅ NCAA API client with retry logic (Story 2-2)
- ✅ Fact and dimension tables (dim_team, dim_date, fact_game) (Stories 2-3, 2-3a, 2-3c)
- ✅ Automatic team discovery from NCAA API (Story 2-3b)
- ✅ Dagster self-hosted orchestration (Story 2-4)
- ✅ Two-layer retry architecture validated (Story 2-5)
- ✅ 15-minute polling schedule operational
- ✅ Production deployment at dagster.gamepulse.top

---

## What Went Well ✅

### 1. Dimensional Modeling Excellence

The dimensional model refactor (Stories 2-3a, 2-3b, 2-3c) delivered portfolio-quality data warehouse patterns:

- **Kimball-style star schema** with surrogate keys (team_key, game_key, date_key)
- **SCD Type 2 readiness** with is_current, valid_from, valid_to fields
- **Date dimension** with NCAA-specific attributes (tournament_round, is_march_madness)
- **Flattened team groups** embedded in dim_team (no over-normalized JOIN overhead)

**Impact**: Demonstrates professional data engineering expertise expected in data solutions architect and analytics engineering roles.

### 2. Automatic Team Discovery Innovation

Story 2-3b implemented intelligent team metadata sync:
- Extracts teams organically from NCAA API game responses
- Auto-populates dim_team with espn_team_id and basic metadata
- Discovered and seeded 25 teams during testing without manual curation
- Preserves manually curated fields (colors, aliases) while syncing API data

**Impact**: Eliminates maintenance burden of tracking 300+ NCAA teams manually.

### 3. Production-Ready Dagster Orchestration

Story 2-4 deployed self-hosted Dagster with clean architecture:
- **Zero FastAPI coupling** - daemon runs independently
- **Asset-oriented paradigm** for data lineage visualization
- **15-minute polling schedule** operational in production
- **Observable at dagster.gamepulse.top** with full run history
- **Separate database** for Dagster metadata (prevents Alembic conflicts)

**Impact**: Modern orchestration with visual data lineage graphs valuable for portfolio demonstrations.

### 4. Honest Testing and Documentation

Story 2-5 validated retry logic and documented **actual behavior, not assumptions**:

**Discoveries:**
- Timeouts do NOT retry (returns empty list via generic Exception handler)
- 4xx errors DO retry (tenacity retries all HTTPStatusError types)
- Backoff timing: ~4s total (2s + 2s), not 6s as initially expected
- Network failures: DNS resolution prevents execution, run stuck in "Queued"

**Impact**: Tests serve as executable documentation of real retry behavior, preventing future confusion.

### 5. Strategic Mid-Epic Pivot

Philip made the call to prioritize dimensional modeling mid-epic:
- Story 2-3 created basic game model
- Story 2-3a immediately refactored to dimensional (before production data)
- Stories 2-3b and 2-3c extended dimensional foundation
- Refactoring early avoided painful live data migration later

**Impact**: Strategic flexibility delivered higher-value foundational architecture.

### 6. Infrastructure Optimization Under Constraints

Team adapted to t2.micro limitations (1GB RAM, 1 vCPU):
- Fixed 28% resting CPU by using production compose files (removed `--reload` flag)
- 4GB swap file prevents OOM crashes
- Optimized healthcheck intervals (10s → 30s)
- Separate Dagster database reduces schema conflicts

**Impact**: System operational on free-tier hosting with room for Epic 3 expansion.

---

## What Didn't Go Well 🔄

### 1. Tech Spec Out of Sync with Dimensional Model

**Issue**: After Story 2-3a renamed tables to dim_team/fact_game, tech spec query examples still reference old names (teams/games).

**Evidence**:
- Epic 2 tech spec lines 314-410 show normalized schema queries
- Story 2-4 instructions reference old table names
- Elena (Junior Dev) noted confusion when reading Story 2-4

**Impact**: Developers reading tech spec see outdated patterns, causing confusion and potential errors in Epic 3.

### 2. greenlet Dependency Blocks Async Database Tests

**Issue**: Story 2-5 couldn't write async database tests due to greenlet dependency causing event loop conflicts.

**Workaround**: Followed Story 2-4 pattern (manual Dagster UI validation) instead of unit tests.

**Impact**: Less comprehensive automated test coverage for Dagster assets. Pattern feels incomplete compared to full unit test suite.

### 3. Code Review Findings Inconsistently Documented

**Issue**: Only Story 2-3b documented code review findings explicitly (4 issues: migration constraints, type safety, 12/13 test failures).

**Reality**: Code reviews happened on all 8 stories, but findings weren't consistently captured in story files.

**Impact**: Lessons learned from reviews not visible in documentation for future reference.

### 4. Infrastructure at Capacity Limits

**Issue**: t2.micro (1GB RAM, 1 vCPU) operating near limits with current services (FastAPI, PostgreSQL, Dagster daemon, Dagster webserver).

**Concerns**:
- Already at 5-10% CPU resting (after optimizations)
- Epic 3 adds API endpoints + React frontend to same instance
- Elena expressed worry about resource exhaustion

**Risk**: May need to upgrade to t2.small (~$9/month) during Epic 3 if performance degrades.

---

## Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Stories Completed | 8/8 (100%) | All acceptance criteria met |
| Story Breakdown | 2-1, 2-2, 2-3, 2-3a, 2-3b, 2-3c, 2-4, 2-5 | 3 dimensional model stories added mid-epic |
| Technical Debt | Minimal | greenlet avoidance pattern, tech spec sync gap |
| Test Coverage | 86% backend | 73 tests passing, 7/7 retry tests passing |
| Code Review Findings | 4 issues (Story 2-3b) | All resolved; other reviews not documented |
| Production Deployment | ✅ Live | dagster.gamepulse.top operational |
| CPU Utilization | 5-10% resting | Down from 28% after production mode fix |
| Dimensional Tables | 3 tables | dim_team (25 teams), dim_date (1,095 dates), fact_game |

---

## Epic 1 Action Items Follow-Through

### AI-1.1: Real-Time CLAUDE.md Updates
**Status**: ✅ **Improved**

**Evidence**:
- Story 2-1 updated dimensional data seeding instructions
- Story 2-5 added comprehensive retry architecture documentation (lines 680-766)
- Charlie (Senior Dev): "Having current docs made implementation faster"

**Verdict**: Keep doing this in Epic 3.

---

### AI-1.2: Cross-Story Documentation Sync
**Status**: ⚠️ **Partial**

**Evidence**:
- Story 2-3a renamed tables (teams → dim_team, games → fact_game)
- Tech spec query examples NOT updated to reflect new names
- Elena noted confusion when reading Story 2-4 instructions

**Verdict**: Need explicit step in DoD to update cross-references when pivoting architecture.

---

### AI-1.3: Definition of Done - Documentation Sync Check
**Status**: ✅ **Improved**

**Evidence**:
- All stories include file lists, completion notes, architectural alignment
- Story 2-3b had comprehensive code review tracking
- Story 2-5 documented actual vs expected behavior honestly

**Verdict**: Execution improved from Epic 1.

---

### AI-1.4: Lightweight Architecture Decision Records (ADRs)
**Status**: ❌ **Not Implemented**

**Evidence**:
- No `docs/adrs/` directory created
- Dagster adoption and dimensional model pivot documented in story notes, not ADRs
- Winston (Architect) acknowledged gap

**Verdict**: Rationale captured in stories, but formal ADR structure skipped. Re-evaluate priority for Epic 3.

---

## Action Items for Epic 3 📋

### AP-2.1: Update Tech Spec Dimensional Query Examples
**Owner**: Dev Agent
**Priority**: High
**Deadline**: Before Story 3-1 starts

**Description**: Update tech-spec-epic-2.md query examples (lines 314-410) to use dim_team/fact_game with surrogate keys instead of old normalized schema (teams/games).

**Acceptance Criteria**:
- All query examples use `dim_team`, `fact_game`, `dim_date` table names
- JOINs use surrogate keys (team_key, game_key, date_key)
- SELECT statements reference current column names (home_team_key vs home_team_id)
- Examples tested for syntax correctness

**Estimated Effort**: 1 hour

**Rationale**: Prevents confusion when Story 3-1 (games endpoint) developer reads tech spec for query patterns.

---

### AP-2.2: Design Health Check Pattern for Dagster Status
**Owner**: Architect + Dev Agent
**Priority**: Medium
**Deadline**: During Story 3-2 implementation

**Description**: Research and design pattern for health endpoint to query Dagster asset materialization status (last successful run, staleness).

**Options to Evaluate**:
1. Dagster GraphQL API query
2. Dagster Python client (dagster package)
3. Direct query to Dagster PostgreSQL metadata schema

**Acceptance Criteria**:
- Design documented in Story 3-2 technical notes
- Approach selected with tradeoffs explained
- Example code snippet provided

**Estimated Effort**: 2 hours (research + design)

**Rationale**: Story 3-2 (health endpoint) needs to report last game update time from Dagster.

---

### AP-2.3: Continue Real-Time Documentation Updates
**Owner**: Dev Agent
**Priority**: Medium
**Ongoing**: Every story in Epic 3

**Description**: Maintain Epic 1 action item AI-1.1 momentum. Update CLAUDE.md, architecture.md, tech specs immediately when discovering new patterns during story implementation.

**Acceptance Criteria**:
- Same as AI-1.1 from Epic 1
- No more than 1 business day lag between code change and doc update
- Changes documented in commit messages

**Rationale**: This is working well in Epic 2. Keep the pattern.

---

### AP-2.4: Monitor t2.micro Performance and Upgrade if Needed
**Owner**: Philip (Project Lead)
**Priority**: High
**Decision**: Risk acceptance - proceed with Epic 3, upgrade if needed

**Context**: t2.micro currently at 5-10% CPU resting with Dagster + FastAPI + PostgreSQL. Epic 3 adds API endpoints + React frontend.

**Upgrade Path**:
- **Trigger symptoms**: Slow API response (>500ms), container restarts, sustained >80% CPU
- **Upgrade target**: t2.small (2GB RAM, 1 vCPU burstable)
- **Cost impact**: ~$9/month ($0.023/hour vs $0.0116/hour)

**Action Items**:
- Monitor CloudWatch CPU metrics during Epic 3 Story 3-1 (first API endpoint)
- Monitor Docker stats (`docker stats`) during local testing with frontend
- Upgrade immediately if performance degrades to maintain demo quality

**Rationale**: Philip wants to stay on free hosting until justified. Epic 3 will reveal if upgrade is necessary.

---

## Patterns and Learnings

### 1. Strategic Pivots Mid-Epic Can Be The Right Call

**Pattern**: Philip prioritized dimensional modeling mid-epic when its importance became clear, even though it added unplanned scope (Stories 2-3a, 2-3b, 2-3c).

**Lesson**: Don't rigidly stick to epic plan if new information reveals a better approach. Refactoring before production data is cheaper than migrating live data later.

**Application**: Epic 3 should remain flexible if API design reveals better patterns during Story 3-1/3-2.

---

### 2. Document Reality, Not Fantasy

**Pattern**: Story 2-5 discovered actual retry behavior didn't match expectations (timeouts don't retry, 4xx errors do retry). Team documented reality honestly in tests.

**Lesson**: Executable tests that document actual library behavior prevent future confusion. Better to know the truth than believe incorrect assumptions.

**Application**: Epic 3 API tests should document actual FastAPI/SQLModel behavior, not idealized behavior.

---

### 3. Async Database Testing Requires greenlet Avoidance

**Pattern**: Story 2-5 and 2-4 avoided async database tests due to greenlet dependency causing event loop issues in CI/CD.

**Workaround**: Manual Dagster UI validation for asset testing, synchronous database tests for SQLModel.

**Lesson**: greenlet adds complexity in CI/CD. Avoid async database tests unless absolutely necessary. Prefer manual validation or synchronous test patterns.

**Application**: Epic 3 Story 3-1 (games endpoint) should use synchronous database tests, not async.

---

### 4. Infrastructure Constraints Drive Creative Solutions

**Pattern**: t2.micro limitations (1GB RAM, 1 vCPU) forced optimizations:
- Production compose files to remove `--reload` flag (28% → 5-10% CPU)
- 4GB swap file for memory headroom
- Separate Dagster database to prevent schema conflicts
- Optimized healthcheck intervals (10s → 30s)

**Lesson**: Constraints breed innovation. Working within t2.micro limits demonstrates engineering resourcefulness.

**Application**: Epic 3 frontend should be optimized for minimal memory/CPU footprint. Consider static React builds served by Traefik instead of dev server.

---

## Next Epic Preview: Epic 3 Dependencies

### What Epic 3 Needs from Epic 2

**Data Availability**:
- ✅ fact_game table populated with game data (Dagster NCAA games asset running)
- ✅ dim_team table with 25+ teams (seeded + auto-discovered)
- ✅ dim_date table with tournament metadata (Sweet 16, Elite 8 flags)

**Dimensional Query Patterns**:
- ⚠️ Tech spec needs updated query examples (AP-2.1 action item)
- ✅ Surrogate key relationships established (team_key, game_key, date_key)

**Health Monitoring**:
- ⚠️ Dagster status query pattern needs design (AP-2.2 action item)
- ✅ Dagster UI accessible at dagster.gamepulse.top for manual verification

**Infrastructure Readiness**:
- ✅ t2.micro operational with 5-10% CPU resting
- ⚠️ May need upgrade to t2.small during Epic 3 (AP-2.4 monitoring)

### Epic 3 Blockers Assessment

**No Critical Blockers**: Epic 3 can start immediately.

**Preparation Tasks** (complete before Story 3-1):
1. Update tech spec dimensional query examples (AP-2.1) - 1 hour
2. Monitor t2.micro performance baseline (AP-2.4) - ongoing

**Parallel Work** (can happen during early Epic 3 stories):
- Design health check Dagster query pattern (AP-2.2) - needed by Story 3-2

---

## Team Feedback

### Philip (Project Lead)
> "Lots of craziness dealing with infrastructure constraints, the t2.micro prod server is just so tiny that we had to do a LOT of optimization and adjustments like adding swap file and minimizing CPU from each container, and it still may not be enough. Still feels like we're mired in the foundation but I'm excited to start building endpoints and seeing the data start flowing."

**Themes**:
- Infrastructure optimization consuming significant effort
- Impatience to move to user-facing features (justified - 2 foundation epics complete)
- Pragmatic risk acceptance (proceed with Epic 3, upgrade if needed)

### Charlie (Senior Dev)
> "That t2.micro constraint is real... we're operating at the edge of what t2.micro can handle."

**Concern**: Infrastructure at capacity limits, Epic 3 will stress test it further.

### Alice (Product Owner)
> "We spent three stories just on the dimensional model refactor - 2-3a, 2-3b, 2-3c - and while it's great foundational work, I know stakeholders are asking 'where's the dashboard?'"

**Tension**: Portfolio-quality architecture vs. demo velocity. Philip's call to prioritize dimensional modeling was correct, but stakeholder pressure acknowledged.

### Elena (Junior Dev)
> "I learned a ton from those stories - surrogate keys, SCD Type 2, date dimensions. That's resume material."

**Positive**: Junior developers gaining data engineering expertise through hands-on implementation.

---

## Retrospective Closure

### Commitments Made Today

**Action Items**: 4
- AP-2.1: Update tech spec dimensional query examples (High priority, pre-Epic 3)
- AP-2.2: Design health check Dagster pattern (Medium priority, during Story 3-2)
- AP-2.3: Continue real-time documentation (Medium priority, ongoing)
- AP-2.4: Monitor t2.micro performance (High priority, ongoing)

**Preparation Tasks**: 2 critical
- Tech spec query examples update (1 hour)
- Health check pattern design (2 hours)

**Total Estimated Preparation Effort**: ~3 hours before Epic 3 Story 3-1 starts

### Key Takeaways

1. **Strategic pivots mid-epic can deliver higher value** - Dimensional model refactor was the right call
2. **Infrastructure constraints drive creative optimization** - t2.micro forces efficiency
3. **Document reality, not fantasy** - Honest testing of retry behavior pays dividends
4. **Real-time documentation is working** - Epic 1 action item AI-1.1 momentum maintained

### Next Steps

1. ✅ **Epic 2 retrospective complete** - Document saved to docs/retrospectives/
2. 🔄 **Execute preparation tasks** - Tech spec update (AP-2.1) before Story 3-1
3. 📊 **Monitor t2.micro baseline** - Establish CPU/memory metrics before Epic 3 load
4. 🚀 **Begin Epic 3 planning** - First working demo with API + dashboard MVP

---

**Team Performance**: Epic 2 delivered 8/8 stories with 100% completion under severe infrastructure constraints. The dimensional data warehouse foundation demonstrates professional data engineering patterns. Zero production incidents. Test coverage at 86%. The team is well-positioned for Epic 3 success.

**Retrospective Status**: ✅ **Completed**

---

*Generated: 2025-11-13*
*Facilitator: Bob (Scrum Master)*
*Next Retrospective: Epic 3 (after 5 stories complete)*
