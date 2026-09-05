# Milestone 5 — Bounded Service Tools and Agent

## Implemented tools

All tools are read-only, allow-listed, Pydantic-validated and return structured results:

- `search_government_sources`
- `search_services`
- `get_service_details`
- `compare_services`
- `retrieve_document`
- `get_source_metadata`

The tool layer has no shell, filesystem, arbitrary HTTP, Python execution or unrestricted database
execution capability.

## Bounded agent

`BoundedServiceAgent` uses a transparent bilingual rule-based intent baseline, searches the
structured service catalogue, and may make one follow-up call for details or comparison. The
maximum number of calls is controlled by `AGENT_MAX_TOOL_CALLS` and defaults to 3.

The API demo endpoint is:

```text
POST /api/v1/agent/service-discovery
```

The agent reports its tool call trace and stopping reason so behaviour can be inspected rather than
hidden behind a single opaque response.

## Structured service records

Migration `0003` adds the `services` table. The repository includes metadata-only service seed
records in `data/services/verified_services.yaml`. Empty requirements/documents/fees are deliberate:
missing fields are not fabricated.

`python scripts/seed_services.py` only inserts a service if its referenced source has already been
successfully ingested. It also requires the seed URL to exactly match the persisted source URL and
uses the source document retrieval timestamp as `last_verified`.

## Tests

Tests cover:

- rejection of non-allow-listed tools
- argument validation
- procedure workflow routing
- hard tool-call bounds
- bilingual intent baseline
- prompt-injection separation in RAG
- unsupported citation marker stripping
- refusal without calling the LLM
- cross-emirate clarification behaviour
