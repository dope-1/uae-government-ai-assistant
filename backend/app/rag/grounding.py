from __future__ import annotations

import re

from app.ingestion.schemas import DocumentChunk
from app.rag.schemas import GroundingAssessment, GroundingLevel
from app.retrieval.tokenization import tokenize

_LOCAL_JURISDICTIONS = {"Abu Dhabi", "Dubai"}

# User requests about which evidence to rely on are instructions to the RAG system, not
# answer-bearing facts. Keeping them in the proposition-focus gate can make a perfectly
# supported question look unsupported (for example, treating "indexed" as a required fact).
_EVIDENCE_PREFERENCE_PATTERNS = (
    re.compile(
        r"\b(?:please\s+)?(?:only\s+)?use\s+(?:the\s+)?official"
        r"(?:\s+indexed)?\s+sources?\b[.!?]*",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:يرجى\s+)?استخدم\s+(?:المصدر\s+الرسمي|المصادر\s+الرسمية)"
        r"(?:\s+المفهرس(?:ة)?)?[.!؟]*"
    ),
)

# Stop words cover grammar, evidence-selection wording and answer-format scaffolding. They
# deliberately do NOT contain high-information attributes such as sponsor, fee, deadline,
# free, insurance or approval. Those must still be supported by the retrieved evidence.
_STOPWORDS = {
    "a",
    "am",
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
    "me",
    "mentioned",
    "my",
    "of",
    "official",
    "on",
    "about",
    "context",
    "page",
    "pages",
    "please",
    "source",
    "sources",
    "the",
    "tell",
    "to",
    "uae",
    "used",
    "website",
    "what",
    "where",
    "which",
    "who",
    "with",
    "would",
    # Arabic grammar and generic question scaffolding.
    "اين",
    "الى",
    "او",
    "باللغة",
    "حكومة",
    "رسمية",
    "رسمي",
    "الرسمية",
    "الرسمي",
    "هي",
    "هو",
    "صفحة",
    "الصفحة",
    "عن",
    "على",
    "في",
    "كيف",
    "لمعلومات",
    "ما",
    "ماذا",
    "معلومات",
    "من",
    "المصدر",
    "مصدر",
    "المصادر",
    "و",
    "هل",
    "اجد",
    "توجد",
    "يوجد",
    "اريد",
    "الخاصة",
    "العربي",
    "العربية",
    "الامارات",
    "الاماراتية",
    "اعمل",
    "اجدها",
    "احتاج",
    "استخدم",
    "طريقة",
    "عبر",
    "ل",
}

# These words express the relationship being asked about, but by themselves do not prove
# the answer. For example, a page that mentions "requirements" does not prove whether a
# sponsor is required. The object/attribute ("sponsor") must be supported.
_RELATION_TERMS = {
    "allow",
    "be",
    "contain",
    "cover",
    "explain",
    "handle",
    "have",
    "include",
    "intend",
    "involve",
    "need",
    "offer",
    "provide",
    "require",
}

