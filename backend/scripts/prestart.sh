#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations for application database
alembic upgrade head

# Create initial data in DB
python app/initial_data.py

# Initialize Dagster database if DAGSTER_POSTGRES_DB is set and differs from app DB
if [ ! -z "$DAGSTER_POSTGRES_DB" ] && [ "$DAGSTER_POSTGRES_DB" != "$POSTGRES_DB" ]; then
    echo "==================================================================="
    echo "Initializing Dagster database: $DAGSTER_POSTGRES_DB"
    echo "==================================================================="

    # Create dagster database if it doesn't exist
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d postgres -c "
        SELECT 'CREATE DATABASE $DAGSTER_POSTGRES_DB'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DAGSTER_POSTGRES_DB')\gexec
    " || echo "Database $DAGSTER_POSTGRES_DB may already exist, continuing..."

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
