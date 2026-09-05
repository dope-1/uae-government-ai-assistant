from __future__ import annotations

from app.ingestion.schemas import DocumentChunk
from app.retrieval.tokenization import tokenize


class TokenOverlapReranker:
    """Deterministic offline reranking baseline used for reproducible CI evaluation."""

    name = "token-overlap-baseline"

    def rerank(
        self, query: str, candidates: list[tuple[DocumentChunk, float]], k: int
    ) -> list[tuple[DocumentChunk, float]]:
        q = set(tokenize(query))
        scored = []
        for chunk, base_score in candidates:
            d = set(tokenize(chunk.text))
            overlap = len(q & d) / max(1, len(q))
            scored.append((chunk, overlap + 0.05 * base_score))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0].id))[:k]


class CrossEncoderReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; install the 'ml' extra"
            ) from exc
        self.name = model_name
        self._model = CrossEncoder(model_name)

    def rerank(
        self, query: str, candidates: list[tuple[DocumentChunk, float]], k: int
    ) -> list[tuple[DocumentChunk, float]]:
        pairs = [(query, chunk.text) for chunk, _ in candidates]
        scores = self._model.predict(pairs)
        ranked = [
            (chunk, float(score))
            for (chunk, _), score in zip(candidates, scores, strict=True)
        ]
        return sorted(ranked, key=lambda pair: -pair[1])[:k]