# Canonicalization is intentionally small and domain-focused. English inflections and the
# Arabic forms used by the indexed service pages map to shared concepts so code-switched
# questions are judged on meaning rather than surface morphology.
_CANONICAL = {
    # English relations / morphology.
    "allows": "allow",
    "allowed": "allow",
    "allowing": "allow",
    "contains": "contain",
    "contained": "contain",
    "containing": "contain",
    "covers": "cover",
    "covered": "cover",
    "covering": "cover",
    "explains": "explain",
    "explained": "explain",
    "explaining": "explain",
    "handles": "handle",
    "handled": "handle",
    "handling": "handle",
    "includes": "include",
    "included": "include",
    "including": "include",
    "intended": "intend",
    "intends": "intend",
    "offers": "offer",
    "offered": "offer",
    "offering": "offer",
    "provides": "provide",
    "provided": "provide",
    "providing": "provide",
    "required": "require",
    "requires": "require",
    "requiring": "require",
    "needed": "need",
    "needs": "need",
    "had": "have",
    "has": "have",
    "sponsors": "sponsor",
    "sponsored": "sponsor",
    "sponsoring": "sponsor",
    "sponsorship": "sponsor",
    "renewal": "renew",
    "renewed": "renew",
    "renewing": "renew",
    "renews": "renew",
    "applications": "apply",
    "application": "apply",
    "applying": "apply",
    "applied": "apply",
    "eligibility": "eligible",
    "requirement": "requirement",
    "requirements": "requirement",
    "documents": "document",
    "fees": "fee",
    "benefits": "benefit",
    "deadlines": "deadline",
    "inspections": "inspection",
    "universities": "university",
    "services": "service",
    "centres": "centre",
    "centers": "center",
    "driving": "drive",
    "driver": "drive",
    "drivers": "drive",
    "licensing": "licence",
    "licences": "licence",
    "licenses": "licence",
    "license": "licence",
    "studying": "student",
    "students": "student",
    "visas": "visa",
    # Arabic relation forms.
    "يتولى": "handle",
    "تتولى": "handle",
    "تقدم": "provide",
    "يقدم": "provide",
    "توفر": "provide",
    "يوفر": "provide",
    "تشمل": "include",
    "يتضمن": "include",
    "تتضمن": "include",
    # Arabic service-domain morphology, mapped across languages for mixed queries.
    "اجدد": "renew",
    "تجديد": "renew",
    "لتجديد": "renew",
    "يجدد": "renew",
    "جدد": "renew",
    "رخصة": "licence",
    "رخص": "licence",
    "ترخيص": "licence",
    "القيادة": "drive",
    "السائقين": "drive",
    "سائقين": "drive",
    "المركبة": "vehicle",
    "المركبات": "vehicle",
    "مركبة": "vehicle",
    "ملكية": "ownership",
    "بملكية": "ownership",
    "تسجيل": "registration",
    "خدمة": "service",
    "الخدمة": "service",
    "خدمات": "service",
    "الخدمات": "service",
    "منصة": "portal",
    "بوابة": "portal",
    "التاشيرات": "visa",
    "للتاشيرات": "visa",
    "تاشيرات": "visa",
    "التاشيرة": "visa",
    "تاشيرة": "visa",
    "الهوية": "identity",
    "وبطاقة": "card",
    "بطاقة": "card",
    "الاقامة": "residence",
    "اقامة": "residence",
    "الذهبية": "golden",
    "ذهبية": "golden",
    "الاتحادي": "federal",
    "اتحادي": "federal",
}

_JURISDICTION_TERMS = {
    "Dubai": {"dubai", "دبي"},
    "Abu Dhabi": {"abu", "dhabi", "ابوظبي"},
    "Federal": {"federal", "اتحادي"},
}


def assess_grounding(
    query: str,
    ranked: list[tuple[DocumentChunk, float]],
    *,
    explicit_jurisdiction: str | None,
    minimum_support: float = 0.20,
    minimum_focus_support: float = 0.60,
) -> GroundingAssessment:
    if not ranked:
        return GroundingAssessment(
            level=GroundingLevel.INSUFFICIENT,
            support_score=0.0,
            focus_score=0.0,
            supporting_sources=0,
            reasons=["No evidence chunks were retrieved."],
        )

    semantic_query = _strip_evidence_preferences(query)
    query_terms = _meaningful_terms(semantic_query)
    jurisdiction_terms = _jurisdiction_terms(explicit_jurisdiction)
    if jurisdiction_terms:
        # The retriever is already jurisdiction-filtered. Do not require body text to repeat
        # English or Arabic spellings of the selected jurisdiction.
        reduced = query_terms - jurisdiction_terms
        if reduced:
            query_terms = reduced

    content_terms_by_chunk = [_canonical_terms(chunk.text) for chunk, _ in ranked]
    overlaps = [
        len(query_terms & content_terms) / max(1, len(query_terms))
        for content_terms in content_terms_by_chunk
    ]
    support = max(overlaps, default=0.0)
    source_count = len({chunk.source_id for chunk, _ in ranked})

    # Titles are useful for identifying the subject, but a title match alone must not prove
    # a requested attribute such as sponsor, fee or deadline.
    title_terms: set[str] = set()
    for chunk, _ in ranked[:4]:
        title_terms.update(_canonical_terms(chunk.title))

    relation_object_terms = _relation_object_terms(semantic_query)
    relation_object_terms -= jurisdiction_terms

    use_support_as_focus = False
    if relation_object_terms:
        # For relational questions, the object after the relation is the decisive fact.
        # "Does the Golden Visa require a sponsor?" -> {"sponsor"}.
        focus_terms = relation_object_terms
    else:
        focus_terms = {
            term
            for term in query_terms
            if term not in title_terms and term not in _RELATION_TERMS
        }
        if not focus_terms:
            # Open descriptive/location questions can consist entirely of subject words that
            # also appear in the title. In that case ordinary topical support is the correct
            # grounding signal; forcing an artificial word such as "who" or "page" would
            # create false refusals.
            focus_terms = set(query_terms)
            use_support_as_focus = True

    best_focus_matches: set[str] = set()
    focus_score = support if use_support_as_focus else 0.0
    if not use_support_as_focus:
        for content_terms in content_terms_by_chunk:
            matches = focus_terms & content_terms
            score = len(matches) / max(1, len(focus_terms))
            if score > focus_score:
                focus_score = score
                best_focus_matches = matches
    else:
        # The displayed missing terms should reflect only genuinely unsupported query terms.
        for content_terms in content_terms_by_chunk:
            matches = focus_terms & content_terms
            if len(matches) > len(best_focus_matches):
                best_focus_matches = matches

    missing_focus_terms = sorted(focus_terms - best_focus_matches)

    # Reject weak or proposition-mismatched evidence before considering jurisdiction
    # ambiguity. Otherwise unrelated results from two emirates can turn an unanswerable
    # question into a misleading "please choose an emirate" response.
    if support < minimum_support:
        return GroundingAssessment(
            level=GroundingLevel.INSUFFICIENT,
            support_score=support,
            focus_score=focus_score,
            supporting_sources=source_count,
            focus_terms=sorted(focus_terms),
            missing_focus_terms=missing_focus_terms,
            reasons=["Retrieved evidence has weak topical support for the question."],
        )

    if focus_score < minimum_focus_support:
        missing = ", ".join(missing_focus_terms[:6]) or "requested fact"
        return GroundingAssessment(
            level=GroundingLevel.INSUFFICIENT,
            support_score=support,
            focus_score=focus_score,
            supporting_sources=source_count,
            focus_terms=sorted(focus_terms),
            missing_focus_terms=missing_focus_terms,
            reasons=[
                "Evidence matches the topic but does not sufficiently support the "
                f"answer-bearing terms: {missing}."
            ],
        )

    jurisdictions = {chunk.jurisdiction for chunk, _ in ranked} & _LOCAL_JURISDICTIONS
    if explicit_jurisdiction is None and len(jurisdictions) > 1:
        return GroundingAssessment(
            level=GroundingLevel.LIMITED,
            support_score=support,
            focus_score=focus_score,
            supporting_sources=source_count,
            focus_terms=sorted(focus_terms),
            missing_focus_terms=missing_focus_terms,
            reasons=["Retrieved evidence spans multiple emirate jurisdictions."],
        )

    return GroundingAssessment(
        level=GroundingLevel.SUFFICIENT,
        support_score=support,
        focus_score=focus_score,
        supporting_sources=source_count,
        focus_terms=sorted(focus_terms),
        missing_focus_terms=missing_focus_terms,
        reasons=["Retrieved evidence supports both the topic and the requested fact."],
    )


