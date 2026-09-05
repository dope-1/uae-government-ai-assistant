from __future__ import annotations


class SentenceTransformerEmbeddingProvider:
    """Production-oriented multilingual embedding provider.

    Default model is multilingual-e5-small (384 dimensions). The dependency and model
    weights are intentionally optional so base API development is possible offline.
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed; install the 'ml' extra"
            ) from exc
        self.name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [[float(value) for value in row] for row in vectors.tolist()]
