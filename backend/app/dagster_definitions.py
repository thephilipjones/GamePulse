"""
Dagster definitions for GamePulse data orchestration.

Registers assets, schedules, and resources for Dagster workspace.
"""

from dagster import (
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    in_process_executor,
    load_assets_from_modules,
)

from app.assets import bluesky_posts as bluesky_posts_module
from app.assets import ncaa_games as ncaa_games_module
from app.assets import reddit_posts as reddit_posts_module
from app.assets import transform_social_posts as transform_social_posts_module
from app.assets.bluesky_posts import bluesky_posts_job, bluesky_posts_schedule
from app.assets.reddit_posts import reddit_posts_job, reddit_posts_schedule
from app.resources.database import DatabaseResource

# Load all assets from assets module
all_assets = load_assets_from_modules(
    [
        ncaa_games_module,
        reddit_posts_module,
        bluesky_posts_module,
        transform_social_posts_module,
    ]
)

# Define asset job for manual materialization (NCAA)
ncaa_games_job = define_asset_job(
    name="materialize_ncaa_games",
    selection="ncaa_games",
    description="Manually materialize NCAA games asset",
)

# Reddit job and schedule imported from reddit_posts module

# Define schedule: every 1 minute (starts RUNNING automatically)
# RATIONALE: Schedule auto-starts on daemon initialization to ensure continuous
# game data ingestion during NCAA basketball season. The retry policy (3 attempts,
# exponential backoff: 2s, 4s, 8s) handles API failures gracefully, making
# auto-start safe. During off-season, materializations complete quickly with
# zero games (no API load). The 1-minute interval provides real-time feel for
# live sports while staying well below NCAA API rate limits (5 req/sec burst).
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    job=ncaa_games_job,
    cron_schedule="* * * * *",  # Every 1 minute - real-time feel for live sports
    description="Materialize NCAA games data every 1 minute",
    execution_timezone="America/New_York",  # NCAA games typically in Eastern Time
    default_status=DefaultScheduleStatus.RUNNING,  # Auto-start for continuous ingestion
)

# Initialize resources
database_resource = DatabaseResource()

# Dagster definitions
defs = Definitions(
    assets=all_assets,
    schedules=[ncaa_games_schedule, reddit_posts_schedule, bluesky_posts_schedule],
    resources={
        "database": database_resource,
    },
    jobs=[ncaa_games_job, reddit_posts_job, bluesky_posts_job],
    executor=in_process_executor,
)
