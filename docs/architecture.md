# Architecture

## User request path (Milestones 1–6)

```text
Browser
  |
  v
Next.js bilingual UI
  |
  | same-origin /api/backend proxy
  v
FastAPI
  |
Query analysis
language + jurisdiction
  |
  v
PostgreSQL hybrid retrieval
   /                 \
lexical FTS          pgvector
   \                 /
    reciprocal-rank fusion
           |
    deterministic rerank
           |
   evidence sufficiency
      /          \
insufficient      sufficient
    |                 |
 refusal         context builder
                       |
              LLM provider abstraction
             /          |          \
      extractive      Ollama    hosted compatible
                       |
               citation sanitation
                       |
       backend provenance/citations
                       |
                       v
                  JSON response
                       |
                       v
        UI answer + grounding + sources
```

The generator never owns citation URLs. Source URLs, authority, jurisdiction and retrieval time come
from indexed database records. The frontend displays those backend citation objects without inventing
or rewriting source destinations.

## Frontend boundary

The browser never needs to know Docker service hostnames. It calls the Next.js route handler at
`/api/backend/*`. The Next.js server forwards requests to FastAPI using `BACKEND_INTERNAL_URL`.

This provides one interface in both environments:

```text
Local development:  Next.js -> http://localhost:8000/api/v1
Docker Compose:      Next.js -> http://backend:8000/api/v1
```

Conversation history and feedback are local browser state in Milestone 6. They are not represented as
server-persisted conversation memory or submitted feedback.

## Structured service tool path

```text
User query
   |
Intent baseline
   |
BoundedServiceAgent (max 3 calls by default)
   |
allow-listed GovernmentToolset
   |
PostgresGovernmentRepository
   |
services / sources / documents tables
```

No arbitrary command execution or unrestricted external HTTP tool is available to the agent.

## Ingestion

```text
Official public source
        |
robots / rate-limit aware downloader
        |
HTML/PDF parser
        |
cleaning + language detection + Arabic normalisation
        |
chunking + stable IDs
        |
embedding provider
        |
PostgreSQL + pgvector
```

`source_id` is retained across sources, documents and chunks, allowing every answer citation to trace
back to the authoritative source record.
