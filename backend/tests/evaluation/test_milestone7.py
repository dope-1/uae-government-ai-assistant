from __future__ import annotations

from pathlib import Path

from app.evaluation.milestone7 import EvaluationCase, load_cases, validate_suite

ROOT = Path(__file__).resolve().parents[3]


def test_milestone7_suite_has_required_scale_and_coverage() -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    assert len(cases) == 180
    assert validate_suite(cases) == []


def test_unanswerable_cases_do_not_claim_expected_sources() -> None:
    cases = load_cases(ROOT / "data/evaluation/milestone7_cases.jsonl")
    for case in cases:
        if case.expected_status == "unverified":
            assert case.answerable is False
            assert case.expected_source_ids == []


def test_case_schema_rejects_invalid_status() -> None:
    payload = {
        "id": "bad",
        "query": "test",
        "language": "en",
        "expected_answer_language": "en",
        "category": "GENERAL_INFORMATION",
        "answerable": True,
        "expected_status": "invented",
    }
    try:
        EvaluationCase.model_validate(payload)
    except ValueError:
        return
    raise AssertionError("invalid status should fail validation")


def test_mixed_language_cases_accept_either_supported_response_language() -> None:
    from datetime import UTC, datetime

    from app.rag.schemas import GroundingAssessment, GroundingLevel, RAGAnswer

    case = EvaluationCase(
        id="mixed-language",
        query="كيف أجدد driving licence في دبي؟",
        language="mixed",
        expected_answer_language="ar",
        category="SERVICE_DISCOVERY",
        jurisdiction="Dubai",
        answerable=True,
        expected_status="answered",
        expected_source_ids=["dubai_services_ar"],
        acceptable_source_ids=["dubai_driving_licence_renew_en"],
        expected_facts=["رخصة"],
    )
    answer = RAGAnswer(
        answer="Renew the driving licence through the official service [S1]",
        language="en",
        jurisdiction="Dubai",
        intent="SERVICE_DISCOVERY",
        status="answered",
        grounding=GroundingAssessment(
            level=GroundingLevel.SUFFICIENT,
            support_score=1.0,
            focus_score=1.0,
            supporting_sources=1,
        ),
        citations=[
            {
                "id": "S1",
                "chunk_id": "chunk",
                "title": "Renew Driving Licence",
                "authority": "RTA",
                "url": "https://example.gov/renew",
                "jurisdiction": "Dubai",
                "retrieved_at": datetime(2026, 9, 3, tzinfo=UTC),
                "relevant_excerpt": "Customers can renew a driving licence online.",
                "source_id": "dubai_driving_licence_renew_en",
                "document_id": "doc",
            }
        ],
    )

    from app.evaluation.milestone7 import score_case

    score = score_case(case, answer)
    assert score.language_correct is True
    assert score.citation_correctness == 1.0
    assert score.citation_completeness == 1.0
    assert score.expected_fact_coverage == 1.0


def test_non_answered_cases_do_not_inflate_fact_and_citation_metrics() -> None:
    from app.evaluation.milestone7 import CaseScore, aggregate

    scores = [
        CaseScore(
            id="answered",
            expected_status="answered",
            actual_status="answered",
            status_correct=True,
            language_correct=True,
            expected_fact_coverage=0.5,
            citation_correctness=0.5,
            citation_completeness=0.5,
            answer_relevance=0.5,
            context_relevance=0.5,
        ),
        CaseScore(
            id="refusal",
            expected_status="unverified",
            actual_status="unverified",
            status_correct=True,
            language_correct=True,
            expected_fact_coverage=None,
            citation_correctness=None,
            citation_completeness=None,
            answer_relevance=None,
            context_relevance=None,
        ),
    ]

    summary = aggregate(scores)
    assert summary["expected_fact_coverage"] == 0.5
    assert summary["citation_correctness"] == 0.5
    assert summary["citation_completeness"] == 0.5
    assert summary["context_fact_coverage"] == 0.5


def test_pure_arabic_case_checks_visible_answer_language_not_only_metadata() -> None:
    from datetime import UTC, datetime

    from app.evaluation.milestone7 import score_case
    from app.rag.schemas import GroundingAssessment, GroundingLevel, RAGAnswer

    case = EvaluationCase(
        id="arabic-visible-language",
        query="كيف أجدد ملكية المركبة في أبوظبي؟",
        language="ar",
        expected_answer_language="ar",
        category="PROCEDURE_INFORMATION",
        jurisdiction="Abu Dhabi",
        answerable=True,
        expected_status="answered",
        expected_source_ids=["abu_dhabi_vehicle_licensing_ar"],
        expected_facts=["مركبة"],
    )
    answer = RAGAnswer(
        answer=(
            "وفقاً للمصادر الرسمية، The platform enables the completion of transactions "
            "using UAE Pass and an active traffic file. [S1]"
        ),
        language="ar",
        jurisdiction="Abu Dhabi",
        intent="PROCEDURE_INFORMATION",
        status="answered",
        grounding=GroundingAssessment(
            level=GroundingLevel.SUFFICIENT,
            support_score=1.0,
            focus_score=1.0,
            supporting_sources=1,
        ),
        citations=[
            {
                "id": "S1",
                "chunk_id": "chunk",
                "title": "خدمات ترخيص المركبات",
                "authority": "Abu Dhabi Mobility",
                "url": "https://example.gov/ar",
                "jurisdiction": "Abu Dhabi",
                "retrieved_at": datetime(2026, 9, 3, tzinfo=UTC),
                "relevant_excerpt": "تشمل خدمات ترخيص المركبات تجديد المركبات.",
                "source_id": "abu_dhabi_vehicle_licensing_ar",
                "document_id": "doc",
            }
        ],
    )

    score = score_case(case, answer)
    assert score.language_correct is False


def test_evaluator_normalizes_arabic_attached_clitics_for_fact_coverage() -> None:
    from datetime import UTC, datetime

    from app.evaluation.milestone7 import score_case
    from app.rag.schemas import GroundingAssessment, GroundingLevel, RAGAnswer

    case = EvaluationCase(
        id="arabic-clitic-eval",
        query="ما الخدمة الرسمية لترخيص المركبات؟",
        language="ar",
        expected_answer_language="ar",
        category="SERVICE_DISCOVERY",
        jurisdiction="Abu Dhabi",
        answerable=True,
        expected_status="answered",
        expected_source_ids=["abu_dhabi_vehicle_licensing_ar"],
        expected_facts=["مركبة"],
    )
    answer = RAGAnswer(
        answer="تشمل الخدمة ترخيص المركبات وتجديدها. [S1]",
        language="ar",
        jurisdiction="Abu Dhabi",
        intent="SERVICE_DISCOVERY",
        status="answered",
        grounding=GroundingAssessment(
            level=GroundingLevel.SUFFICIENT,
            support_score=1.0,
            focus_score=1.0,
            supporting_sources=1,
        ),
        citations=[
            {
                "id": "S1",
                "chunk_id": "chunk",
                "title": "خدمات ترخيص المركبات",
                "authority": "Abu Dhabi Mobility",
                "url": "https://example.gov/ar",
                "jurisdiction": "Abu Dhabi",
                "retrieved_at": datetime(2026, 9, 3, tzinfo=UTC),
                "relevant_excerpt": "الخدمة الرسمية لترخيص المركبات تشمل التجديد.",
                "source_id": "abu_dhabi_vehicle_licensing_ar",
                "document_id": "doc",
            }
        ],
    )

    score = score_case(case, answer)
    assert score.expected_fact_coverage == 1.0
    assert score.context_relevance == 1.0
