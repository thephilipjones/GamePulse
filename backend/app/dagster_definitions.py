"""
Dagster definitions for GamePulse data orchestration.

Registers assets, schedules, and resources for Dagster workspace.
"""

from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    in_process_executor,
    load_assets_from_modules,
)

from app.assets import ncaa_games as ncaa_games_module
from app.resources.database import DatabaseResource

# Load all assets from assets module
all_assets = load_assets_from_modules([ncaa_games_module])

# Define asset job for manual materialization
ncaa_games_job = define_asset_job(
    name="materialize_ncaa_games",
    selection="ncaa_games",
    description="Manually materialize NCAA games asset",
)

# Define schedule: every 15 minutes
ncaa_games_schedule = ScheduleDefinition(
    name="ncaa_games_schedule",
    job=ncaa_games_job,
    cron_schedule="*/15 * * * *",  # Every 15 minutes
    description="Materialize NCAA games data every 15 minutes",
    execution_timezone="America/New_York",  # NCAA games typically in Eastern Time
)

# Initialize resources
database_resource = DatabaseResource()

# Dagster definitions
defs = Definitions(
    assets=all_assets,
    schedules=[ncaa_games_schedule],
    resources={
        "database": database_resource,
    },
    jobs=[ncaa_games_job],
    executor=in_process_executor,
)
