# Milestone 2 — Data pipeline completion record

## Implemented

- versioned source manifest for Federal, Abu Dhabi and Dubai sources
- English and Arabic source metadata
- rate-limited HTTP downloader
- `robots.txt` enforcement
- HTML parsing and cleaning
- PDF text extraction
- language detection
- Arabic normalisation
- deterministic overlapping chunking
- embedding-provider interface
- production-oriented multilingual E5 provider
- offline hashing embedding baseline
- PostgreSQL source/document/chunk persistence
- pgvector `vector(384)` column and HNSW cosine index
- Alembic migration `0002`
- ingestion CLI

## Verification performed here

- unit/integration-style ingestion tests pass using deterministic local fixtures
- HTML parsing verified
- PDF parsing verified on a generated text PDF
- Arabic normalisation and language detection verified
- source-manifest validation verified
- downloader verified with mocked HTTP transport
- explicit `robots.txt` denial verified
- embedding generation verified with the local baseline provider
- Alembic SQL generation verified through revision `0002`

## Environment-limited checks

A live fetch of the Federal Golden Visa source was attempted and failed because this execution
workspace cannot resolve external DNS. The failure is surfaced as `SourceDownloadError`; it is not
silently replaced by fixture data.

The production E5 provider is implemented but could not be executed because the optional
`sentence-transformers` package and model weights cannot be downloaded from this workspace.

## Gate decision

The ingestion architecture and deterministic execution path are verified. Live-network and real-E5
smoke tests remain required on a normal development machine before production claims are made.
