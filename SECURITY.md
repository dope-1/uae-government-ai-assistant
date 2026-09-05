# Security

This is an independent portfolio/research project, not an official UAE government service.

## Data and secrets

- Do not put real credentials, UAE government credentials, API keys or private citizen data in the repository.
- Secrets belong in environment variables or a deployment secrets manager and must never be committed.
- Production telemetry intentionally excludes raw user questions, answer text and client IP addresses.
- Redis cache keys contain hashes of canonical request fields rather than raw questions.

## Production controls

Milestone 8 adds request IDs, structured JSON logs, request-size limits, trusted-host validation,
security headers, Redis-backed rate limiting, bounded Redis response caching and guarded operational
metrics. `APP_ENV=production` fails fast if wildcard CORS/trusted hosts are configured, rate limiting
or security headers are disabled, the local development database credential is still present, or the
operations metrics endpoint is enabled without `OPS_METRICS_TOKEN`.

`RATE_LIMIT_TRUST_FORWARDED_FOR=true` should be used only when the backend is private behind a
trusted reverse proxy that overwrites `X-Forwarded-For`; otherwise direct clients could spoof that
header. The default is `false`.

The ingestion pipeline uses allow-listed project source manifests; the public API does not accept an
arbitrary URL to fetch, which keeps user-driven SSRF outside the application boundary.

## Reporting

Do not include real secrets in security reports or issues. Report the affected component, expected
behaviour, reproduction steps using synthetic data, and the minimum information necessary to fix it.
