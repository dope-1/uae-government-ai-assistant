# Retrieval experiments

Run from the repository root:

```bash
python scripts/evaluate.py
```

The script evaluates `bm25`, `dense`, `hybrid` and `hybrid_rerank` against the deterministic offline
fixture and rewrites `offline_baseline_results.json` with actual measured values.
