from __future__ import annotations

from enum import StrEnum


class Intent(StrEnum):
    SERVICE_DISCOVERY = "SERVICE_DISCOVERY"
    PROCEDURE_INFORMATION = "PROCEDURE_INFORMATION"
    DOCUMENT_REQUIREMENTS = "DOCUMENT_REQUIREMENTS"
    ELIGIBILITY = "ELIGIBILITY"
    FEES = "FEES"
    DEADLINES = "DEADLINES"
    LOCATION_INFORMATION = "LOCATION_INFORMATION"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    COMPARISON = "COMPARISON"
    FOLLOW_UP = "FOLLOW_UP"
    UNKNOWN = "UNKNOWN"


class RuleBasedIntentClassifier:
    """Transparent bilingual baseline; later milestones can benchmark learned alternatives."""

    def classify(self, query: str) -> Intent:
        text = query.lower()
        patterns: list[tuple[Intent, tuple[str, ...]]] = [
            (Intent.COMPARISON, ("compare", "difference", "versus", " vs ", "مقارنة", "الفرق")),
            (Intent.FEES, ("fee", "fees", "cost", "price", "رسوم", "تكلفة")),
            (
                Intent.DOCUMENT_REQUIREMENTS,
                ("document", "documents", "required papers", "وثائق", "مستند"),
            ),
            (Intent.ELIGIBILITY, ("eligible", "eligibility", "qualify", "أهلية", "مؤهل")),
            (Intent.DEADLINES, ("deadline", "expiry", "expire", "how long", "موعد", "انتهاء")),
            (Intent.LOCATION_INFORMATION, ("where", "location", "centre", "center", "أين", "موقع")),
            (
                Intent.PROCEDURE_INFORMATION,
                ("how do", "how can", "steps", "procedure", "كيف", "خطوات"),
            ),
            (Intent.SERVICE_DISCOVERY, ("service", "services", "خدمة", "خدمات")),
        ]
        for intent, terms in patterns:
            if any(term in text for term in terms):
                return intent
        return Intent.GENERAL_INFORMATION if query.strip() else Intent.UNKNOWN
