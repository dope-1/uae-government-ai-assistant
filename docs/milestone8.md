# Milestone 8 — Production Engineering

Milestone 8 hardens the assistant as an operable service without adding paid infrastructure.
It does not change the Milestone 7 evaluation set or intentionally retune retrieval/RAG behaviour.

## Implemented controls

### Redis response caching

`POST /api/v1/chat` and `POST /api/v1/search` use deterministic Redis JSON cache keys. Raw user
questions do not appear in Redis key names; the canonical request payload is SHA-256 hashed.
Responses expose `X-Cache: HIT|MISS|BYPASS`. The default TTL is five minutes. `CACHE_VERSION` is an
explicit invalidation knob and should be bumped after a corpus/retrieval contract change.

Cache failures are fail-open: the request executes normally and a structured warning is emitted.
Redis remains a readiness dependency because it is also used for rate limiting.

### Structured observability

HTTP middleware emits JSON logs containing request ID, method, path, status and duration only. It
does not log raw questions or answers. RAG completion telemetry contains status, language,
jurisdiction, model/provider metadata, token counts when the provider reports them, estimated cost
when prices are explicitly configured, and citation count.

Every HTTP response receives `X-Request-ID`. A valid caller-supplied request ID is preserved;
otherwise the API generates one.

`GET /api/v1/ops/metrics` exposes low-cardinality process-local diagnostics: per-route latency
samples, 5xx counts, cache hit/miss rates, rate-limit count and model/token/cost aggregates. In
production this endpoint requires `Authorization: Bearer <OPS_METRICS_TOKEN>`.

### Rate limiting

The expensive chat, search and service-discovery POST endpoints use a Redis fixed-window limiter.
Client identifiers are hashed before they are placed in Redis keys. The default is 60 requests per
60 seconds. Successful requests receive `X-RateLimit-*` headers; rejected requests receive HTTP 429
and `Retry-After`.

The limiter defaults to fail-open on Redis errors so an observability/cache outage does not silently
turn into a total API outage. Production teams may set `RATE_LIMIT_FAIL_OPEN=false` if availability
policy requires fail-closed behaviour.

`RATE_LIMIT_TRUST_FORWARDED_FOR=false` by default. Enable it only when the backend is private behind
a trusted reverse proxy that overwrites `X-Forwarded-For`.

### Model and cost tracking

OpenAI-compatible providers already expose prompt/completion tokens when returned by the provider.
Milestone 8 also records Ollama `prompt_eval_count` and `eval_count`. Local extractive/Ollama paths
are tracked as zero hosted-model cost. For an OpenAI-compatible endpoint, estimated cost remains
`null` unless both per-million-token prices are explicitly configured; no price is fabricated.

### Security hardening

- Trusted host validation.
- 16 KiB default request-body ceiling for write requests.
- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy` headers.
- HSTS in `APP_ENV=production`.
- Production startup rejects wildcard CORS/hosts, disabled rate limiting/security headers, the local
  development database credential, and an unprotected enabled operations endpoint.
- Public API inputs remain bounded by Pydantic limits and no endpoint accepts an arbitrary fetch URL.
- `scripts/security_audit_m8.py` scans tracked/source text for a small set of high-confidence secrets
  and fails if `.env` is tracked.

## Performance benchmark

With the backend running:

```powershell
python scripts\performance_m8.py --endpoint chat --requests 30 --concurrency 5
```

The script writes `experiments/evaluation/milestone8_performance_results.json` with throughput,
status counts, p50/p95/p99/max latency, cache-hit counts and request-ID coverage. It intentionally
omits raw queries and responses.

The default workload stays below the default rate-limit budget. Raise the limit temporarily or run a
separate controlled environment before benchmarking larger loads.

## Verification

Run from the repository root after applying the patch:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
ruff check . --fix
ruff check .
mypy app
python -m pytest -q
cd ..
python scripts\security_audit_m8.py
docker compose up -d --build --force-recreate backend frontend
Invoke-RestMethod http://localhost:8000/api/v1/ready
python scripts\performance_m8.py --endpoint chat --requests 30 --concurrency 5
```

Do not claim the performance numbers until that live benchmark has actually run on the developer
machine. The Milestone 7 result files remain frozen inputs and are not rewritten by Milestone 8.
