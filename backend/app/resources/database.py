"""Dagster database resource for async PostgreSQL connections."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dagster import ConfigurableResource, InitResourceContext
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


class DatabaseResource(ConfigurableResource):  # type: ignore[type-arg]
    """Dagster resource for managing async database connections.

    Provides async SQLModel sessions for asset materializations.
    Uses postgresql+asyncpg for async operations.

    Note: Creates engine lazily per-process to support Dagster's multiprocess executor.
    """

    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None
    _pid: int | None = None  # Track which process created the engine

    def _ensure_engine(self) -> None:
        """Lazily create engine in current process if not already created."""
        current_pid = os.getpid()

        # Create new engine if we're in a new process or haven't created one yet
        if self._engine is None or self._pid != current_pid:
            # Convert postgresql+psycopg to postgresql+asyncpg for async operations
            db_uri = str(settings.SQLALCHEMY_DATABASE_URI)
            async_db_uri = db_uri.replace("postgresql+psycopg", "postgresql+asyncpg")

            self._engine = create_async_engine(
                async_db_uri,
                echo=False,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=3,  # Reduced for in-process executor (was 5)
                max_overflow=5,  # Reduced for in-process executor (was 10)
            )

            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._pid = current_pid

    @asynccontextmanager
    async def yield_for_execution(  # type: ignore[override]
        self, context: InitResourceContext
    ) -> AsyncGenerator["DatabaseResource", None]:
        """Async context manager for resource lifecycle with proper cleanup.

        This replaces teardown_after_execution to properly handle async engine
        disposal in the same event loop where the engine was created. This
        prevents "RuntimeError: got Future attached to a different loop" errors.

        Per SQLAlchemy docs: "It's advisable to invoke AsyncEngine.dispose()
        using await when the AsyncEngine will go out of context."
        """
        self._ensure_engine()
        try:
            yield self
        finally:
            # Dispose engine when execution completes
            if self._engine and self._pid == os.getpid():
                await self._engine.dispose()
                self._engine = None
                self._session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager providing an async database session.

        Usage in Dagster asset:
            async with database.get_session() as session:
                result = await session.execute(select(Team))
                teams = result.scalars().all()
        """
        self._ensure_engine()

        if not self._session_factory:
            raise RuntimeError("DatabaseResource engine initialization failed.")

        session: AsyncSession = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
