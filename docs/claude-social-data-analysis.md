# Modern Data Stack Architecture for Sports Analytics ELT Pipeline

Your sports analytics project with NCAA game data and social sentiment is well-positioned to leverage modern data stack best practices. With Dagster already fetching NCAA API data into PostgreSQL/TimescaleDB, you're ready to extend this foundation with professional patterns that demonstrate strong data engineering competency.

## The modern data stack thrives on specialization

Each tool in your stack—Dagster, dbt, and potentially Airbyte—excels at a specific layer of the data lifecycle. **Dagster orchestrates and extracts**, **dbt transforms**, and **Airbyte moves data from external sources**. The key to success is respecting these boundaries while creating seamless integration between them. For your use case with existing Dagster extractors and PostgreSQL/TimescaleDB as your warehouse, the recommended pattern is unified orchestration: Dagster coordinates everything while delegating SQL transformations to dbt and optionally using Airbyte for external sources where pre-built connectors add value.

## Tool boundaries and responsibilities

**Dagster handles orchestration and extraction**. Its software-defined assets approach treats each data asset (table, model, ML output) as a first-class citizen with automatic dependency tracking. For your project, Dagster should continue extracting NCAA game data via API calls, coordinate when dbt models run, manage dependencies between ingestion and transformation, implement data quality monitoring with freshness policies, and handle retry logic for API failures. Dagster's asset-centric design means each dbt model becomes a separate observable asset, enabling granular monitoring and selective execution. Don't use Dagster for SQL transformations—while technically possible, this duplicates dbt's purpose and loses dbt's testing and documentation benefits.

**dbt owns all SQL transformations** after data lands in your warehouse. For sports analytics, dbt should create staging models that clean raw NCAA game data (standardize team names, fix data types, parse timestamps), build intermediate models that calculate game-level metrics (point differentials, shooting percentages, possession statistics), construct mart models that aggregate season statistics and rankings, and implement data quality tests ensuring referential integrity and business rule validation. dbt's strength is making transformation logic version-controlled, testable, and documented. Every transformation should live in dbt models using SELECT statements, with ref() functions creating automatic dependency graphs. Don't use dbt for data extraction—it expects data already loaded into the warehouse. Don't use dbt for complex orchestration—basic scheduling exists but Dagster provides superior workflow management.

**Airbyte specializes in external data movement** with 350+ pre-built connectors. For your social sentiment data, evaluate whether Airbyte adds value. Use Airbyte if you're pulling from platforms with existing connectors (Twitter/X if API access available, news APIs, established social platforms). However, **for Reddit and Bluesky, build custom extractors in Dagster**. Reddit's API isn't accepting applications, forcing JSON endpoint usage. Bluesky's AT Protocol is new with limited Airbyte support. Custom Dagster assets give you maximum flexibility for these non-standard sources while maintaining unified observability. The overhead of running Airbyte for just 1-2 custom connectors isn't justified when Dagster handles this natively.

## Integration architecture for your stack

**Recommended pattern: Dagster orchestrates dbt, with native ingestion**. This unified orchestration provides complete end-to-end visibility through Dagster's UI, automatic cross-tool dependency management, and single source of truth for data lineage. Dagster's DbtProjectComponent treats each dbt model as an individual asset, not a black-box task. You get model-level observability showing which specific transformations succeeded or failed, the ability to run subsets of models through Dagster's UI, and automatic dependency resolution between API extractions and dbt transformations.

**Implementation example**:

