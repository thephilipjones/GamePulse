"""
Dagster definitions for GamePulse data orchestration.

Registers assets, schedules, and resources for Dagster workspace.
"""

from dagster import (
    DefaultScheduleStatus,
    Definitions,
    RunRequest,
    ScheduleEvaluationContext,
    SkipReason,
    define_asset_job,
    in_process_executor,
    load_assets_from_modules,
    schedule,
)
from dagster._core.storage.dagster_run import DagsterRunStatus, RunsFilter

from app.assets import bluesky_posts as bluesky_posts_module
from app.assets import cleanup_raw_posts as cleanup_raw_posts_module
from app.assets import ncaa_games as ncaa_games_module
from app.assets import quality_checks as quality_checks_module
from app.assets import reddit_posts as reddit_posts_module
from app.assets import social_sentiment as social_sentiment_module
from app.assets import transform_social_posts as transform_social_posts_module
from app.assets.bluesky_posts import bluesky_posts_job, extract_bluesky_posts_schedule
from app.assets.cleanup_raw_posts import (
    cleanup_unmatched_posts_job,
    cleanup_unmatched_posts_schedule,
)
from app.assets.reddit_posts import extract_reddit_posts_schedule, reddit_posts_job
from app.resources.database import DatabaseResource

# Load all assets from assets module
all_assets = load_assets_from_modules(
    [
        ncaa_games_module,
        reddit_posts_module,
        bluesky_posts_module,
        transform_social_posts_module,
        social_sentiment_module,
        cleanup_raw_posts_module,  # Cleanup old unmatched posts (Story 4-7)
        quality_checks_module,  # Asset checks for data quality monitoring (Story 4-7)
    ]
)

# Define asset job for manual materialization (NCAA)
ncaa_games_job = define_asset_job(
    name="materialize_ncaa_games",
    selection="ncaa_games",
    description="Manually materialize NCAA games asset",
)

# Reddit and Bluesky jobs and schedules imported from their modules

# Define sentiment analysis job for manual materialization (Story 4-5)
# NOTE: Auto-materialize policy triggers this automatically when transform_social_posts completes
calculate_sentiment_job = define_asset_job(
    name="materialize_calculate_sentiment",
    selection="calculate_sentiment",
    description="Analyze sentiment of social posts and link to games",
)


# Define NCAA games schedule: every 1 minute (starts RUNNING automatically)
# RATIONALE: Schedule auto-starts on daemon initialization to ensure continuous
# game data ingestion during NCAA basketball season. The retry policy (3 attempts,
# exponential backoff: 2s, 4s, 8s) handles API failures gracefully, making
# auto-start safe. During off-season, materializations complete quickly with
# zero games (no API load). The 1-minute interval provides real-time feel for
# live sports while staying well below NCAA API rate limits (5 req/sec burst).
@schedule(
    job=ncaa_games_job,
    cron_schedule="* * * * *",  # Every 1 minute - real-time feel for live sports
    execution_timezone="America/New_York",  # NCAA games typically in Eastern Time
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start for continuous ingestion
)
def ncaa_games_schedule(context: ScheduleEvaluationContext) -> RunRequest | SkipReason:
    """
    Schedule NCAA games materialization every minute.
    Skips if there are already queued or running runs for this job.
    """
    job_name = "materialize_ncaa_games"

    # Check for queued or running runs for this specific job
    filters = RunsFilter(
        statuses=[DagsterRunStatus.QUEUED, DagsterRunStatus.STARTED],
        job_name=job_name,
    )
    existing_runs = context.instance.get_runs_count(filters=filters)

    if existing_runs > 0:
        return SkipReason(
            f"Skipping: {existing_runs} run(s) already queued or running for {job_name}"
        )

    return RunRequest()


# Initialize resources
database_resource = DatabaseResource()

# Dagster definitions
defs = Definitions(
    assets=all_assets,
    schedules=[
        ncaa_games_schedule,
        extract_reddit_posts_schedule,
        extract_bluesky_posts_schedule,
        cleanup_unmatched_posts_schedule,  # Daily cleanup of old unmatched posts (Story 4-7)
    ],
    resources={
        "database": database_resource,
    },
    jobs=[
        ncaa_games_job,
        reddit_posts_job,
        bluesky_posts_job,
        calculate_sentiment_job,  # Manual materialization only (auto-materialize policy)
        cleanup_unmatched_posts_job,  # Manual cleanup trigger (also runs daily via schedule)
    ],
    executor=in_process_executor,
)
