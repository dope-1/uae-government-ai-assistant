# Model Card — UAE Government AI Assistant

## Model / system name

UAE Government AI Assistant

## System type

Bilingual Arabic/English retrieval-augmented public-service information assistant.

This is a system-level model card. The application combines deterministic retrieval, multilingual embeddings, reranking, grounding logic and a conservative answer generator.

## Intended use

The system is intended to:

- demonstrate production AI engineering and multilingual RAG;
- help users locate relevant official UAE public-service information;
- answer bounded factual questions using retrieved official-source evidence;
- expose citations so users can verify important information at the source.

## Out-of-scope use

The system is not intended to:

- provide legal or immigration advice;
- make authoritative eligibility determinations;
- replace official government portals;
- submit applications or payments;
- modify government records;
- make autonomous decisions on behalf of users.

## Languages and jurisdictions

Languages:

- English
- Arabic

Jurisdictions represented in the bounded demo corpus:

- UAE Federal
- Dubai
- Abu Dhabi

## Data

The deployed corpus contains 12 enabled official sources:

- Federal: 5
- Dubai: 3
- Abu Dhabi: 4
- English: 7
- Arabic: 5

The structured service catalogue contains 11 verified services.

The project records source provenance and only seeds structured services when an ingested source exists.

## Embeddings

Production embedding model:

`intfloat/multilingual-e5-small`

The model is packaged into the backend container image.

## Retrieval

The production retrieval stack combines:

- lexical search;
- pgvector dense search;
- reciprocal-rank fusion;
- reranking;
- jurisdiction filtering.

## Answer generation

The public deployment uses a conservative extractive generation path.

The system performs grounding/support checks and may refuse when evidence is insufficient rather than producing unsupported free-form answers.

## Evaluation

Frozen Milestone 7 retrieval:

| Metric | Result |
|---|---:|
| Recall@5 | 1.000 |
| Precision@5 | 0.200 |
| MRR | 0.941026 |
| NDCG@5 | 0.956408 |

Frozen Milestone 7 end-to-end:

| Metric | Result |
|---|---:|
| Status accuracy | 1.000 |
| Language accuracy | 1.000 |
| Expected fact coverage | 1.000 |
| Citation correctness | 1.000 |
| Citation completeness | 1.000 |
| Context fact coverage | 0.984615 |
| Lexical relevance | 0.680736 |

These are fixed engineering benchmark results, not universal real-world accuracy guarantees.

## Qualitative review caveat

The qualitative set contains 30 samples. Ten English samples were manually reviewed by the developer; twenty Arabic/mixed samples were AI-assisted. It is therefore not described as an independent 30-case human review.

## Safety and grounding

Implemented controls include:

- source-grounded citations;
- insufficient-evidence refusal;
- jurisdiction filtering;
- cross-jurisdiction conflict handling;
- separation of retrieved content from system instructions;
- bounded allow-listed read-only agent tools;
- request size limits;
- rate limiting;
- trusted-host validation;
- protected operational metrics.

## Privacy

Operational telemetry is designed not to record:

- raw user queries;
- generated answer text;
- client IP addresses.

Browser conversation history is local to the user's browser in the current implementation.

## Limitations

The corpus is deliberately bounded and does not cover every UAE government service.

Government procedures, fees, requirements and URLs can change after ingestion. Users should verify important information through the cited official source.

Arabic quality is evaluated partly through AI-assisted review rather than fully independent bilingual human review.

The public answer path prioritises groundedness over conversational creativity and may refuse questions that a broader general-purpose model might attempt to answer.

## Responsible deployment

This project is an independent portfolio/research system and is not affiliated with the UAE Government or any UAE government organisation.
