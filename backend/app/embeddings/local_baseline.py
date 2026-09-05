from __future__ import annotations

from sklearn.feature_extraction.text import HashingVectorizer


class HashingEmbeddingProvider:
    """Offline multilingual lexical baseline, not a semantic production embedding model."""

    name = "hashing-char-ngram-baseline"

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._vectorizer = HashingVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            n_features=dimension,
            alternate_sign=False,
            norm="l2",
            lowercase=True,
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        matrix = self._vectorizer.transform(texts).toarray()
        return [[float(value) for value in row] for row in matrix]
