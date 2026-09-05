# Milestone 1 — Foundation decision record

## Scope

Milestone 1 establishes only the project foundation: repository structure, Python/FastAPI backend, PostgreSQL with pgvector, Redis, Docker Compose, configuration management, health/readiness endpoints, CI, migrations, and initial tests. RAG, ingestion, agents, LLM calls, evaluation datasets, and the frontend are intentionally deferred.

## Technical decisions

- **Python 3.12 in containers**: current, broadly supported by the selected backend packages.
- **FastAPI + Pydantic v2**: typed API contracts and OpenAPI generation.
- **PostgreSQL 16 + pgvector**: one durable relational store with vector capability, avoiding a second vector database during the portfolio's initial stages.
- **Redis 7**: reserved for caching/rate-limiting/session support in later milestones.
- **SQLAlchemy async + asyncpg**: async database boundary without tying domain logic to a driver.
- **Alembic**: migration path begins with enabling pgvector; domain tables arrive in later milestones.
- **Docker Compose**: reproducible local infrastructure with no paid cloud dependency.
- **CI on Python 3.12**: Ruff, mypy, pytest, and backend Docker image build.

## External accounts / API keys

None are required for Milestone 1. A hosted LLM provider and cloud deployment credentials are intentionally not introduced yet.

## Verification contract

A completed Milestone 1 should satisfy:

1. Backend unit/API tests pass.
2. Python source compiles.
3. Compose YAML parses successfully.
4. In a Docker-capable environment, `docker compose up --build` starts PostgreSQL, Redis, and FastAPI, after which `/api/v1/health` returns 200 and `/api/v1/ready` returns 200.
5. `ruff check .` and `mypy app` pass in the development environment/CI.

This workspace does not have Docker, Ruff, or mypy installed globally, so those commands cannot be truthfully reported as locally executed unless dependencies are installed. CI is configured to execute them from declared project dependencies.
