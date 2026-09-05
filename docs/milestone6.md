# Milestone 6 — Bilingual Frontend

## Scope

Milestone 6 adds the production-style user interface without changing the retrieval or grounding
semantics verified in Milestones 1–5.

## Stack

- Next.js App Router
- React
- TypeScript in strict mode
- responsive CSS with no government-brand copying
- same-origin server-side proxy to the FastAPI API

## Implemented experience

- English and Arabic UI modes
- RTL/LTR document direction switching
- chat interface wired to `POST /api/v1/chat`
- Federal / Abu Dhabi / Dubai / automatic jurisdiction selection
- visible grounding state: grounded, limited evidence, or not verified
- expandable citations with authority, jurisdiction, excerpt, retrieval time and official link
- indexed service explorer wired to `GET /api/v1/services`
- runtime readiness card for FastAPI, PostgreSQL and Redis
- suggested Federal, Dubai and Abu Dhabi demo prompts
- responsive desktop/tablet/mobile layouts
- browser-local conversation history
- browser-local thumbs-up/down feedback placeholder
- explicit independent-project/non-affiliation disclaimer
- accessible keyboard submission and focus states
- reduced-motion support

## Honesty boundaries

Conversation history in this milestone is a browser-local presentation feature. The backend does not
yet use prior turns as semantic context, so the frontend does not claim that follow-up questions are
resolved from server-side conversation memory.

Feedback controls are also stored locally only. They are visually available for product evaluation,
but are not described as submitted to the backend until a later feedback persistence milestone.

The UI labels the backend grounding score as a support heuristic and explicitly states that it is not
a calibrated probability.

## API boundary

Browser requests use:

```text
Browser
  |
  v
Next.js /api/backend/*
  |
  v
FastAPI /api/v1/*
```

This keeps the Docker-only hostname `backend` on the server side and prevents environment-specific
backend URLs from leaking into browser code.

Local Next.js development defaults to `http://localhost:8000/api/v1`; Docker sets
`BACKEND_INTERNAL_URL=http://backend:8000/api/v1`.

## Local verification

```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
npm run lint
npm run typecheck
npm run build
npm run dev
```

With the full Docker stack:

```powershell
docker compose up -d --build
```

Then open `http://localhost:3000`.
