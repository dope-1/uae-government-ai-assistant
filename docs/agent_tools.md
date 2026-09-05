# Agent Tool Contracts

The Milestone 5 agent is deliberately bounded and read-only.

| Tool | Purpose | Important limits |
|---|---|---|
| `search_government_sources` | Find indexed authoritative sources | query <= 300 chars, max 20 results |
| `search_services` | Find structured services | jurisdiction filter, max 20 results |
| `get_service_details` | Fetch one known service | typed service ID only |
| `compare_services` | Compare known services | 2–4 IDs |
| `retrieve_document` | Fetch an indexed document | output capped at 20,000 chars |
| `get_source_metadata` | Fetch stored provenance | source ID only |

Tool failures are converted into structured errors and logged. There is no fallback to arbitrary
execution when a tool fails.