def _relation_object_terms(text: str) -> set[str]:
    raw_tokens = tokenize(text)
    canonical_tokens = [_canonical_token(token) for token in raw_tokens]
    boundary_terms = {"for", "in", "on", "from", "with", "about", "في", "من", "عن", "على"}

    for index, term in enumerate(canonical_tokens):
        if term not in _RELATION_TERMS:
            continue
        objects: set[str] = set()
        for raw, canonical in zip(
            raw_tokens[index + 1 :], canonical_tokens[index + 1 :], strict=True
        ):
            if raw in boundary_terms or canonical in boundary_terms:
                break
            if canonical not in _STOPWORDS and canonical not in _RELATION_TERMS:
                objects.add(canonical)
        if objects:
            return objects
    return set()


def _meaningful_terms(text: str) -> set[str]:
    return {
        canonical
        for token in tokenize(text)
        if (canonical := _canonical_token(token)) not in _STOPWORDS
    }


def _canonical_terms(text: str) -> set[str]:
    return {_canonical_token(token) for token in tokenize(text)}


_ARABIC_CLITIC_PREFIXES = {"و", "ف", "ب", "ك", "ل"}


def _canonical_token(token: str) -> str:
    direct = _CANONICAL.get(token)
    if direct is not None:
        return direct

    # Arabic attaches short conjunction/preposition clitics directly to nouns:
    # برخص -> ب + رخص, لترخيص -> ل + ترخيص, والهوية -> و + الهوية.
    # Only strip a prefix when the resulting token is a known domain concept. This keeps
    # normalization conservative and avoids turning unrelated Arabic words into matches.
    candidate = token
    for _ in range(2):
        if len(candidate) <= 3 or candidate[0] not in _ARABIC_CLITIC_PREFIXES:
            break
        candidate = candidate[1:]
        canonical = _CANONICAL.get(candidate)
        if canonical is not None:
            return canonical

    return token


def _jurisdiction_terms(jurisdiction: str | None) -> set[str]:
    if jurisdiction is None:
        return set()
    return set(_JURISDICTION_TERMS.get(jurisdiction, set()))


def _strip_evidence_preferences(text: str) -> str:
    cleaned = text
    for pattern in _EVIDENCE_PREFERENCE_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    return " ".join(cleaned.split())