```python
# dagster_project/definitions.py
from dagster import asset, Definitions, AssetExecutionContext
from dagster_dbt import DbtProject, dbt_assets
import requests
from pathlib import Path

# 1. Custom NCAA API extractor (continues your existing pattern)
@asset(
    group_name="raw_sports",
    retry_policy=RetryPolicy(max_retries=3, delay=30)
)
def raw_ncaa_games(context: AssetExecutionContext) -> int:
    """Extract NCAA game data with watermarking"""
    watermark = get_watermark('ncaa_games')
    games = fetch_ncaa_api(since=watermark)

    # Idempotent load: delete overlapping range, insert new
    load_to_raw_table('raw.ncaa_games', games)
    update_watermark('ncaa_games', max(g['updated_at'] for g in games))

    context.log.info(f"Loaded {len(games)} games")
    return len(games)

# 2. Social sentiment extractors (custom Dagster assets)
@asset(group_name="raw_social")
def raw_reddit_posts(context: AssetExecutionContext) -> int:
    """Extract Reddit posts via JSON endpoints"""
    # Pagination with cursor tracking
    posts = fetch_reddit_json(subreddits=['CollegeBasketball', 'CFB'])
    load_to_raw_table('raw.reddit_posts', posts)
    return len(posts)

@asset(group_name="raw_social")
def raw_bluesky_posts(context: AssetExecutionContext) -> int:
    """Extract Bluesky posts via AT Protocol"""
    posts = fetch_bluesky_feed(hashtags=['MarchMadness', 'CFB'])
    load_to_raw_table('raw.bluesky_posts', posts)
    return len(posts)

# 3. dbt assets for transformations
dbt_project = DbtProject(project_dir=Path("dbt_project"))

@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project
)
def sports_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """All dbt models as Dagster assets"""
    yield from dbt.cli(["build"], context=context).stream()

# 4. Unified definitions
defs = Definitions(
    assets=[
        raw_ncaa_games,
        raw_reddit_posts,
        raw_bluesky_posts,
        sports_dbt_assets
    ],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)}
)
```

**dbt automatically inherits dependencies**. When you define sources in dbt pointing to your raw tables, Dagster infers that `raw_ncaa_games` must complete before staging models run. Use the source_key_prefix parameter to map dbt sources to Dagster assets systematically.

## ELT architecture patterns for your pipeline

**Structure your data flow in three tiers**. The raw/landing layer stores API responses exactly as received—no transformations. For NCAA games, Reddit posts, and Bluesky posts, write JSON or flattened records directly to raw schema tables. This preserves source data for debugging and enables reprocessing without hitting APIs again. **Critical principle**: never transform during extraction to avoid straining source systems and losing auditability.

**The staging layer lives in dbt** as your first transformation step. Staging models perform light cleaning and standardization without business logic. For NCAA games, this means casting data types, standardizing team names to match your dimension table, parsing ISO timestamps to PostgreSQL timestamp types, and renaming cryptic API fields to clear names. For social data, staging extracts common fields into a unified schema (detailed below). Name staging models with stg_ prefix and keep transformations simple and declarative.

**The marts layer implements business logic**. After staging creates clean, consistent foundations, mart models build analytics-ready datasets. For sports analytics, create fact tables like fct_game_results with calculated metrics (point differential, possession efficiency, shooting percentages) and dimension tables like dim_teams, dim_players, and dim_dates. For social sentiment, build fct_social_mentions linking posts to games via timestamps and keywords, calculate engagement scores and sentiment aggregations, and join social activity to game outcomes for correlation analysis.

**Folder structure for your project**:

```
sports_analytics/
├── dagster_project/
│   ├── definitions.py
│   ├── assets/
│   │   ├── ncaa_extractors.py      # NCAA game API
│   │   ├── reddit_extractors.py    # Reddit JSON endpoints
│   │   ├── bluesky_extractors.py   # Bluesky AT Protocol
│   │   └── dbt_assets.py           # dbt integration
│   ├── resources/
│   │   ├── api_clients.py          # API wrapper classes
│   │   └── database.py             # TimescaleDB connection
│   └── utils/
│       ├── rate_limiters.py        # Rate limiting logic
│       └── watermark.py            # Incremental state tracking
│
├── dbt_project/
│   ├── models/
│   │   ├── staging/
│   │   │   ├── ncaa/
│   │   │   │   ├── _sources.yml
│   │   │   │   ├── stg_ncaa_games.sql
│   │   │   │   └── stg_ncaa_teams.sql
│   │   │   └── social/
│   │   │       ├── _sources.yml
│   │   │       ├── stg_reddit_posts.sql
│   │   │       └── stg_bluesky_posts.sql
│   │   ├── intermediate/
│   │   │   ├── int_game_metrics.sql
│   │   │   └── int_social_unified.sql
│   │   └── marts/
│   │       ├── sports/
│   │       │   ├── fct_game_results.sql
│   │       │   └── dim_teams.sql
│   │       └── social/
│   │           └── fct_social_mentions.sql
│   ├── tests/
│   └── macros/
```

