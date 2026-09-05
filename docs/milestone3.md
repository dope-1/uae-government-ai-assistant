# Milestone 3 — Retrieval completion record

## Implemented

- Unicode/Arabic-aware query tokenisation
- BM25 retrieval
- dense vector retrieval
- reciprocal-rank-fusion hybrid retrieval
- deterministic reranking baseline
- optional production cross-encoder reranker
- jurisdiction metadata filtering
- Recall@K
- Precision@K
- MRR
- NDCG@K
- reproducible offline evaluation runner
- English, Arabic and mixed-language evaluation queries

## Verification

`python scripts/evaluate.py` reproduces the checked-in results file. The current test suite verifies
all four retrieval modes and confirms that jurisdiction filtering can exclude an otherwise matching
chunk from a different emirate.

## Important model distinction

The metrics checked into this milestone use the offline hashing embedding baseline and deterministic
reranker. They are engineering regression metrics only. The repository must not describe them as
results for multilingual E5 or BGE reranking until those models are actually executed.

## Next milestone

Milestone 4 can now integrate retrieval with grounded generation, citation construction,
insufficient-evidence behaviour and bilingual answer generation. Before public deployment, the live
source ingestion and production multilingual model smoke tests should also be run in an environment
with internet access and PostgreSQL/pgvector available.
