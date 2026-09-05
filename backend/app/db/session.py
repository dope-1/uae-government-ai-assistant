from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.db.connection import prepare_asyncpg_connection


def create_engine(settings: Settings) -> AsyncEngine:
    database_url, connect_args = prepare_asyncpg_connection(settings.database_url)
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
