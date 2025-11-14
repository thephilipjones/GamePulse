FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

# Install PostgreSQL client for database operations in prestart script
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/app

# Copy configuration files (change less frequently than app code)
COPY ./pyproject.toml ./uv.lock ./alembic.ini ./workspace.yaml /app/

# Create DAGSTER_HOME directory for Dagster metadata storage
RUN mkdir -p /tmp/dagster_home

# Copy Dagster configuration to DAGSTER_HOME
COPY ./dagster_home/dagster.yaml /tmp/dagster_home/dagster.yaml

# Copy application code (changes most frequently)
COPY ./app /app/app

# Copy scripts (change rarely, placed after app for better layer caching)
COPY ./scripts /app/scripts

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
