from __future__ import annotations

import math
from collections import Counter

from app.ingestion.schemas import DocumentChunk
from app.retrieval.tokenization import tokenize


class BM25Index:
    def __init__(self, chunks: list[DocumentChunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.avgdl = sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.tokens:
            self.doc_freq.update(set(tokens))

    def search(
        self,
        query: str,
        k: int = 10,
        *,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        q_tokens = tokenize(query)
        n_docs = len(self.chunks)
        scored: list[tuple[DocumentChunk, float]] = []
        for chunk, tokens, doc_len in zip(self.chunks, self.tokens, self.lengths, strict=True):
            if jurisdiction and chunk.jurisdiction != jurisdiction:
                continue
            tf = Counter(tokens)
            score = 0.0
            for term in q_tokens:
                df = self.doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                freq = tf.get(term, 0)
                denom = freq + self.k1 * (
                    1 - self.b + self.b * doc_len / self.avgdl
                ) if self.avgdl else 1.0
                score += idf * (freq * (self.k1 + 1)) / denom
            scored.append((chunk, score))
        return sorted(scored, key=lambda pair: (-pair[1], pair[0].id))[:k]
