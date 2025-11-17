# GamePulse Future Enhancements

This document tracks potential enhancements that are out of scope for MVP but may be valuable in future iterations.

## Dimensional Data Enhancements

### 1. Team Colors Automation

**Context**: Currently, only 20 teams have manually curated colors in `teams.json`. Auto-discovered teams from Story 2-3b lack colors, resulting in a plain UI for those teams.

**Gap**: 330+ teams need colors for optimal UX (team color accents in game cards, score displays).

**Options**:

1. **Web Scraping from ESPN**
   - Scrape ESPN team pages for official team colors
   - Extract from CSS or team logo images
   - **Pros**: Authoritative source, comprehensive coverage
   - **Cons**: Brittle (HTML changes break scraper), legal concerns
   - **Effort**: 4-6 hours

2. **Third-Party API** (e.g., TeamColors API, TheSportsDB)
   - Use API like `teamcolors.jim-nielsen.com` or SportsDB
   - Map ESPN team IDs to external API IDs
   - **Pros**: Maintained by community, structured data
   - **Cons**: May lack NCAA coverage, requires API key
   - **Effort**: 3-4 hours

3. **Color Extraction from Logos**
   - Fetch team logos from ESPN or NCAA
   - Use Python library (ColorThief, Pillow) to extract dominant colors
   - **Pros**: Automated, no manual curation
   - **Cons**: May not match official branding, requires logo URLs
   - **Effort**: 5-7 hours

4. **Manual Curation** (Status Quo)
   - Continue updating `teams.json` as needed
   - Focus on top 50-100 teams that appear in March Madness
   - **Pros**: Accurate, controlled, simple
   - **Cons**: Labor-intensive for full coverage
   - **Effort**: Ongoing (10-15 minutes per team)

**Recommendation**: Option 2 (Third-Party API) or Option 4 (Manual Curation for top teams)

**Priority**: Low (colors are UI enhancement, not functional requirement)

**Estimated Effort**: 3-7 hours depending on approach

---

### 2. Team Aliases Generation/Fetching

**Context**: Reddit matching (Epic 4) requires team aliases for fuzzy matching. Current seed data has manually curated aliases like ["Duke", "Blue Devils", "Duke Blue Devils", "Blue Devil"] for accurate post detection.

**Gap**: Auto-discovered teams lack aliases, reducing Reddit matching accuracy.

**Options**:

1. **LLM Generation** (GPT-4, Claude)
   - Prompt: "Generate all common aliases and variations for NCAA team '{team_name}'"
   - Example: "Duke Blue Devils" → ["Duke", "Blue Devils", "Dukies", "Blue Devil", "Duke University"]
   - **Pros**: Fast, scales to all teams, creative variations
   - **Cons**: May generate incorrect aliases, requires API cost
   - **Effort**: 6-8 hours (prompt engineering + validation)

2. **Web Scraping** (Wikipedia, ESPN)
   - Scrape Wikipedia infobox for "Nickname" field
   - Parse ESPN team pages for official nicknames
   - **Pros**: Authoritative sources
   - **Cons**: Brittle, misses informal variations (e.g., "Dukies")
   - **Effort**: 8-10 hours

3. **Manual Curation** (Status Quo)
   - Observe Reddit patterns during Epic 4 implementation
   - Add aliases for teams that appear in high-engagement posts
   - **Pros**: Accurate, based on real usage patterns
   - **Cons**: Labor-intensive, reactive (misses posts initially)
   - **Effort**: Ongoing (5-10 minutes per team)

4. **Hybrid: LLM + Manual Validation**
   - LLM generates initial aliases
   - Human reviews and refines based on Reddit observations
   - **Pros**: Best of both worlds (speed + accuracy)
   - **Cons**: Still requires manual review time
   - **Effort**: 6-8 hours (LLM) + ongoing validation

**Recommendation**: Option 4 (LLM + Manual Validation) for top 100 teams

**Priority**: Medium (affects Reddit matching quality in Epic 4)

**Estimated Effort**: 6-10 hours for automated generation + validation

---

### 3. Conference/TeamGroup Automation

**Context**: NCAA API scoreboard endpoint does NOT provide conference data. Current approach: manually curate 6 major conferences in `conferences.json`. Auto-discovered teams get NULL `team_group_id`, which impacts rivalry detection (same conference = 1.2x engagement factor).

