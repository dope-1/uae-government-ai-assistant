from __future__ import annotations

import argparse
import asyncio
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "experiments" / "evaluation" / "milestone8_performance_results.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Milestone 8 HTTP concurrency benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint", choices=("health", "search", "chat"), default="chat")
    parser.add_argument("--requests", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument(
        "--query",
        default="Does the UAE Golden Visa require a sponsor?",
        help="Repeated benchmark query. Raw query text is not written to the results JSON.",
    )
    parser.add_argument("--jurisdiction", default="Federal")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


async def one_request(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    query: str,
    jurisdiction: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if endpoint == "health":
            response = await client.get("/api/v1/health")
        elif endpoint == "search":
            response = await client.post(
                "/api/v1/search",
                json={"query": query, "jurisdiction": jurisdiction, "k": 5},
            )
        else:
            response = await client.post(
                "/api/v1/chat",
                json={"message": query, "jurisdiction": jurisdiction},
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status": response.status_code,
            "latency_ms": elapsed_ms,
            "cache": response.headers.get("x-cache", "NONE"),
            "request_id_present": bool(response.headers.get("x-request-id")),
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "status": 0,
            "latency_ms": elapsed_ms,
            "cache": "NONE",
            "request_id_present": False,
            "error": type(exc).__name__,
        }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.requests < 1:
        raise ValueError("--requests must be at least 1")
    if args.concurrency < 1:
        raise ValueError("--concurrency must be at least 1")

    semaphore = asyncio.Semaphore(args.concurrency)
    base_url = args.base_url.rstrip("/")

    async with httpx.AsyncClient(base_url=base_url, timeout=args.timeout) as client:
        # Warm one deterministic request so the measured run contains realistic cache behaviour.
        await one_request(
            client,
            endpoint=args.endpoint,
            query=args.query,
            jurisdiction=args.jurisdiction,
        )

        async def bounded() -> dict[str, Any]:
            async with semaphore:
                return await one_request(
                    client,
                    endpoint=args.endpoint,
                    query=args.query,
                    jurisdiction=args.jurisdiction,
                )

        started = time.perf_counter()
        results = await asyncio.gather(*(bounded() for _ in range(args.requests)))
        wall_seconds = time.perf_counter() - started

    latencies = sorted(float(item["latency_ms"]) for item in results)
    statuses = Counter(str(item["status"]) for item in results)
    cache = Counter(str(item["cache"]) for item in results)
    errors = Counter(str(item["error"]) for item in results if item["error"])
    success_count = sum(1 for item in results if 200 <= int(item["status"]) < 400)

    return {
        "evaluation": "milestone8_performance",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "endpoint": args.endpoint,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "wall_seconds": round(wall_seconds, 4),
        "throughput_requests_per_second": round(args.requests / max(wall_seconds, 1e-9), 3),
        "success_rate": round(success_count / args.requests, 6),
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
            "p99": round(_percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3),
        },
        "status_counts": dict(sorted(statuses.items())),
        "cache_counts": dict(sorted(cache.items())),
        "request_id_coverage": round(
            sum(bool(item["request_id_present"]) for item in results) / args.requests,
            6,
        ),
        "transport_errors": dict(sorted(errors.items())),
        "privacy_note": "Benchmark output intentionally excludes raw query text and responses.",
    }


def _percentile(ordered: list[float], fraction: float) -> float:
    if not ordered:
        return math.nan
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def main() -> None:
    args = parse_args()
    result = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
