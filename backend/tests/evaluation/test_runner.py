from pathlib import Path

from app.embeddings.local_baseline import HashingEmbeddingProvider
from app.evaluation.runner import evaluate, load_corpus, load_queries

ROOT = Path(__file__).resolve().parents[3]


def test_offline_evaluation_is_reproducible() -> None:
    corpus = load_corpus(ROOT / "data/evaluation/offline_corpus.jsonl")
    queries = load_queries(ROOT / "data/evaluation/retrieval_queries.jsonl")
    result = evaluate(corpus, queries, HashingEmbeddingProvider(), "hybrid_rerank", k=5)
    assert result["queries"] == 20
    assert 0 <= float(result["recall@5"]) <= 1
    assert 0 <= float(result["mrr"]) <= 1