**Gap**: 330+ teams across 32 conferences need conference assignments for accurate rivalry detection.

**Options**:

1. **Find Alternative NCAA API Endpoint**
   - Research NCAA official API or other sports data APIs for conference rosters
   - Example: NCAA Stats API, SportsData.io
   - **Pros**: Structured data, authoritative
   - **Cons**: May require paid API, endpoint may not exist
   - **Effort**: 4-6 hours (research + integration)

2. **Web Scraping** (ESPN, Wikipedia)
   - Scrape ESPN conference pages for team rosters
   - Parse Wikipedia "NCAA Division I conferences" for team lists
   - **Pros**: Comprehensive coverage
   - **Cons**: Brittle, changes break scraper
   - **Effort**: 8-12 hours

3. **Inference from Schedule Patterns**
   - Analyze team matchups over time (teams that play each other frequently → same conference)
   - Use clustering algorithms on game history
   - **Pros**: Data-driven, no external dependencies
   - **Cons**: Requires historical data, accuracy varies
   - **Effort**: 12-16 hours (data analysis + algorithm)

4. **Manual Curation** (Status Quo)
   - Maintain 6 major conferences (ACC, Big Ten, Big 12, SEC, Pac-12, Big East)
   - Add others as needed based on game observations
   - **Pros**: Simple, accurate for top conferences
   - **Cons**: Incomplete coverage (misses mid-major rivalries)
   - **Effort**: Ongoing (15-20 minutes per conference)

**Recommendation**: Option 4 (Manual Curation) for MVP; Option 1 (API) if found during Epic 4

**Priority**: Low (rivalry detection has fallback for NULL conference; 6 major conferences cover most high-profile rivalries)

**Estimated Effort**: 8-12 hours depending on data source availability

**Note**: Could be Story 2-3c if API source is discovered, but not needed for MVP.

---

### 4. Historical Team Data Backfill

**Context**: Story 2-3b focuses on forward-looking team discovery (teams that play games going forward). Historical games and team metadata are not backfilled.

**Gap**: No historical team stats, rosters, or past performance data.

**Options**:

1. **Backfill from NCAA API** (if historical endpoint exists)
   - Fetch games from previous seasons
   - Sync teams from those games
   - **Effort**: 4-6 hours

2. **Third-Party Historical Data** (SportsDB, Kaggle datasets)
   - Import historical NCAA team data
   - Merge with current teams
   - **Effort**: 6-10 hours

**Recommendation**: Defer to Epic 5+ (out of scope for MVP)

**Priority**: Low (MVP focuses on current season forward)

---

### 5. Team Roster and Player Data

**Context**: Current team data is high-level (name, colors, conference). No player-level data (names, positions, stats).

**Gap**: Cannot display player-specific insights (e.g., "Top scorer: Player X").

**Options**:

1. **Fetch from NCAA API** (if available)
2. **Scrape from ESPN rosters**
3. **Defer to future epic**

**Recommendation**: Out of scope for MVP (Epic 6+ feature)

**Priority**: Low

---

### 6. Team Logos Fetching and Storage

**Context**: Team logos provide visual identity and enhance UX in game cards, dashboards, and team displays. Currently, no team logos are stored or displayed in GamePulse.

**Gap**: 350+ NCAA teams need logos for optimal UI/UX. Logos improve brand recognition, visual appeal, and user engagement.

**Image Sources Research**:

1. **ESPN CDN** (Most Comprehensive)
   - URL Pattern: `https://a.espncdn.com/i/teamlogos/ncaa/500/{team_id}.png`
   - Example: Duke (team_id=150) → `https://a.espncdn.com/i/teamlogos/ncaa/500/150.png`
   - Sizes available: 500px, 200px, 100px, 50px (replace `/500/` in URL)
   - **Pros**:
     - Direct correlation with ESPN team IDs (already have `espn_team_id` from Story 2-3b)
     - Reliable, high-quality images
     - Comprehensive coverage (350+ teams)
     - Multiple sizes available
     - CDN-backed (fast, reliable)
   - **Cons**:
     - No official API (URL pattern discovered, may change)
     - Possible rate limiting on bulk downloads
     - Legal/licensing considerations (fair use for sports stats app likely OK)
   - **Effort**: 3-4 hours (simple implementation)

