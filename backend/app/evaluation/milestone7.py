from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from statistics import mean
from typing import Literal

from pydantic import BaseModel, Field

from app.rag.schemas import RAGAnswer
from app.retrieval.tokenization import tokenize

Language = Literal["en", "ar", "mixed"]
ExpectedStatus = Literal["answered", "unverified", "needs_clarification"]
SUITE_VERSION = "m7-v2"

_EVAL_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "can",
    "do",
    "does",
    "for",
    "from",
    "government",
    "groups",
    "guidance",
    "how",
    "i",
    "in",
    "information",
    "is",
    "it",
    "kind",
    "mean",
    "my",
    "of",
    "official",
    "on",
    "about",
    "context",
    "page",
    "please",
    "source",
    "sources",
    "tell",
    "the",
    "to",
    "uae",
    "what",
    "where",
    "which",
    "who",
    "with",
    "في",
    "من",
    "ما",
    "ماذا",
    "كيف",
    "هل",
    "على",
    "عن",
    "الى",
    "او",
    "و",
    "اين",
    "رسمية",
    "رسمي",
    "الرسمية",
    "الرسمي",
    "هي",
    "هو",
    "المصدر",
    "المصادر",
    "معلومات",
    "العربي",
    "العربية",
    "الامارات",
    "الاماراتية",
    "اعمل",
    "اجد",
    "اجدها",
    "احتاج",
    "استخدم",
    "طريقة",
    "عبر",
    "ل",
}

# Independent evaluator-side concept normalization. It is intentionally small: enough to
# avoid scoring "renew" vs "renewing" or "رخصة" vs "رخص" as different facts, including in
# mixed-language cases, without pretending to be a semantic judge.
_EVAL_CANONICAL = {
    "renewal": "renew",
    "renewed": "renew",
    "renewing": "renew",
    "renews": "renew",
    "driving": "drive",
    "driver": "drive",
    "drivers": "drive",
    "licensing": "licence",
    "licences": "licence",
    "licenses": "licence",
    "license": "licence",
    "visas": "visa",
    "students": "student",
    "studying": "student",
    "services": "service",
    "requirements": "requirement",
    "fees": "fee",
    "sponsors": "sponsor",
    "sponsorship": "sponsor",
    "اجدد": "renew",
    "تجديد": "renew",
    "لتجديد": "renew",
    "يجدد": "renew",
    "رخصة": "licence",
    "رخص": "licence",
    "ترخيص": "licence",
    "القيادة": "drive",
    "السائقين": "drive",
    "المركبة": "vehicle",
    "المركبات": "vehicle",
    "مركبة": "vehicle",
    "ملكية": "ownership",
    "بملكية": "ownership",
    "تسجيل": "registration",
    "التاشيرات": "visa",
    "للتاشيرات": "visa",
    "تاشيرات": "visa",
    "التاشيرة": "visa",
    "تاشيرة": "visa",
    "الاقامة": "residence",
    "اقامة": "residence",
    "الذهبية": "golden",
    "ذهبية": "golden",
    "الهوية": "identity",
    "التأشيرات": "visa",
    "تأشيرات": "visa",
}


class EvaluationCase(BaseModel):
    id: str
    query: str
    language: Language
    expected_answer_language: Literal["en", "ar"]
    category: str
    jurisdiction: str | None = None
    answerable: bool
    expected_status: ExpectedStatus
    expected_source_ids: list[str] = Field(default_factory=list)
    acceptable_source_ids: list[str] = Field(default_factory=list)
    expected_service_id: str | None = None
    expected_facts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @property
    def relevant_source_ids(self) -> set[str]:
        return set(self.expected_source_ids) | set(self.acceptable_source_ids)


class CaseScore(BaseModel):
    id: str
    expected_status: ExpectedStatus
    actual_status: str
    status_correct: bool
    language_correct: bool
    expected_fact_coverage: float | None
    citation_correctness: float | None
    citation_completeness: float | None
    answer_relevance: float | None
    context_relevance: float | None


