# Responsible AI and Limitations

## Purpose

The UAE Government AI Assistant is an independent portfolio/research project designed to demonstrate multilingual retrieval, grounded RAG, production engineering and cloud deployment.

It is not an official UAE government system.

## Design principles

### Ground answers in official sources

The system retrieves from a bounded set of official sources and constructs citations on the backend.

### Prefer refusal over unsupported claims

The RAG pipeline contains support checks and can return an insufficient-evidence result when the retrieved context does not adequately support an answer.

### Preserve jurisdiction

Federal, Dubai and Abu Dhabi information can differ. The system includes jurisdiction filters and conflict handling to reduce cross-emirate mixing.

### Bound agent behaviour

The service-discovery agent uses allow-listed read-only tools and explicit tool-call limits. It does not execute transactions or write to government systems.

### Minimise operational data

Operational telemetry is designed not to record raw queries, answer text or client IP addresses.

## Known limitations

1. **Bounded coverage.** The demo corpus contains 12 enabled sources and is not a comprehensive representation of UAE public services.
2. **Information freshness.** Government procedures, fees, eligibility rules and URLs can change.
3. **No authoritative eligibility decisions.** The system should not be used as the sole basis for immigration, legal or financial decisions.
4. **Arabic evaluation limitation.** Part of the qualitative Arabic/mixed-language review was AI-assisted rather than independently reviewed by a fluent human evaluator.
5. **Extractive public answer path.** The production demo intentionally favours conservative source-grounded extraction over broad generative flexibility.
6. **No transactions.** The application does not submit forms, make payments or modify government records.
7. **Portfolio-scale deployment.** Runtime and scaling limits are configured for a public demonstration, not high-volume government production traffic.

## User-facing guidance

Important decisions should be verified using the official source linked in the answer.

A citation should be treated as a route to authoritative information, not as evidence that this portfolio application is itself authoritative.

## Security controls

Production engineering includes:

- managed secret storage;
- trusted-host validation;
- security headers;
- request-size limits;
- rate limiting;
- authenticated operational metrics;
- privacy-aware structured telemetry.

## Evaluation transparency

Automated metrics are reported as fixed benchmark results. They are not presented as calibrated probabilities or universal production accuracy.

Qualitative results explicitly distinguish the ten manually reviewed English samples from the twenty AI-assisted Arabic/mixed-language samples.

## Non-affiliation notice

This project is not affiliated with the UAE Government, TAMM, Dubai Digital Authority or any UAE ministry, authority or government organisation.
