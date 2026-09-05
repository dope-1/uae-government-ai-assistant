from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CASES = 30
SCORES = [
    "faithfulness_1_5",
    "answer_relevance_1_5",
    "citation_completeness_1_5",
    "language_quality_1_5",
]


def _validated_score(row: dict[str, str], name: str) -> float:
    raw = row.get(name, "").strip()
    if not raw:
        raise SystemExit(f"{row.get('case_id', '<unknown>')}: {name} is blank.")
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(
            f"{row.get('case_id', '<unknown>')}: {name} must be numeric (1-5), got {raw!r}."
        ) from exc
    if value < 1 or value > 5:
        raise SystemExit(
            f"{row.get('case_id', '<unknown>')}: {name} must be between 1 and 5, got {value}."
        )
    return value


def _metric_means(rows: list[dict[str, str]]) -> dict[str, float]:
    return {
        name.replace("_1_5", "_mean"): mean(_validated_score(row, name) for row in rows)
        for name in SCORES
    }


def main() -> None:
    path = ROOT / "data/evaluation/human_review_sample.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != EXPECTED_CASES:
        raise SystemExit(
            f"Human review must contain exactly {EXPECTED_CASES} rows; found {len(rows)}."
        )

    case_ids = [row.get("case_id", "").strip() for row in rows]
    if any(not case_id for case_id in case_ids):
        raise SystemExit("Every human-review row must have a case_id.")
    if len(case_ids) != len(set(case_ids)):
        raise SystemExit("Human-review case IDs must be unique.")

    # Require all 30 rows to be fully reviewed. The previous behavior silently aggregated a
    # partial sheet, which could be mistaken for the required 30-case human evaluation.
    for row in rows:
        for name in SCORES:
            _validated_score(row, name)

    summary: dict[str, object] = {
        "reviewed_cases": len(rows),
        **_metric_means(rows),
        "language_distribution": dict(Counter(row["language"] for row in rows)),
        "jurisdiction_distribution": dict(Counter(row["jurisdiction"] for row in rows)),
    }

    by_language: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_jurisdiction: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_language[row["language"]].append(row)
        by_jurisdiction[row["jurisdiction"]].append(row)

    summary["by_language"] = {
        language: {"cases": len(group), **_metric_means(group)}
        for language, group in sorted(by_language.items())
    }
    summary["by_jurisdiction"] = {
        jurisdiction: {"cases": len(group), **_metric_means(group)}
        for jurisdiction, group in sorted(by_jurisdiction.items())
    }

    low_score_cases = []
    for row in rows:
        scores = {name: _validated_score(row, name) for name in SCORES}
        if any(value <= 2 for value in scores.values()):
            low_score_cases.append(
                {
                    "case_id": row["case_id"],
                    "language": row["language"],
                    "jurisdiction": row["jurisdiction"],
                    "scores": scores,
                    "reviewer_notes": row.get("reviewer_notes", ""),
                }
            )
    summary["low_score_cases"] = low_score_cases

    output = ROOT / "experiments/evaluation/milestone7_human_review_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
