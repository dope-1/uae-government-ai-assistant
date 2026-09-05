from __future__ import annotations

import argparse
import asyncio
import json

import httpx


CASES = [
    {
        "name": "Dubai service discovery",
        "endpoint": "/api/v1/agent/service-discovery",
        "payload": {
            "message": "How do I renew my driving licence in Dubai?",
            "jurisdiction": "Dubai",
        },
    },
    {
        "name": "Abu Dhabi service discovery",
        "endpoint": "/api/v1/agent/service-discovery",
        "payload": {
            "message": "How do I renew my driving licence in Abu Dhabi?",
            "jurisdiction": "Abu Dhabi",
        },
    },
    {
        "name": "Arabic Dubai service discovery",
        "endpoint": "/api/v1/agent/service-discovery",
        "payload": {
            "message": "كيف أجدد رخصة القيادة في دبي؟",
            "jurisdiction": "Dubai",
        },
    },
    {
        "name": "Arabic Abu Dhabi service discovery",
        "endpoint": "/api/v1/agent/service-discovery",
        "payload": {
            "message": "كيف أجدد رخصة القيادة في أبوظبي؟",
            "jurisdiction": "Abu Dhabi",
        },
    },
    {
        "name": "Dubai grounded RAG",
        "endpoint": "/api/v1/chat",
        "payload": {
            "message": "How do I renew my driving licence in Dubai?",
            "jurisdiction": "Dubai",
        },
    },
    {
        "name": "Abu Dhabi grounded RAG",
        "endpoint": "/api/v1/chat",
        "payload": {
            "message": "What official Abu Dhabi service handles driving licence renewal?",
            "jurisdiction": "Abu Dhabi",
        },
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live multi-jurisdiction API smoke tests")
    parser.add_argument("--base-url", default="http://localhost:8000")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
        ready = await client.get("/api/v1/ready")
        ready.raise_for_status()
        print("READY", json.dumps(ready.json(), ensure_ascii=False))
        print()
        for case in CASES:
            response = await client.post(case["endpoint"], json=case["payload"])
            print(f"=== {case['name']} ===")
            print(f"HTTP {response.status_code}")
            if response.is_success:
                print(json.dumps(response.json(), ensure_ascii=False, indent=2))
            else:
                print(response.text)
            print()


if __name__ == "__main__":
    asyncio.run(run())
