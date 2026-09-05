from app.production.telemetry import TelemetryRegistry


def test_telemetry_is_aggregate_and_privacy_safe() -> None:
    telemetry = TelemetryRegistry()
    telemetry.record_request("GET", "/api/v1/health", 200, 12.5)
    telemetry.record_request("GET", "/api/v1/health", 503, 20.0)
    telemetry.record_cache("chat", hit=True)
    telemetry.record_cache("chat", hit=False)
    telemetry.record_rate_limited()
    telemetry.record_model(
        provider="extractive",
        model="extractive-grounded",
        prompt_tokens=None,
        completion_tokens=None,
        estimated_cost_usd=0.0,
    )
    snapshot = telemetry.snapshot()
    assert snapshot["privacy"] == {
        "raw_queries_recorded": False,
        "answer_text_recorded": False,
        "client_ip_recorded": False,
    }
    requests = snapshot["requests"]
    assert isinstance(requests, dict)
    assert requests["GET /api/v1/health"]["count"] == 2
    assert requests["GET /api/v1/health"]["errors_5xx"] == 1
    cache = snapshot["cache"]
    assert isinstance(cache, dict)
    assert cache["chat"]["hit_rate"] == 0.5
    assert snapshot["rate_limited_requests"] == 1
