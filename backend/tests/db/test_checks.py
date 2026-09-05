from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

import app.db.checks as checks_module
from app.core.config import Settings


class _FakeResult:
    def scalar_one(self) -> int:
        return 1


class _FakeConnection:
    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, _: object) -> _FakeResult:
        return _FakeResult()


class _FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    def connect(self) -> _FakeConnection:
        return _FakeConnection()

    async def dispose(self) -> None:
        self.disposed = True


@pytest.mark.asyncio
async def test_check_postgres_normalizes_neon_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    fake_engine = _FakeEngine()

    def fake_create_async_engine(url: str, **kwargs: Any) -> AsyncEngine:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return cast(AsyncEngine, fake_engine)

    monkeypatch.setattr(checks_module, "create_async_engine", fake_create_async_engine)
    settings = cast(
        Settings,
        SimpleNamespace(
            database_url=(
                "postgresql://user:pass@example.neon.tech/db"
                "?sslmode=require&channel_binding=require"
            ),
            ready_check_timeout_seconds=1.0,
        ),
    )

    assert await checks_module.check_postgres(settings) is True
    assert captured["url"] == "postgresql+asyncpg://user:pass@example.neon.tech/db"
    assert captured["kwargs"]["connect_args"] == {"ssl": True}
    assert fake_engine.disposed is True
