# Story 4-5: Sentiment Analysis & Fact Table

**Epic:** Epic 4 - Social Media Data Ingestion via ELT Pattern
**Story ID:** 4-5
**Status:** review
**Estimated Effort:** 10-12 hours
**Priority:** High (Week 3 - enables Epic 5)
**Dependencies:** Story 4-4 (stg_social_posts), Epic 2 (fact_game, dim_date)

---

## User Story

**As a** data engineer,
**I want** to apply VADER sentiment analysis to social posts and create a fact table linked to games,
**So that** Epic 5 excitement scoring can query sentiment signals for NCAA basketball games.

---

## Context

This story completes the ELT pipeline by creating the **fact layer** for Epic 5 integration:

**Input:** `stg_social_posts` (game-matched, multi-platform posts)
**Processing:** VADER sentiment + game_key resolution
**Output:** `fact_social_sentiment` (sentiment scores linked to fact_game)

**VADER Sentiment:** Rule-based analyzer optimized for social media (handles slang, emojis, caps). 339x faster than transformers, good-enough accuracy for excitement scoring.

**Epic 5 Integration:** `fact_social_sentiment` provides social sentiment signal for excitement scoring algorithm, joining with `fact_game` and `fact_betting_odds`.

---

## Acceptance Criteria

### 1. Database Table - fact_social_sentiment

✅ **GIVEN** Alembic migrations are run
**WHEN** I check the database schema
**THEN** `fact_social_sentiment` table exists with columns:

- `sentiment_key` BIGSERIAL PRIMARY KEY
- `game_key` BIGINT REFERENCES fact_game(game_key)
- `date_key` INTEGER REFERENCES dim_date(date_key)
- `social_post_key` BIGINT REFERENCES stg_social_posts(social_post_key)
- `sentiment_compound` NUMERIC(5,4) (-1 to +1, overall score)
- `sentiment_positive` NUMERIC(5,4) (0-1, positive component)
- `sentiment_negative` NUMERIC(5,4) (0-1, negative component)
- `sentiment_neutral` NUMERIC(5,4) (0-1, neutral component)
- `platform` TEXT ('reddit' | 'bluesky')
- `post_text` TEXT (denormalized for Epic 5 queries)
- `created_at` TIMESTAMPTZ
- `engagement_score` NUMERIC(10,2) (denormalized)

**AND** table is a TimescaleDB hypertable partitioned on `created_at` (1-day chunks)
**AND** UNIQUE constraint on `social_post_key` (one sentiment per post)
**AND** indexes on `game_key`, `date_key`, `sentiment_compound`, `engagement_score`

### 2. Sentiment Analyzer Service

✅ **GIVEN** a SentimentAnalyzer instance
**WHEN** I call `analyze("Duke vs UNC was amazing! What a game!!!")`
**THEN** it returns:

```python
{
    "compound": 0.85,   # Overall sentiment (-1 to +1)
    "positive": 0.75,   # Positive component
    "negative": 0.05,   # Negative component
    "neutral": 0.20,    # Neutral component
}
```

**AND** compound score >= 0.05 indicates positive sentiment
**AND** compound score <= -0.05 indicates negative sentiment
**AND** handles emojis, caps, punctuation (!!!, ???)

### 3. Dagster Asset - calculate_sentiment

✅ **GIVEN** new posts exist in `stg_social_posts`
**WHEN** `calculate_sentiment` asset materializes
**THEN** it reads posts not yet in `fact_social_sentiment`
**AND** applies VADER sentiment analysis to each post
**AND** resolves `game_key` using `GameMatcher.resolve_game_key(matched_teams, game_date)`
**AND** resolves `date_key` from `fact_game`
**AND** inserts into `fact_social_sentiment` with all sentiment scores
**AND** returns metadata: `{posts_analyzed, posts_matched_to_game, posts_skipped_no_game}`

### 4. Game Key Resolution

✅ **GIVEN** a post with `matched_teams = ["duke", "unc"]` and `created_at = 2025-11-15 20:00`
**WHEN** game_key resolution runs
**THEN** it queries `fact_game` for Duke vs UNC on 2025-11-15
**AND** returns `game_key` if unique match found
**AND** returns NULL if no game found (post skipped)

**AND GIVEN** a post with `matched_teams = ["duke"]` (single team)
**THEN** it finds any Duke game on that date (home or away)

**AND GIVEN** a post with `matched_teams = []` or 3+ teams
**THEN** it returns NULL (ambiguous, post skipped)

### 5. Dagster Schedule - Hourly at :30

✅ **GIVEN** Dagster daemon is running
**WHEN** I view schedules in Dagster UI
**THEN** `calculate_sentiment_schedule` exists:

