from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.embeddings.local_baseline import HashingEmbeddingProvider  # noqa: E402
from app.ingestion.schemas import DocumentChunk  # noqa: E402
from app.llm.providers import GroundedExtractiveLLMProvider  # noqa: E402
from app.rag.service import GroundedRAGService  # noqa: E402
from app.retrieval.pipeline import RetrievalPipeline  # noqa: E402


class OfflineRetriever:
    def __init__(self, pipeline: RetrievalPipeline) -> None:
        self.pipeline = pipeline

    async def search(
        self,
        query: str,
        *,
        k: int = 6,
        candidate_k: int = 24,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        return self.pipeline.search(
            query,
            method="hybrid_rerank",
            k=k,
            candidate_k=candidate_k,
            jurisdiction=jurisdiction,
        )


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_corpus() -> list[DocumentChunk]:
    path = ROOT / "data/evaluation/offline_corpus.jsonl"
    return [DocumentChunk.model_validate(item) for item in read_jsonl(path)]


async def run() -> None:
    cases = read_jsonl(ROOT / "data/evaluation/rag_cases.jsonl")
    provider = HashingEmbeddingProvider()
    pipeline = RetrievalPipeline(load_corpus(), provider)
    service = GroundedRAGService(OfflineRetriever(pipeline), GroundedExtractiveLLMProvider())

    rows: list[dict[str, object]] = []
    for case in cases:
        answer = await service.answer(
            str(case["query"]),
            jurisdiction=str(case["jurisdiction"]) if case.get("jurisdiction") else None,
        )
        relevant = set(case.get("relevant_ids", []))
        cited = {citation.chunk_id for citation in answer.citations}
        expected_phrases = [str(value).lower() for value in case.get("expected_phrases", [])]
        answer_text = answer.answer.lower()
        rows.append(
            {
                "id": case["id"],
                "status_correct": answer.status == case["expected_status"],
                "language_correct": answer.language == case["language"],
                "fact_coverage": (
                    mean(float(phrase in answer_text) for phrase in expected_phrases)
                    if expected_phrases
                    else 1.0
                ),
                "citation_precision": (
                    len(cited & relevant) / len(cited) if cited else (1.0 if not relevant else 0.0)
                ),
                "citation_recall": (
                    len(cited & relevant) / len(relevant)
                    if relevant
                    else (1.0 if not cited else 0.0)
                ),
                "citation_present_when_answered": (
                    answer.status != "answered" or bool(answer.citations)
                ),
            }
        )

    results = {
        "evaluation": "offline_grounded_rag_regression",
        "generator": "grounded-extractive-baseline",
        "retrieval": "hybrid_rerank_offline_baseline",
        "queries": len(rows),
        "status_accuracy": mean(float(row["status_correct"]) for row in rows),
        "language_accuracy": mean(float(row["language_correct"]) for row in rows),
        "expected_fact_coverage": mean(float(row["fact_coverage"]) for row in rows),
        "citation_precision": mean(float(row["citation_precision"]) for row in rows),
        "citation_recall": mean(float(row["citation_recall"]) for row in rows),
        "citation_presence_rate": mean(
            float(row["citation_present_when_answered"]) for row in rows
        ),
        "cases": rows,
        "limitations": (
            "Deterministic offline regression checks over a small curated fixture; "
            "not a production "
            "faithfulness score and not an LLM-as-judge evaluation."
        ),
    }
    out = ROOT / "experiments/rag/offline_grounded_rag_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(run())
