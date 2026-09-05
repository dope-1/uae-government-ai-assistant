from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class CacheBackend(Protocol):
    async def get(self, key: str) -> Any: ...

    async def set(self, key: str, value: str, *, ex: int) -> Any: ...


class RedisJSONCache:
    """Small fail-open JSON cache backed by Redis.

    Cache keys contain only a SHA-256 digest of canonical request fields, so raw user
    questions are not persisted in Redis key names.
    """

    def __init__(
        self,
        backend: CacheBackend,
        *,
        namespace: str,
        version: str,
        ttl_seconds: int,
        enabled: bool = True,
    ) -> None:
        self.backend = backend
        self.namespace = namespace.strip(":")
        self.version = version.strip(":")
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled

    def make_key(self, resource: str, payload: Mapping[str, object]) -> str:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{self.namespace}:{self.version}:{resource}:{digest}"

    async def get(self, key: str) -> str | None:
        if not self.enabled:
            return None
        try:
            value = await self.backend.get(key)
        except Exception as exc:
            logger.warning("cache.read_failed", error_type=type(exc).__name__)
            return None
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def set(self, key: str, value: str) -> bool:
        if not self.enabled:
            return False
        try:
            await self.backend.set(key, value, ex=self.ttl_seconds)
        except Exception as exc:
            logger.warning("cache.write_failed", error_type=type(exc).__name__)
            return False
        return True