2. **NCAA Official Site**
   - URL Pattern: Varies, no consistent pattern discovered
   - **Pros**: Official source, legally clear
   - **Cons**: Inconsistent URLs, harder to automate, may not cover all teams
   - **Effort**: 8-12 hours (scraping, URL discovery)

3. **TheSportsDB API** (Free)
   - API: `https://www.thesportsdb.com/api/v1/json/{api_key}/searchteams.php?t={team_name}`
   - Returns: `strTeamBadge` (team logo URL)
   - **Pros**: Structured API, free tier available, legal to use
   - **Cons**:
     - Requires team name matching (not ESPN ID)
     - NCAA coverage may be incomplete
     - External dependency (API availability)
     - Rate limits on free tier
   - **Effort**: 6-8 hours (team matching + integration)

4. **Wikipedia/Wikimedia Commons**
   - Scrape Wikipedia team pages for logo images
   - **Pros**: High-quality images, open license (often public domain or CC)
   - **Cons**: Inconsistent availability, scraping brittle, manual mapping required
   - **Effort**: 10-15 hours (scraping + mapping)

5. **Manual Upload** (Status Quo)
   - Download logos manually, upload to S3/CloudFront
   - **Pros**: Full control, guaranteed quality
   - **Cons**: Labor-intensive (350+ teams × ~5 minutes each = 29 hours)
   - **Effort**: 29+ hours

**Storage Options**:

1. **AWS S3 + CloudFront CDN** (Recommended)
   - Store logos in S3 bucket: `s3://gamepulse-assets/team-logos/{team_id}.png`
   - Serve via CloudFront: `https://cdn.gamepulse.top/team-logos/{team_id}.png`
   - **Pros**:
     - Scalable, reliable, fast global delivery
     - Low cost (S3: ~$0.023/GB/month, CloudFront: ~$0.085/GB transfer)
     - Infrastructure already on AWS
     - Can set cache headers for optimal performance
   - **Cons**: Additional AWS resources to manage
   - **Cost Estimate**: ~350 logos × 50KB avg = ~17.5MB → ~$0.40/month S3 + ~$1.50/month CloudFront (assuming 100GB/month traffic)
   - **Effort**: 4-6 hours (S3 setup, CloudFront config, Terraform)

2. **External CDN (ESPN Direct Link)**
   - Store only ESPN CDN URLs in database, hotlink directly
   - Example: Store `https://a.espncdn.com/i/teamlogos/ncaa/500/150.png` in `dim_team.logo_url`
   - **Pros**:
     - Zero storage cost
     - Zero bandwidth cost
     - No upload needed
     - ESPN's CDN performance (excellent)
   - **Cons**:
     - Dependency on ESPN (URL changes break logos)
     - Potential legal concerns (hotlinking without permission)
     - No control over image availability
     - Cannot customize or optimize images
   - **Effort**: 1-2 hours (just store URL pattern in database)

3. **PostgreSQL BYTEA** (Not Recommended)
   - Store logo images as binary data in `dim_team` table
   - **Pros**: No external dependencies, fully self-contained
   - **Cons**:
     - Database bloat (350 logos × 50KB = 17.5MB in DB)
     - Poor performance (every query fetches image data)
     - No CDN caching
     - Difficult to serve to frontend efficiently
   - **Effort**: 2-3 hours (schema change, serving logic)

4. **GitHub Repository** (Budget Option)
   - Store logos in `backend/app/static/logos/` directory
   - Serve via FastAPI static files or commit to git
   - **Pros**: Simple, no external service, version controlled
   - **Cons**:
     - Git bloat (binary files in repo)
     - No CDN (slower for users)
     - Increases Docker image size
     - Not scalable for large asset libraries
   - **Effort**: 1-2 hours (directory structure, serving)

**Recommended Implementation**:

**Option A: ESPN CDN Hotlinking (Quick Win - 1-2 hours)**
- Add `logo_url` VARCHAR field to `dim_team` table
- Generate URL pattern: `https://a.espncdn.com/i/teamlogos/ncaa/500/{espn_team_id}.png`
- Store URL during team sync (Story 2-3b integration)
- Frontend fetches directly from ESPN CDN
- **Trade-off**: Dependency on ESPN, but fast to implement and zero cost

