from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)

_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


class RateLimitBackend(Protocol):
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> Any: ...


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RedisFixedWindowRateLimiter:
    """Redis-backed fixed-window limiter with hashed client identifiers."""

    def __init__(
        self,
        backend: RateLimitBackend,
        *,
        namespace: str,
        limit: int,
        window_seconds: int,
        enabled: bool = True,
        fail_open: bool = True,
    ) -> None:
        self.backend = backend
        self.namespace = namespace.strip(":")
        self.limit = limit
        self.window_seconds = window_seconds
        self.enabled = enabled
        self.fail_open = fail_open

    async def check(self, client_identifier: str, resource: str) -> RateLimitDecision:
        if not self.enabled:
            return RateLimitDecision(True, self.limit, self.limit, 0)

        fingerprint = hashlib.sha256(client_identifier.encode("utf-8")).hexdigest()[:24]
        key = f"{self.namespace}:rate:{resource}:{fingerprint}"
        try:
            raw = await self.backend.eval(
                _RATE_LIMIT_SCRIPT,
                1,
                key,
                self.window_seconds,
            )
            current, ttl = _parse_counter(raw)
        except Exception as exc:
            logger.warning(
                "rate_limit.backend_failed",
                error_type=type(exc).__name__,
                fail_open=self.fail_open,
            )
            if self.fail_open:
                return RateLimitDecision(True, self.limit, self.limit, 0)
            return RateLimitDecision(False, self.limit, 0, self.window_seconds)

        retry_after = max(1, ttl if ttl > 0 else self.window_seconds)
        remaining = max(0, self.limit - current)
        return RateLimitDecision(
            allowed=current <= self.limit,
            limit=self.limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )


def _parse_counter(raw: object) -> tuple[int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError("Unexpected Redis rate-limit response")
    return int(raw[0]), int(raw[1])