## Incremental loading for sports and social data

**Time-based partitioning works best for sports data**. NCAA games have natural date partitions (game dates), making date-based incremental loading straightforward. In Dagster, define daily partitions matching your expected data arrival. Extract games for specific date ranges, making backfills trivial—just reprocess historical partitions. In dbt, use incremental materialization with date filters to only process new games.

**Example incremental pattern in dbt**:

```sql
-- models/staging/ncaa/stg_ncaa_games.sql
{{
    config(
        materialized='incremental',
        unique_key='game_id',
        on_schema_change='append_new_columns'
    )
}}

SELECT
    game_id,
    game_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    updated_at
FROM {{ source('raw', 'ncaa_games') }}

{% if is_incremental() %}
-- 7-day lookback window for late-arriving game stat corrections
WHERE updated_at > (
    SELECT DATEADD(day, -7, MAX(updated_at)) FROM {{ this }}
)
{% endif %}
```

**For social media, implement cursor-based pagination** because posts arrive continuously. Reddit's JSON endpoints return after/before cursors for pagination. Bluesky's AT Protocol uses cursor tokens in feed responses. Store the last cursor value in a control table or use Dagster's partitioning to track state. Each extraction fetches posts since the last cursor, writes to raw tables with upsert logic (posts may be edited), and updates the cursor position. Handle deletions by tracking post IDs and marking deleted content rather than removing records (preserves historical sentiment analysis).

**Idempotency is non-negotiable**. Every pipeline stage must produce identical results when run multiple times with the same inputs. For sports data with natural keys (game_id), use MERGE/UPSERT operations. For time-series social data, use delete-write patterns scoped to specific time ranges. Example: when reprocessing Reddit posts from January 15, delete posts WHERE created_date = '2024-01-15' before inserting, ensuring no duplicates even if the pipeline reruns.

**Watermarking for production reliability**:

```python
# Store watermarks in control table
CREATE TABLE pipeline_watermarks (
    source_name VARCHAR(100) PRIMARY KEY,
    last_value TIMESTAMP,
    last_updated TIMESTAMP
)

# Extraction with watermarking
def extract_with_watermark(source_name: str, fetch_fn):
    watermark = get_watermark(source_name) or '2023-01-01'
    new_data = fetch_fn(since=watermark)

    if new_data:
        max_timestamp = max(item['timestamp'] for item in new_data)
        load_idempotently(source_name, new_data)
        update_watermark(source_name, max_timestamp)
```

## API rate limits and failure handling

**Reddit rate limits**: JSON endpoints allow ~100 requests per minute for unauthenticated access. Implement client-side rate limiting with request tracking. Use exponential backoff when encountering 429 responses, respecting Retry-After headers.

**Bluesky rate limits**: AT Protocol specifies limits per endpoint, typically 3000 requests per 5-minute window for authenticated clients. The platform returns rate limit headers (RateLimit-Remaining, RateLimit-Reset) to guide throttling.

**Comprehensive error handling pattern**:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import time

@retry(
    retry=retry_if_exception_type((ConnectionError, Timeout)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
def fetch_with_retry(url, session):
    response = session.get(url, timeout=30)

    # Rate limiting
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        raise ConnectionError("Rate limited")

    # Server errors are transient
    if response.status_code >= 500:
        raise ConnectionError(f"Server error: {response.status_code}")

    # Client errors are permanent
    if 400 <= response.status_code < 500:
        raise ValueError(f"Client error: {response.status_code}")

    return response.json()
```

**Rate limiter implementation**:

```python
from collections import deque
import time

class RateLimiter:
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()

    def wait_if_needed(self):
        now = time.time()

        # Remove expired requests
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()

        # Wait if at limit
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0])
            time.sleep(sleep_time)

        self.requests.append(now)
