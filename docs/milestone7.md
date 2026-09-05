# Milestone 7 — Evaluation & Safety

Milestone 7 expands the small engineering regressions into a versioned bilingual evaluation and
safety framework. It does **not** claim production accuracy or semantic faithfulness until those
numbers have actually been measured on the live corpus and, for faithfulness, human-reviewed.

## Versioned evaluation suite

`data/evaluation/milestone7_cases.jsonl` contains 180 cases:

- 80 English
- 65 Arabic
- 35 mixed Arabic/English
- 130 answerable
- 30 deliberately unanswerable
- 20 jurisdiction-conflict / clarification cases

The current benchmark revision is `m7-v2`. Version 2 removes synthetic `variant N` text from the
mixed-language prompts, treats equivalent English/Arabic official pages as acceptable source
alternatives for code-switched service questions, and validates that synthetic labels cannot be
reintroduced accidentally.

The suite includes service discovery, procedures, Federal residency information, Dubai and Abu
Dhabi jurisdiction handling, mixed-language queries, adversarial prompts, unavailable information
and multi-step questions. Every answerable case labels expected source IDs and, where applicable, a
structured service ID. Unknown facts intentionally have no labelled source.

Validate the suite without calling a model or network service:

```bash
python scripts/validate_m7_dataset.py
```

## Live retrieval evaluation

With the real local backend running:

```bash
python scripts/evaluate_m7_retrieval_live.py --k 5
```

This reports source-level Recall@5, Precision@5, MRR and NDCG@5. Source-level labels are used so a
legitimate re-ingestion that changes chunk IDs does not invalidate the benchmark. For a
mixed-language information need, an explicitly labelled English or Arabic equivalent source may
satisfy source recall; the report records `suite_version=m7-v2` so results cannot be confused with
the earlier benchmark revision.

## Live grounded-answer evaluation

```bash
python scripts/evaluate_m7_live.py
```

The deterministic report includes:

- expected status accuracy, with separate answered/refusal/clarification breakdowns
- response-language accuracy; pure EN/AR cases are strict, while code-switched cases accept either
  supported response language unless a future case explicitly requests one
- normalized expected-fact coverage on answerable cases only
- citation correctness on answerable cases only
- citation completeness, where one labelled source-equivalent is sufficient
- normalized lexical query/answer overlap as a diagnostic only
- context fact coverage computed from citation excerpts, independently of source-ID correctness

Expected refusals and clarification turns are excluded from fact/citation/context averages. Their
lack of citations is therefore no longer counted as a perfect citation score. None of these
deterministic metrics is a semantic faithfulness judge. The live report keeps `faithfulness=null`
until a human review is completed.

Use `--limit N` for a smoke run or `--tag adversarial` to isolate tagged cases.

## Grounding and jurisdiction safety

The Milestone 7 live diagnostic exposed three runtime failure classes that are now regression-tested:

1. question scaffolding such as `which`, `who`, `intended`, `page`, and Arabic equivalents was being
   treated as answer-bearing evidence;
2. Arabic morphology and mixed Arabic/English concepts such as `أجدد`/`تجديد`/`renew` and
   `رخصة`/`licence` were not canonicalized consistently;
3. jurisdiction ambiguity was inferred only from the retrieved top chunks, which could silently
   choose Dubai when one source dominated the index.

The grounding gate now canonicalizes these domain concepts, keeps high-information attributes such
as sponsor/fee/deadline/free/approval strict, checks evidence insufficiency before cross-emirate
ambiguity, and asks for an emirate for jurisdiction-dependent driving/vehicle renewal questions even
when retrieval is one-sided. A query that explicitly names both Dubai and Abu Dhabi is not silently
collapsed to one emirate.

## Human review

Generate a 30-case stratified review sheet only after the `m7-v2` live run is satisfactory:

```bash
python scripts/create_human_review_sample.py
```

If a full live evaluation report exists, the generator pre-fills answers and citation URLs; otherwise
it leaves those fields blank. Reviewers should record 1–5 scores for faithfulness, answer relevance,
citation completeness and language quality, plus free-text notes. Human scores must not be filled
synthetically. Aggregate only completed human rows with:

```bash
python scripts/score_human_review.py
```

## Safety regression

The automated safety tests cover:

- retrieved prompt injection remaining untrusted evidence
- fake citation-marker removal
- insufficient-evidence refusal before generation
- unsupported sponsor/attribute refusal despite topical source matches
- cross-emirate ambiguity requiring clarification even with one-sided retrieval
- weak unrelated cross-emirate evidence remaining unverified rather than requesting a jurisdiction
- Arabic morphology and mixed-language grounding

Run them with the normal backend test suite:

```bash
cd backend
pytest
```

## Reporting rule

Only metrics generated by the current suite version may be quoted in the README. The earlier
`m7-v1` 180-case diagnostic was used to find benchmark/runtime defects and must not be presented as
the final Milestone 7 score. Semantic faithfulness remains pending human review.
