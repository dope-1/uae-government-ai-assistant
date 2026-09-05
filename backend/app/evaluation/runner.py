from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from app.embeddings.base import EmbeddingProvider
from app.evaluation.metrics import ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
from app.ingestion.schemas import DocumentChunk
from app.retrieval.pipeline import RetrievalPipeline


@dataclass(frozen=True)
class EvalQuery:
    id: str
    query: str
    relevant_ids: set[str]
    language: str


def load_corpus(path: Path) -> list[DocumentChunk]:
    chunks = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            chunks.append(DocumentChunk.model_validate(json.loads(line)))
    return chunks


def load_queries(path: Path) -> list[EvalQuery]:
    queries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            queries.append(
                EvalQuery(
                    id=row["id"],
                    query=row["query"],
                    relevant_ids=set(row["relevant_ids"]),
                    language=row["language"],
                )
            )
    return queries


def evaluate(
    chunks: list[DocumentChunk],
    queries: list[EvalQuery],
    provider: EmbeddingProvider,
    method: str,
    *,
    k: int = 5,
) -> dict[str, float | int | str]:
    pipeline = RetrievalPipeline(chunks, provider)
    rows = []
    for query in queries:
        results = pipeline.search(query.query, method=method, k=k)
        retrieved = [chunk.id for chunk, _ in results]
        rows.append(
            (
                recall_at_k(retrieved, query.relevant_ids, k),
                precision_at_k(retrieved, query.relevant_ids, k),
                reciprocal_rank(retrieved, query.relevant_ids),
                ndcg_at_k(retrieved, query.relevant_ids, k),
            )
        )
    return {
        "method": method,
        "queries": len(queries),
        f"recall@{k}": mean(row[0] for row in rows),
        f"precision@{k}": mean(row[1] for row in rows),
        "mrr": mean(row[2] for row in rows),
        f"ndcg@{k}": mean(row[3] for row in rows),
    }
