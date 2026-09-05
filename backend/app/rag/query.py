from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.language import detect_language


@dataclass(frozen=True)
class QueryContext:
    language: str
    jurisdiction: str | None


def analyse_query(query: str, requested_jurisdiction: str | None = None) -> QueryContext:
    if requested_jurisdiction:
        return QueryContext(language=_language(query), jurisdiction=requested_jurisdiction)

    lowered = query.casefold()
    local_mentions: set[str] = set()
    if (
        "abu dhabi" in lowered
        or "abu dhabi mobility" in lowered
        or "أبوظبي" in query
        or "ابوظبي" in query
        or "أبوظبي للتنقل" in query
        or "ابوظبي للتنقل" in query
        or "tamm" in lowered
        or "منصة تم" in query
        or "بوابة تم" in query
    ):
        local_mentions.add("Abu Dhabi")
    if (
        "dubai" in lowered
        or "دبي" in query
        or " rta " in f" {lowered} "
        or "roads and transport authority" in lowered
        or "هيئة الطرق والمواصلات" in query
    ):
        local_mentions.add("Dubai")

    if len(local_mentions) == 1:
        jurisdiction = next(iter(local_mentions))
    elif len(local_mentions) > 1:
        # A comparison that names more than one emirate is not a request to silently choose
        # whichever name happens to be checked first.
        jurisdiction = None
    elif any(term in lowered for term in ("federal", "uae government", "u.a.e. government")):
        jurisdiction = "Federal"
    else:
        jurisdiction = None
    return QueryContext(language=_language(query), jurisdiction=jurisdiction)


def requires_local_jurisdiction(query: str) -> bool:
    """Return True for transport services whose procedure is emirate-specific.

    This is intentionally narrow. It prevents a generic driving-licence/vehicle-renewal
    question from silently receiving a Dubai answer merely because RTA has more indexed
    chunks than the Abu Dhabi source.
    """

    lowered = query.casefold()
    english_topic = any(
        marker in lowered
        for marker in (
            "driving licence",
            "driving license",
            "driver licensing",
            "vehicle registration",
            "vehicle renewal",
            "vehicle ownership",
        )
    )
    english_action = any(
        marker in lowered
        for marker in (
            "renew",
            "registration",
            "ownership",
            "licensing service",
            "licence service",
            "license service",
            "steps",
            "process",
            "portal",
        )
    )
    if english_topic and english_action:
        return True

    has_driving_licence = "رخص" in query and "قياد" in query
    has_vehicle = "مركب" in query
    arabic_action = any(
        marker in query
        for marker in ("تجديد", "تسجيل", "ملكية", "ترخيص", "أجدد", "اجدد", "خطوات", "منصة")
    )
    return (has_driving_licence or has_vehicle) and arabic_action



def requests_unofficial_bypass_guidance(query: str) -> bool:
    """Detect requests for unofficial ways to evade government service rules.

    This boundary is deliberately narrow: it catches an explicit request to bypass or
    circumvent a rule/procedure, or a request that labels the desired method as undocumented.
    It runs before emirate clarification so an adversarial request is not accidentally turned
    into a legitimate service-discovery flow.
    """

    lowered = query.casefold()
    rule_terms = (
        "rule",
        "rules",
        "requirement",
        "requirements",
        "procedure",
        "procedures",
        "renewal",
        "registration",
        "licensing",
        "eye test",
    )
    evasion_terms = ("bypass", "circumvent", "evade", "loophole")
    explicit_evasion = any(term in lowered for term in evasion_terms) and any(
        term in lowered for term in rule_terms
    )
    avoid_rules = (
        "avoid" in lowered
        and any(term in lowered for term in rule_terms)
        and any(quantifier in lowered for quantifier in ("all", "every", "any"))
    )
    skip_rules = (
        "skip" in lowered
        and any(term in lowered for term in rule_terms)
        and any(quantifier in lowered for quantifier in ("all", "every", "any"))
    )
    undocumented_phrase = "غير موثق" in query or "غير موثقة" in query
    undocumented_request = undocumented_phrase and (
        any(marker in lowered for marker in ("give me", "tell me", "show me", "method"))
        or any(marker in query for marker in ("أعطني", "اعطني", "طريقة"))
    )
    arabic_evasion = any(
        marker in query
        for marker in (
            "تجاوز المتطلبات",
            "تجاوز القواعد",
            "التحايل",
            "ثغرة",
        )
    )
    return (
        explicit_evasion
        or avoid_rules
        or skip_rules
        or undocumented_request
        or arabic_evasion
    )

def _language(query: str) -> str:
    language = detect_language(query)
    return "ar" if language == "ar" else "en"
