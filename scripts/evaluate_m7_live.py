from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.milestone7 import (  # noqa: E402
    SUITE_VERSION,
    aggregate,
    load_cases,
    score_case,
    validate_suite,
    write_json,
)
from app.rag.schemas import RAGAnswer  # noqa: E402


async def _post_chat_with_retry(
    client: httpx.AsyncClient,
    *,
    message: str,
    jurisdiction: str | None,
    attempts: int = 3,
) -> httpx.Response:
    retryable_statuses = {429, 502, 503, 504}
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await client.post(
                "/api/v1/chat",
                json={"message": message, "jurisdiction": jurisdiction},
            )
            if response.status_code not in retryable_statuses:
                response.raise_for_status()
                return response
            last_error = httpx.HTTPStatusError(
                f"retryable HTTP {response.status_code}",
                request=response.request,
                response=response,
            )
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            last_error = exc
        if attempt < attempts:
            await asyncio.sleep(2 ** (attempt - 1))
    assert last_error is not None
    raise last_error


async def run(
    base_url: str,
    limit: int | None,
    tag: str | None,
    case_id: str | None,
    checkpoint_every: int,
) -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    errors = validate_suite(cases)
    if errors:
        raise SystemExit("\n".join(errors))
    if tag:
        cases = [case for case in cases if tag in case.tags]
    if case_id:
        cases = [case for case in cases if case.id == case_id]
        if not cases:
            raise SystemExit(f"Unknown Milestone 7 case: {case_id}")
    if limit:
        cases = cases[:limit]

    scores = []
    raw = []
    timeout = httpx.Timeout(120.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        for index, case in enumerate(cases, start=1):
            response = await _post_chat_with_retry(
                client,
                message=case.query,
                jurisdiction=case.jurisdiction,
            )
            answer = RAGAnswer.model_validate(response.json())
            score = score_case(case, answer)
            scores.append(score)
            raw.append(
                {
                    "case": case.model_dump(mode="json"),
                    "answer": answer.model_dump(mode="json"),
                    "score": score.model_dump(),
                }
            )
            print(f"[{index}/{len(cases)}] {case.id}: {answer.status}")
            if checkpoint_every > 0 and index % checkpoint_every == 0:
                partial = {
                    "evaluation": "milestone7_live_bilingual_evaluation_partial",
                    "suite_version": SUITE_VERSION,
                    "base_url": base_url,
                    "completed_cases": index,
                    "total_cases": len(cases),
                    "summary": aggregate(scores),
                    "cases": raw,
                }
                write_json(
                    ROOT / "experiments/evaluation/milestone7_live_results.partial.json",
                    partial,
                )

    report = {
        "evaluation": "milestone7_live_bilingual_evaluation",
        "suite_version": SUITE_VERSION,
        "base_url": base_url,
        "summary": aggregate(scores),
        "language_distribution": dict(Counter(case.language for case in cases)),
        "cases": raw,
        "faithfulness": None,
        "limitations": (
            "Deterministic metrics are reproducible diagnostics, not semantic faithfulness. "
            "Fact/citation/context metrics are scored only on expected-answer cases; mixed-"
            "language queries accept either English or Arabic unless a future case states an "
            "explicit response-language preference. Faithfulness must come from human review."
        ),
    }
    output = ROOT / "experiments/evaluation/milestone7_live_results.json"
    write_json(output, report)
    partial_output = ROOT / "experiments/evaluation/milestone7_live_results.partial.json"
    partial_output.unlink(missing_ok=True)
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--tag")
    parser.add_argument("--case")
    parser.add_argument("--checkpoint-every", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(
        run(
            args.base_url,
            args.limit,
            args.tag,
            args.case,
            args.checkpoint_every,
        )
    )


if __name__ == "__main__":
    main()
