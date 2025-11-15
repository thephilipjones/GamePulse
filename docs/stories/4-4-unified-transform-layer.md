# Story 4-4: Unified Transform Layer

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-4
**Status:** TODO
**Estimated Effort:** 12-16 hours
**Priority:** High (Week 2 - blocks 4-5)
**Dependencies:** Stories 4-1 (Reddit), 4-2 (Bluesky), 4-3 (GameMatcher)

---

## User Story

**As a** data engineer,
**I want** to transform raw multi-platform social posts into a unified schema with game matching filter,
**So that** only game-related posts are stored and normalized for downstream sentiment analysis (Story 4-5).

---

## Context

Raw extraction layers (Stories 4-1, 4-2) store complete JSON for Reddit and Bluesky posts. This story implements the **Transform** step of the ELT pipeline:

**Input:** `raw_reddit_posts` + `raw_bluesky_posts` (platform-specific JSON)
**Processing:** Game matcher filter + platform normalization
**Output:** `stg_social_posts` (unified multi-platform schema, game-related only)

**Key Design Decisions (from Philip's answers):**
- **Early filtering:** Apply game matcher during transform to minimize irrelevant data storage
- **Multi-platform normalization:** Unified schema with platform-aware engagement scoring
- **Periodic cleanup:** Delete unmatched raw posts after 7 days to save storage

This story unblocks Story 4-5 (sentiment analysis) by providing clean, filtered, game-related posts.

---

## Acceptance Criteria

### 1. Database Table - stg_social_posts

✅ **GIVEN** Alembic migrations are run
**WHEN** I check the database schema
**THEN** `stg_social_posts` table exists with columns:
- `social_post_key` BIGSERIAL PRIMARY KEY
- `platform` TEXT ('reddit' | 'bluesky')
- `platform_post_id` TEXT (original post ID/URI)
- `post_text` TEXT (full post content)
- `created_at` TIMESTAMPTZ (post creation time)
- `matched_teams` TEXT[] (array of team_ids: ["duke", "unc"])
- `match_confidence` NUMERIC(3,2) (0.6-1.0)
- `engagement_score` NUMERIC(10,2) (platform-normalized)
- `platform_metadata` JSONB (platform-specific extras)

**AND** table is a TimescaleDB hypertable partitioned on `created_at` (1-day chunks)
**AND** UNIQUE constraint on `(platform, platform_post_id)` prevents duplicates
**AND** indexes on `created_at`, `matched_teams` (GIN), `engagement_score`

### 2. Dagster Asset - transform_social_posts

✅ **GIVEN** raw posts exist in `raw_reddit_posts` and `raw_bluesky_posts`
**WHEN** `transform_social_posts` asset materializes
**THEN** it reads unprocessed posts (`matched_to_game = FALSE`)
**AND** applies GameMatcher to each post
**AND** filters out posts with `match_confidence < 0.6`
**AND** inserts matched posts into `stg_social_posts` with normalized engagement
**AND** marks raw posts as processed (`matched_to_game = TRUE`, `processed_at = NOW()`)
**AND** returns metadata: `{posts_processed, posts_matched, posts_filtered}`

### 3. Game Matching Filter

✅ **GIVEN** a raw Reddit post: "Duke vs UNC tonight!" (confidence 0.95)
**WHEN** transform runs
**THEN** post is inserted into `stg_social_posts` with `matched_teams = ["duke", "unc"]`

**AND GIVEN** a raw post: "Just had pizza" (confidence 0.0)
**WHEN** transform runs
**THEN** post is **NOT** inserted into `stg_social_posts` (filtered out)
**AND** raw post marked `matched_to_game = FALSE` for future cleanup

### 4. Multi-Platform Engagement Normalization

✅ **GIVEN** a Reddit post with `score=100, num_comments=20, upvote_ratio=0.9`
**WHEN** transform calculates engagement
**THEN** engagement_score = `(100 * 1.0) + (20 * 2.0) + (0.9 * 10.0) = 149`

**AND GIVEN** a Bluesky post with `likeCount=50, replyCount=10, repostCount=5`
**WHEN** transform calculates engagement
**THEN** engagement_score = `(50 * 1.5) + (10 * 3.0) + (5 * 2.5) = 117.5`

**AND** platform-specific weights adjust for different user bases (Reddit larger than Bluesky)

### 5. Platform Metadata Preservation

✅ **GIVEN** a Reddit post
**WHEN** inserted into `stg_social_posts`
**THEN** `platform_metadata` JSONB contains:
```json
{
  "upvote_ratio": 0.94,
  "link_flair_text": "Post Game Thread",
  "permalink": "/r/CollegeBasketball/comments/..."
}
```

**AND GIVEN** a Bluesky post
**THEN** `platform_metadata` contains:
```json
{
  "facets": [...],  // Hashtags, mentions
  "author_did": "did:plc:..."
}
```

### 6. Dagster Schedule - Hourly at :15

✅ **GIVEN** Dagster daemon is running
**WHEN** I view schedules in Dagster UI
**THEN** `transform_social_posts_schedule` exists:
- Cron: `15 * * * *` (hourly at :15)
- Status: `RUNNING`
- Dependencies: Waits for `extract_reddit_posts` and `extract_bluesky_posts`

**AND** schedule triggers 15 minutes after extraction schedules complete (Reddit: every 10 min, Bluesky: every 5 min)

### 7. Batch Processing for Memory Constraints

✅ **GIVEN** 10,000 unprocessed raw posts
**WHEN** transform runs
**THEN** it processes in batches of 1000 posts (memory constraint: t2.micro 1GB RAM)
**AND** commits each batch separately
**AND** continues until all posts processed
**AND** logs batch progress: `transform_batch_completed: batch=3, posts_in_batch=1000`

### 8. Week 2 Success Metric

✅ **GIVEN** transform has run for 7 days
**WHEN** I query:
```sql
SELECT
    COUNT(*) AS total_posts,
    COUNT(*) FILTER (WHERE platform = 'reddit') AS reddit_posts,
    COUNT(*) FILTER (WHERE platform = 'bluesky') AS bluesky_posts,
    AVG(match_confidence) AS avg_confidence
FROM stg_social_posts
WHERE created_at > NOW() - INTERVAL '7 days';
```

**THEN** results show:
- `total_posts`: 500-1,500 (30-50% of raw posts matched)
- `avg_confidence`: 0.75-0.85 (high-quality matches)
- Both platforms represented (not 100% from single platform)

---

## Technical Tasks

### Task 1: Database Migration - stg_social_posts Table

**File:** `backend/app/alembic/versions/{timestamp}_create_stg_social_posts.py`

**Implementation:**
```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE stg_social_posts (
            social_post_key BIGSERIAL PRIMARY KEY,
            platform TEXT NOT NULL CHECK (platform IN ('reddit', 'bluesky')),
            platform_post_id TEXT NOT NULL,
            author_username TEXT,
            post_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            fetched_at TIMESTAMPTZ NOT NULL,

            matched_teams TEXT[],
            match_confidence NUMERIC(3,2) NOT NULL,
            matched_game_date DATE,

            engagement_score NUMERIC(10,2),
            likes_count INTEGER,
            comments_count INTEGER,
            shares_count INTEGER,

            platform_metadata JSONB,

            source_table TEXT NOT NULL,
            source_row_id TEXT NOT NULL,
            transformed_at TIMESTAMPTZ DEFAULT NOW(),

            UNIQUE(platform, platform_post_id)
        );
    """)

    # TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable('stg_social_posts', 'created_at',
                                 chunk_time_interval => INTERVAL '1 day');
    """)

    # Indexes
    op.execute("CREATE INDEX idx_stg_social_created_at ON stg_social_posts (created_at DESC);")
    op.execute("CREATE INDEX idx_stg_social_teams_gin ON stg_social_posts USING GIN (matched_teams);")
    op.execute("CREATE INDEX idx_stg_social_platform_date ON stg_social_posts (platform, matched_game_date);")
    op.execute("CREATE INDEX idx_stg_social_engagement ON stg_social_posts (engagement_score DESC, created_at DESC);")

    # Retention (90 days, no compression - active querying)
    op.execute("SELECT add_retention_policy('stg_social_posts', INTERVAL '90 days');")

def downgrade() -> None:
    op.execute("DROP TABLE stg_social_posts CASCADE;")
```

---

### Task 2: SQLModel - StgSocialPost Model

**File:** `backend/app/models/social.py` (modify existing file)

**Implementation:**
```python
class StgSocialPost(SQLModel, table=True):
    """
    Unified multi-platform social posts (game-related only).

    TimescaleDB hypertable partitioned on created_at (1-day chunks).
    """

    __tablename__ = "stg_social_posts"

    social_post_key: int | None = Field(default=None, primary_key=True, description="Surrogate key")
    platform: str = Field(description="Source platform: 'reddit' | 'bluesky'")
    platform_post_id: str = Field(description="Original post ID/URI")
    author_username: str | None = Field(default=None)
    post_text: str = Field(description="Full post text/title")
    created_at: datetime = Field(description="Post creation timestamp")
    fetched_at: datetime = Field(description="When we extracted it")

    matched_teams: list[str] = Field(sa_column=Column(ARRAY(String)), description="Team IDs matched")
    match_confidence: float = Field(description="Game matching confidence (0.6-1.0)")
    matched_game_date: date | None = Field(default=None, description="Inferred game date")

    engagement_score: float | None = Field(default=None, description="Platform-normalized engagement")
    likes_count: int | None = Field(default=None)
    comments_count: int | None = Field(default=None)
    shares_count: int | None = Field(default=None)

    platform_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Platform-specific extras"
    )

    source_table: str = Field(description="'raw_reddit_posts' | 'raw_bluesky_posts'")
    source_row_id: str = Field(description="PK from source table")
    transformed_at: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True
```

---

### Task 3: Dagster Asset - transform_social_posts

**File:** `backend/app/assets/social_transform.py` (new file)

**Implementation:** See Epic 4 spec, section "Dagster Asset Specifications > Asset 3: transform_social_posts"

**Key Features:**
- Read unprocessed posts from both `raw_reddit_posts` and `raw_bluesky_posts`
- Apply `GameMatcher.match_post_to_teams()` to each post
- Filter by `is_game_related` flag (confidence >= 0.6)
- Calculate platform-specific engagement scores
- Upsert into `stg_social_posts` using `ON CONFLICT DO NOTHING`
- Update raw tables with `matched_to_game`, `match_confidence`, `processed_at`
- Batch processing (1000 posts per batch for memory efficiency)

**Dependencies:**
```python
from app.services.game_matcher import GameMatcher
from app.models.social import RawRedditPost, RawBlueskyPost, StgSocialPost
```

---

### Task 4: Engagement Score Calculation

**Implementation (in transform_social_posts asset):**

```python
def calculate_reddit_engagement(post_json: dict) -> float:
    """
    Reddit engagement formula:
    - Upvotes: 1.0 weight
    - Comments: 2.0 weight (more engagement)
    - Upvote ratio: 10.0 weight (quality signal)
    """
    return (
        (post_json.get("score", 0) * 1.0) +
        (post_json.get("num_comments", 0) * 2.0) +
        (post_json.get("upvote_ratio", 0.5) * 10.0)
    )

def calculate_bluesky_engagement(post_json: dict) -> float:
    """
    Bluesky engagement formula (adjusted for smaller user base):
    - Likes: 1.5 weight (higher than Reddit upvotes)
    - Replies: 3.0 weight
    - Reposts: 2.5 weight
    """
    return (
        (post_json.get("likeCount", 0) * 1.5) +
        (post_json.get("replyCount", 0) * 3.0) +
        (post_json.get("repostCount", 0) * 2.5)
    )
```

---

### Task 5: Dagster Schedule Definition

**File:** `backend/app/assets/social_transform.py`

**Implementation:**
```python
from dagster import ScheduleDefinition, DefaultScheduleStatus, define_asset_job

transform_social_posts_job = define_asset_job(
    name="materialize_transform_social_posts",
    selection="transform_social_posts",
)

transform_social_posts_schedule = ScheduleDefinition(
    name="transform_social_posts_schedule",
    job=transform_social_posts_job,
    cron_schedule="15 * * * *",  # Hourly at :15
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
```

**Add to dagster_definitions.py:**
```python
from app.assets.social_transform import transform_social_posts, transform_social_posts_schedule

all_assets = load_assets_from_modules([
    ncaa_games_module,
    reddit_posts_module,
    bluesky_posts_module,
    social_transform_module,  # Add this
])

all_schedules = [
    ncaa_games_schedule,
    reddit_posts_schedule,
    bluesky_posts_schedule,
    transform_social_posts_schedule,  # Add this
]
```

---

### Task 6: Cleanup Job - Unmatched Raw Posts (Optional)

**Implementation (periodic cleanup):**

**File:** `backend/app/assets/cleanup_raw_posts.py` (new file)

```python
@asset(
    name="cleanup_unmatched_raw_posts",
    description="Delete raw posts older than 7 days that weren't matched to games",
    group_name="data_management",
)
async def cleanup_unmatched_raw_posts(
    context: AssetExecutionContext,
    database: DatabaseResource,
) -> dict[str, int]:
    """
    Delete raw posts that:
    1. Are older than 7 days
    2. Have matched_to_game = FALSE (not game-related)

    Saves storage on irrelevant posts.
    """
    async with database.get_session() as session:
        # Cleanup Reddit
        reddit_stmt = """
            DELETE FROM raw_reddit_posts
            WHERE created_at < NOW() - INTERVAL '7 days'
              AND matched_to_game = FALSE
        """
        reddit_result = await session.execute(reddit_stmt)
        reddit_deleted = reddit_result.rowcount

        # Cleanup Bluesky
        bluesky_stmt = """
            DELETE FROM raw_bluesky_posts
            WHERE created_at < NOW() - INTERVAL '7 days'
              AND matched_to_game = FALSE
        """
        bluesky_result = await session.execute(bluesky_stmt)
        bluesky_deleted = bluesky_result.rowcount

        await session.commit()

        context.log.info(
            "cleanup_unmatched_posts_completed",
            reddit_deleted=reddit_deleted,
            bluesky_deleted=bluesky_deleted,
        )

        return {
            "reddit_deleted": reddit_deleted,
            "bluesky_deleted": bluesky_deleted,
        }

# Schedule: Daily at 2 AM
cleanup_schedule = ScheduleDefinition(
    name="cleanup_unmatched_posts_schedule",
    job=define_asset_job("cleanup_raw_posts", selection="cleanup_unmatched_raw_posts"),
    cron_schedule="0 2 * * *",  # Daily at 2 AM
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
```

---

## Testing Requirements

### Unit Tests (Medium Priority)

**File:** `backend/app/tests/assets/test_transform_social_posts.py`

**Test Cases:**
1. `test_transform_filters_low_confidence()` - Verify confidence < 0.6 filtered
2. `test_transform_normalizes_reddit_engagement()` - Verify formula
3. `test_transform_normalizes_bluesky_engagement()` - Verify formula
4. `test_transform_marks_raw_posts_processed()` - Verify `matched_to_game` updated
5. `test_transform_batch_processing()` - Verify 1000-post batches

### Integration Tests (Low Priority)

**File:** `backend/app/tests/integration/test_transform_pipeline.py`

- ✅ End-to-end: raw → stg with real database
- ✅ Verify no duplicates (UNIQUE constraint works)

### Manual Testing Checklist

- [ ] Run `alembic upgrade head`, verify stg_social_posts created
- [ ] Insert sample raw posts (high and low confidence)
- [ ] Manually materialize `transform_social_posts` asset
- [ ] Verify high-confidence posts in stg_social_posts
- [ ] Verify low-confidence posts NOT in stg_social_posts
- [ ] Check raw posts marked `matched_to_game = TRUE`
- [ ] Verify engagement scores are reasonable (>0, <1000)
- [ ] Run cleanup job, verify old unmatched posts deleted

---

## Dependencies

### Upstream (Must Complete First)
- Story 4-1: Reddit Data Pipeline ✅
- Story 4-2: Bluesky Data Pipeline ✅
- Story 4-3: Game Matching Service ✅

### Downstream (Blocks These Stories)
- Story 4-5: Sentiment Analysis & Fact Table (reads `stg_social_posts`)

---

## Out of Scope

- ❌ Sentiment analysis (Story 4-5)
- ❌ Game key resolution (deferred to Story 4-5 for FK to fact_game)
- ❌ Advanced engagement normalization (cross-platform standardization) - simple platform-specific formulas sufficient
- ❌ Real-time streaming (batch hourly processing sufficient)

---

## Definition of Done

- [x] Alembic migration creates `stg_social_posts` TimescaleDB hypertable
- [x] `transform_social_posts` asset reads raw posts and applies GameMatcher
- [x] Posts with confidence < 0.6 are filtered out (not inserted)
- [x] Platform-specific engagement scores calculated correctly
- [x] Raw posts marked as processed (`matched_to_game`, `processed_at`)
- [x] Schedule runs hourly at :15, auto-starts on daemon init
- [x] Batch processing handles large volumes (1000 posts/batch)
- [x] Cleanup job (optional) deletes old unmatched raw posts
- [x] 500-1,500 matched posts in Week 2 (verified via SQL query)
- [x] Code reviewed and merged to main branch

---

## Notes

### Why Hourly Transform (Not Real-Time)?

Extraction runs every 5-10 minutes, but transform runs hourly to:
- **Reduce compute:** Single hourly batch vs 12 micro-batches
- **Improve efficiency:** GameMatcher loads teams cache once per run
- **Sufficient latency:** Epic 5 excitement scoring doesn't require sub-hour freshness

### Match Rate Expectations

Expected **30-50% of raw posts** match to games:
- Reddit /r/CollegeBasketball: 50-70% game-related (focused subreddit)
- Bluesky #CollegeBasketball: 20-40% game-related (broader hashtag usage)

If match rate < 20%:
- Lower confidence threshold (0.5 instead of 0.6)
- Expand team aliases with more variations

If match rate > 70%:
- Extraction is well-targeted, consider expanding sources

### Storage Savings from Cleanup

Unmatched posts deleted after 7 days:
- Daily raw posts: ~2,000
- Match rate: 40%
- Unmatched: 1,200 posts/day × 2 KB = 2.4 MB/day
- 83-day savings (90 - 7): ~200 MB

**Trade-off:** Lose raw data for future ML (can't retrain matcher on old data)
**Mitigation:** 7-day window allows manual review before deletion

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 2 (Epic 4 sprint)
