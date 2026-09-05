from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.milestone7 import load_cases  # noqa: E402

LANGUAGES = ("en", "ar", "mixed")
# Human faithfulness scoring is intentionally limited to substantive answered cases.
# Automated M7 already evaluates refusals and clarification decisions across all 180 cases.
JURISDICTION_QUOTAS = {
    "Federal": 4,
    "Dubai": 3,
    "Abu Dhabi": 3,
}
TARGET_PER_LANGUAGE = sum(JURISDICTION_QUOTAS.values())
TARGET_TOTAL = TARGET_PER_LANGUAGE * len(LANGUAGES)


def _live_answers() -> dict[str, tuple[str, str, str]]:
    path = ROOT / "experiments/evaluation/milestone7_live_results.json"
    if not path.exists():
        return {}

    payload = json.loads(path.read_text(encoding="utf-8"))
    answers: dict[str, tuple[str, str, str]] = {}
    for row in payload.get("cases", []):
        case_id = str(row["case"]["id"])
        answer = row["answer"]
        citation_rows = answer.get("citations", [])
        urls = "; ".join(str(item.get("url", "")) for item in citation_rows)
        evidence_parts: list[str] = []
        for item in citation_rows:
            marker = str(item.get("id", ""))
            source_id = str(item.get("source_id", ""))
            authority = str(item.get("authority", ""))
            title = str(item.get("title", ""))
            excerpt = str(item.get("relevant_excerpt", ""))
            url = str(item.get("url", ""))
            evidence_parts.append(
                f"{marker} | source_id={source_id} | authority={authority} | title={title}\n"
                f"excerpt: {excerpt}\nurl: {url}"
            )
        answers[case_id] = (
            str(answer.get("answer", "")),
            urls,
            "\n\n".join(evidence_parts),
        )
    return answers


def _evenly_spaced(items: list[Any], count: int) -> list[Any]:
    if count <= 0:
        return []
    if len(items) < count:
        raise ValueError(f"Need {count} cases but only {len(items)} are available.")
    if len(items) == count:
        return list(items)
    # Deterministic midpoint sampling avoids simply taking the first N near-duplicate paraphrases.
    indices = [((2 * i + 1) * len(items)) // (2 * count) for i in range(count)]
    return [items[index] for index in indices]


def _select_sample(cases: list[Any]) -> list[Any]:
    selected: list[Any] = []
    for language in LANGUAGES:
        language_cases = [
            case
            for case in cases
            if case.language == language and case.expected_status == "answered"
        ]
        if len(language_cases) < TARGET_PER_LANGUAGE:
            raise SystemExit(
                f"Not enough answered {language} cases for human review: "
                f"need {TARGET_PER_LANGUAGE}, found {len(language_cases)}."
            )

        language_selected: list[Any] = []
        for jurisdiction, quota in JURISDICTION_QUOTAS.items():
            bucket = [case for case in language_cases if case.jurisdiction == jurisdiction]
            if len(bucket) < quota:
                raise SystemExit(
                    f"Not enough answered {language}/{jurisdiction} cases: "
                    f"need {quota}, found {len(bucket)}."
                )
            language_selected.extend(_evenly_spaced(bucket, quota))

        if len({case.id for case in language_selected}) != TARGET_PER_LANGUAGE:
            raise SystemExit(f"Duplicate cases selected for language={language}.")
        selected.extend(language_selected)

    if len(selected) != TARGET_TOTAL or len({case.id for case in selected}) != TARGET_TOTAL:
        raise SystemExit("Human-review sample must contain exactly 30 unique cases.")
    return selected


def main() -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    sample = _select_sample(cases)
    live = _live_answers()

    output = ROOT / "data/evaluation/human_review_sample.csv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_id",
                "language",
                "query",
                "jurisdiction",
                "answer",
                "citations",
                "citation_evidence",
                "faithfulness_1_5",
                "answer_relevance_1_5",
                "citation_completeness_1_5",
                "language_quality_1_5",
                "reviewer_notes",
            ]
        )
        for case in sample:
            answer, citations, citation_evidence = live.get(case.id, ("", "", ""))
            writer.writerow(
                [
                    case.id,
                    case.language,
                    case.query,
                    case.jurisdiction or "",
                    answer,
                    citations,
                    citation_evidence,
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )

    language_counts = Counter(case.language for case in sample)
    jurisdiction_counts = Counter(case.jurisdiction for case in sample)
    source = "live answers + frozen citation excerpts prefilled" if live else "blank answer fields"
    print(f"Wrote {output} with {len(sample)} answerable human-review cases ({source}).")
    print(f"Language distribution: {dict(language_counts)}")
    print(f"Jurisdiction distribution: {dict(jurisdiction_counts)}")
    if live and any(not live.get(case.id, ("", "", ""))[0] for case in sample):
        raise SystemExit("At least one selected case is missing a live answer; rerun the full live evaluation.")
    print("Review rubric: docs/human_review_rubric.md")


if __name__ == "__main__":
    main()
