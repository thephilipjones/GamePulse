from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import engine
from app.main import app


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Function-scoped database session with transaction rollback for isolation.

    Uses transaction rollback instead of DELETE statements for better performance.
    Each test gets a fresh transaction that is rolled back after completion.
    Safe for parallel execution with pytest-xdist.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
