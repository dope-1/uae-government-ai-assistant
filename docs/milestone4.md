# Milestone 4 — Grounded Bilingual RAG

## Implemented

- `POST /api/v1/chat`
- PostgreSQL lexical retrieval + pgvector dense retrieval + reciprocal-rank fusion
- deterministic reranking baseline for the live API path
- Arabic/English language detection and same-language responses
- explicit jurisdiction detection/filtering
- cross-emirate ambiguity handling
- backend-built citation objects from retrieved metadata
- unsupported citation-marker removal
- proposition-aware insufficient-evidence refusal before generation
- retrieval evidence treated as untrusted prompt data
- provider abstraction with:
  - offline grounded extractive baseline
  - local Ollama provider
  - hosted OpenAI-compatible provider
- offline regression evaluation for answer status, language, fact coverage and citations

## Safety boundary

Government facts must come from retrieved evidence. The LLM receives evidence inside clearly marked
`<evidence>` blocks and the system prompt explicitly treats those blocks as untrusted data. URLs are
never requested from the model: citation URLs are constructed from stored source metadata.

Grounding uses two conservative gates before generation. The first checks topical overlap. The second
checks **answer-bearing focus terms** after discounting the service/title subject and generic relation
verbs. This prevents a page about the Golden Visa from being treated as evidence that a sponsor is or
is not required when the retrieved passage never mentions sponsorship. If either gate fails, the
generator is not called and the assistant returns an unverified response. This is a deterministic safety
heuristic, not semantic entailment or a calibrated confidence probability.

If top evidence spans both Dubai and Abu Dhabi and the question did not specify an emirate, the
assistant asks for jurisdiction instead of merging rules.

## Offline RAG regression

Run:

```bash
python scripts/evaluate_rag.py
```

The checked-in 10-case fixture produced:

| Check | Result |
|---|---:|
| Status accuracy | 1.000 |
| Language accuracy | 1.000 |
| Expected fact coverage | 1.000 |
| Citation precision | 0.850 |
| Citation recall | 0.950 |
| Citation presence rate | 1.000 |

These are deterministic regression checks over a tiny curated fixture. They are **not** production
accuracy, calibrated confidence, semantic faithfulness, or an LLM-as-judge result.

## Provider configuration

The safe local default is:

```env
LLM_PROVIDER=extractive
```

For a local model server:

```env
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
```

For a hosted OpenAI-compatible API, set the provider, base URL, model and API key. No hosted key is
required for the default development path.
