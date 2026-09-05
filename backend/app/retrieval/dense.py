from __future__ import annotations

import numpy as np

from app.embeddings.base import EmbeddingProvider
from app.ingestion.schemas import DocumentChunk


class DenseIndex:
    def __init__(self, chunks: list[DocumentChunk], provider: EmbeddingProvider) -> None:
        self.chunks = chunks
        self.provider = provider
        self.matrix = np.asarray(provider.embed([chunk.text for chunk in chunks]), dtype=float)
        self.matrix = self._normalize(self.matrix)

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.where(norms == 0, 1.0, norms)

    def search(
        self,
        query: str,
        k: int = 10,
        *,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        vector = np.asarray(self.provider.embed([query]), dtype=float)
        vector = self._normalize(vector)[0]
        scores = self.matrix @ vector
        if jurisdiction:
            mask = np.asarray(
                [chunk.jurisdiction == jurisdiction for chunk in self.chunks],
                dtype=bool,
            )
            scores = np.where(mask, scores, -np.inf)
        ordered_indices = np.argsort(-scores, kind="stable")
        order = [
            int(index)
            for index in ordered_indices
            if np.isfinite(scores[int(index)])
        ][:k]
        return [(self.chunks[i], float(scores[i])) for i in order]
