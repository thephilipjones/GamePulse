from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models.dim_date import DimDate
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Function-scoped database session with transaction rollback for isolation.

    Deletes seed data from Alembic migrations at the start of each test transaction,
    then uses transaction rollback for cleanup. This ensures tests are isolated from
    both seed data and each other's changes.
    Safe for parallel execution with pytest-xdist.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Delete seed data within this transaction to ensure clean state
    # Order matters: delete child tables (FactGame) before parent tables (DimTeam, DimDate)
    session.execute(delete(FactGame))
    session.execute(delete(DimTeam))
    session.execute(delete(DimDate))
    session.flush()  # Make deletions visible within transaction

    yield session

    session.close()
    transaction.rollback()  # Rolls back all changes including deletions
    connection.close()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


# Async database fixtures for integration tests
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine():
    """
    Session-scoped async engine for integration tests.

    Uses asyncpg driver and NullPool to prevent connection pool issues in tests.
    """
    async_db_uri = str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    engine = create_async_engine(
        async_db_uri,
        echo=False,
        poolclass=NullPool,  # Disable pooling for tests
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped async session with transaction rollback for isolation.

    Mirrors the sync 'db' fixture behavior:
    - Deletes seed data at start of each test
    - Uses transaction rollback for cleanup
    - Safe for parallel execution with pytest-xdist
    """
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        async with session.begin():
            # Delete seed data within this transaction to ensure clean state
            # Order matters: delete child tables (FactGame) before parent tables (DimTeam, DimDate)
            await session.execute(delete(FactGame))
            await session.execute(delete(DimTeam))
            await session.execute(delete(DimDate))
            await session.flush()  # Make deletions visible within transaction

            yield session

            # Transaction automatically rolls back on context exit


@pytest_asyncio.fixture(scope="function")
async def _db(session) -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for session fixture (backward compatibility).

    Some tests use _db instead of session - this alias maintains compatibility.
    """
    yield session
