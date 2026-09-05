from fastapi.testclient import TestClient

import app.api.v1.health as health_module


async def _true(_: object) -> bool:
    return True


async def _false(_: object) -> bool:
    return False


def test_ready_when_dependencies_are_healthy(client: TestClient, monkeypatch: object) -> None:
    monkeypatch.setattr(health_module, "check_postgres", _true)  # type: ignore[attr-defined]
    monkeypatch.setattr(health_module, "check_redis", _true)  # type: ignore[attr-defined]
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"postgres": True, "redis": True},
    }


def test_not_ready_when_dependency_fails(client: TestClient, monkeypatch: object) -> None:
    monkeypatch.setattr(health_module, "check_postgres", _true)  # type: ignore[attr-defined]
    monkeypatch.setattr(health_module, "check_redis", _false)  # type: ignore[attr-defined]
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