**Option B: S3 + CloudFront (Production-Ready - 8-10 hours)**
- One-time bulk download from ESPN CDN (or TheSportsDB)
- Upload to S3 bucket with organized structure
- Configure CloudFront distribution
- Add Terraform for infrastructure as code
- Store CloudFront URL in `dim_team.logo_url`
- **Trade-off**: Higher effort, but full control and professional setup

**Hybrid Approach (Best of Both Worlds - 6-8 hours)**:
1. Start with ESPN CDN hotlinking (Story 2-3b can add this)
2. Background job downloads logos to S3 (Epic 5+)
3. Gradually migrate URLs from ESPN to CloudFront
4. Fallback to ESPN if S3 image missing (resilience)

**Schema Changes**:
```python
class DimTeam(SQLModel, table=True):
    # ... existing fields ...

    logo_url: str | None = None  # NEW: Logo image URL
    logo_source: str | None = None  # NEW: "espn_cdn" | "s3_cloudfront" | "manual"
```

**Implementation Tasks** (for future story):
1. Add `logo_url` and `logo_source` fields to `dim_team`
2. Update team sync service to generate ESPN CDN URLs
3. (Optional) Create background job to download and upload to S3
4. (Optional) Set up S3 bucket + CloudFront with Terraform
5. Update frontend to display team logos in game cards
6. Add fallback image for teams without logos

**Legal Considerations**:
- **Fair Use**: Using team logos for sports statistics display likely falls under fair use
- **ESPN Hotlinking**: No explicit prohibition found, but not officially sanctioned
- **TheSportsDB**: API terms allow free use with attribution
- **Best Practice**: Add attribution footer: "Team logos courtesy of ESPN/NCAA"
- **Risk**: Low for non-commercial use; monitor for cease-and-desist

**Recommendation**: Option A (ESPN CDN Hotlinking) for MVP, Option B (S3 + CloudFront) for production polish

**Priority**: Medium-Low (UI enhancement, improves UX but not critical functionality)

**Estimated Effort**:
- Quick win (ESPN hotlink): 1-2 hours
- Production (S3 + CloudFront): 8-10 hours
- Hybrid approach: 6-8 hours

---

## Testing & Infrastructure Enhancements

### 7. Fix DimTeam Timestamp Timezone Handling

**Context**: DimTeam model uses timezone-aware datetime defaults (`datetime.now(timezone.utc)`), but the database schema uses `TIMESTAMP WITHOUT TIME ZONE` columns. This mismatch causes test failures when tests create DimTeam instances directly in Python.

**Current Behavior**:
- Production code works fine (uses raw SQL INSERT that bypasses Python defaults)
- Tests that manually create DimTeam instances fail with timezone comparison errors
- FactGame model correctly uses `DateTime(timezone=True)` in sa_column definitions

**Gap**: Architectural inconsistency between DimTeam and FactGame timestamp handling.

**Root Cause**:
- Migration `d115685a3652` created columns with plain `sa.TIMESTAMP()` (naive)
- Model defaults create timezone-aware datetimes
- Python model defaults and database schema don't match

**Fix Required**:
1. Update DimTeam model to use `sa_column=Column(DateTime(timezone=True))` for:
   - `valid_from`
   - `valid_to`
   - `created_at`
   - `updated_at`
2. Create Alembic migration to convert `TIMESTAMP` → `TIMESTAMP WITH TIME ZONE`
3. Re-enable full test suite (currently using simplified subset)

**Impact**:
- **Low Production Risk**: Production code bypasses Python defaults entirely
- **Medium Maintenance Risk**: Developers may be confused by timezone mismatch
- **Low Urgency**: Current simplified tests validate core business logic

**Recommendation**:
- Fix during next infrastructure improvement sprint
- Align DimTeam with FactGame architecture patterns
- Migration is straightforward column type conversion

**Priority**: Low (technical debt, not blocking functionality)

**Estimated Effort**: 2-3 hours
- Update model definitions: 30 minutes
- Create and test migration: 1 hour
- Validate full test suite: 1 hour
- Deploy and verify: 30 minutes

**Related Story**: Story 2-4 (Dagster orchestration)

**Notes**:
- Story 2-4 uses simplified test suite (2 passing tests) to validate core logic
- Full test suite (6 tests) blocked by timezone issue
- Manual Dagster UI validation confirms asset works correctly