def load_cases(path: Path) -> list[EvaluationCase]:
    return [
        EvaluationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_suite(cases: list[EvaluationCase]) -> list[str]:
    errors: list[str] = []
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("Evaluation case IDs must be unique.")
    if not 150 <= len(cases) <= 300:
        errors.append("Milestone 7 suite must contain between 150 and 300 cases.")

    languages = Counter(case.language for case in cases)
    for language in ("en", "ar", "mixed"):
        if languages[language] < 20:
            errors.append(f"Suite needs at least 20 {language} cases.")

    required_tags = {"unanswerable", "adversarial", "jurisdiction_conflict", "multi_step"}
    tags = {tag for case in cases for tag in case.tags}
    for tag in sorted(required_tags - tags):
        errors.append(f"Suite is missing required tag: {tag}")

    for case in cases:
        if case.expected_status == "answered" and not case.relevant_source_ids:
            errors.append(f"{case.id}: answered case needs at least one relevant source.")
        if case.expected_status != "answered" and case.acceptable_source_ids:
            errors.append(f"{case.id}: non-answered case must not define acceptable sources.")
        if "variant " in case.query.casefold():
            errors.append(f"{case.id}: benchmark query contains a synthetic variant label.")
    return errors


def score_case(case: EvaluationCase, answer: RAGAnswer) -> CaseScore:
    # Pure-language cases have an unambiguous expectation. Code-switched queries without an
    # explicit language request may reasonably be answered in either supported language, so
    # they are not penalized for an arbitrary English-vs-Arabic choice.
    language_correct = _language_is_acceptable(case, answer)

    relevant_sources = case.relevant_source_ids
    cited = {citation.source_id for citation in answer.citations}

    if case.expected_status == "answered":
        fact_coverage = _fact_coverage(case.expected_facts, answer.answer)
        correctness = (
            len(cited & relevant_sources) / len(cited) if cited else 0.0
        )
        # Any member of an explicitly labelled source-equivalence set is sufficient for the
        # case. This matters for mixed-language questions where both EN and AR official pages
        # support the same service.
        completeness = float(bool(cited & relevant_sources))
        answer_relevance = _lexical_relevance(case.query, answer.answer)
        citation_context = " ".join(citation.relevant_excerpt for citation in answer.citations)
        context_relevance = _fact_coverage(case.expected_facts, citation_context)
    else:
        # Fact/citation/relevance metrics are not applicable to expected refusals or
        # clarification turns. Treating their empty citations as perfect would inflate the
        # aggregate benchmark and obscure answerable-case failures.
        fact_coverage = None
        correctness = None
        completeness = None
        answer_relevance = None
        context_relevance = None

    return CaseScore(
        id=case.id,
        expected_status=case.expected_status,
        actual_status=answer.status,
        status_correct=answer.status == case.expected_status,
        language_correct=language_correct,
        expected_fact_coverage=fact_coverage,
        citation_correctness=correctness,
        citation_completeness=completeness,
        answer_relevance=answer_relevance,
        context_relevance=context_relevance,
    )


def aggregate(scores: list[CaseScore]) -> dict[str, float | int | dict[str, object]]:
    if not scores:
        return {"cases": 0}

    status_breakdown: dict[str, object] = {}
    for expected in ("answered", "unverified", "needs_clarification"):
        subset = [score for score in scores if score.expected_status == expected]
        status_breakdown[expected] = {
            "cases": len(subset),
            "accuracy": mean(float(score.status_correct) for score in subset) if subset else None,
        }

    return {
        "cases": len(scores),
        "status_accuracy": mean(float(score.status_correct) for score in scores),
        "language_accuracy": mean(float(score.language_correct) for score in scores),
        "expected_fact_coverage": _mean_defined(
            score.expected_fact_coverage for score in scores
        ),
        "citation_correctness": _mean_defined(score.citation_correctness for score in scores),
        "citation_completeness": _mean_defined(
            score.citation_completeness for score in scores
        ),
        "answer_relevance_lexical": _mean_defined(score.answer_relevance for score in scores),
        "context_fact_coverage": _mean_defined(score.context_relevance for score in scores),
        "status_breakdown": status_breakdown,
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fact_coverage(facts: list[str], text: str) -> float:
    if not facts:
        return 1.0
    text_terms = _concept_terms(text)
    covered = []
    folded = text.casefold()
    for fact in facts:
        fact_terms = _concept_terms(fact)
        if fact_terms:
            covered.append(float(fact_terms <= text_terms))
        else:
            covered.append(float(fact.casefold() in folded))
    return mean(covered)


def _lexical_relevance(query: str, answer: str) -> float:
    query_terms = _concept_terms(query)
    answer_terms = _concept_terms(answer)
    if not query_terms:
        return 0.0
    return len(query_terms & answer_terms) / len(query_terms)


_ARABIC_CLITIC_PREFIXES = {"و", "ف", "ب", "ك", "ل"}


def _eval_canonical_token(token: str) -> str:
    direct = _EVAL_CANONICAL.get(token)
    if direct is not None:
        return direct
    candidate = token
    for _ in range(2):
        if len(candidate) <= 3 or candidate[0] not in _ARABIC_CLITIC_PREFIXES:
            break
        candidate = candidate[1:]
        direct = _EVAL_CANONICAL.get(candidate)
        if direct is not None:
            return direct
    return token


def _language_is_acceptable(case: EvaluationCase, answer: RAGAnswer) -> bool:
    if answer.language not in {"en", "ar"}:
        return False
    if case.language == "mixed":
        return True
    if answer.language != case.expected_answer_language:
        return False

    # Validate the actual user-visible answer, not only the response metadata. This catches
    # cases where an Arabic response was labelled "ar" but contained an Arabic lead-in
    # followed by an English evidence dump.
    arabic_letters = sum(1 for char in answer.answer if "\u0600" <= char <= "\u06ff")
    latin_letters = sum(1 for char in answer.answer.casefold() if "a" <= char <= "z")
    total = arabic_letters + latin_letters
    if total == 0:
        return True
    arabic_ratio = arabic_letters / total
    if case.expected_answer_language == "ar":
        return arabic_ratio >= 0.50
    return arabic_ratio <= 0.35


def _concept_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in tokenize(text):
        canonical = _eval_canonical_token(token)
        if canonical not in _EVAL_STOPWORDS and not canonical.isdigit():
            terms.add(canonical)
    return terms


def _mean_defined(values: Iterable[float | None]) -> float:
    defined = [float(value) for value in values if value is not None]
    return mean(defined) if defined else 0.0
