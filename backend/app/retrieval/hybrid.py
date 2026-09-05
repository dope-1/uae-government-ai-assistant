from __future__ import annotations

from app.ingestion.schemas import DocumentChunk


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[DocumentChunk, float]]],
    *,
    k: int = 10,
    rrf_constant: int = 60,
) -> list[tuple[DocumentChunk, float]]:
    scores: dict[str, float] = {}
    chunks: dict[str, DocumentChunk] = {}
    for ranked in ranked_lists:
        for rank, (chunk, _) in enumerate(ranked, start=1):
            chunks[chunk.id] = chunk
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (rrf_constant + rank)
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))[:k]
    return [(chunks[chunk_id], scores[chunk_id]) for chunk_id in ordered]
