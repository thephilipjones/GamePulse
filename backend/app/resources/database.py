"""Dagster database resource for async PostgreSQL connections."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dagster import ConfigurableResource
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


class DatabaseResource(ConfigurableResource):
    """Dagster resource for managing async database connections.

    Provides async SQLModel sessions for asset materializations.
    Uses postgresql+asyncpg for async operations.

    Note: Creates engine lazily per-process to support Dagster's multiprocess executor.
    """

    _engine: AsyncEngine | None = None
    _session_factory: sessionmaker | None = None
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

            self._session_factory = sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            self._pid = current_pid

    def teardown_after_execution(self, context) -> None:
        """Dispose of async engine when resource is unloaded."""
        if self._engine and self._pid == os.getpid():
            import asyncio

            # Only dispose if we're in the same process that created it
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Can't run sync in async context, engine will be garbage collected
                    pass
                else:
                    asyncio.run(self._engine.dispose())
            except Exception:
                # Best effort cleanup
                pass

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
