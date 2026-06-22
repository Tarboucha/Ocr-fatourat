from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# --- Sync session for the Celery worker -------------------------------------
# Celery tasks are sync; running async SQLAlchemy inside them is a footgun, so
# the worker uses a plain sync engine/session. Created lazily so the async API
# process never opens a sync pool.
_sync_engine = None
_SyncSessionLocal = None


def get_sync_sessionmaker():
    global _sync_engine, _SyncSessionLocal
    if _SyncSessionLocal is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        _sync_engine = create_engine(
            settings.sync_database_url, echo=False, pool_pre_ping=True
        )
        _SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)
    return _SyncSessionLocal
