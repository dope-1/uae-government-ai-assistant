# Milestone 7 human-review rubric

The 30-case human review is a semantic check of **substantive answered cases**. Automated M7 already
measures refusal / `unverified` / `needs_clarification` status behavior across the full 180-case suite.
Keeping the human sheet answerable-only avoids treating citation completeness as a vacuous perfect
score on refusals.

The generator selects 10 English, 10 Arabic and 10 mixed-language cases. Within each language it
selects 4 Federal, 3 Dubai and 3 Abu Dhabi cases, spread deterministically across each bucket rather
than taking the first ten near-duplicate benchmark paraphrases.

Review the **answer against the frozen `citation_evidence` column**. The URL column is provided for
navigation, but the frozen excerpt is the evidence that was actually available to the assistant at
evaluation time. Do not reward a claim merely because a current webpage now contains information
that was absent from the frozen excerpt.

## Scoring

Use whole-number scores from 1 to 5. Add a short `reviewer_notes` explanation for any score of 3 or
below, and for any surprising or borderline case.

### Faithfulness

- **5** — Every material factual claim is directly supported by the cited frozen evidence; no
  contradiction or unsupported extrapolation.
- **4** — Supported overall, with only a minor wording/imprecision issue that does not change the
  user's likely understanding.
- **3** — Mostly supported, but at least one meaningful claim is weakly supported, overgeneralized,
  or more specific than the evidence.
- **2** — Multiple material claims are unsupported or misleading, although some relevant evidence
  exists.
- **1** — The answer is substantially contradicted by the evidence, fabricated, or grounded in the
  wrong topic/service.

### Answer relevance

- **5** — Directly answers the user's actual question and includes the important requested detail.
- **4** — Answers the question with a small omission or some unnecessary wording.
- **3** — Partially answers it, misses a meaningful requested aspect, or is noticeably indirect.
- **2** — Weakly related but does not resolve the user's request.
- **1** — Essentially a non-answer or answers a different question.

### Citation completeness

- **5** — Every material externally verifiable claim that needs evidence is covered by an
  appropriate citation, and citation markers map to supporting frozen excerpts.
- **4** — Nearly complete; one minor claim could use better citation support.
- **3** — At least one meaningful claim lacks adequate citation support, but most claims are cited.
- **2** — Several important claims are uncited or mapped to weak/irrelevant excerpts.
- **1** — Citations are absent, materially wrong, or do not support the answer.

### Language quality

Judge the language the user actually sees, not the response metadata.

- **5** — Natural, clear and professionally written in the expected language; code-switching only
  where appropriate for official names/terms.
- **4** — Clear and correct with minor awkwardness or a small unnecessary borrowed phrase.
- **3** — Understandable but noticeably awkward, mechanically translated, or inconsistently mixed.
- **2** — Difficult to read, contains substantial wrong-language content, or has serious grammar.
- **1** — Unusable or predominantly in the wrong language.

## Completion rule

All 30 rows and all four score columns must be completed before `scripts/score_human_review.py`
will produce a Milestone 7 human-review result. The scorer reports overall means plus language and
jurisdiction breakdowns, and flags cases containing a score of 2 or below for follow-up.
