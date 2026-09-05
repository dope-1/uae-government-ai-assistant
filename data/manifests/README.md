# Source manifests

`official_sources.yaml` is the initial Milestone 2 ingestion manifest. It records only public
official sources and preserves authority, jurisdiction, language and document type metadata.

The downloader is designed to check `robots.txt` and rate-limit requests. Adding a source to this
file does not by itself constitute permission to scrape it; terms, copyright and source-specific
access conditions must still be reviewed.
