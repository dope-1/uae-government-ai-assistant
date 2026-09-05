from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.production.cache import CacheBackend, RedisJSONCache
from app.production.telemetry import TelemetryRegistry


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = cast(
        async_sessionmaker[AsyncSession],
        request.app.state.session_factory,
    )
    async with session_factory() as session:
        yield session


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_telemetry(request: Request) -> TelemetryRegistry:
    return cast(TelemetryRegistry, request.app.state.telemetry)


def get_cache(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedisJSONCache:
    return RedisJSONCache(
        cast(CacheBackend, get_redis(request)),
        namespace=settings.cache_namespace,
        version=settings.cache_version,
        ttl_seconds=settings.cache_ttl_seconds,
        enabled=settings.cache_enabled,
    )
