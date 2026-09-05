from __future__ import annotations

from typing import Any

import pytest

from app.production.cache import RedisJSONCache


class FakeCacheBackend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiry: dict[str, int] = {}

    async def get(self, key: str) -> Any:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> Any:
        self.values[key] = value
        self.expiry[key] = ex
        return True


class FailingCacheBackend:
    async def get(self, key: str) -> Any:
        del key
        raise RuntimeError("redis down")

    async def set(self, key: str, value: str, *, ex: int) -> Any:
        del key, value, ex
        raise RuntimeError("redis down")


@pytest.mark.asyncio
async def test_cache_key_is_deterministic_and_hides_raw_query() -> None:
    backend = FakeCacheBackend()
    cache = RedisJSONCache(
        backend,
        namespace="uae",
        version="v1",
        ttl_seconds=300,
    )
    payload = {"message": "Does the UAE Golden Visa require a sponsor?", "jurisdiction": "Federal"}
    first = cache.make_key("chat", payload)
    second = cache.make_key("chat", dict(reversed(list(payload.items()))))
    assert first == second
    assert "Golden Visa" not in first
    assert first.startswith("uae:v1:chat:")


@pytest.mark.asyncio
async def test_cache_round_trip_uses_ttl() -> None:
    backend = FakeCacheBackend()
    cache = RedisJSONCache(backend, namespace="uae", version="v1", ttl_seconds=123)
    key = cache.make_key("chat", {"message": "hello"})
    assert await cache.get(key) is None
    assert await cache.set(key, '{"ok":true}') is True
    assert await cache.get(key) == '{"ok":true}'
    assert backend.expiry[key] == 123


@pytest.mark.asyncio
async def test_cache_fails_open() -> None:
    cache = RedisJSONCache(
        FailingCacheBackend(),
        namespace="uae",
        version="v1",
        ttl_seconds=60,
    )
    assert await cache.get("key") is None
    assert await cache.set("key", "value") is False
