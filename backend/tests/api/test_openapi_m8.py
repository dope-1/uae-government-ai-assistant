from fastapi.testclient import TestClient


def test_openapi_exposes_operations_metrics(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/v1/ops/metrics" in schema["paths"]
