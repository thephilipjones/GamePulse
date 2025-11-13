from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models.dim_date import DimDate
from app.models.dim_team import DimTeam

# Create async engine for async tests
_async_db_uri = str(settings.SQLALCHEMY_DATABASE_URI).replace(
    "postgresql+psycopg", "postgresql+asyncpg"
)
async_engine = create_async_engine(
    _async_db_uri, echo=False, pool_pre_ping=True, poolclass=None
)
async_session_maker = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


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
    session.execute(delete(DimTeam))
    session.execute(delete(DimDate))
    session.flush()  # Make deletions visible within transaction

    yield session

    session.close()
    transaction.rollback()  # Rolls back all changes including deletions
    connection.close()


@pytest_asyncio.fixture(scope="function")
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session fixture for testing async operations.

    Uses async SQLAlchemy session with cleanup after each test.
    """
    async with async_session_maker() as session:
        # Delete seed data before test
        await session.execute(delete(DimTeam))
        await session.execute(delete(DimDate))
        await session.commit()

        yield session

        # Clean up after test
        await session.rollback()
        await session.execute(delete(DimTeam))
        await session.execute(delete(DimDate))
        await session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
