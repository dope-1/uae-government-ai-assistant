from __future__ import annotations

import argparse
import asyncio
import json
import sys
from math import log2
from pathlib import Path
from statistics import mean

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.milestone7 import (  # noqa: E402
    SUITE_VERSION,
    load_cases,
    validate_suite,
    write_json,
)


def source_metrics(returned: list[str], relevant: set[str], k: int) -> dict[str, float]:
    ranked = returned[:k]
    hits = [1 if source in relevant else 0 for source in ranked]
    # Each case represents one information need. ``relevant`` may contain equivalent
    # English/Arabic official sources, so only the first accepted source satisfies the
    # relevance group; retrieving another language version is not a second required fact.
    first_hit_rank = next((rank for rank, hit in enumerate(hits, start=1) if hit), None)
    recall = float(first_hit_rank is not None) if relevant else 1.0
    precision = (1.0 / k) if first_hit_rank is not None else 0.0
    rr = (1.0 / first_hit_rank) if first_hit_rank is not None else 0.0
    ndcg = (1.0 / log2(first_hit_rank + 1)) if first_hit_rank is not None else 0.0
    return {"recall": recall, "precision": precision, "mrr": rr, "ndcg": ndcg}


async def _post_search_with_retry(
    client: httpx.AsyncClient,
    *,
    query: str,
    jurisdiction: str | None,
    k: int,
    attempts: int = 3,
) -> httpx.Response:
    retryable_statuses = {429, 502, 503, 504}
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = await client.post(
                "/api/v1/search",
                json={"query": query, "jurisdiction": jurisdiction, "k": k},
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
    k: int,
    limit: int | None,
    case_id: str | None,
    checkpoint_every: int,
) -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    errors = validate_suite(cases)
    if errors:
        raise SystemExit("\n".join(errors))
    cases = [case for case in cases if case.expected_source_ids]
    if case_id:
        cases = [case for case in cases if case.id == case_id]
        if not cases:
            raise SystemExit(f"Unknown answerable Milestone 7 case: {case_id}")
    if limit:
        cases = cases[:limit]

    rows = []
    async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(120.0)) as client:
        for index, case in enumerate(cases, start=1):
            response = await _post_search_with_retry(
                client,
                query=case.query,
                jurisdiction=case.jurisdiction,
                k=k,
            )
            hits = response.json()
            returned: list[str] = []
            for hit in hits:
                source_id = str(hit["citation"]["source_id"])
                if source_id not in returned:
                    returned.append(source_id)
            metrics = source_metrics(returned, case.relevant_source_ids, k)
            rows.append({"id": case.id, "returned_sources": returned, **metrics})
            print(f"[{index}/{len(cases)}] {case.id} recall={metrics['recall']:.3f}")
            if checkpoint_every > 0 and index % checkpoint_every == 0:
                partial = {
                    "evaluation": "milestone7_live_retrieval_partial",
                    "suite_version": SUITE_VERSION,
                    "k": k,
                    "completed_cases": index,
                    "total_cases": len(cases),
                    "rows": rows,
                }
                write_json(
                    ROOT
                    / "experiments/evaluation/milestone7_live_retrieval_results.partial.json",
                    partial,
                )

    report = {
        "evaluation": "milestone7_live_retrieval",
        "suite_version": SUITE_VERSION,
        "k": k,
        "cases": len(rows),
        f"recall@{k}": mean(row["recall"] for row in rows),
        f"precision@{k}": mean(row["precision"] for row in rows),
        "mrr": mean(row["mrr"] for row in rows),
        f"ndcg@{k}": mean(row["ndcg"] for row in rows),
        "rows": rows,
        "limitations": (
            "Relevance is labelled at source level because live chunk IDs may change "
            "after re-ingestion. Recall is case-level source-equivalence recall: any "
            "accepted English/Arabic source can satisfy a mixed-language information need."
        ),
    }
    output = ROOT / "experiments/evaluation/milestone7_live_retrieval_results.json"
    write_json(output, report)
    partial_output = ROOT / "experiments/evaluation/milestone7_live_retrieval_results.partial.json"
    partial_output.unlink(missing_ok=True)
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    print(f"Wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case")
    parser.add_argument("--checkpoint-every", type=int, default=10)
    args = parser.parse_args()
    asyncio.run(
        run(
            args.base_url,
            args.k,
            args.limit,
            args.case,
            args.checkpoint_every,
        )
    )


if __name__ == "__main__":
    main()
