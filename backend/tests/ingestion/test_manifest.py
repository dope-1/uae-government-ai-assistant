from pathlib import Path

from app.ingestion.manifest import load_manifest

ROOT = Path(__file__).resolve().parents[3]


def test_official_manifest_covers_target_jurisdictions_and_languages() -> None:
    sources = load_manifest(ROOT / "data/manifests/official_sources.yaml")
    assert len(sources) >= 12
    assert {source.jurisdiction for source in sources} == {"Federal", "Abu Dhabi", "Dubai"}
    assert {source.language for source in sources} == {"en", "ar"}


def test_expanded_manifest_contains_live_demo_sources() -> None:
    sources = load_manifest(ROOT / "data/manifests/official_sources.yaml")
    ids = {source.id for source in sources}
    assert {
        "federal_visa_types_ar",
        "dubai_driving_licence_renew_en",
        "dubai_services_ar",
        "abu_dhabi_driver_licensing_en",
        "abu_dhabi_vehicle_licensing_en",
        "abu_dhabi_driver_licensing_ar",
        "abu_dhabi_vehicle_licensing_ar",
    } <= ids
