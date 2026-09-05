from __future__ import annotations

from app.embeddings.base import EmbeddingProvider
from app.ingestion.schemas import DocumentChunk
from app.retrieval.bm25 import BM25Index
from app.retrieval.dense import DenseIndex
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.reranking import TokenOverlapReranker


class RetrievalPipeline:
    def __init__(self, chunks: list[DocumentChunk], provider: EmbeddingProvider) -> None:
        self.chunks = chunks
        self.bm25 = BM25Index(chunks)
        self.dense = DenseIndex(chunks, provider)
        self.reranker = TokenOverlapReranker()

    def search(
        self,
        query: str,
        *,
        method: str = "hybrid_rerank",
        k: int = 5,
        candidate_k: int = 20,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        if method == "bm25":
            return self.bm25.search(query, k, jurisdiction=jurisdiction)
        if method == "dense":
            return self.dense.search(query, k, jurisdiction=jurisdiction)
        bm25 = self.bm25.search(query, candidate_k, jurisdiction=jurisdiction)
        dense = self.dense.search(query, candidate_k, jurisdiction=jurisdiction)
        hybrid = reciprocal_rank_fusion([bm25, dense], k=candidate_k)
        if method == "hybrid":
            return hybrid[:k]
        if method == "hybrid_rerank":
            return self.reranker.rerank(query, hybrid, k)
        raise ValueError(f"unknown retrieval method: {method}")
