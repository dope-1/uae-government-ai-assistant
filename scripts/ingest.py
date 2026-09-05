from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine, create_session_factory  # noqa: E402
from app.embeddings.local_baseline import HashingEmbeddingProvider  # noqa: E402
from app.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider  # noqa: E402
from app.ingestion.downloader import (  # noqa: E402
    PublicSourceDownloader,
    SourceDownloadError,
)
from app.ingestion.manifest import load_manifest  # noqa: E402
from app.ingestion.parsers import ParseError  # noqa: E402
from app.ingestion.pipeline import IngestionPipeline  # noqa: E402
from app.ingestion.storage import PostgresIngestionStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest public UAE government sources")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/official_sources.yaml",
    )
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument(
        "--jurisdiction",
        choices=["Federal", "Abu Dhabi", "Dubai"],
        help="Ingest only sources from one jurisdiction.",
    )
    parser.add_argument(
        "--language",
        choices=["en", "ar"],
        help="Ingest only sources in one manifest language.",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Print enabled source IDs and exit without downloading anything.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["e5", "hashing"],
        default="e5",
        help=(
            "Use e5 for production-oriented multilingual embeddings; "
            "hashing is an offline baseline."
        ),
    )
    parser.add_argument("--no-persist", action="store_true")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    sources = [source for source in load_manifest(args.manifest) if source.enabled]
    if args.source_id:
        wanted = set(args.source_id)
        sources = [source for source in sources if source.id in wanted]
    if args.jurisdiction:
        sources = [source for source in sources if source.jurisdiction == args.jurisdiction]
    if args.language:
        sources = [source for source in sources if source.language == args.language]
    if args.list_sources:
        for source in sources:
            print(
                f"{source.id:40} {source.jurisdiction:10} {source.language} "
                f"{source.authority} -> {source.url}"
            )
        return
    if not sources:
        raise SystemExit("No enabled sources selected")

    provider = (
        SentenceTransformerEmbeddingProvider()
        if args.embedding_provider == "e5"
        else HashingEmbeddingProvider()
    )
    pipeline = IngestionPipeline(PublicSourceDownloader(), provider)
    settings = get_settings()
    engine = create_engine(settings) if not args.no_persist else None
    session_factory = create_session_factory(engine) if engine else None
    failures: list[str] = []
    try:
        for source in sources:
            try:
                document, chunks = await pipeline.ingest(source)
                print(
                    f"{source.id}: title={document.title!r} language={document.language} "
                    f"chunks={len(chunks)} embedding={provider.name}"
                )
                if session_factory:
                    async with session_factory() as session:
                        await PostgresIngestionStore(session).save(
                            source, document, chunks, provider
                        )
            except (SourceDownloadError, ParseError) as exc:
                failures.append(source.id)
                print(f"{source.id}: FAILED: {exc}", file=sys.stderr)
    finally:
        if engine:
            await engine.dispose()
    if failures:
        raise SystemExit(f"Ingestion failed for {len(failures)} source(s): {', '.join(failures)}")


if __name__ == "__main__":
    asyncio.run(run())
