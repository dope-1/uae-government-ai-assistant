from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.embeddings.local_baseline import HashingEmbeddingProvider  # noqa: E402
from app.evaluation.runner import evaluate, load_corpus, load_queries  # noqa: E402


def main() -> None:
    corpus = load_corpus(ROOT / "data/evaluation/offline_corpus.jsonl")
    queries = load_queries(ROOT / "data/evaluation/retrieval_queries.jsonl")
    provider = HashingEmbeddingProvider(dimension=384)
    methods = ["bm25", "dense", "hybrid", "hybrid_rerank"]
    results = [evaluate(corpus, queries, provider, method, k=5) for method in methods]
    out = ROOT / "experiments/retrieval/offline_baseline_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
