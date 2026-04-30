from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import HTTPConnection

from services.api.config import ApiSettings


class DatabaseUnavailableError(RuntimeError):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_engine_url: str | None = None


def get_session_factory(settings: ApiSettings) -> async_sessionmaker[AsyncSession]:
    global _engine, _session_factory, _engine_url
    if _session_factory is not None and _engine_url == settings.database_url:
        return _session_factory
    try:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    except ModuleNotFoundError as exc:
        raise DatabaseUnavailableError(f"database driver unavailable: {exc.name}") from exc
    except Exception as exc:
        raise DatabaseUnavailableError(f"database engine unavailable: {exc}") from exc
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    _engine_url = settings.database_url
    return _session_factory


async def get_db_session(connection: HTTPConnection) -> AsyncIterator[AsyncSession]:
    settings: ApiSettings = connection.app.state.settings
    try:
        session_factory = get_session_factory(settings)
    except DatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "down", "message": str(exc)},
        ) from exc

    async with session_factory() as session:
        yield session


async def close_database_engine() -> None:
    global _engine, _session_factory, _engine_url
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _engine_url = None
