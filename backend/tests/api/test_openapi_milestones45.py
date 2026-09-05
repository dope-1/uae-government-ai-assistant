from fastapi.testclient import TestClient


def test_openapi_exposes_rag_and_agent_endpoints(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/chat" in paths
    assert "/api/v1/search" in paths
    assert "/api/v1/services" in paths
    assert "/api/v1/services/{service_id}" in paths
    assert "/api/v1/sources" in paths
    assert "/api/v1/sources/{source_id}" in paths
    assert "/api/v1/agent/service-discovery" in paths
