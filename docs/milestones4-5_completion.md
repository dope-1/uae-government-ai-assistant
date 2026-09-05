# Milestones 4–5 Completion Report

## Milestone 4

Implemented grounded bilingual RAG with hybrid PostgreSQL retrieval, jurisdiction handling,
evidence-sufficiency checks, backend-created citations, citation-marker validation, unverified
responses, prompt-injection separation and three generation-provider paths.

## Milestone 5

Implemented structured service storage, six typed read-only tools, a bounded deterministic
service-discovery agent, source/service API endpoints and metadata-only service seeding tied to
successfully ingested official sources.

## Verification performed in build workspace

- backend test suite: 30 passed
- Python compilation: passed
- retrieval regression: reproduced
- grounded RAG regression: reproduced
- Alembic static SQL generation through revision `0003`: passed

Ruff and mypy could not be executed in this workspace because the environment cannot reach PyPI and
does not have those executables installed. They remain required local verification steps.

## Required developer-machine verification

1. merge the repository without deleting `.env` or `backend/.venv`
2. reinstall editable dev dependencies
3. run Ruff, mypy and pytest
4. run `alembic upgrade head`
5. rebuild the backend container
6. verify `/ready`
7. seed verified service metadata
8. test `/chat`, `/search`, `/services`, `/sources` and the bounded-agent endpoint
