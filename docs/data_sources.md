# Data sources and ingestion policy

Milestone 2 introduces a versioned source manifest at `data/manifests/official_sources.yaml`.
The scope intentionally stays small enough to audit, but now covers a 12-source live demo corpus
across UAE Federal Government, Abu Dhabi and Dubai, with both English and Arabic sources.

The selected domains are public official-government or government-authority sites:

- UAE Government Portal (`u.ae`)
- Abu Dhabi Mobility / Integrated Transport Centre (`admobility.gov.ae`)
- Dubai Roads and Transport Authority (`rta.ae`)
- Abu Dhabi Police traffic e-services (`es.adpolice.gov.ae`)

The manifest stores authority, jurisdiction, expected language and document type for each source.
The ingestion downloader sends an explicit research-project user agent, checks `robots.txt`, uses a
per-host delay and follows redirects. A `robots.txt` prohibition is treated as a hard failure.

## Live source handling

Live source text is downloaded only at ingestion time. The repository does not contain mirrors of
complete government pages. `data/evaluation/offline_corpus.jsonl` contains short paraphrased records
for deterministic retrieval testing when CI has no internet access. Those records are test fixtures,
not a substitute for live government content.

## Source metadata retained by the pipeline

Each parsed document and chunk carries:

- source ID and source URL
- authority
- jurisdiction
- title
- language
- document type
- retrieval timestamp
- stable document/chunk IDs

The database schema also stores a SHA-256 digest of cleaned document content so future ingestion
runs can detect content changes.

## Multi-jurisdiction live demo

The expansion stage adds current Federal Arabic pages, current Dubai RTA driving-licence and vehicle
renewal pages, a current Arabic RTA service catalogue, TAMM driving/transport catalogues, and current
Abu Dhabi Police traffic e-service catalogues in English and Arabic. See
`docs/corpus_expansion.md` for the exact verification workflow.

Use `python scripts/audit_corpus.py` after ingestion to report which manifest sources are actually
persisted, their chunk counts and approximate extracted word counts.

## Known limitations

- Dynamic pages may require source-specific extraction rules in later iterations.
- Scanned PDFs are not OCRed in Milestone 2; PDFs must contain extractable text.
- Terms-of-service review remains a human responsibility before adding new source domains.
- Some official portals are JavaScript-heavy; server-returned HTML can be shallower than the page
  rendered in a browser. The corpus audit exposes this instead of silently treating topical content
  as complete evidence.
