# Story 4.8: Game Matching Post-Processor (Transform Layer Optimization)

Status: ready-for-dev

## Story

As a data engineer,
I want to batch-process stg_social_posts with GameMatcher to filter non-game posts,
So that storage and downstream processing costs are reduced by 10-20%.

## Context

**Origin:** Story 4-4 intentionally deferred GameMatcher integration from the transform layer to maintain separation of concerns, improve performance, and preserve data flexibility. The original requirement (Story 4-4 AC #3) specified filtering posts during transformation, but the implementation kept the transform layer focused on normalization only.

**Current State:**
- Transform layer (Story 4-4): Normalizes all posts → stg_social_posts (sets matched_to_game = FALSE)
- Sentiment layer (Story 4-5): Matches posts to games for FK resolution via GameMatcher.resolve_game_key()
- All posts (matched and unmatched) remain in stg_social_posts

**Problem:**
While functionally correct, storing all posts (including non-game content) leads to:
- **Storage overhead:** ~1,200 extra posts/day × 90 days = ~25 MB additional storage
- **Processing overhead:** Story 4-5 processes 100% of posts vs. 40% if filtered earlier (~12 seconds/day additional processing)

**Solution:**
Add a post-processing step that batch-matches stg_social_posts to games and optionally filters non-game posts to optimize storage and downstream processing.

## Acceptance Criteria

### 1. New Dagster Asset - match_posts_to_games

**GIVEN** Dagster daemon is running
**WHEN** I define the match_posts_to_games asset
**THEN** it has the following configuration:
- `name="match_posts_to_games"`
- `description="Batch-process stg_social_posts to match posts to games and filter irrelevant content"`
- `group_name="social_media_transformation"`
- `compute_kind="python"`
- `deps=[transform_social_posts]` (runs after transform completes)
- `retry_policy=RetryPolicy(max_retries=2, delay=10, backoff=Backoff.LINEAR)`

### 2. Batch Processing Logic

**GIVEN** stg_social_posts contains 5,000 posts with matched_to_game = FALSE
**WHEN** match_posts_to_games asset materializes
**THEN** it processes posts in batches of 2500 (optimized for t4g.small memory)
**AND** for each batch:
1. SELECT posts WHERE matched_to_game = FALSE LIMIT 2500
2. Initialize GameMatcher(session) once per batch
3. For each post:
   - Extract post_text
   - Call GameMatcher.match_post_to_teams(post_text)
   - Update matched_to_game = is_game_related
   - Update match_confidence = confidence score
4. Commit batch
**AND** logs structured metadata:
```python
{
    "posts_processed": 5000,
    "posts_matched": 2000,
    "posts_filtered": 3000,
    "match_rate": "40.0%",
    "batches_executed": 2
}
```

### 3. Optional Post Filtering (Configurable)

**GIVEN** environment variable `FILTER_LOW_CONFIDENCE_POSTS=true`
**WHEN** match_posts_to_games processes a post with match_confidence < 0.6
**THEN** it deletes the post from stg_social_posts
**AND** logs deletion count

**AND GIVEN** `FILTER_LOW_CONFIDENCE_POSTS=false` (default)
**WHEN** match_posts_to_games processes low-confidence posts
**THEN** it updates match metadata but keeps the post in stg_social_posts
**AND** preserves data for future ML experimentation

### 4. Database Schema Updates

**GIVEN** Story 4-4 created stg_social_posts without matched_to_game column
**WHEN** I run Alembic migration for Story 4-8
**THEN** stg_social_posts has the following new columns:
- `matched_to_game` BOOLEAN DEFAULT FALSE (indicates if post has been processed)
- `match_confidence` NUMERIC(3,2) (0.0-1.0 confidence score from GameMatcher)

**Note:** If Story 4-4 already added these columns (implementation detail), skip this AC.

### 5. Dagster Schedule - Daily at 3:00 AM

**GIVEN** Dagster daemon is running
**WHEN** I view schedules in Dagster UI
**THEN** `match_posts_to_games_schedule` exists with:
- Cron: `0 3 * * *` (daily at 3 AM)
- Status: `RUNNING` (default)
- Timezone: `America/New_York`
- Runs after cleanup job from Story 4-7 completes

**Rationale:** Daily batch processing sufficient (not real-time requirement). Scheduled after cleanup to avoid processing posts about to be deleted.

### 6. Integration with Story 4-5

**GIVEN** Story 4-5 sentiment analysis asset is operational
**WHEN** match_posts_to_games runs and updates stg_social_posts
**THEN** Story 4-5 continues to work without modification
**AND** Story 4-5 skips posts with matched_to_game = FALSE OR match_confidence < 0.6
**AND** no duplicate game matching occurs (Story 4-5 already matches for FK resolution)

**Note:** This story adds transform-layer filtering; Story 4-5 retains its game_key resolution logic.

### 7. Performance Metrics

**GIVEN** match_posts_to_games has run for 7 days
**WHEN** I query stg_social_posts
**THEN** I observe:
- **Match rate:** 30-50% of posts marked matched_to_game = TRUE (expected from Epic 4 spec)
- **Storage reduction (if filtering enabled):** ~10-20% fewer total posts
- **Processing time:** ~5-7 seconds per 1000 posts (same as Story 4-4 original estimate)

## Tasks / Subtasks

### Task 1: Database Migration (If Needed) - AC #4
- [ ] Check if stg_social_posts already has matched_to_game and match_confidence columns
- [ ] If missing, create Alembic migration: `{timestamp}_add_game_matching_to_stg_social_posts.py`
- [ ] Add columns: matched_to_game BOOLEAN DEFAULT FALSE, match_confidence NUMERIC(3,2)
- [ ] Run migration: `alembic upgrade head`
- [ ] Verify columns in psql: `\d stg_social_posts`

### Task 2: Dagster Asset - match_posts_to_games (AC #1, #2, #3)
- [ ] Create file: `backend/app/assets/match_posts_to_games.py`
- [ ] Import dependencies:
  - `from app.services.game_matcher import GameMatcher`
  - `from app.models.social import StgSocialPost`
- [ ] Define `@asset` with configuration from AC #1
- [ ] Implement batch processing logic:
  - SELECT posts WHERE matched_to_game = FALSE LIMIT 2500
  - Initialize GameMatcher once per batch
  - For each post: extract text, match teams, update metadata
  - Optionally delete low-confidence posts if env var set
  - Commit each batch
- [ ] Add structured logging (context.log.info) for progress tracking
- [ ] Return metadata dict with counts and match_rate %

### Task 3: Environment Variable Configuration (AC #3)
- [ ] Add to `.env.example`:
  ```bash
  # Game Matching Post-Processor (Story 4-8)
  FILTER_LOW_CONFIDENCE_POSTS=false  # true = delete, false = keep for ML
  ```
- [ ] Document in CLAUDE.md under Epic 4 section
- [ ] Update AWS Parameter Store mapping (if deploying to production)

### Task 4: Dagster Schedule Definition (AC #5)
- [ ] Define schedule in `match_posts_to_games.py`:
  - `match_posts_to_games_schedule`
  - Cron: `0 3 * * *`
  - Timezone: `America/New_York`
  - DefaultScheduleStatus: `RUNNING`
- [ ] Register in `backend/app/dagster_definitions.py`:
  - Import match_posts_to_games asset
  - Import match_posts_to_games_schedule
  - Add to all_assets list
  - Add to all_schedules list
- [ ] Restart Dagster daemon
- [ ] Verify schedule in Dagster UI

### Task 5: Integration Testing (AC #6, #7)
- [ ] Manually insert sample posts into stg_social_posts (with and without game mentions)
- [ ] Run: `dagster asset materialize -m app.dagster_definitions match_posts_to_games`
- [ ] Verify matched posts have matched_to_game = TRUE and confidence scores
- [ ] Verify unmatched posts have matched_to_game = FALSE and confidence = 0.0
- [ ] Test with FILTER_LOW_CONFIDENCE_POSTS=true: verify low-confidence posts deleted
- [ ] Test with FILTER_LOW_CONFIDENCE_POSTS=false: verify low-confidence posts retained
- [ ] Verify Story 4-5 sentiment asset still works without modification
- [ ] Query performance metrics (AC #7): match rate, storage reduction, processing time

### Task 6: Update Documentation
- [ ] Update Epic 4 data flow diagram (if not already done by SM)
- [ ] Document in Story 4-4 Dev Notes: "Game matching moved to Story 4-8"
- [ ] Update CLAUDE.md: Add Story 4-8 to Epic 4 story list

## Dev Notes

### Relationship to Story 4-4

**Story 4-4 Implementation Decision:**
- Transform layer kept focused on **normalization only** (engagement scores, platform unification)
- Game matching **intentionally deferred** for separation of concerns and performance
- Documented in Story 4-4 Dev Notes (lines 503-508)

**Story 4-8 Purpose:**
- Add game matching as **separate post-processing optimization**
- Does NOT replace Story 4-5's game matching (Story 4-5 needs game_key for FK resolution)
- Provides **storage and processing efficiency** by filtering earlier in pipeline

### Relationship to Story 4-5

**Story 4-5 Game Matching:**
- Purpose: Resolve game_key FK for fact_social_sentiment table
- Logic: GameMatcher.resolve_game_key(matched_teams, game_date)
- Behavior: Skips posts with no game match (logs `posts_skipped_no_game`)
- Status: Required for Epic 5 integration, NOT replaced by this story

**Story 4-8 Game Matching:**
- Purpose: Filter non-game posts from stg_social_posts to reduce storage/processing
- Logic: GameMatcher.match_post_to_teams(post_text)
- Behavior: Updates match metadata, optionally deletes low-confidence posts
- Status: Optional optimization, can be deferred indefinitely

### Architecture Context

**Current Flow (Without Story 4-8):**
1. Extract (Stories 4-1, 4-2) → raw tables (all posts)
2. Transform (Story 4-4) → stg_social_posts (all posts, normalized)
3. Sentiment (Story 4-5) → fact_social_sentiment (only matched posts)

**Flow With Story 4-8:**
1. Extract (Stories 4-1, 4-2) → raw tables (all posts)
2. Transform (Story 4-4) → stg_social_posts (all posts, normalized)
3. **Match (Story 4-8) → stg_social_posts (filter non-game posts)** ← NEW
4. Sentiment (Story 4-5) → fact_social_sentiment (only matched posts)

**Benefits:**
- Story 4-5 processes fewer posts (40% instead of 100%)
- Storage savings: 10-20% reduction in stg_social_posts
- Preserves Story 4-4's separation of concerns

### Performance Optimization Context

**Why Daily (Not Real-Time)?**
- Sentiment analysis (Story 4-5) runs hourly, already handles unmatched posts gracefully
- Daily batch sufficient for storage optimization
- Reduces GameMatcher initialization overhead (once per day vs. multiple times per day)

**Expected Runtime:**
- 2,000 posts/day × 1ms per match = ~2 seconds matching
- Database updates = ~1-2 seconds
- **Total: ~5 seconds per day**

### Testing Strategy

**Priority 1: Integration Tests**
- Test with/without FILTER_LOW_CONFIDENCE_POSTS flag
- Verify Story 4-5 unaffected
- Verify no duplicate matching overhead

**Priority 2: Performance Validation**
- Measure actual match rate (30-50% expected)
- Measure storage reduction (if filtering enabled)
- Verify processing time within estimates

**Skip (Nice-to-Have):**
- Unit tests for individual functions (GameMatcher already tested in Story 4-3)

### References

**Related Stories:**
- [Story 4-3: Game Matching Service](4-3-game-matching-service.md) - GameMatcher implementation
- [Story 4-4: Unified Transform Layer](4-4-unified-transform-layer.md) - Deferred game matching decision
- [Story 4-5: Sentiment Analysis](4-5-sentiment-analysis-fact-table.md) - Game key resolution

**Epic 4 Technical Specification:**
- [Epic 4: Social Media ELT](../epics/epic-4-social-media-elt.md) - Overall architecture

**Sprint Change Proposal:**
- [Sprint Change Proposal 2025-11-16](../sprint-change-proposal-2025-11-16.md) - Decision documentation

## Priority

**LOW** - Performance optimization, not functional requirement

**Prioritization Guidance:**
- **Defer indefinitely** if storage/performance acceptable after Epic 4 completion
- **Prioritize for Epic 9** (Testing & Quality) if optimization needed
- **Deprioritize** if Epic 5 integration reveals no bottlenecks

## Estimated Effort

**8-12 hours**

**Breakdown:**
- Database migration (if needed): 1 hour
- Dagster asset implementation: 3-4 hours
- Schedule configuration: 1 hour
- Integration testing: 2-3 hours
- Documentation updates: 1-2 hours

## Dev Agent Record

### Context Reference
- [Story Context XML](4-8-game-matching-post-processor.context.xml) - Generated 2025-11-16
