# Milestone 9 — Deployment

This document deploys the frozen Milestone 8 system without changing the Milestone 7 RAG/evaluation
contract.

The project is an independent portfolio/research application. It is not an official UAE government
service and is not affiliated with any UAE government authority.

## Recommended deployment architecture

| Layer | Service | Reason |
|---|---|---|
| Frontend | Vercel Hobby | Native Next.js deployment, HTTPS, CDN and Git-based deploys |
| Backend | Hugging Face Docker Space, CPU Basic | The E5 + PyTorch runtime needs substantially more memory than 512 MB free web-service tiers |
| PostgreSQL + pgvector | Neon Free | Managed PostgreSQL, pgvector support, TLS, enough capacity for the small demo corpus |
| Redis | Upstash Redis Free | Managed TLS Redis suitable for cache/rate-limit state |

Research date: 4 September 2026. Re-check provider limits before deployment because cloud plans can
change. At this date Vercel Hobby is free for personal projects; Neon Free provides 0.5 GB storage;
Upstash Free provides 256 MB / 500K commands monthly; Hugging Face CPU Basic has no hourly hardware
cost but creating Docker/Gradio compute Spaces requires a PRO account ($9/month).

Official references:

- https://vercel.com/docs/plans/hobby
- https://neon.com/pricing
- https://neon.com/docs/ai/ai-google-colab
- https://upstash.com/pricing/redis
- https://huggingface.co/pricing
- https://huggingface.co/docs/hub/spaces-sdks-docker
- https://huggingface.co/docs/hub/spaces-overview

## Why not the Render Free backend for this build?

Render Free currently provides 512 MB RAM and spins down after 15 minutes idle. The project's
`intfloat/multilingual-e5-small` runtime uses PyTorch/SentenceTransformers and is a poor fit for a
512 MB process budget. A paid Render instance with at least 2 GB RAM remains a valid alternative,
but the deployment below uses a Hugging Face Docker Space because it fits the model more naturally.

## 1. Local verification before deployment

From `backend`:

```powershell
ruff check .
mypy app
python -m pytest -q
```

From the project root:

```powershell
python scripts\security_audit_m8.py
python scripts\export_hf_space.py
```

The exporter creates `dist\huggingface-space`. It copies only the backend runtime source and creates
a Docker Space Dockerfile that bakes the frozen multilingual E5 model into the image. It does not
copy `.env`, local databases, tests, evaluation responses, or user data.

## 2. Create the managed PostgreSQL database

1. Create a Neon project.
2. Use the same major PostgreSQL family supported by the project (PostgreSQL 16 is preferred).
3. In the Neon connection dialog, select a **direct/unpooled** connection for the bootstrap and API.
4. Copy the connection string. Neon normally gives a URL beginning with `postgresql://` and TLS
   parameters such as `sslmode=require`. The M9 backend normalizes that URL for SQLAlchemy/asyncpg.
5. Never commit this connection string.

The Free plan's 0.5 GB storage is sufficient for this small portfolio corpus, but it is not a
production-SLA database.

## 3. Create Redis

Create one Upstash Redis database and copy the TLS connection URL. Use the Redis protocol URL that
starts with `rediss://`, not the REST URL/token, because this backend uses `redis-py`.

Never commit the Redis password.

## 4. Bootstrap the cloud database from the trusted local project

Do this **before** making the public backend live. The existing local manifest and verified-service
catalogue remain the source of truth; the deployment bundle does not invent or duplicate them.

In the same PowerShell session with the backend venv activated:

```powershell
$env:DATABASE_URL = '<NEON_DIRECT_CONNECTION_STRING>'
python scripts\bootstrap_m9_cloud.py
Remove-Item Env:DATABASE_URL
```

The script runs, in order:

1. Alembic migrations (including pgvector extension/schema)
2. live official-source ingestion
3. verified structured-service seeding
4. corpus audit

It refuses to run against localhost and never prints the raw connection string.

## 5. Create the Hugging Face Docker Space

A PRO account is required to create a Docker Space on compute as of the research date.

1. Create a **public Docker Space** named something like `uae-government-ai-assistant-api`.
2. Keep CPU Basic hardware. It provides 2 vCPU / 16 GB RAM and has no hourly hardware charge.
3. Clone the new Space repository to a separate folder.
4. Copy the **contents** of `dist\huggingface-space` into the Space repository.
5. Commit and push.

