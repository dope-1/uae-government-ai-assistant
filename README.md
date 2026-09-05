# UAE Government AI Assistant

Independent portfolio/research project for a bilingual Arabic-English UAE government-information
assistant. It is **not an official UAE government service and is not affiliated with TAMM, the UAE
Government, Dubai Digital Authority, or any UAE ministry or government organisation**.

## Current status

**Milestones 1–7 are frozen and Milestone 8 production engineering is implemented for local
verification.** The repository includes the backend foundation, real public-source ingestion,
retrieval/evaluation, grounded bilingual RAG, citations, refusal behaviour, structured service
lookup, bounded read-only agent tools, a production-style bilingual Next.js interface, Redis-backed
caching/rate limiting, structured observability, model/cost telemetry, performance tooling and
security hardening. The expanded demo corpus covers Federal, Dubai and Abu Dhabi English/Arabic
workflows, with live audit and cross-jurisdiction smoke utilities.

## Implemented capabilities

- FastAPI with health/readiness, chat, search, service and bounded-agent endpoints
- PostgreSQL + pgvector and Redis
- Alembic migrations through `0003`
- 12-source Federal / Abu Dhabi / Dubai English-Arabic live-demo manifest
- HTML and PDF ingestion
- Arabic normalisation and language detection
- deterministic chunking and source provenance
- multilingual E5 embedding path plus offline deterministic baseline
- BM25, dense, hybrid RRF and reranking experiments
- PostgreSQL lexical + pgvector hybrid retrieval for the RAG API
- jurisdiction filtering and cross-emirate conflict handling
- grounded Arabic/English generation
- backend-constructed source citations
- proposition-aware insufficient-evidence refusal
- prompt-injection separation for retrieved content
- hosted/local model-provider abstraction
- structured government-service records
- six allow-listed read-only tools
- bounded service-discovery agent with tool traces
- bilingual Next.js App Router frontend with responsive Arabic RTL / English LTR layouts
- expandable citation cards, jurisdiction and grounding indicators, indexed service explorer
- same-origin Next.js-to-FastAPI proxy for local and Docker networking
- browser-local conversation history and clearly labelled local feedback controls
- Redis response caching for chat/search with hashed deterministic keys and TTL/version invalidation
- structured JSON request/RAG telemetry with privacy-safe request IDs and no raw query logging
- Redis-backed rate limiting for expensive POST endpoints
- model token/cost accounting without inventing hosted-provider prices
- request-body limits, trusted hosts, security headers and production configuration fail-fast checks
- reproducible HTTP concurrency benchmark and source secret-audit scripts

## Verified Milestones 1–3

On the developer Windows/Docker environment on 2 September 2026:

- FastAPI readiness returned PostgreSQL=`true`, Redis=`true`
- 19/19 pre-Milestone-4 backend tests passed
- Ruff passed after formatting fixes
- mypy reported no issues in 42 source files
- the 20-query retrieval benchmark reproduced the checked-in metrics
- live ingestion downloaded the official federal Golden Visa page
- `intfloat/multilingual-e5-small` generated the persisted chunk embedding
- PostgreSQL confirmed `embedding_model=intfloat/multilingual-e5-small` and `has_embedding=true`

## Retrieval baseline

These are offline engineering-regression metrics, not production accuracy claims:

| Method | Recall@5 | Precision@5 | MRR | NDCG@5 |
|---|---:|---:|---:|---:|
| BM25 | 0.975 | 0.230 | 0.967 | 0.956 |
| Dense hashing baseline | 0.975 | 0.230 | 0.917 | 0.919 |
| Hybrid | 1.000 | 0.240 | 0.942 | 0.945 |
| Hybrid + rerank | 1.000 | 0.240 | 0.975 | 0.971 |

Reproduce with:

```bash
python scripts/evaluate.py
```

## Grounded RAG regression

`python scripts/evaluate_rag.py` currently produces the checked-in 10-case deterministic regression:

| Check | Result |
|---|---:|
| Status accuracy | 1.000 |
| Language accuracy | 1.000 |
| Expected fact coverage | 0.900 |
| Citation precision | 1.000 |
| Citation recall | 0.950 |
| Citation presence rate | 1.000 |

The fixture is intentionally small. These numbers are not a production faithfulness score or a
calibrated probability.

## Local infrastructure

```powershell
Copy-Item .env.example .env
docker compose up -d --build
cd backend
alembic upgrade head
```

