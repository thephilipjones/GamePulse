from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.db import engine
from app.main import app
from app.models import Item
from app.models.dim_team import DimTeam


@pytest.fixture(scope="function", autouse=True)
def db() -> Generator[Session, None, None]:
    """
    Function-scoped database session that cleans up test data after each test.

    Changed from session-scoped to function-scoped to ensure proper isolation
    between tests, especially for team_sync tests that create/modify teams.
    """
    with Session(engine) as session:
        # Clean up before test (remove any leftover data)
        session.execute(delete(DimTeam))
        session.execute(delete(Item))
        session.commit()

        yield session

        # Clean up after test
        session.rollback()  # Rollback any uncommitted changes
        session.execute(delete(DimTeam))
        session.execute(delete(Item))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
