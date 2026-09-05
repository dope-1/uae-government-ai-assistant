from pathlib import Path

import yaml

from app.ingestion.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[3]


def test_verified_service_catalogue_references_manifest_sources() -> None:
    manifest = {
        source.id: source for source in load_manifest(ROOT / "data/manifests/official_sources.yaml")
    }
    payload = yaml.safe_load(
        (ROOT / "data/services/verified_services.yaml").read_text(encoding="utf-8")
    )
    services = payload["services"]

    ids = [service["id"] for service in services]
    assert len(ids) == len(set(ids))
    assert {service["jurisdiction"] for service in services} == {
        "Federal",
        "Abu Dhabi",
        "Dubai",
    }
    assert any("تجديد رخصة القيادة" in service["service_name"] for service in services)

    for service in services:
        source = manifest[service["source_id"]]
        assert str(source.url).rstrip("/") == str(service["official_url"]).rstrip("/")
        assert source.jurisdiction == service["jurisdiction"]