Host-side scripts use `localhost:5432` / `localhost:6379`; Docker Compose overrides the backend to use
Docker-network hostnames `postgres` and `redis`.

Frontend: `http://localhost:3000`

OpenAPI: `http://localhost:8000/docs`


## Frontend development

The frontend uses a server-side proxy so browser code does not need Docker-only backend hostnames.

```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
npm run lint
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:3000`. Conversation history and thumbs-up/down feedback are intentionally
browser-local in Milestone 6; the UI does not claim backend conversation memory or feedback
persistence that has not been implemented yet.

## Live source ingestion

```powershell
cd backend
python -m pip install -e ".[ml]"
cd ..
python scripts\ingest.py --list-sources
python scripts\ingest.py --jurisdiction Dubai
python scripts\ingest.py --jurisdiction "Abu Dhabi"
python scripts\ingest.py --jurisdiction Federal
```

Audit what actually landed in PostgreSQL rather than assuming a successful HTTP response yielded a
complete page:

```powershell
python scripts\audit_corpus.py
```

## Structured service metadata

After migration `0003`, seed only services whose official sources have actually been ingested:

```powershell
python scripts\seed_services.py
```

The script skips services without an ingested source and never fills unknown requirements, documents
or fees with guessed values. The expanded catalogue includes localised Arabic discovery entries for
Federal, Dubai and Abu Dhabi demo workflows.

After seeding and rebuilding the backend, run the live cross-jurisdiction smoke suite:

```powershell
python scripts\smoke_multijurisdiction.py
```

## Ask the RAG service

The zero-key default uses the conservative extractive generator:

```powershell
python scripts\chat.py "Does the UAE Golden Visa require a sponsor?" --jurisdiction Federal
```

Or call:

```text
POST /api/v1/chat
POST /api/v1/search
GET  /api/v1/services
GET  /api/v1/services/{id}
GET  /api/v1/sources
GET  /api/v1/sources/{id}
POST /api/v1/agent/service-discovery
GET  /api/v1/health
GET  /api/v1/ready
```

For a local LLM, configure `LLM_PROVIDER=ollama`. A hosted OpenAI-compatible provider is also
available, but no hosted key is required for local development.

## Development verification

```powershell
cd backend
python -m pip install -e ".[dev]"
ruff check .
mypy app
python -m pytest -q
cd ..
python scripts\evaluate.py
python scripts\evaluate_rag.py
```

## Documentation

- `docs/architecture.md`
- `docs/data_sources.md`
- `docs/evaluation.md`
- `docs/milestone1.md`
- `docs/milestone2.md`
- `docs/milestone3.md`
- `docs/milestone4.md`
- `docs/milestone5.md`
- `docs/milestone6.md`
- `docs/milestone7.md`
- `docs/agent_tools.md`
- `docs/model_card.md`
- `docs/corpus_expansion.md`

## Milestone 7 evaluation & safety

The frozen `m7-v2` suite contains 180 English/Arabic/mixed-language cases. The final developer
run produced 1.000 status accuracy, 1.000 language accuracy, 1.000 expected-fact coverage, 1.000
citation correctness, 1.000 citation completeness, 0.984615 context-fact coverage and 0.680736
lexical answer relevance. On the 130 answerable retrieval cases, Recall@5 was 1.000, Precision@5
0.200, MRR 0.941026 and NDCG@5 0.956408.

The qualitative 30-case sheet produced means of 4.50/5 faithfulness, 4.60/5 answer relevance,
4.50/5 citation completeness and 4.43/5 language quality. Methodology note: 10 English rows were
reviewed manually by the developer and the remaining 20 Arabic/mixed rows were AI-assisted, so the
repository does **not** describe that result as an independent 30-case human review. See the
checked-in Milestone 7 result JSON files and `docs/milestone7.md`.

## Milestone 8 production engineering

Milestone 8 adds Redis response caching, structured JSON observability, request IDs, Redis-backed
rate limiting, provider/token/cost accounting, security headers, trusted-host and request-size
controls, guarded operations metrics, a source secret audit, and a reproducible concurrency
benchmark. See `docs/milestone8.md`. The implementation should not be described as locally verified
until the full Ruff/mypy/pytest/Docker/performance commands in that document have run successfully.

## Next milestone

Milestone 9 deploys the frontend, backend and database/Redis infrastructure.
