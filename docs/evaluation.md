# Evaluation

## Retrieval regression

`python scripts/evaluate.py` evaluates the small checked-in bilingual retrieval fixture with
Recall@5, Precision@5, MRR and NDCG@5. It compares BM25, deterministic dense hashing, hybrid RRF and
hybrid + deterministic reranking.

The fixture is for repeatable CI/regression testing; it is not a production benchmark.

## Grounded RAG regression

`python scripts/evaluate_rag.py` runs the small English/Arabic regression covering answerable
Federal information, Dubai and Abu Dhabi procedures, Arabic queries, unavailable information and
cross-emirate ambiguity. It is an engineering gate rather than the Milestone 7 benchmark.

## Milestone 7 live benchmark

The current suite version is `m7-v2` and contains 180 cases. Run:

```bash
python scripts/validate_m7_dataset.py
python scripts/evaluate_m7_retrieval_live.py
python scripts/evaluate_m7_live.py
```

The live answer report separates status accuracy from answerable-only fact/citation metrics. Expected
refusals and clarification turns are not counted as perfect citation/fact scores. `context_fact_coverage`
is computed from citation excerpts and is independent of citation source-ID correctness.

`answer_relevance_lexical` is a normalized lexical-overlap diagnostic, not a semantic relevance
score. Mixed-language cases accept either English or Arabic output unless an explicit response
language is requested by a future benchmark case. Semantic faithfulness is intentionally left null
until the human-review workflow is completed.

The first full `m7-v1` run was a diagnostic run and revealed benchmark and grounding defects. Do not
quote its aggregate values as final project quality metrics. Final reported results must include the
`suite_version` emitted by the evaluation scripts.
