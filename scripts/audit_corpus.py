from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine, create_session_factory  # noqa: E402
from app.ingestion.manifest import load_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the live PostgreSQL corpus against the official-source manifest"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/official_sources.yaml",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    manifest = [source for source in load_manifest(args.manifest) if source.enabled]
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    records: list[dict[str, object]] = []
    try:
        async with factory() as session:
            for source in manifest:
                row = (
                    await session.execute(
                        text(
                            """
                            SELECT
                                s.id AS source_id,
                                (SELECT COUNT(*) FROM documents d WHERE d.source_id = s.id)
                                    AS documents,
                                (
                                    SELECT COUNT(*)
                                    FROM document_chunks dc
                                    WHERE dc.source_id = s.id
                                ) AS chunks,
                                (
                                    SELECT MAX(d.retrieved_at)
                                    FROM documents d
                                    WHERE d.source_id = s.id
                                ) AS latest_retrieved_at,
                                (
                                    SELECT COALESCE(
                                        SUM(array_length(regexp_split_to_array(d.content, '\\s+'), 1)),
                                        0
                                    )
                                    FROM documents d
                                    WHERE d.source_id = s.id
                                ) AS approx_words,
                                (
                                    SELECT ARRAY_REMOVE(
                                        ARRAY_AGG(DISTINCT dc.embedding_model), NULL
                                    )
                                    FROM document_chunks dc
                                    WHERE dc.source_id = s.id
                                ) AS embedding_models
                            FROM sources s
                            WHERE s.id = :source_id
                            """
                        ),
                        {"source_id": source.id},
                    )
                ).mappings().first()
                ingested = row is not None and int(row["documents"] or 0) > 0
                records.append(
                    {
                        "source_id": source.id,
                        "jurisdiction": source.jurisdiction,
                        "language": source.language,
                        "authority": source.authority,
                        "ingested": ingested,
                        "documents": int(row["documents"] or 0) if row else 0,
                        "chunks": int(row["chunks"] or 0) if row else 0,
                        "approx_words": int(row["approx_words"] or 0) if row else 0,
                        "embedding_models": list(row["embedding_models"] or []) if row else [],
                        "latest_retrieved_at": (
                            row["latest_retrieved_at"].isoformat()
                            if row and row["latest_retrieved_at"] is not None
                            else None
                        ),
                    }
                )
    finally:
        await engine.dispose()

    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return

    print("SOURCE ID                                JURISDICTION LANG DOCS CHUNKS WORDS STATUS")
    print("-" * 96)
    for record in records:
        status = "OK" if record["ingested"] else "MISSING"
        print(
            f"{str(record['source_id']):40} "
            f"{str(record['jurisdiction']):12} "
            f"{str(record['language']):4} "
            f"{int(record['documents']):4} "
            f"{int(record['chunks']):6} "
            f"{int(record['approx_words']):5} {status}"
        )

    ingested = [record for record in records if record["ingested"]]
    by_jurisdiction = Counter(str(record["jurisdiction"]) for record in ingested)
    by_language = Counter(str(record["language"]) for record in ingested)
    print()
    print(f"Ingested {len(ingested)}/{len(records)} enabled manifest sources.")
    print(f"By jurisdiction: {dict(sorted(by_jurisdiction.items()))}")
    print(f"By language: {dict(sorted(by_language.items()))}")


if __name__ == "__main__":
    asyncio.run(run())
