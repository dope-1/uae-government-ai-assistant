# Frontend

Next.js bilingual interface for the UAE Government AI Assistant portfolio project.

## Local development

Start the FastAPI backend on port 8000 first, then:

```powershell
Copy-Item .env.local.example .env.local
npm install
npm run lint
npm run typecheck
npm run build
npm run dev
```

Open `http://localhost:3000`.

`BACKEND_INTERNAL_URL` is read only by the Next.js server proxy. Browser requests use
`/api/backend/*`, so Docker-only hostnames are never exposed to client code.

## Docker

From the repository root:

```powershell
docker compose up -d --build
```

The frontend container listens on port 3000 and waits for the FastAPI readiness healthcheck.

## Milestone 6 state boundaries

- Conversation history is persisted to browser `localStorage` only.
- Feedback buttons are persisted in the local conversation only and are not submitted to the backend.
- The backend grounding score is shown as a support heuristic, never as a calibrated probability.
- Citations and official URLs come from backend provenance objects; the frontend does not generate them.
