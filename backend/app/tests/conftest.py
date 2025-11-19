from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models.dim_date import DimDate
from app.models.dim_team import DimTeam
from app.models.fact_game import FactGame
from app.models.reddit import RawRedditPost
from app.models.social import (
    FactSocialSentiment,
    RawBlueskyPost,
    StgSocialPost,
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
    # Order matters: delete child tables first to avoid foreign key violations
    session.execute(delete(FactSocialSentiment))  # Child of FactGame
    session.execute(delete(FactGame))  # Child of DimTeam, DimDate
    session.execute(delete(StgSocialPost))
    session.execute(delete(RawBlueskyPost))
    session.execute(delete(RawRedditPost))
    session.execute(delete(DimTeam))  # Parent table
    session.execute(delete(DimDate))  # Parent table
    session.flush()  # Make deletions visible within transaction

    yield session

    session.close()
    transaction.rollback()  # Rolls back all changes including deletions
    connection.close()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def client_with_db(db: Session) -> Generator[TestClient, None, None]:
    """
    TestClient that shares the test session with the app.

    Use this fixture when you need to create test data in the database
    and then access it through the API. The app's get_db dependency is
    overridden to return the test session, so both test code and app
    code see the same data (and changes are rolled back after each test).

    Example:
        def test_get_item(self, client_with_db: TestClient, db: Session):
            # Create test data
            item = Item(name="test")
            db.add(item)
            db.flush()

            # Access via API (will see the item)
            response = client_with_db.get(f"/items/{item.id}")
            assert response.status_code == 200
    """

    def get_test_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = get_test_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


# Async database fixtures for integration tests
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def async_engine() -> AsyncGenerator[Any, None]:
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
async def session(async_engine: Any) -> AsyncGenerator[AsyncSession, None]:
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
            # Order matters: delete child tables first to avoid foreign key violations
            await session.execute(delete(FactSocialSentiment))  # Child of FactGame
            await session.execute(delete(FactGame))  # Child of DimTeam, DimDate
            await session.execute(delete(StgSocialPost))
            await session.execute(delete(RawBlueskyPost))
            await session.execute(delete(RawRedditPost))
            await session.execute(delete(DimTeam))  # Parent table
            await session.execute(delete(DimDate))  # Parent table
            await session.flush()  # Make deletions visible within transaction

            yield session

            # Transaction automatically rolls back on context exit


@pytest_asyncio.fixture(scope="function")
async def _db(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for session fixture (backward compatibility).

    Some tests use _db instead of session - this alias maintains compatibility.
    """
    yield session
