from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments/evaluation/milestone9_deployment_results.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the public Milestone 9 deployment"
    )
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--backend-url", required=True)
    parser.add_argument("--ops-token")
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args()


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> tuple[int, dict[str, str], bytes, float]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    merged_headers = {"User-Agent": "uae-government-ai-assistant-m9-verifier/1.0"}
    if payload is not None:
        merged_headers["Content-Type"] = "application/json"
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(
        url, data=body, headers=merged_headers, method=method
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            return (
                response.status,
                {key.casefold(): value for key, value in response.headers.items()},
                response_body,
                (time.perf_counter() - started) * 1000,
            )
    except urllib.error.HTTPError as exc:
        return (
            exc.code,
            {key.casefold(): value for key, value in exc.headers.items()},
            exc.read(),
            (time.perf_counter() - started) * 1000,
        )


def _json(body: bytes) -> dict[str, Any]:
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")
    return value


def main() -> None:
    args = parse_args()
    frontend = args.frontend_url.rstrip("/")
    backend = args.backend_url.rstrip("/")
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, **details: Any) -> None:
        checks.append({"name": name, "passed": passed, **details})
        print(f"{'PASS' if passed else 'FAIL'} {name}")

    status, headers, body, latency = _request(
        f"{backend}/api/v1/ready", timeout=args.timeout
    )
    ready = _json(body) if status == 200 else {}
    ready_dependencies = (
        ready.get("dependencies") if isinstance(ready.get("dependencies"), dict) else {}
    )

    record(
        "backend readiness",
        status == 200
        and bool(ready_dependencies.get("postgres"))
        and bool(ready_dependencies.get("redis")),
        status=status,
        latency_ms=round(latency, 3),
        postgresql=ready_dependencies.get("postgres"),
        redis=ready_dependencies.get("redis"),
    )
    record(
        "backend request/security headers",
        bool(headers.get("x-request-id"))
        and headers.get("x-content-type-options") == "nosniff"
        and bool(headers.get("strict-transport-security")),
    )

    status, _, _, latency = _request(frontend, timeout=args.timeout)
    record("frontend root", status == 200, status=status, latency_ms=round(latency, 3))

    status, _, body, latency = _request(
        f"{frontend}/api/backend/ready", timeout=args.timeout
    )
    proxied_ready = _json(body) if status == 200 else {}
    proxied_dependencies = (
        proxied_ready.get("dependencies")
        if isinstance(proxied_ready.get("dependencies"), dict)
        else {}
    )

    record(
        "frontend-to-backend proxy",
        status == 200
        and bool(proxied_dependencies.get("postgres"))
        and bool(proxied_dependencies.get("redis")),
        status=status,
        latency_ms=round(latency, 3),
    )

    status, chat_headers, body, latency = _request(
        f"{frontend}/api/backend/chat",
        method="POST",
        payload={
            "message": "What is the UAE Golden Visa?",
            "jurisdiction": "Federal",
        },
        timeout=args.timeout,
    )
    chat = _json(body) if status == 200 else {}
    citations = chat.get("citations") if isinstance(chat.get("citations"), list) else []
    record(
        "end-to-end grounded chat",
        status == 200
        and chat.get("status") == "answered"
        and len(citations) >= 1
        and bool(chat_headers.get("x-request-id")),
        status=status,
        latency_ms=round(latency, 3),
        response_status=chat.get("status"),
        citations=len(citations),
        cache=chat_headers.get("x-cache"),
    )

    ops_headers = None
    if args.ops_token:
        ops_headers = {"Authorization": f"Bearer {args.ops_token}"}
    status, _, body, latency = _request(
        f"{backend}/api/v1/ops/metrics",
        headers=ops_headers,
        timeout=args.timeout,
    )
    if args.ops_token:
        ops = _json(body) if status == 200 else {}
        privacy = ops.get("privacy") if isinstance(ops.get("privacy"), dict) else {}
        record(
            "protected operational metrics",
            status == 200
            and privacy.get("raw_queries_recorded") is False
            and privacy.get("answer_text_recorded") is False
            and privacy.get("client_ip_recorded") is False,
            status=status,
            latency_ms=round(latency, 3),
        )
    else:
        record(
            "operational metrics require authentication",
            status == 401,
            status=status,
            latency_ms=round(latency, 3),
        )

    passed = all(bool(check["passed"]) for check in checks)
    result = {
        "evaluation": "milestone9_deployment",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "frontend_url": frontend,
        "backend_url": backend,
        "passed": passed,
        "checks": checks,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {OUTPUT}")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