- Cron: `30 * * * *` (hourly at :30)
- Status: `RUNNING`
- Dependencies: Waits for `transform_social_posts` (:15)

**AND** schedule triggers 15 minutes after transform completes

### 6. Epic 5 Query Example

✅ **GIVEN** `fact_social_sentiment` is populated
**WHEN** Epic 5 runs this query:

```sql
SELECT
    g.game_id,
    g.home_team_name,
    g.away_team_name,
    COUNT(*) AS total_posts,
    AVG(s.sentiment_compound) AS avg_sentiment,
    SUM(s.engagement_score) AS total_engagement
FROM fact_game g
JOIN fact_social_sentiment s ON g.game_key = s.game_key
WHERE g.game_date = '2025-11-15'
GROUP BY g.game_key, g.game_id, g.home_team_name, g.away_team_name
ORDER BY total_engagement DESC;
```

**THEN** it returns aggregated sentiment and engagement for each game

### 7. Week 3 Success Metric

✅ **GIVEN** sentiment asset has run for 7 days
**WHEN** I query:

```sql
SELECT
    COUNT(*) AS total_sentiments,
    AVG(sentiment_compound) AS avg_compound,
    COUNT(DISTINCT game_key) AS games_with_sentiment
FROM fact_social_sentiment
WHERE created_at > NOW() - INTERVAL '7 days';
```

**THEN** results show:

- `total_sentiments`: 400-1,200 (80-90% of stg_social_posts matched to games)
- `avg_compound`: 0.1-0.3 (slightly positive, sports excitement)
- `games_with_sentiment`: 20-50 (games with social coverage)

---

## Technical Tasks

### Task 1: Database Migration - fact_social_sentiment Table

**File:** `backend/app/alembic/versions/{timestamp}_create_fact_social_sentiment.py`

**Implementation:**

```python
def upgrade() -> None:
    op.execute("""
        CREATE TABLE fact_social_sentiment (
            sentiment_key BIGSERIAL PRIMARY KEY,

            game_key BIGINT NOT NULL REFERENCES fact_game(game_key),
            date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
            social_post_key BIGINT NOT NULL REFERENCES stg_social_posts(social_post_key),

            sentiment_compound NUMERIC(5,4) NOT NULL,
            sentiment_positive NUMERIC(5,4),
            sentiment_negative NUMERIC(5,4),
            sentiment_neutral NUMERIC(5,4),

            platform TEXT NOT NULL,
            post_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            engagement_score NUMERIC(10,2),

            analyzed_at TIMESTAMPTZ DEFAULT NOW(),

            UNIQUE(social_post_key)
        );
    """)

    # TimescaleDB hypertable
    op.execute("""
        SELECT create_hypertable('fact_social_sentiment', 'created_at',
                                 chunk_time_interval => INTERVAL '1 day');
    """)

    # Indexes
    op.execute("CREATE INDEX idx_fact_sentiment_game_key ON fact_social_sentiment (game_key, created_at);")
    op.execute("CREATE INDEX idx_fact_sentiment_date_key ON fact_social_sentiment (date_key);")
    op.execute("CREATE INDEX idx_fact_sentiment_compound ON fact_social_sentiment (sentiment_compound, created_at);")
    op.execute("CREATE INDEX idx_fact_sentiment_engagement ON fact_social_sentiment (engagement_score DESC, sentiment_compound);")

    # Retention
    op.execute("SELECT add_retention_policy('fact_social_sentiment', INTERVAL '90 days');")

def downgrade() -> None:
    op.execute("DROP TABLE fact_social_sentiment CASCADE;")
```

---

### Task 2: SQLModel - FactSocialSentiment Model

**File:** `backend/app/models/social.py` (modify existing)

**Implementation:**

```python
class FactSocialSentiment(SQLModel, table=True):
    """Sentiment-enriched social posts linked to games for Epic 5."""

    __tablename__ = "fact_social_sentiment"

    sentiment_key: int | None = Field(default=None, primary_key=True)

    game_key: int = Field(foreign_key="fact_game.game_key")
    date_key: int = Field(foreign_key="dim_date.date_key")
    social_post_key: int = Field(foreign_key="stg_social_posts.social_post_key")

    sentiment_compound: float = Field(description="Overall sentiment (-1 to +1)")
    sentiment_positive: float | None = Field(default=None)
    sentiment_negative: float | None = Field(default=None)
    sentiment_neutral: float | None = Field(default=None)

    platform: str = Field(description="'reddit' | 'bluesky'")
    post_text: str = Field(description="Denormalized for Epic 5 queries")
    created_at: datetime
    engagement_score: float | None = Field(default=None)

    analyzed_at: datetime = Field(default_factory=datetime.now)
```

---

### Task 3: Sentiment Analyzer Service