```

## Unified schema for social sentiment data

**Design a schema that accommodates both platforms** while preserving unique features. Use a base fact table with common fields plus platform-specific JSON columns for flexibility.

**Core unified schema**:

```sql
-- Unified social media posts table
CREATE TABLE staging.social_posts (
    post_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,  -- 'reddit', 'bluesky'
    author_id VARCHAR(255),
    author_username VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    content_text TEXT,
    content_url TEXT,

    -- Standardized engagement (normalized for cross-platform comparison)
    engagement_score INTEGER,  -- Composite score
    engagement_upvotes INTEGER,
    engagement_downvotes INTEGER,
    engagement_comments INTEGER,
    engagement_shares INTEGER,

    -- Platform-specific data as JSONB
    platform_metadata JSONB,

    -- Classification
    detected_topics TEXT[],
    sentiment_score FLOAT,
    is_game_related BOOLEAN,
    related_game_ids TEXT[],

    -- Metadata
    extracted_at TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create TimescaleDB hypertable for time-series queries
SELECT create_hypertable('staging.social_posts', 'created_at');
```

**Mapping platform-specific fields**:

**Reddit to unified schema**:
- post_id ← `id` (Reddit's unique identifier)
- author_username ← `author`
- created_at ← `created_utc` (convert Unix timestamp)
- content_text ← `title` + `selftext` (concatenate for full content)
- engagement_upvotes ← `ups`
- engagement_downvotes ← `downs`
- engagement_comments ← `num_comments`
- platform_metadata ← `{awards: [], subreddit: "...", permalink: "...", gilded: 0, controversiality: ...}`

**Bluesky to unified schema**:
- post_id ← `uri` (AT Protocol URI)
- author_id ← `author.did`
- author_username ← `author.handle`
- created_at ← `createdAt`
- content_text ← `record.text`
- engagement_upvotes ← `likeCount`
- engagement_shares ← `repostCount` + `quoteCount`
- engagement_comments ← `replyCount`
- platform_metadata ← `{facets: [], embed: {...}, labels: []}`

**Staging models in dbt**:

```sql
-- models/staging/social/stg_reddit_posts.sql
SELECT
    id AS post_id,
    'reddit' AS platform,
    author AS author_username,
    TO_TIMESTAMP(created_utc) AS created_at,
    COALESCE(title || ' ' || selftext, title) AS content_text,
    ups AS engagement_upvotes,
    downs AS engagement_downvotes,
    num_comments AS engagement_comments,
    (ups - downs + num_comments) AS engagement_score,
    JSON_BUILD_OBJECT(
        'subreddit', subreddit,
        'permalink', permalink,
        'awards', awards,
        'gilded', gilded
    )::JSONB AS platform_metadata
FROM {{ source('raw', 'reddit_posts') }}
WHERE id IS NOT NULL

-- models/staging/social/stg_bluesky_posts.sql
SELECT
    uri AS post_id,
    'bluesky' AS platform,
    author_handle AS author_username,
    created_at::TIMESTAMP AS created_at,
    record_text AS content_text,
    like_count AS engagement_upvotes,
    0 AS engagement_downvotes,
    reply_count AS engagement_comments,
    (like_count + repost_count * 2 + reply_count) AS engagement_score,
    JSON_BUILD_OBJECT(
        'repost_count', repost_count,
        'quote_count', quote_count,
        'facets', facets
    )::JSONB AS platform_metadata
FROM {{ source('raw', 'bluesky_posts') }}
WHERE uri IS NOT NULL
```

**Unified intermediate model**:

```sql
-- models/intermediate/int_social_unified.sql
WITH reddit AS (
    SELECT * FROM {{ ref('stg_reddit_posts') }}
),
bluesky AS (
    SELECT * FROM {{ ref('stg_bluesky_posts') }}
),
combined AS (
    SELECT * FROM reddit
    UNION ALL
    SELECT * FROM bluesky
)
SELECT
    *,
    -- Game detection logic
    CASE
        WHEN content_text ~* '(NCAA|college basketball|march madness|final four)'
        THEN TRUE
        ELSE FALSE
    END AS is_game_related,

    -- Extract team mentions
    REGEXP_MATCHES(content_text, team_pattern, 'gi') AS mentioned_teams
FROM combined
```

**Handling platform-specific features**: Keep unique platform attributes in the platform_metadata JSONB column. This allows querying Reddit-specific features (awards, gilded counts, controversiality) without cluttering the main schema. When analyzing Reddit posts specifically, extract from JSONB: `platform_metadata->>'subreddit'`. Similarly, Bluesky's facets (mentions, hashtags, links) and embedded media live in platform_metadata for platform-specific analysis while maintaining a clean unified schema for cross-platform queries.

## TimescaleDB-specific optimizations

**Leverage hypertables for time-series sports data**. Game results and social posts are inherently time-series. Convert these tables to hypertables to enable automatic time-based partitioning, fast time-range queries, and compression.

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert tables to hypertables
SELECT create_hypertable('staging.ncaa_games', 'game_date',
    chunk_time_interval => INTERVAL '1 week');

SELECT create_hypertable('staging.social_posts', 'created_at',
    chunk_time_interval => INTERVAL '1 day');
```

**Implement continuous aggregates** for frequently queried metrics. Sports analytics involves repeated aggregations (season statistics, player averages, daily social mention counts). Continuous aggregates pre-compute these as materialized views that refresh automatically.

**Example in dbt with post-hooks**:

```sql
-- models/marts/sports/daily_game_stats.sql
{{
    config(
        materialized='view',
        post_hook=[
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS daily_game_stats_cagg
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 day', game_date) AS day,
                home_team_id,
                COUNT(*) AS games_played,
                AVG(home_score - away_score) AS avg_point_differential
            FROM {{ this }}
            GROUP BY day, home_team_id
            """,
            """
            SELECT add_continuous_aggregate_policy('daily_game_stats_cagg',
                start_offset => INTERVAL '7 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour')
            """
        ]
    )
}}
```

**Apply compression for older data**. TimescaleDB's columnar compression achieves 90-98% storage reduction for time-series data. Compress data older than 7-14 days that's queried less frequently.

```sql
ALTER TABLE staging.social_posts SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'platform',
    timescaledb.compress_orderby = 'created_at DESC'
);

SELECT add_compression_policy('staging.social_posts',
    compress_after => INTERVAL '14 days');
```

**Set retention policies** to automatically drop old raw data while preserving aggregates. Keep raw social posts for 90 days, continuous aggregates for 2+ years.

```sql
SELECT add_retention_policy('staging.social_posts',
    drop_after => INTERVAL '90 days');
```

**Optimize queries with time_bucket**: TimescaleDB's time_bucket function efficiently groups time-series data into intervals. Use this for all temporal aggregations.

```sql
-- Daily social mention counts by platform
SELECT
    time_bucket('1 day', created_at) AS day,
    platform,
    COUNT(*) AS post_count,
    AVG(engagement_score) AS avg_engagement
FROM staging.social_posts
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY day, platform
ORDER BY day DESC;
```

## Testing and data quality checks

**Implement testing at three levels**. Unit tests verify transformation logic in Python functions. Integration tests validate end-to-end pipeline flows. Data quality tests catch data anomalies and schema violations.

**dbt tests for data quality**:

```yaml
# models/staging/ncaa/schema.yml
models:
  - name: stg_ncaa_games
    description: "Cleaned NCAA game results"
    tests:
      - dbt_utils.recency:
          datepart: day
          field: game_date
          interval: 2
    columns:
      - name: game_id
        tests:
          - unique
          - not_null
      - name: home_team_id
        tests:
          - not_null
          - relationships:
              to: ref('dim_teams')
              field: team_id
      - name: home_score
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 200
```

**Custom dbt tests for sports logic**:

```sql
-- tests/assert_score_differential_matches.sql
-- Validate calculated fields
SELECT
    game_id,
    home_score,
    away_score,
    point_differential,
    (home_score - away_score) AS expected_differential
FROM {{ ref('fct_game_results') }}
WHERE point_differential != (home_score - away_score)
```

**Great Expectations for statistical validation**:

```python
import great_expectations as gx

context = gx.get_context()
suite = context.add_expectation_suite("social_posts_quality")

validator = context.get_validator(
    datasource_name="timescale",
    data_asset_name="staging.social_posts"
)

# Statistical expectations
validator.expect_column_values_to_not_be_null("post_id")
validator.expect_column_values_to_be_unique("post_id")
validator.expect_column_mean_to_be_between("engagement_score",
    min_value=0, max_value=1000)
validator.expect_column_values_to_be_in_set("platform",
    ["reddit", "bluesky"])

# Custom business logic
validator.expect_column_pair_values_a_to_be_greater_than_b(
    column_A="updated_at", column_B="created_at")
```

**Dagster asset checks** for freshness and volume:

```python
from dagster import asset_check, AssetCheckResult

@asset_check(asset=raw_ncaa_games)
def check_ncaa_games_freshness() -> AssetCheckResult:
    """Verify game data is less than 24 hours old"""
    max_timestamp = get_max_timestamp('raw.ncaa_games', 'updated_at')
    age_hours = (datetime.now() - max_timestamp).total_seconds() / 3600

    return AssetCheckResult(
        passed=age_hours < 24,
        metadata={"age_hours": age_hours}
    )

@asset_check(asset=raw_reddit_posts)
def check_reddit_volume() -> AssetCheckResult:
    """Detect volume anomalies"""
    recent_count = get_row_count_last_24h('raw.reddit_posts')
    avg_count = get_avg_daily_count('raw.reddit_posts', days=7)

    is_normal = 0.5 * avg_count <= recent_count <= 2.0 * avg_count

    return AssetCheckResult(
        passed=is_normal,
        metadata={
            "recent_count": recent_count,
            "avg_count": avg_count
        }
    )
```

## Production best practices for portfolio impact

**Demonstrate professional data engineering** through these practices that set your project apart:

**1. Comprehensive documentation**. Write a README that immediately communicates your technical depth. Include an architecture diagram showing data flow from APIs through Dagster to TimescaleDB to dbt transformations. Document your design decisions in Architecture Decision Records (ADRs)—why you chose Dagster over Airflow, why custom extractors instead of Airbyte, how you designed the unified social schema. Add a "Lessons Learned" section reflecting on challenges and solutions.

**2. CI/CD pipeline**. Set up GitHub Actions to run dbt tests on every pull request, execute unit tests for Python extraction code, validate SQL compilation without deployment, and deploy to production only after manual approval. This shows you understand production deployment patterns.

```yaml
# .github/workflows/ci.yml
name: Data Pipeline CI
on: pull_request

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run pytest
        run: pytest tests/
      - name: Run dbt tests
        run: |
          cd dbt_project
          dbt deps
          dbt build --target dev
        env:
          DB_HOST: ${{ secrets.DEV_DB_HOST }}
```

**3. Observable data lineage**. Use Dagster's asset lineage graph to visualize dependencies. In dbt, document every model with descriptions explaining purpose and business logic. Use dbt's built-in lineage to show how raw data flows through staging to marts. Add column-level documentation explaining metric calculations.

**4. Monitoring and alerting**. Create a Grafana dashboard showing pipeline health metrics: job success rates, data freshness by source, row counts over time, API rate limit utilization, and query performance. Even without active monitoring, having dashboards demonstrates operational thinking. In Dagster, define freshness policies on critical assets.

**5. Performance optimization documentation**. Benchmark key operations and document optimizations. Show TimescaleDB query performance before/after hypertable conversion, compression ratios achieved on social data, and continuous aggregate speedup for common queries. Include query plans (EXPLAIN ANALYZE) for complex queries demonstrating understanding of database optimization.

**6. Error handling and logging**. Every API call should have retry logic with exponential backoff. Log structured JSON for easy parsing. Handle edge cases explicitly—missing fields, malformed responses, null values. Show defensive programming throughout.

**7. Data quality as a first-class concern**. Don't just test that code runs—test that data is correct. Implement schema validation on API responses, business rule validation in dbt, statistical anomaly detection with Great Expectations, and referential integrity checks between related tables. Document your data quality framework in the README.

**8. Security and configuration management**. Never commit credentials. Use environment variables for sensitive configuration. Include a .env.example file showing required variables without values. Use secrets management (even if just local .env files) to demonstrate security awareness.

**9. Modular, reusable code**. Extract common patterns into utility functions—API clients, rate limiters, watermark managers. In dbt, create reusable macros for common transformations. Show you write DRY (Don't Repeat Yourself) code rather than copying-and-pasting.

**10. Clear code organization**. Follow the folder structure outlined earlier with clear separation between extraction, transformation, and analysis layers. Name files and functions descriptively. Add docstrings explaining purpose, parameters, and return values. Format code consistently using Black for Python and SQLFluff for SQL.

## Practical implementation roadmap

**Week 1-2: Foundation**. Continue using your existing Dagster NCAA extractor. Add watermarking for incremental loads. Set up dbt project with staging models for NCAA data. Create TimescaleDB hypertables. Write initial documentation.

**Week 3-4: Social data integration**. Build Reddit extractor in Dagster with JSON endpoint pagination. Build Bluesky extractor with AT Protocol integration. Implement unified social schema in staging models. Add data quality tests for both platforms.

**Week 5-6: Transformations and analytics**. Build intermediate models calculating game metrics and unified social posts. Create mart models joining games to social mentions. Implement sentiment detection or game correlation analysis. Add continuous aggregates for common time-series queries.

**Week 7-8: Production polish**. Add comprehensive testing (unit, integration, data quality). Set up CI/CD pipeline. Create monitoring dashboards. Write ADRs documenting key decisions. Record demo video. Deploy live demo if possible. Write blog post explaining your approach.

## Key takeaways

**Respect tool boundaries**: Dagster orchestrates and extracts, dbt transforms with SQL, and you use native Dagster assets instead of Airbyte for custom APIs. This separation creates maintainable, testable pipelines.

**Design for idempotency from day one**. Use watermarking for incremental extraction, delete-write patterns for time-partitioned data, and upsert logic for data with natural keys. Every pipeline stage should safely support reruns.

**Leverage TimescaleDB for time-series optimization**. Sports game data and social posts are naturally time-series. Hypertables enable efficient partitioning, continuous aggregates pre-compute common metrics, and compression reduces storage costs dramatically.

**Build a unified schema for heterogeneous sources**. Create a common structure for Reddit and Bluesky posts with standardized engagement metrics while preserving platform-specific features in JSONB columns. This enables cross-platform analysis without losing platform nuances.

**Make quality visible**. Implement dbt tests for business rules, Great Expectations for statistical validation, Dagster asset checks for freshness and volume, and monitoring dashboards showing data health. Data quality isn't an afterthought—it's a core feature.

**Document for humans**. Write README, ADRs, code comments, and dbt model descriptions as if your future employer will read them (they will). Explain not just what your code does but why you made specific design choices. Demonstrate clear thinking and communication.

**Show production readiness**. CI/CD pipeline, error handling, logging, monitoring, security practices, and performance optimization distinguish hobby projects from portfolio pieces that demonstrate professional competency. These practices signal you understand real-world data engineering challenges.

Your sports analytics project with NCAA data and social sentiment offers a perfect canvas for demonstrating modern data stack expertise. By following these patterns—unified orchestration with Dagster, SQL transformations in dbt, custom extractors for non-standard sources, TimescaleDB optimizations for time-series data, and production-grade practices throughout—you'll create a portfolio project that clearly demonstrates data engineering competency to hiring managers.
