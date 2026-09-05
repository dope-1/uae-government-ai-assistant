from fastapi.testclient import TestClient


def test_health_has_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "bad id with spaces"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad id with spaces"
    assert len(response.headers["x-request-id"]) == 32


def test_oversized_write_request_returns_413_without_hitting_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        content=b"x" * 20_000,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.headers["x-request-id"]
    assert "configured limit" in response.json()["detail"]


def test_ops_metrics_expose_only_aggregate_privacy_flags(client: TestClient) -> None:
    client.get("/api/v1/health")
    response = client.get("/api/v1/ops/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["privacy"] == {
        "raw_queries_recorded": False,
        "answer_text_recorded": False,
        "client_ip_recorded": False,
    }
    assert "GET /api/v1/health" in body["requests"]