---

### 8. Docker Layer Caching to ECR Registry

**Context**: After Phase 1-3 pipeline optimizations (parallel builds, parallel tests, shallow clones), additional performance gains can be achieved through persistent Docker layer caching.

**Current State**:
- Using GitHub Actions cache (`cache-from: type=gha`)
- GHA cache has 10GB limit per repository
- Cache can be evicted, causing rebuild from scratch
- Cache is scoped to workflows/branches

**Gap**: No persistent cache layer beyond GitHub Actions lifetime (7-day retention).

**Proposed Enhancement**:
Store Docker build cache layers in ECR registry for more persistent caching.

**Implementation**:
```yaml
- name: Build and push backend image
  uses: docker/build-push-action@v5
  with:
    context: ./backend
    push: true
    tags: |
      ${{ secrets.ECR_BACKEND_URL }}:${{ github.sha }}
      ${{ secrets.ECR_BACKEND_URL }}:latest
    cache-from: |
      type=gha
      type=registry,ref=${{ secrets.ECR_BACKEND_URL }}:buildcache
    cache-to: |
      type=gha,mode=max
      type=registry,ref=${{ secrets.ECR_BACKEND_URL }}:buildcache,mode=max
```

**Benefits**:
- **Persistent cache**: Survives GitHub Actions cache evictions
- **Cross-branch caching**: Cache layers shared across all branches
- **Faster cold builds**: ~20-30 seconds faster when GHA cache misses
- **Redundancy**: Falls back to GHA cache if ECR unavailable

**Considerations**:
- **ECR storage costs**: ~$0.10/GB/month (estimate ~2-3GB per image = ~$0.20-$0.30/month)
- **Network costs**: Minimal (same AWS region as EC2)
- **Complexity**: Adds another cache source to manage
- **Cache invalidation**: Need lifecycle policy to clean old cache layers

**Estimated Effort**: 1-2 hours
- Update workflow cache configuration: 30 minutes
- Add ECR lifecycle policy for buildcache: 30 minutes
- Test and validate: 30-60 minutes

**Priority**: Low (incremental gain after Phases 1-3)

**Estimated Savings**: 20-30 seconds on builds when GHA cache is cold

**When to Implement**: After validating Phase 1-3 optimizations in production for 2-4 weeks

---

### 9. Path-Based Conditional Job Execution

**Context**: Currently, every push to `main` rebuilds and deploys everything, even if changes only affect documentation or single modules.

**Current Behavior**:
- Doc-only changes trigger full pipeline (6-7 jobs, ~3 minutes)
- Backend-only changes rebuild frontend unnecessarily
- Frontend-only changes rebuild backend unnecessarily

**Gap**: No intelligent job skipping based on changed files.

**Proposed Enhancement**:
Use path filters to conditionally execute jobs based on which files changed.

**Implementation**:
```yaml
jobs:
  # Detect what changed
  changes:
    runs-on: ubuntu-latest
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
      infra: ${{ steps.filter.outputs.infra }}
      docs: ${{ steps.filter.outputs.docs }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2  # Need previous commit for diff
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - '.github/workflows/deploy.yml'
            frontend:
              - 'frontend/**'
              - '.github/workflows/deploy.yml'
            infra:
              - 'terraform/**'
              - 'docker-compose*.yml'
            docs:
              - '**.md'
              - 'docs/**'

  lint-backend:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    # ... rest of job

  lint-frontend:
    needs: changes
    if: needs.changes.outputs.frontend == 'true'
    # ... rest of job

  build-backend:
    needs: [changes, test-backend, validate-docker]
    if: needs.changes.outputs.backend == 'true'
    # ... rest of job

  build-frontend:
    needs: [changes, generate-client]
    if: needs.changes.outputs.frontend == 'true'
    # ... rest of job

  deploy:
    needs: [changes, build-backend, build-frontend]
    # Always deploy if either backend or frontend was built
    if: |
      always() &&
      (needs.changes.outputs.backend == 'true' || needs.changes.outputs.frontend == 'true')
    # ... rest of job
```

