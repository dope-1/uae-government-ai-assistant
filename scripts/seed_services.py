from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine, create_session_factory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed verified structured service metadata")
    parser.add_argument(
        "--file", type=Path, default=ROOT / "data/services/verified_services.yaml"
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    payload = yaml.safe_load(args.file.read_text(encoding="utf-8"))
    services = payload.get("services", [])
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    inserted = 0
    skipped = 0
    try:
        async with factory() as session:
            for service in services:
                source_row = (
                    await session.execute(
                        text(
                            """
                            SELECT s.url, MAX(d.retrieved_at) AS retrieved_at
                            FROM sources s
                            LEFT JOIN documents d ON d.source_id = s.id
                            WHERE s.id = :id
                            GROUP BY s.url
                            """
                        ),
                        {"id": service["source_id"]},
                    )
                ).mappings().first()
                if source_row is None or source_row["retrieved_at"] is None:
                    skipped += 1
                    print(f"SKIP {service['id']}: source {service['source_id']} is not ingested")
                    continue
                if str(source_row["url"]) != str(service["official_url"]):
                    raise ValueError(
                        f"Service {service['id']} URL does not match its ingested source URL"
                    )
                await session.execute(
                    text(
                        """
                        INSERT INTO services
                            (id, service_name, authority, jurisdiction, category, description,
                             requirements, documents, fees, official_url, last_verified, source_id)
                        VALUES
                            (:id, :service_name, :authority, :jurisdiction, :category, :description,
                             CAST(:requirements AS json), CAST(:documents AS json),
                             CAST(:fees AS json),
                             :official_url, :last_verified, :source_id)
                        ON CONFLICT (id) DO UPDATE SET
                            service_name = EXCLUDED.service_name,
                            authority = EXCLUDED.authority,
                            jurisdiction = EXCLUDED.jurisdiction,
                            category = EXCLUDED.category,
                            description = EXCLUDED.description,
                            requirements = EXCLUDED.requirements,
                            documents = EXCLUDED.documents,
                            fees = EXCLUDED.fees,
                            official_url = EXCLUDED.official_url,
                            last_verified = EXCLUDED.last_verified,
                            source_id = EXCLUDED.source_id
                        """
                    ),
                    {
                        **service,
                        "requirements": json.dumps(service.get("requirements", [])),
                        "documents": json.dumps(service.get("documents", [])),
                        "fees": json.dumps(service.get("fees", [])),
                        "last_verified": source_row["retrieved_at"],
                    },
                )
                inserted += 1
            await session.commit()
    finally:
        await engine.dispose()
    print(f"Inserted/updated {inserted} service(s); skipped {skipped} without an ingested source.")


if __name__ == "__main__":
    asyncio.run(run())
