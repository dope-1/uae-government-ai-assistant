from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine, create_session_factory  # noqa: E402
from app.rag.factory import build_rag_service  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask the grounded UAE government assistant")
    parser.add_argument("message")
    parser.add_argument("--jurisdiction", choices=["Federal", "Abu Dhabi", "Dubai"])
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            answer = await build_rag_service(session, settings).answer(
                args.message, jurisdiction=args.jurisdiction
            )
            print(json.dumps(answer.model_dump(mode="json"), indent=2, ensure_ascii=False))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
