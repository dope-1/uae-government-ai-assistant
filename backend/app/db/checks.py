import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings
from app.db.connection import prepare_asyncpg_connection

Check = Callable[[], Awaitable[bool]]


async def check_postgres(settings: Settings) -> bool:
    engine: AsyncEngine | None = None
    try:
        database_url, connect_args = prepare_asyncpg_connection(settings.database_url)
        engine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        async with asyncio.timeout(settings.ready_check_timeout_seconds):
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT 1"))
                return bool(result.scalar_one() == 1)
    except Exception:
        return False
    finally:
        if engine is not None:
            await engine.dispose()


async def check_redis(settings: Settings) -> bool:
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.redis_url, decode_responses=True)
        try:
            async with asyncio.timeout(settings.ready_check_timeout_seconds):
                return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False
