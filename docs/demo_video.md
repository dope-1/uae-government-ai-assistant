# Demo and Portfolio Recording Guide

## Live demo

https://uae-government-ai-assistant.vercel.app

## Recommended 90-second demo flow

### 1. Open with the system

Show the home page and state:

> This is an independent bilingual UAE public-service RAG portfolio project covering Federal, Dubai and Abu Dhabi information. It is not an official government application.

### 2. Show production readiness

Briefly point to:

- Backend: Ready
- PostgreSQL: Ready
- Redis: Ready
- service explorer

### 3. Dubai grounded query

Ask:

```text
How do I renew my driving licence in Dubai?
```

Show:

- Dubai jurisdiction;
- grounded status;
- citation/source card;
- official RTA source.

### 4. Federal query

Ask:

```text
Where can I find official information about UAE Golden Visas?
```

Show the UAE Government Portal citation.

### 5. Arabic

Switch to Arabic and demonstrate RTL layout with one Arabic query.

### 6. Close with architecture

Show `docs/assets/architecture.png` and summarise:

```text
Vercel → Next.js proxy → Cloud Run → Neon pgvector + Upstash Redis
```

Mention that production secrets are managed outside the repository.

## Suggested recording checklist

- 1080p screen recording
- browser zoom around 90–100%
- hide unrelated bookmarks/tabs
- use the canonical production URL
- avoid showing cloud consoles, environment variables or secrets
- keep the independent/non-government disclaimer visible at least once
- do not claim the 30-case qualitative evaluation was fully human-reviewed

## Portfolio screenshots

Included assets:

- `docs/assets/demo-home.png`
- `docs/assets/demo-dubai-grounded.png`
- `docs/assets/demo-federal-grounded.png`
- `docs/assets/architecture.png`

An Arabic screenshot can be added later if desired, but no screenshot should be fabricated.

## Suggested portfolio description

> Production-style bilingual Arabic/English UAE public-service AI assistant using FastAPI, Next.js, PostgreSQL/pgvector, Redis, multilingual E5 embeddings, hybrid retrieval, reranking, grounded RAG, citations, bounded agent tools and cloud deployment on Vercel + Google Cloud Run.
