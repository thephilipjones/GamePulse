#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations for application database
alembic upgrade head

# Create initial data in DB
python app/initial_data.py

# Seed/extend dim_date dimension table
if [ "${DIM_DATE_AUTO_SEED:-true}" = "true" ]; then
    echo "==================================================================="
    echo "Seeding/extending dim_date dimension table"
    echo "==================================================================="

    START_YEAR=${DIM_DATE_START_YEAR:-}
    END_YEAR=${DIM_DATE_END_YEAR:-}

    if [ -n "$START_YEAR" ] && [ -n "$END_YEAR" ]; then
        echo "Using custom date range: $START_YEAR to $END_YEAR"
        python -m app.scripts.seed_dim_date --start-year $START_YEAR --end-year $END_YEAR
    else
        echo "Using auto-detected date range (current_year - 1 to current_year + 2)"
        python -m app.scripts.seed_dim_date
    fi

    echo "==================================================================="
    echo "dim_date seeding complete"
    echo "==================================================================="
fi

# Initialize Dagster database if DAGSTER_POSTGRES_DB is set and differs from app DB
if [ ! -z "$DAGSTER_POSTGRES_DB" ] && [ "$DAGSTER_POSTGRES_DB" != "$POSTGRES_DB" ]; then
    echo "==================================================================="
    echo "Initializing Dagster database: $DAGSTER_POSTGRES_DB"
    echo "==================================================================="

    # Create dagster database if it doesn't exist
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '$DAGSTER_POSTGRES_DB'" | grep -q 1 || \
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d postgres -c \
        "CREATE DATABASE $DAGSTER_POSTGRES_DB" || \
    echo "Database $DAGSTER_POSTGRES_DB may already exist, continuing..."

    # Run Dagster schema migration
    echo "Running Dagster instance migration..."
    # Ensure DAGSTER_HOME is set and points to the config location
    export DAGSTER_HOME=${DAGSTER_HOME:-/tmp/dagster_home}

    if [ -f "$DAGSTER_HOME/dagster.yaml" ]; then
        dagster instance migrate || {
            echo "WARNING: Dagster migration failed. This may be expected if tables already exist."
            echo "Continuing with startup..."
        }
    else
        echo "WARNING: dagster.yaml not found at $DAGSTER_HOME/dagster.yaml"
        echo "Skipping Dagster migration. This may cause issues if Dagster tables don't exist."
    fi

    echo "==================================================================="
    echo "Dagster database initialization complete"
    echo "==================================================================="
fi
