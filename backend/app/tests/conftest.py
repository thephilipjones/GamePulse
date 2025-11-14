from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

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
