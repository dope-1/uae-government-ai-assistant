# Model / Provider Card

## Embeddings

Default: `intfloat/multilingual-e5-small` through `sentence-transformers`.

The embedding layer is abstracted behind `EmbeddingProvider`. A deterministic hashing provider is
retained solely for offline tests and reproducible regression benchmarks; it is not presented as a
production semantic model.

## Generation

The application supports three generation paths:

1. `grounded-extractive-baseline` — no external model; selects concise query-relevant sentences from retrieved evidence and cites them.
2. Ollama — local/open-source model serving path.
3. OpenAI-compatible hosted API — optional hosted provider path.

No provider is permitted to create citation URLs. Citation provenance is constructed by the backend
from retrieved database metadata.

## Known limitations

- The offline extractive baseline is intentionally simplistic.
- The small RAG evaluation set is a regression fixture, not a representative production benchmark.
- Full bilingual human evaluation and adversarial evaluation are deferred to Milestone 7.
- Confidence is a heuristic evidence-support level, not a calibrated probability.
