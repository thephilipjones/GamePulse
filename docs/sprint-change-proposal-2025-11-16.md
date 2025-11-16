# Sprint Change Proposal - Story 4-4 Game Matching Deferral

**Date:** 2025-11-16
**Prepared By:** Bob (Scrum Master)
**Epic:** Epic 4 (Social Media ELT Pipeline)
**Triggering Story:** 4-4 (Unified Transform Layer)

---

## Section 1: Issue Summary

### Problem Statement

During Story 4-4 implementation, the development team made an architectural decision to **defer GameMatcher integration from the transform layer**. The original acceptance criteria (AC #3, lines 73-89) specified that the transform asset should:

1. Apply GameMatcher to each post
2. Filter posts with confidence < 0.6
3. Only insert matched (game-related) posts into `stg_social_posts`
4. Update raw posts with match status

The actual implementation (documented in Story 4-4 Dev Notes, lines 503-508) deferred this game matching to maintain:
- **Separation of concerns:** Transform = normalization only
- **Performance:** GameMatcher is expensive (fuzzy matching), running inline would slow the pipeline
- **Flexibility:** Game matching can be tuned separately without touching transform logic
- **Data preservation:** Keep ALL posts in `stg_social_posts` for future ML experimentation

### Discovery Context

This architectural decision was made consciously during Story 4-4 development and properly documented in the Dev Notes. It's being surfaced now as you prepare to start Stories 4-5 and 4-6 to ensure alignment across the team and documentation.

### Evidence

**Original Specification (Story 4-4 AC #3, lines 73-89):**
```python
# Specified behavior:
match_result = game_matcher.match_post_to_teams(post_text)
if match_result["match_confidence"] < 0.6:
    # Filter out - do NOT insert to stg_social_posts
    raw_post.matched_to_game = FALSE
else:
    # Insert matched post only
    stg_social_posts.insert(...)
```

**Actual Implementation (Story 4-4 Dev Notes, line 503-508):**
```
3. **Removed Game Matching from Transform Layer (Deferred)**
   - Original plan included GameMatcher integration in transform
   - **Decision:** Keep transform layer focused on normalization only
   - Game matching moved to separate future story (better separation of concerns)
```

---

## Section 2: Impact Analysis

### Epic Impact

**Epic 4 (Social Media ELT):**
- ✅ **Can be completed as originally planned**
- Stories 4-5 and 4-6 have no blocking dependencies on transform-layer matching
- Story 4-5 already implements game matching for its own needs (game_key FK resolution via `GameMatcher.resolve_game_key()`, lines 82-99)
- **Expected outcome (line 147):** "80-90% of stg_social_posts matched to games" - Story 4-5 achieves this

**Future Epics:**
- ✅ **Epic 5 (Moment Detection):** NO IMPACT
  - Epic 5 consumes `fact_social_sentiment`, which is populated by Story 4-5
  - Story 4-5's game matching provides required FK linkage

### Story Impact

**Story 4-5 (Sentiment Analysis):**
- ✅ **NO CHANGES NEEDED**
- Already implements game matching at sentiment layer (AC #4, lines 89-99)
- Processes stg_social_posts and calls `GameMatcher.resolve_game_key()` for FK resolution
- Skips posts with no game match (logged as `posts_skipped_no_game`)

**Story 4-6 (Orchestration):**
- ✅ **NO CHANGES NEEDED**
- Focus: Pipeline reliability, retry policies, observability, data quality checks
- No dependency on matched vs. unmatched posts

**New Story Needed:**
- 📝 **Story 4-7: Game Matching Post-Processor** (Optional optimization)
  - Batch-process stg_social_posts to add game matching metadata
  - Filter/delete non-game posts to reduce storage 10-20%
  - Can be prioritized after Epic 4 completion

### Artifact Conflicts

**PRD ([docs/PRD.md](docs/PRD.md)):**
- ✅ **NO CONFLICTS** - PRD specifies outcomes (excitement scoring), not implementation layers

**Architecture ([docs/architecture.md](docs/architecture.md)):**
- ✅ **NO CONFLICTS** - Architecture doesn't specify game matching layer

**Epic 4 Technical Spec ([docs/epics/epic-4-social-media-elt.md](docs/epics/epic-4-social-media-elt.md)):**
- ⚠️ **MINOR UPDATE NEEDED** - Lines 96-108 describe transform as including game matcher
  - Update data flow diagram to reflect normalization-only transform
  - Add note that game matching happens in Story 4-5 (FK resolution layer)

**Sprint Status ([docs/sprint-status.yaml](docs/sprint-status.yaml)):**
- ✅ **UP TO DATE** - Story 4-4 marked "in-progress", accurately reflects current state

### Technical Impact

**Current Architecture (Two-Stage Matching Pattern):**

1. **Stage 1 (Story 4-4 - Transform Layer):**
   - Normalizes posts from raw tables → stg_social_posts
   - Sets `matched_to_game = FALSE` (deferred matching)
   - ALL posts flow through regardless of game relevance

2. **Stage 2 (Story 4-5 - Sentiment Layer):**
   - Reads stg_social_posts
   - Uses GameMatcher to resolve game_key for FK linkage
   - Skips posts with no game match (logged)

**Storage Impact:**
- Current: ALL posts stored in stg_social_posts (~2,000 daily)
- Original design: Only matched posts (~800 daily, 40% match rate)
- Difference: +1,200 posts/day × 90 days = ~25 MB extra storage
- **Verdict:** Acceptable within 20GB EC2 disk budget

**Performance Impact:**
- Story 4-5 processes 100% of stg_social_posts (vs. 40% if filtered earlier)
- Additional processing: 1,200 extra posts/day × 0.01s VADER analysis = ~12 seconds/day
- **Verdict:** Negligible performance impact

---

## Section 3: Recommended Approach

### Selected Path: **Direct Adjustment** (Add Story 4-7 as Optional Optimization)

**Summary:** Document the architectural decision, proceed with Stories 4-5 and 4-6 as planned, and create Story 4-7 to capture the deferred transform-layer matching as a future optimization opportunity.

### Rationale

1. **Current implementation is correct:**
   - Transform does normalization (its core responsibility)
   - Story 4-5 does game matching for FK resolution (its requirement)
   - Clear separation of concerns

2. **No blocking issues:**
   - Epic 4 deliverable as-is
   - Epic 5 receives required data from Story 4-5
   - All acceptance criteria achievable

3. **Better architecture:**
   - Separation of concerns: normalization vs. filtering
   - Performance flexibility: can optimize matching independently
   - Data preservation: keeps all posts for future ML

4. **Demonstrates iterative improvement:**
   - "Build → measure → optimize" pattern
   - Shows pragmatic engineering vs. premature optimization
   - Portfolio value: documents trade-off reasoning

### Effort Estimate

- **Epic 4 Timeline Impact:** NONE
- **Story 4-7 Effort (if prioritized later):** 8-12 hours
- **Documentation Updates:** 1-2 hours (Epic 4 spec, sprint status)

### Risk Assessment

- **Technical Risk:** LOW - Current implementation proven in Story 4-4 testing
- **Timeline Risk:** NONE - No delay to Stories 4-5, 4-6, or Epic 4 completion
- **Scope Risk:** NONE - Epic 4 goals achievable without Story 4-7

---

## Section 4: Detailed Change Proposals

### Proposal 1: Update Epic 4 Technical Specification

**File:** [docs/epics/epic-4-social-media-elt.md](docs/epics/epic-4-social-media-elt.md)
**Section:** Data Flow Diagram (lines 96-108)

**Change:**
```diff
│  transform_social_posts (Hourly)                                        │
│  ├─ Read: raw_reddit_posts, raw_bluesky_posts                           │
- │  ├─ Game Matcher: Fuzzy team name matching (dim_team.aliases)           │
- │  ├─ Filter: Only game-related posts (confidence > 0.6)                  │
│  ├─ Normalize: Engagement scoring (platform-aware formulas)             │
- │  └─ Write: stg_social_posts (unified multi-platform schema)             │
+ │  └─ Write: stg_social_posts (all posts, matched_to_game=FALSE)         │
+ │                                                                          │
+ │  Note: Game matching deferred to Story 4-5 (FK resolution layer)        │
```

**Justification:** Accurately reflects Story 4-4 implementation decision.

---

### Proposal 2: Add Story 4-7 to Sprint Status

**File:** [docs/sprint-status.yaml](docs/sprint-status.yaml)
**Section:** Epic 4 stories (after line 88)

**Change:**
```diff
  4-4-unified-transform-layer: in-progress # Dev started 2025-11-16
  4-5-sentiment-analysis-fact-table: drafted
  4-6-orchestration-data-management: drafted
+ 4-7-game-matching-post-processor: drafted # Optimization - batch match stg_social_posts
  epic-4-retrospective: optional
```

**Justification:** Tracks deferred work for future prioritization.

---

### Proposal 3: Create Story 4-7 Draft

**File:** NEW - `docs/stories/4-7-game-matching-post-processor.md`

**Content Summary:**
```markdown
# Story 4.7: Game Matching Post-Processor (Transform Layer Optimization)

## Story
As a data engineer,
I want to batch-process stg_social_posts with GameMatcher to filter non-game posts,
So that storage and downstream processing are optimized by 10-20%.

## Context
Story 4-4 intentionally deferred game matching to maintain separation of concerns.
This story adds game matching as a post-processing optimization.

## Acceptance Criteria
1. Dagster asset: `match_posts_to_games` (runs after transform_social_posts)
2. Batch-processes stg_social_posts WHERE matched_to_game = FALSE (2500/batch)
3. Updates matched_to_game and match_confidence columns
4. Optional: Deletes posts with confidence < 0.6 (configurable via env var)
5. Logs: posts_processed, posts_matched, posts_filtered, match_rate

## Dependencies
- Story 4-4: stg_social_posts table exists
- Story 4-5: Sentiment analysis unaffected

## Priority
LOW - Performance optimization, not functional requirement

## Estimated Effort
8-12 hours
```

**Justification:** Documents deferred work with clear acceptance criteria for future implementation.

---

## Section 5: Implementation Handoff

### Change Scope Classification: **MINOR**

**Scope:** Direct documentation updates + story drafting
**Implementation:** Scrum Master (documentation) + Product Owner (Story 4-7 prioritization)
**No code changes required**

### Handoff Plan

**Immediate Actions (Scrum Master - Philip):**
1. ✅ Update Epic 4 spec data flow diagram (Proposal 1)
2. ✅ Add Story 4-7 to sprint-status.yaml (Proposal 2)
3. ✅ Draft Story 4-7 file (Proposal 3)
4. ✅ Notify development team of documented decision

**Future Actions (Product Owner - Philip):**
1. Review Story 4-7 priority after Epic 4 completion
2. Evaluate based on:
   - Actual storage usage after 30 days
   - Story 4-5 performance metrics (posts_skipped_no_game count)
   - Epic 5 integration experience
3. Options:
   - **Defer indefinitely** if current architecture performs well
   - **Prioritize for Epic 9** (Testing & Quality) as optimization story
   - **Deprioritize** if storage/performance acceptable

**Development Team (Philip):**
1. Continue Story 4-4 completion (no changes)
2. Proceed with Story 4-5 as drafted (no changes)
3. Proceed with Story 4-6 as drafted (no changes)

### Success Criteria

**Proposal accepted if:**
- ✅ Epic 4 timeline unaffected (Stories 4-5, 4-6 proceed as planned)
- ✅ Epic 5 integration verified (Story 4-5 provides required data)
- ✅ Documentation accurately reflects implementation
- ✅ Story 4-7 captured for future prioritization

---

## Conclusion

The Story 4-4 game matching deferral is an **intentional architectural decision**, not a requirement failure. The current implementation:
- ✅ **Maintains Epic 4 schedule** (no delay to 4-5, 4-6 completion)
- ✅ **Enables Epic 5 integration** (Story 4-5 provides matched sentiment data)
- ✅ **Demonstrates better architecture** (separation of concerns, performance flexibility)
- ✅ **Preserves future options** (raw data for ML, Story 4-7 for optimization)

**Recommendation:** **APPROVE** this course correction and proceed with Epic 4 execution as planned.

---

**End of Sprint Change Proposal**
