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

# Define asset jobs for NCAA games (Story 4-11: Split into today vs window)
ncaa_games_today_job = define_asset_job(
    name="materialize_ncaa_games_today",
    selection="ncaa_games_today",
    description="Materialize NCAA games for today only (live updates)",
)

ncaa_games_window_job = define_asset_job(
    name="materialize_ncaa_games_window",
    selection="ncaa_games_window",
    description="Materialize NCAA games for 7 days historical + 7 days future",
)

# Reddit and Bluesky jobs and schedules imported from their modules

# Define sentiment analysis job for manual materialization (Story 4-5)
# NOTE: Auto-materialize policy triggers this automatically when transform_social_posts completes
calculate_sentiment_job = define_asset_job(
    name="materialize_calculate_sentiment",
    selection="calculate_sentiment",
    description="Analyze sentiment of social posts and link to games",
)


# Define NCAA games schedule: every 15 minutes for today's games (live updates)
# RATIONALE: 15-minute interval provides timely live score updates while being
# API-friendly. Historical and future games are handled by the window schedule
# (runs daily) since they don't change frequently.
@schedule(
    job=ncaa_games_today_job,
    cron_schedule="*/15 * * * *",  # Every 15 minutes
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
def ncaa_games_today_schedule(
    context: ScheduleEvaluationContext,
) -> RunRequest | SkipReason:
    """
    Schedule NCAA today's games materialization every 15 minutes.
    Skips if there are already queued or running runs for this job.
    """
    job_name = "materialize_ncaa_games_today"

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


# Define NCAA games window schedule: once daily at 6 AM
# Fetches historical (7 days back) and future (7 days forward) games
@schedule(
    job=ncaa_games_window_job,
    cron_schedule="0 6 * * *",  # Daily at 6:00 AM Eastern
    execution_timezone="America/New_York",
    default_status=DefaultScheduleStatus.RUNNING,
)
def ncaa_games_window_schedule(
    _context: ScheduleEvaluationContext,
) -> RunRequest | SkipReason:
    """
    Schedule NCAA historical/future games window materialization once daily.
    Runs at 6 AM to populate yesterday's games and upcoming week.
    """
    return RunRequest()


# Initialize resources
database_resource = DatabaseResource()

# Dagster definitions
defs = Definitions(
    assets=all_assets,
    schedules=[
        ncaa_games_today_schedule,  # Every 15 min for live updates
        ncaa_games_window_schedule,  # Daily at 6 AM for historical/future
        extract_reddit_posts_schedule,
        extract_bluesky_posts_schedule,
        cleanup_unmatched_posts_schedule,  # Daily cleanup of old unmatched posts (Story 4-7)
    ],
    resources={
        "database": database_resource,
    },
    jobs=[
        ncaa_games_today_job,
        ncaa_games_window_job,
        reddit_posts_job,
        bluesky_posts_job,
        calculate_sentiment_job,  # Manual materialization only (auto-materialize policy)
        cleanup_unmatched_posts_job,  # Manual cleanup trigger (also runs daily via schedule)
    ],
    executor=in_process_executor,
)
