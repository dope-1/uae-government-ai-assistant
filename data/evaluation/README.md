# Evaluation data

- `rag_cases.jsonl`: small deterministic grounded-RAG engineering regression.
- `offline_corpus.jsonl`: checked-in offline retrieval fixture.
- `retrieval_queries.jsonl`: small retrieval regression queries.
- `milestone7_cases.jsonl`: 180-case bilingual/mixed-language live evaluation suite (`m7-v2`).
- `human_review_sample.csv`: generated review template; regenerate after the final live M7 run.

Milestone 7 source labels are source-level rather than chunk-level so re-ingestion does not make the
benchmark stale solely because chunk IDs changed. Mixed-language service cases can declare
`acceptable_source_ids` for equivalent official English/Arabic pages. A small number of pure-language
cases may also accept a more specific official cross-language page when the preferred same-language
page does not contain the requested detail; response language is evaluated independently.
`expected_source_ids` remains the preferred gold source; an accepted alternative is not treated as
hallucinated evidence.

Do not insert synthetic markers such as `variant 2` into benchmark queries. The suite validator
rejects them.
