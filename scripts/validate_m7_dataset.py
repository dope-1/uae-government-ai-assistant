from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.milestone7 import (  # noqa: E402
    SUITE_VERSION,
    load_cases,
    validate_suite,
)


def main() -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    errors = validate_suite(cases)

    manifest = yaml.safe_load(
        (ROOT / "data/manifests/official_sources.yaml").read_text(encoding="utf-8")
    )
    catalogue = yaml.safe_load(
        (ROOT / "data/services/verified_services.yaml").read_text(encoding="utf-8")
    )
    source_ids = {str(item["id"]) for item in manifest["sources"]}
    service_ids = {str(item["id"]) for item in catalogue["services"]}
    for case in cases:
        unknown_sources = case.relevant_source_ids - source_ids
        if unknown_sources:
            errors.append(f"{case.id} references unknown sources: {sorted(unknown_sources)}")
        if case.expected_service_id and case.expected_service_id not in service_ids:
            errors.append(f"{case.id} references unknown service: {case.expected_service_id}")

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"VALID: {len(cases)} Milestone 7 cases ({SUITE_VERSION})")
    print("languages", dict(Counter(case.language for case in cases)))
    print("statuses", dict(Counter(case.expected_status for case in cases)))
    print("categories", dict(Counter(case.category for case in cases)))


if __name__ == "__main__":
    main()