**Benefits**:
- **Doc-only changes**: Skip all builds/tests (~3 minutes saved)
- **Backend-only changes**: Skip frontend lint/test/build (~40-50s saved)
- **Frontend-only changes**: Skip backend lint/test/build (~60-70s saved)
- **Faster iteration**: Developers get faster feedback on focused changes

**Considerations**:
- **Complexity**: More complex workflow logic, harder to debug
- **Edge cases**: Must handle "always deploy" logic correctly
- **Testing**: Requires thorough testing of all path combinations
- **Maintenance**: Path filters must be updated when repo structure changes
- **Risk**: Incorrect path filters could skip critical jobs

**Examples of Time Savings**:

| Change Type | Current | Optimized | Savings |
|-------------|---------|-----------|---------|
| Docs only (CLAUDE.md) | 3 min | 10s (change detection only) | 2m 50s |
| Backend only (app/*.py) | 3 min | 2m 20s (skip frontend) | 40s |
| Frontend only (src/*.tsx) | 3 min | 2m (skip backend) | 1m |
| Both modified | 3 min | 3 min | 0s |

**Estimated Effort**: 2 hours
- Implement path filter logic: 1 hour
- Test all path combinations: 45 minutes
- Document path filter rules: 15 minutes

**Priority**: Low (optimization for high-frequency development, less valuable for low-frequency deployments)

**Estimated Savings**: Variable (0-170s depending on change type)

**When to Implement**:
- After validating Phase 1-3 in production
- When team is making frequent doc/single-module changes
- Consider if deployment frequency increases significantly

**Risks**:
- Medium risk: Incorrect filters could skip critical jobs
- Requires extensive testing matrix
- May need "force full rebuild" mechanism for edge cases

---

### 10. Async Integration Test Infrastructure for Dagster Assets

**Context**: Dagster asset tests currently use configuration validation + manual UI validation pattern (established in Story 2-5). Integration tests requiring async database operations are skipped due to missing async fixtures.

**Current State**:
- ✅ **Unit tests**: 100% coverage of business logic (e.g., 8 passing tests in `test_sentiment_analyzer.py`)
- ✅ **Configuration tests**: Retry policies, asset metadata, constants validated
- ✅ **Manual validation**: Dagster UI materialization confirms end-to-end functionality
- ⚠️ **Integration tests**: 4 tests in `test_calculate_sentiment.py` skipped via `@pytest.mark.skip` decorator

**Gap**: Missing async fixtures prevent automated end-to-end testing of Dagster assets with database operations.

**Missing Fixtures**:
1. `async_session` (AsyncSession) - Async database session with transaction rollback for test isolation
2. `test_context` (AssetExecutionContext) - Mock Dagster execution context using `build_asset_context()`

**Current Test Coverage for Sentiment Feature (Story 4-5)**:
- ✅ VADER sentiment analysis logic: 8/8 passing unit tests
- ✅ Asset configuration: Retry policy, auto-materialize, metadata validated
- ✅ Production deployment: Asset materializes successfully in Dagster UI
- ⏸️ Integration tests: 4 skipped tests
  - `test_process_matched_posts` - End-to-end FK validation
  - `test_skip_posts_without_game_match` - NULL game_key handling
  - `test_no_unprocessed_posts` - Empty database graceful handling
  - `test_idempotency` - Running twice doesn't duplicate records

**Validation Strategy (Current)**:
- **Story 2-5 precedent**: Manual Dagster UI validation instead of async DB tests
- **Rationale**: Greenlet dependency issues, async complexity, manual validation sufficient
- **Resolution**: AC7 and AC9 validated via "Code review + manual Dagster UI"

**Implementation Requirements** (if pursuing):

1. **Async Session Fixture** (3-4 hours)
   - SQLAlchemy AsyncEngine with event loop management
   - Transaction rollback for test isolation
   - Database URL conversion (`postgresql+psycopg` → `postgresql+asyncpg`)
   - Compatibility with pytest-xdist (parallel execution)
   - Delete seed data for test isolation (similar to sync `db` fixture)

2. **Dagster Test Context Fixture** (1-2 hours)
   - Use `build_asset_context()` from Dagster testing utilities
   - Configure with DatabaseResource
   - Compatible with logging/resources

3. **Test Updates** (1-2 hours)
   - Remove `@pytest.mark.skip` decorators
   - Update fixtures from `session` → `async_session`
   - Verify async/await patterns
   - Run locally and in CI

**Technical Dependencies**:
- ✅ pytest-asyncio installed (v0.24.0)
- ✅ asyncpg installed (v0.30.0)
- ✅ Python 3.12 in CI (Python 3.14 locally skips tests due to Dagster incompatibility)
- ⚠️ Potential greenlet compatibility issues (historical problem from Story 2-5)
- ⚠️ Event loop management with pytest-xdist parallel execution

**Risks**:
- Greenlet compatibility issues with async SQLAlchemy (Story 2-5 context)
- Parallel test execution conflicts with async fixtures
- CI environment differences (Python 3.12 vs 3.14)

**Alternative Validation** (Current Approach):
- Unit tests cover 100% of sentiment analysis logic
- Manual Dagster UI validation confirms end-to-end functionality
- Code review validated FK relationships, idempotency, edge cases
- Production deployment successful (Story 4-5 approved 2025-11-16)

**Value Assessment**:
- **Low incremental value**: Tests would formalize what's already validated
- **Not blocking**: Epic 5 can consume `fact_social_sentiment` without these tests
- **Pattern establishment**: Would enable automated testing for future Dagster assets

**Recommendation**:
- Continue manual Dagster UI validation pattern (status quo) for MVP
- Consider implementing if team scales or needs automated regression testing
- Revisit when multiple Dagster assets require similar integration tests

**Priority**: Low (technical debt, not blocking functionality)

**Estimated Effort**: 5-8 hours
- Async session fixture: 3-4 hours
- Dagster context fixture: 1-2 hours
- Test updates and validation: 1-2 hours

**Related Stories**:
- Story 2-5: Established manual Dagster UI validation precedent
- Story 4-5: Sentiment analysis with 4 skipped integration tests
- Story 4-4: Transform layer tests also use manual validation pattern

**When to Implement**:
- Story 4-9 or later (after Epic 4 completion)
- When team needs automated regression testing for Dagster assets
- If greenlet/async compatibility improves with future library updates

**Test Files**:
- Skipped: `/Users/Philip/dev/gamepulse/backend/app/tests/assets/test_calculate_sentiment.py`
- Pattern reference: `/Users/Philip/dev/gamepulse/backend/app/tests/assets/test_transform_social_posts.py` (lines 367-391)

---

## Implementation Priority

| Enhancement | Priority | Estimated Effort | Recommended Approach | Epic Target |
|-------------|----------|------------------|---------------------|-------------|
| Team Colors | Low | 3-7 hours | Third-party API or Manual (top 100) | Epic 5+ |
| Team Aliases | Medium | 6-10 hours | LLM + Manual Validation (top 100) | Epic 4 or 5 |
| Team Logos | Medium-Low | 1-10 hours | ESPN CDN Hotlink (quick) or S3+CloudFront (production) | Epic 3 or 5 |
| Conferences | Low | 8-12 hours | Manual Curation (status quo) | Epic 5+ |
| Historical Backfill | Low | 6-10 hours | Defer | Epic 6+ |
| Player Rosters | Low | 10-15 hours | Defer | Epic 7+ |
| DimTeam Timezone Fix | Low | 2-3 hours | Update model + migration | Infrastructure Sprint |
| Docker ECR Caching | Low | 1-2 hours | ECR buildcache with lifecycle policy | After Phase 1-3 validation |
| Path-Based Job Skipping | Low | 2 hours | Path filters with dorny/paths-filter | High-frequency development periods |
| Async Test Infrastructure | Low | 5-8 hours | Manual validation (status quo) or implement async fixtures | Story 4-9 or later |

## Notes
- All enhancements are **optional** for MVP
- Priority should be reassessed during Epic 4 (Reddit Matching) based on actual data quality needs
- Manual curation remains viable for top-tier teams (quality over coverage philosophy)
- Team aliases may become higher priority if Reddit matching shows poor accuracy without them

## Follow-Up Process

When implementing any of these enhancements:

1. **Update Story 2-3b** reference in implementation to indicate enhancement is being added
2. **Create new story** (e.g., Story 5-X for Epic 5 enhancements)
3. **Document chosen approach** and rationale in architecture.md
4. **Update backend/app/data/README.md** with new automation processes
5. **Add tests** for new automation logic
6. **Monitor data quality** metrics after deployment