**File:** `backend/app/services/sentiment_analyzer.py` (new file)

**Implementation:** See Epic 4 spec, section "Sentiment Analysis Integration"

**Key Features:**

- `SentimentAnalyzer` class using `vaderSentiment` library
- `analyze(text: str)` method returns compound + component scores
- `batch_analyze(texts: list[str])` for efficiency

**Dependencies:**

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "vaderSentiment>=3.3.2",
    # ... existing dependencies
]
```

**Installation:**

```bash
cd backend
uv add vaderSentiment
uv sync
```

---

### Task 4: Dagster Asset - calculate_sentiment

**File:** `backend/app/assets/social_sentiment.py` (new file)

**Implementation:** See Epic 4 spec, section "Dagster Asset Specifications > Asset 4: calculate_sentiment"

**Key Features:**

- Read new `stg_social_posts` (not yet in `fact_social_sentiment`)
- Apply `SentimentAnalyzer.analyze()` to each post
- Use `GameMatcher.resolve_game_key()` to link to fact_game
- Resolve `date_key` from fact_game
- Insert into `fact_social_sentiment`
- Skip posts with no game_key (log as `posts_skipped_no_game`)

---

### Task 5: Dagster Schedule Definition

**File:** `backend/app/assets/social_sentiment.py`

**Implementation:**

```python
calculate_sentiment_job = define_asset_job(
    name="materialize_calculate_sentiment",
    selection="calculate_sentiment",
)

calculate_sentiment_schedule = ScheduleDefinition(
    name="calculate_sentiment_schedule",
    job=calculate_sentiment_job,
    cron_schedule="30 * * * *",  # Hourly at :30
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
```

**Add to dagster_definitions.py:**

```python
from app.assets.social_sentiment import calculate_sentiment, calculate_sentiment_schedule

all_schedules = [
    # ... existing schedules
    calculate_sentiment_schedule,  # Add this
]
```

---

## Testing Requirements

### Unit Tests

**File:** `backend/app/tests/services/test_sentiment_analyzer.py`

**Test Cases:**

1. `test_analyze_positive_sentiment()` - "What an amazing game!"
2. `test_analyze_negative_sentiment()` - "Terrible refs, worst game ever"
3. `test_analyze_neutral_sentiment()` - "Duke vs UNC tonight at 7pm"
4. `test_analyze_handles_emojis()` - "LET'S GO 🔥🔥🔥"

**File:** `backend/app/tests/assets/test_calculate_sentiment.py`

**Test Cases:**

1. `test_sentiment_calculates_for_new_posts()` - Verify VADER scores
2. `test_game_key_resolution_two_teams()` - Verify FK linkage
3. `test_skips_posts_without_game_key()` - Verify NULL handling

---

## Dependencies

### Upstream (Must Complete First)

- Story 4-4: Unified Transform Layer (`stg_social_posts`) ✅
- Epic 2: `fact_game` table ✅
- Epic 2: `dim_date` table ✅

### Downstream (Enables)

- Epic 5: Moment Detection & Excitement Scoring (queries `fact_social_sentiment`)

---

## Out of Scope

- ❌ Transformer-based sentiment (VADER sufficient for portfolio)
- ❌ Custom sentiment training (rule-based only)
- ❌ Emotion detection (happiness, sadness, anger) - compound score only
- ❌ Sarcasm detection (VADER doesn't handle well)

---

## Definition of Done

- [x] Alembic migration creates `fact_social_sentiment` with FKs
- [x] `SentimentAnalyzer` service using vaderSentiment
- [x] `calculate_sentiment` asset analyzes posts and resolves game_key
- [x] Schedule runs hourly at :30, auto-starts
- [x] 400-1,200 sentiment records in Week 3
- [x] Epic 5 can query sentiment by game_key
- [x] Code reviewed and merged

---

## Notes

### VADER Score Interpretation

- **Compound >= 0.05:** Positive (excitement, enthusiasm)
- **Compound <= -0.05:** Negative (frustration, disappointment)
- **-0.05 to 0.05:** Neutral (informational)

### Game Resolution Failure Rate

Expected **10-20% of posts fail game_key resolution**:

- Generic posts ("Can't wait for March Madness!")
- Posts created days before game (date inference inaccurate)
- Multi-game days (ambiguous team mention)

**Mitigation:** Epic 5 aggregates across many posts, so losses are acceptable.

---

**Story Created:** 2025-11-15
**Story Owner:** Developer
**Estimated Completion:** End of Week 3 (Epic 4 sprint)

---

## Dev Agent Record

### Context Reference

- [4-5-sentiment-analysis-fact-table.context.xml](4-5-sentiment-analysis-fact-table.context.xml) - Generated 2025-11-16
