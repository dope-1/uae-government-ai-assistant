from __future__ import annotations

from typing import Any

import pytest

from app.production.rate_limit import RedisFixedWindowRateLimiter


class FakeRateBackend:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> Any:
        del script, numkeys
        key = str(keys_and_args[0])
        self.counts[key] = self.counts.get(key, 0) + 1
        return [self.counts[key], 60]


class FailingRateBackend:
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> Any:
        del script, numkeys, keys_and_args
        raise RuntimeError("redis down")


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_budget_and_hashes_identifier() -> None:
    backend = FakeRateBackend()
    limiter = RedisFixedWindowRateLimiter(
        backend,
        namespace="uae",
        limit=2,
        window_seconds=60,
    )
    first = await limiter.check("203.0.113.8", "chat")
    second = await limiter.check("203.0.113.8", "chat")
    third = await limiter.check("203.0.113.8", "chat")
    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.remaining == 0
    assert all("203.0.113.8" not in key for key in backend.counts)


@pytest.mark.asyncio
async def test_rate_limit_can_fail_open_or_closed() -> None:
    open_limiter = RedisFixedWindowRateLimiter(
        FailingRateBackend(),
        namespace="uae",
        limit=2,
        window_seconds=60,
        fail_open=True,
    )
    closed_limiter = RedisFixedWindowRateLimiter(
        FailingRateBackend(),
        namespace="uae",
        limit=2,
        window_seconds=60,
        fail_open=False,
    )
    assert (await open_limiter.check("client", "chat")).allowed is True
    closed = await closed_limiter.check("client", "chat")
    assert closed.allowed is False
    assert closed.retry_after_seconds == 60
