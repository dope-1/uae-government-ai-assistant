# Multi-jurisdiction corpus expansion

This stage sits between Milestones 5 and 6. Its purpose is to verify the already-built ingestion,
retrieval, RAG and bounded-agent architecture against a small but real bilingual corpus spanning the
Federal Government, Dubai and Abu Dhabi before a frontend is placed on top of it.

## Enabled live-source set

The primary manifest is `data/manifests/official_sources.yaml`. It now contains 12 enabled sources:

- **Federal / English:** Golden Visa, student residence, residence-visa index (`u.ae`)
- **Federal / Arabic:** Arabic equivalents of those three federal pages (`u.ae`)
- **Dubai / English:** RTA Renew Driving Licence and Renew Vehicle Ownership detail pages
- **Dubai / Arabic:** current RTA Arabic service catalogue covering driving-licence and
  vehicle-ownership service families
- **Abu Dhabi / English:** TAMM Obtain Driving Licence life-event catalogue plus the Abu Dhabi
  Police traffic e-services catalogue
- **Abu Dhabi / Arabic:** TAMM drive-and-transport catalogue plus the Arabic Abu Dhabi Police
  traffic e-services catalogue

The Abu Dhabi Police catalogue is useful for cross-jurisdiction verification because its current
English page explicitly lists both `Renew driving license` and `Vehicle registration renewal` while
remaining an Abu Dhabi authority source. Dubai's RTA pages provide separate Dubai evidence for the
same broad service families. This lets tests verify that similarly named services do not get mixed
between emirates.

## Source-quality boundary

Some government portals are JavaScript-heavy. A successful HTTP fetch does not guarantee that every
section visible in a browser was present in the server-returned HTML. The ingestion system therefore
continues to treat the stored live corpus as the source of truth: if a fact is absent from the
indexed text, grounded RAG must refuse to infer it even if the fact is known elsewhere.

The new `scripts/audit_corpus.py` command makes shallow or missing sources visible by showing live
source coverage, document/chunk counts and approximate extracted word counts. Rendered-browser or
source-specific extraction can be added later for pages whose server HTML proves too shallow.

## Ingestion commands

List the enabled sources without loading E5 or making network requests:

```powershell
python scripts\ingest.py --list-sources
```

Ingest jurisdiction by jurisdiction so failures are easy to diagnose:

```powershell
python scripts\ingest.py --jurisdiction Dubai
python scripts\ingest.py --jurisdiction "Abu Dhabi"
python scripts\ingest.py --jurisdiction Federal
```

Or ingest only Arabic sources:

```powershell
python scripts\ingest.py --language ar
```

Re-running a source is safe: ingestion uses stable source/document/chunk IDs and upserts persisted
records.

## Audit and service seeding

After ingestion:

```powershell
python scripts\audit_corpus.py
python scripts\seed_services.py
```

The service seeder still refuses to create a structured service record until its referenced official
source has actually been ingested. Unknown requirements, documents and fees remain empty rather than
being guessed.

## Live smoke verification

With the backend running, execute:

```powershell
python scripts\smoke_multijurisdiction.py
```

The smoke script exercises:

1. Dubai English service discovery
2. Abu Dhabi English service discovery
3. Dubai Arabic service discovery
4. Abu Dhabi Arabic service discovery
5. Dubai grounded RAG
6. Abu Dhabi grounded RAG

The expected property is **jurisdiction separation**, not identical answers. Dubai requests must use
Dubai/RTA evidence; Abu Dhabi requests must use Abu Dhabi/TAMM or Abu Dhabi Police evidence. Missing
facts should remain `unverified` rather than being borrowed from another emirate.
