# Evaluation Summary

## Scope

The evaluation suite is an engineering benchmark for this repository. It is not a claim of universal production accuracy across all UAE government information.

Milestone 7 is frozen and is the final automated evaluation baseline for the documented version.

## Retrieval

130 answerable queries:

| Metric | Result |
|---|---:|
| Recall@5 | **1.000** |
| Precision@5 | **0.200** |
| MRR | **0.941026** |
| NDCG@5 | **0.956408** |

Recall@5 is the main retrieval coverage signal in this fixed benchmark. Precision@5 is intentionally lower because five candidates are retrieved while the benchmark typically has a small number of relevant items.

## End-to-end RAG

180 English, Arabic and mixed-language cases:

| Metric | Result |
|---|---:|
| Status accuracy | **1.000** |
| Language accuracy | **1.000** |
| Expected fact coverage | **1.000** |
| Citation correctness | **1.000** |
| Citation completeness | **1.000** |
| Context fact coverage | **0.984615** |
| Lexical relevance | **0.680736** |

The metrics are deterministic engineering checks over a fixed dataset. They should not be interpreted as calibrated confidence probabilities.

## Qualitative review

30 samples were scored:

- 10 English samples were manually reviewed by the developer.
- 20 Arabic/mixed-language samples were AI-assisted because the developer does not independently read Arabic.

The project therefore does **not** describe the qualitative set as 30 independent human reviews.

| Dimension | Mean |
|---|---:|
| Faithfulness | 4.50 / 5 |
| Answer relevance | 4.60 / 5 |
| Citation completeness | 4.50 / 5 |
| Language quality | 4.43 / 5 |

## Production engineering verification

Before deployment:

```text
Ruff: clean
mypy: no issues in 76 source files
pytest: 111 tests passed
security audit: passed
```

## Public deployment verification

Milestone 9:

```text
PASS backend readiness
PASS backend request/security headers
PASS frontend root
PASS frontend-to-backend proxy
PASS end-to-end grounded chat
PASS operational metrics require authentication
```

The verifier recorded `"passed": true`.

## Reproducibility

Relevant scripts include:

```text
scripts/evaluate.py
scripts/evaluate_rag.py
scripts/evaluate_m7_retrieval_live.py
scripts/evaluate_m7_live.py
scripts/performance_m8.py
scripts/security_audit_m8.py
scripts/verify_deployment_m9.py
```

Frozen Milestone 7 numbers should not be silently replaced by later ad-hoc runs when documenting this release.

## Interpretation

The evaluation demonstrates that the implementation satisfies its fixed portfolio benchmark and deployment checks. It does not establish completeness of UAE public-service coverage, legal correctness for every individual circumstance or future validity after government information changes.
