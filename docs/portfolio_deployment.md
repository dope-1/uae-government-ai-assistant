# Production Deployment

## Status

Milestone 9 deployment is complete and publicly verified.

**Canonical frontend:**  
https://uae-government-ai-assistant.vercel.app

The frontend is deployed on Vercel. The FastAPI backend runs on Google Cloud Run in `europe-west3`, with Neon PostgreSQL + pgvector and Upstash Redis in Frankfurt-region infrastructure.

## Deployment topology

```text
Browser
   ↓
Vercel / Next.js
   ↓
same-origin server proxy
   ↓
Google Cloud Run / FastAPI
   ├─ Neon PostgreSQL + pgvector
   └─ Upstash Redis
```

## Backend deployment

The backend container includes `intfloat/multilingual-e5-small`, avoiding a runtime model download for the production embedding path.

Production controls include:

- 1 vCPU
- 2 GiB memory
- concurrency 4
- minimum instances 0
- maximum instances 1
- request timeout 300 seconds
- public HTTPS ingress
- dedicated runtime service account
- Secret Manager injection for database, Redis and ops credentials

## Frontend deployment

The repository is connected to Vercel through GitHub.

Vercel project configuration:

- Framework: Next.js
- Root directory: `frontend`
- server-side backend variable: `BACKEND_INTERNAL_URL`
- production domain: `uae-government-ai-assistant.vercel.app`

`output: "standalone"` remains available for non-Vercel Docker/self-hosted builds and is disabled when Vercel performs its own Next.js packaging.

## Deployment verification

The public verifier checks:

```text
PASS backend readiness
PASS backend request/security headers
PASS frontend root
PASS frontend-to-backend proxy
PASS end-to-end grounded chat
PASS operational metrics require authentication
```

Final machine-readable result:

`experiments/evaluation/milestone9_deployment_results.json`

The recorded result has `"passed": true`.

## Operational security

Secrets are not stored in the repository. Production credentials are supplied through managed secret storage.

Operational metrics are protected. Without authentication the public metrics endpoint is expected to return HTTP 401.

The application also includes:

- trusted-host validation
- security headers
- request-body size controls
- Redis-backed rate limiting
- privacy-aware operational telemetry
- request IDs
- cache TTL/version invalidation

## Cost posture

The public portfolio deployment is intentionally low-scale:

- Cloud Run scales to zero and is capped at one instance.
- The embedding model is packaged into the image.
- The default public answer path is extractive rather than a paid hosted LLM.
- Managed service usage is bounded for a portfolio demonstration.

## Re-verification

Use:

```powershell
python scripts/verify_deployment_m9.py `
  --frontend-url "https://uae-government-ai-assistant.vercel.app" `
  --backend-url "https://uae-government-ai-assistant-api-osj6ztd3ua-ey.a.run.app"
```

Do not pass production secrets on the command line unless there is a specific reason to verify an authenticated endpoint.