Example after replacing `<HF_USERNAME>` and `<SPACE_NAME>`:

```powershell
cd E:\Projects
git clone https://huggingface.co/spaces/<HF_USERNAME>/<SPACE_NAME> uae-ai-hf-space
Copy-Item E:\Projects\uae-government-ai-assistant\dist\huggingface-space\* `
    E:\Projects\uae-ai-hf-space -Recurse -Force
cd E:\Projects\uae-ai-hf-space
git add .
git commit -m "Deploy UAE Government AI Assistant API"
git push
```

The Space URL will normally be:

```text
https://<HF_USERNAME>-<SPACE_NAME>.hf.space
```

## 6. Configure backend Space secrets/variables

In the Space settings, put credentials in **Secrets** and non-secret settings in **Variables**.

Secrets:

```text
DATABASE_URL=<Neon direct connection string>
REDIS_URL=<Upstash rediss:// connection string>
OPS_METRICS_TOKEN=<long random token>
```

Variables (replace hostnames with the actual deployed values):

```text
APP_ENV=production
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1
CORS_ORIGINS=https://<VERCEL_PROJECT>.vercel.app
TRUSTED_HOSTS=<HF_USERNAME>-<SPACE_NAME>.hf.space,localhost,127.0.0.1
READY_CHECK_TIMEOUT_SECONDS=8

EMBEDDING_PROVIDER=e5
EMBEDDING_MODEL=intfloat/multilingual-e5-small
LLM_PROVIDER=extractive
CACHE_ENABLED=true
CACHE_VERSION=m8-v1
CACHE_TTL_SECONDS=300
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_FAIL_OPEN=true
RATE_LIMIT_TRUST_FORWARDED_FOR=false
MAX_REQUEST_BODY_BYTES=16384
SECURITY_HEADERS_ENABLED=true
OPS_METRICS_ENABLED=true
```

Do not set wildcard CORS/trusted hosts. Do not publish the operations token.

After the Space becomes healthy, test:

```text
https://<HF_USERNAME>-<SPACE_NAME>.hf.space/api/v1/ready
```

## 7. Put the main project in Git before Vercel import

The current local directory might not yet be a Git repository. Before `git add`, verify `.gitignore`
contains at least:

```text
.env
.venv/
backend/.venv/
node_modules/
frontend/node_modules/
.next/
frontend/.next/
__pycache__/
*.pyc
dist/
```

Then initialize/push the main project to the portfolio GitHub repository. Do not commit any secret.

## 8. Deploy the Next.js frontend to Vercel

1. Import the main GitHub repository into Vercel.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Next.js.
4. Add the Production environment variable:

```text
BACKEND_INTERNAL_URL=https://<HF_USERNAME>-<SPACE_NAME>.hf.space/api/v1
```

5. Deploy.

The browser calls the same-origin Next.js route `/api/backend/...`; the Vercel server route then
forwards to the backend. The backend URL is therefore not embedded in client-side JavaScript.

## 9. Final public verification

After both URLs are live:

```powershell
python scripts\verify_deployment_m9.py `
    --frontend-url https://<VERCEL_PROJECT>.vercel.app `
    --backend-url https://<HF_USERNAME>-<SPACE_NAME>.hf.space
```

Without an operations token, the verifier expects `/api/v1/ops/metrics` to return `401`.
To also verify authenticated private telemetry:

```powershell
python scripts\verify_deployment_m9.py `
    --frontend-url https://<VERCEL_PROJECT>.vercel.app `
    --backend-url https://<HF_USERNAME>-<SPACE_NAME>.hf.space `
    --ops-token '<OPS_METRICS_TOKEN>'
```

The verifier writes:

```text
experiments/evaluation/milestone9_deployment_results.json
```

It checks backend readiness, PostgreSQL/Redis connectivity, production security headers, the Vercel
frontend, the same-origin proxy, one grounded end-to-end chat response with citations, and protection
of the operations endpoint.

## Milestone 9 completion gate

Milestone 9 is complete only after all of the following are observed on the real deployment:

- backend public HTTPS endpoint is live
- PostgreSQL readiness is true
- Redis readiness is true
- frontend public HTTPS endpoint is live
- Vercel proxy reaches the backend
- grounded chat returns at least one citation
- operations metrics are protected by bearer authentication
- `verify_deployment_m9.py` exits successfully and writes a passing result

Do not claim deployment completion based only on local Docker tests or successful cloud builds.
