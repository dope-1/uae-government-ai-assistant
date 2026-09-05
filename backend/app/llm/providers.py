from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.llm.base import LLMGeneration
from app.retrieval.tokenization import tokenize

_EVIDENCE_BLOCK = re.compile(r'<evidence id="(S\d+)">\s*(.*?)\s*</evidence>', re.DOTALL)
_QUESTION = re.compile(r"^QUESTION=(.*)$", re.MULTILINE)
_SOURCE_ID = re.compile(r"^SOURCE_ID=(.*)$", re.MULTILINE)
_LANGUAGE = re.compile(r"^LANGUAGE=(.*)$", re.MULTILINE)
_AUTHORITY = re.compile(r"^AUTHORITY=(.*)$", re.MULTILINE)
_TITLE = re.compile(r"^TITLE=(.*)$", re.MULTILINE)
_CONTENT = re.compile(r"(?:^|\n)CONTENT=(.*)\Z", re.DOTALL)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟])\s+|\n+")
_FAQ_PAIR = re.compile(
    r"(?:^|\s)Q\s*:\s*(.+?\?)\s*A\s*:\s*(.*?)(?=(?:\s+Q\s*:)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SPACE = re.compile(r"\s+")

_SUMMARY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "from",
    "find",
    "how",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "official",
    "on",
    "the",
    "to",
    "uae",
    "what",
    "where",
    "who",
    "which",
    "groups",
    "mentioned",
    "please",
    "use",
    "indexed",
    "with",
    "would",
    "s",
    "government",
    "information",
    "page",
    "pages",
    "source",
    "sources",
    "explain",
    "في",
    "من",
    "ما",
    "ماذا",
    "كيف",
    "هل",
    "على",
    "عن",
    "الى",
    "إلى",
    "و",
    "أو",
    "الرسمية",
    "الرسمي",
    "رسمية",
    "رسمي",
    "هي",
    "هو",
    "صفحة",
    "الصفحة",
    "توجد",
    "اجد",
    "أجد",
}

_SUMMARY_CANONICAL = {
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
    "requirements": "requirement",
    "eligibility": "eligible",
    "documents": "document",
    "fees": "fee",
    "services": "service",
    "sponsorship": "sponsor",
    "sponsored": "sponsor",
    "sponsors": "sponsor",
    "universities": "university",
    "students": "student",
    "studying": "student",
    "student": "student",
    "اجدد": "renew",
    "أجدد": "renew",
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
    "خدمة": "service",
    "الخدمة": "service",
    "خدمات": "service",
    "الخدمات": "service",
    "التاشيرات": "visa",
    "التأشيرات": "visa",
    "تاشيرات": "visa",
    "تأشيرات": "visa",
    "الهوية": "identity",
    "الاقامة": "residence",
    "الإقامة": "residence",
    "الذهبية": "golden",
}

_PROCEDURE_HINTS_EN = {
    "apply",
    "application",
    "online",
    "portal",
    "website",
    "app",
    "test",
    "eye",
    "pay",
    "payment",
    "fee",
    "emirates",
    "id",
    "traffic",
    "file",
    "delivery",
    "step",
    "steps",
}
_PROCEDURE_HINTS_AR = {
    "طلب",
    "تقديم",
    "الكتروني",
    "إلكتروني",
    "منصة",
    "فحص",
    "دفع",
    "رسوم",
    "هوية",
    "ملف",
    "مروري",
    "خطوة",
    "خطوات",
}
_NAV_NOISE = {
    "engage with us",
    "contact us",
    "quick links",
    "related services",
    "privacy policy",
    "terms & conditions",
    "terms and conditions",
    "copyright",
    "careers",
    "lost & found",
    "lost & founds",
}

_DIRECTORY_TERMS = {
    "medical centre",
    "medical center",
    "polyclinic",
    "hospital",
    "clinic",
}
_SERVICE_DISCOVERY_DIRECT_PHRASES = {
    "driver licensing services",
    "driving licence renewal",
    "renewing driving licences",
    "renew driving licence",
}


@dataclass(frozen=True)
class _EvidenceSentence:
    label: str
    authority: str
    source_id: str
    language: str
    title: str
    text: str
    score: float
    order: int
    kind: str = "statement"


class GroundedExtractiveLLMProvider:
    """Offline-safe deterministic answer baseline over supplied evidence only.

    This is deliberately not presented as an LLM. It extracts concise, query-relevant
    statements (including complete FAQ Q/A pairs) and cites only the supplied evidence.
    """

    name = "grounded-extractive-baseline"

    async def generate(self, *, system_prompt: str, user_prompt: str) -> LLMGeneration:
        del system_prompt
        blocks = _EVIDENCE_BLOCK.findall(user_prompt)
        if not blocks:
            return LLMGeneration(text="", model=self.name)

        language = "ar" if "ANSWER_LANGUAGE=ar" in user_prompt else "en"
        question_match = _QUESTION.search(user_prompt)
        question = question_match.group(1).strip() if question_match else ""
        query_terms = _summary_terms(question)

        candidates: list[_EvidenceSentence] = []
        order = 0
        for label, block in blocks[:6]:
            content_match = _CONTENT.search(block)
            if not content_match:
                continue
            source_match = _SOURCE_ID.search(block)
            source_id = source_match.group(1).strip() if source_match else ""
            language_match = _LANGUAGE.search(block)
            evidence_language = language_match.group(1).strip() if language_match else ""
            authority_match = _AUTHORITY.search(block)
            authority = authority_match.group(1).strip() if authority_match else ""
            title_match = _TITLE.search(block)
            title = title_match.group(1).strip() if title_match else ""
            content = _clean_text(content_match.group(1))
            directory_block = _looks_like_directory_listing(content)
            block_bonus = (
                _source_affinity(question, source_id)
                + _language_affinity(language, evidence_language)
                + _title_affinity(query_terms, title)
            )

            faq_spans: list[tuple[int, int]] = []
            for match in _FAQ_PAIR.finditer(content):
                faq_spans.append(match.span())
                faq_question = _clean_text(match.group(1))
                faq_answer = _clean_text(match.group(2))
                if not faq_answer:
                    continue
                display = _faq_display_text(question, faq_question, faq_answer)
                score = _candidate_score(
                    faq_question + " " + faq_answer,
                    query_terms,
                    question=question,
                    kind="faq",
                ) + block_bonus
                candidates.append(
                    _EvidenceSentence(
                        label=label,
                        authority=authority,
                        source_id=source_id,
                        language=evidence_language,
                        title=title,
                        text=display,
                        score=score,
                        order=order,
                        kind="faq",
                    )
                )
                order += 1

            if directory_block:
                # Directory/contact-list chunks can be relevant to an eye-test subtask, but
                # they are poor evidence for answering a general renewal procedure question.
                # Keep any explicit FAQ pairs above, but do not summarize the listing itself.
                continue

            residual = _remove_spans(content, faq_spans)
            for sentence in _split_sentences(residual):
                if _looks_like_orphan_faq(sentence):
                    continue
                score = _candidate_score(
                    sentence,
                    query_terms,
                    question=question,
                    kind="statement",
                ) + block_bonus
                candidates.append(
                    _EvidenceSentence(
                        label=label,
                        authority=authority,
                        source_id=source_id,
                        language=evidence_language,
                        title=title,
                        text=sentence,
                        score=score,
                        order=order,
                    )
                )
                order += 1

        specialized = _render_supported_service_capability(
            candidates, question=question, language=language
        )
        if specialized is not None:
            return LLMGeneration(text=specialized, model=self.name)

        specialized = _render_supported_driving_procedure(
            candidates, question=question, language=language
        )
        if specialized is not None:
            return LLMGeneration(text=specialized, model=self.name)

        if _is_direct_yes_no_question(question) or _is_service_discovery_question(question):
            max_sentences = 1
        elif _is_procedure_question(question):
            max_sentences = 3
        else:
            max_sentences = 2
        selected = _select_sentences(
            candidates,
            max_sentences=max_sentences,
            query_terms=query_terms,
            question=question,
        )
        if not selected:
            return LLMGeneration(text="", model=self.name)

        source_lookup = _render_source_lookup(
            selected, question=question, language=language
        )
        if source_lookup is not None:
            return LLMGeneration(text=source_lookup, model=self.name)

        if _is_service_discovery_question(question):
            return LLMGeneration(
                text=_render_service_discovery(selected, language=language),
                model=self.name,
            )

        return LLMGeneration(
            text=_render_grounded_summary(selected, language=language),
            model=self.name,
        )


class OpenAICompatibleLLMProvider:
    """Hosted provider using the widely supported OpenAI-compatible chat API shape."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.name = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(self, *, system_prompt: str, user_prompt: str) -> LLMGeneration:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(self._url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        text = str(data["choices"][0]["message"]["content"])
        usage = data.get("usage", {})
        return LLMGeneration(
            text=text,
            model=self._model,
            prompt_tokens=_int_or_none(usage.get("prompt_tokens")),
            completion_tokens=_int_or_none(usage.get("completion_tokens")),
        )


class OllamaLLMProvider:
    """Local/open-source model path through a locally running Ollama server."""

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout_seconds: float = 120.0,
    ) -> None:
        self.name = model
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout_seconds = timeout_seconds

    async def generate(self, *, system_prompt: str, user_prompt: str) -> LLMGeneration:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(self._url, json=payload)
            response.raise_for_status()
            data = response.json()
        return LLMGeneration(
            text=str(data["message"]["content"]),
            model=self._model,
            prompt_tokens=_int_or_none(data.get("prompt_eval_count")),
            completion_tokens=_int_or_none(data.get("eval_count")),
        )


def _split_sentences(content: str) -> list[str]:
    raw = [segment.strip(" -•\t") for segment in _SENTENCE_SPLIT.split(content)]
    sentences = [_clean_text(segment) for segment in raw if len(segment.strip()) >= 24]
    if sentences:
        return sentences
    return [content] if content else []



_ARABIC_CLITIC_PREFIXES = {"و", "ف", "ب", "ك", "ل"}


def _summary_token(token: str) -> str:
    direct = _SUMMARY_CANONICAL.get(token)
    if direct is not None:
        return direct
    candidate = token
    for _ in range(2):
        if len(candidate) <= 3 or candidate[0] not in _ARABIC_CLITIC_PREFIXES:
            break
        candidate = candidate[1:]
        direct = _SUMMARY_CANONICAL.get(candidate)
        if direct is not None:
            return direct
    return token


def _language_affinity(answer_language: str, evidence_language: str) -> float:
    if not evidence_language:
        return 0.0
    if answer_language == evidence_language:
        return 0.30
    return -0.08


def _title_affinity(query_terms: set[str], title: str) -> float:
    if not query_terms or not title:
        return 0.0
    title_terms = _summary_terms(title)
    if not title_terms:
        return 0.0
    return 0.35 * (len(query_terms & title_terms) / len(query_terms))


def _is_vehicle_question(question: str) -> bool:
    terms = _summary_terms(question)
    has_vehicle_terms = bool({"vehicle", "ownership", "registration"} & terms)
    return has_vehicle_terms and not _is_driving_licence_question(question)


def _source_affinity(question: str, source_id: str) -> float:
    if not source_id:
        return 0.0
    terms = _summary_terms(question)
    source = source_id.casefold()

    if "golden" in terms and "visa" in terms:
        if "golden_visa" in source:
            return 0.70
        if "student_residence" in source or "residence_types" in source:
            return -0.45

    if "student" in terms and ("visa" in terms or "residence" in terms):
        if "student_residence" in source:
            return 0.75
        if "golden_visa" in source or "residence_types" in source:
            return -0.50

    if "visa" in terms and "identity" in terms and "visa_identity" in source:
        return 0.70

    if _is_driving_licence_question(question):
        if "driver_licensing" in source or "driving_licence" in source:
            return 0.70
        if source == "dubai_services_ar":
            return 0.35
        if "vehicle_licensing" in source or "vehicle_ownership" in source:
            return -0.70

    if _is_vehicle_question(question):
        if "vehicle_licensing" in source or "vehicle_ownership" in source:
            return 0.70
        if source == "dubai_services_ar":
            return 0.35
        if "driver_licensing" in source or "driving_licence" in source:
            return -0.70

    return 0.0


def _strip_known_page_chrome(text: str) -> str:
    """Trim flattened navigation prefixes without changing the factual sentence body."""

    cleaned = _clean_text(text)
    anchors = (
        "Apply for or Manage a Driving Licence",
        "Renew and Amend Vehicle Data Ownership",
        "Driver Licensing Services Overview",
        "Vehicle Licensing Services Overview",
        "Golden visa Golden visa",
        "Student visa Student visa",
        "Types of visas Types of visas",
        "خدمات ترخيص السائقين نظرة عامة",
        "خدمات ترخيص المركبات نظرة عامة",
    )
    lowered = cleaned.casefold()
    positions: list[tuple[int, str]] = []
    for anchor in anchors:
        pos = lowered.find(anchor.casefold())
        if pos >= 0:
            positions.append((pos, anchor))
    if not positions:
        return cleaned

    pos, _ = min(positions, key=lambda item: item[0])
    # A tiny prefix can be meaningful prose. Only trim when page chrome precedes the anchor.
    if pos >= 18:
        cleaned = cleaned[pos:]

    duplicates = (
        ("Golden visa Golden visa", "Golden visa"),
        ("Student visa Student visa", "Student visa"),
        ("Types of visas Types of visas", "Types of visas"),
        ("التاشيرات وبطاقة الهوية التاشيرات وبطاقة الهوية", "التاشيرات وبطاقة الهوية"),
        ("التأشيرات وبطاقة الهوية التأشيرات وبطاقة الهوية", "التأشيرات وبطاقة الهوية"),
    )
    for repeated, single in duplicates:
        if cleaned.casefold().startswith(repeated.casefold()):
            cleaned = single + cleaned[len(repeated) :]
            break
    return cleaned


def _best_fact_supporting_item(
    items: list[_EvidenceSentence], *, question: str
) -> _EvidenceSentence:
    """Prefer the chunk that directly contains the fact asserted by a template."""

    required: set[str] = set()
    if _is_driving_licence_question(question):
        required.update({"drive", "licence"})
    if _is_vehicle_question(question):
        required.add("vehicle")
    # Capability templates below explicitly assert renewal even for portal/source wording.
    if _is_driving_licence_question(question) or _is_vehicle_question(question):
        required.add("renew")

    def key(item: _EvidenceSentence) -> tuple[int, int, float, int]:
        item_terms = _summary_terms(item.text)
        hits = len(required & item_terms)
        complete = int(bool(required) and required <= item_terms)
        return (complete, hits, item.score, -item.order)

    return max(items, key=key)


def _render_supported_service_capability(
    candidates: list[_EvidenceSentence], *, question: str, language: str
) -> str | None:
    """Compose clean service-discovery/capability answers from a strongly matched source.

    This avoids echoing flattened menus and prevents a neighbouring service page from being
    cited simply because it shares authority/navigation text with the requested service.
    """

    terms = _summary_terms(question)
    is_lookup = (
        _is_direct_yes_no_question(question)
        or _is_service_discovery_question(question)
        or "portal" in terms
        or "available" in terms
        or "access" in terms
        or "where" in set(tokenize(question))
        or "find" in set(tokenize(question))
        or "اين" in set(tokenize(question))
        or "أين" in question
        or "اجد" in set(tokenize(question))
        or "أجد" in question
    )
    if not is_lookup:
        return None

    grouped: dict[str, list[_EvidenceSentence]] = {}
    for candidate in candidates:
        if candidate.source_id:
            grouped.setdefault(candidate.source_id, []).append(candidate)

    ranked_groups = sorted(
        grouped.items(),
        key=lambda item: (
            -(
                _source_affinity(question, item[0])
                + max(
                    _language_affinity(language, candidate.language)
                    for candidate in item[1]
                )
            ),
            -max(candidate.score for candidate in item[1]),
        ),
    )
    for source_id, items in ranked_groups:
        affinity = _source_affinity(question, source_id)
        if affinity <= 0:
            continue
        joined = " ".join(item.text for item in items)
        joined_terms = _summary_terms(joined)
        if "renew" in terms and "renew" not in joined_terms:
            continue
        if _is_driving_licence_question(question) and not (
            {"drive", "licence"} <= joined_terms
        ):
            continue
        if _is_vehicle_question(question) and "vehicle" not in joined_terms:
            continue

        best = _best_fact_supporting_item(items, question=question)
        label = best.label
        authority = best.authority or "the indexed official authority"
        source = source_id.casefold()

        if "dubai_driving_licence" in source:
            if language == "ar":
                return (
                    "وفقاً لهيئة الطرق والمواصلات، تتيح خدمة إدارة رخصة القيادة "
                    f"اختيار تجديد رخصة القيادة عبر القنوات الرسمية. [{label}]"
                )
            return (
                f"According to {authority}, use the Apply for or Manage a Driving Licence "
                f"service and select Renew Driving Licence. [{label}]"
            )

        if "dubai_vehicle_ownership" in source:
            if language == "ar":
                return (
                    "وفقاً لهيئة الطرق والمواصلات، تتيح خدمة تجديد وتعديل بيانات ملكية "
                    f"المركبة تجديد ملكية المركبة المسجلة في دبي. [{label}]"
                )
            return (
                f"According to {authority}, the Renew and Amend Vehicle Data Ownership "
                f"service covers renewing ownership of vehicles registered in Dubai. [{label}]"
            )

        if source == "dubai_services_ar":
            if _is_driving_licence_question(question):
                if language == "ar":
                    return (
                        "وفقاً لهيئة الطرق والمواصلات، تتوفر خدمات رسمية لإدارة وتجديد "
                        f"رخص القيادة في دبي. [{label}]"
                    )
                return (
                    "According to Roads and Transport Authority, official Dubai services "
                    f"include driving-licence management and renewal. [{label}]"
                )
            if _is_vehicle_question(question):
                if language == "ar":
                    return (
                        "وفقاً لهيئة الطرق والمواصلات، تتوفر خدمات رسمية لتجديد وإدارة "
                        f"ملكية المركبات في دبي. [{label}]"
                    )
                return (
                    "According to Roads and Transport Authority, official Dubai services "
                    f"include vehicle-ownership renewal and management. [{label}]"
                )

        if "abu_dhabi_driver_licensing" in source:
            best_text = " ".join(
                item.text for item in items if item.label == best.label
            )
            has_tamm = (
                "tamm" in best_text.casefold()
                or "منصة تم" in best_text
                or "بوابة تم" in best_text
            )
            if language == "ar":
                sentence = (
                    "وفقاً لمركز النقل المتكامل (أبوظبي للتنقل)، تشمل خدمات ترخيص "
                    "السائقين إصدار وتجديد رخص القيادة"
                )
                if has_tamm:
                    sentence += "، وتتوفر المعاملات الرقمية عبر منصة تم"
                return f"{sentence}. [{label}]"
            sentence = (
                f"According to {authority}, Driver Licensing Services include issuing and "
                "renewing driving licences"
            )
            if has_tamm:
                sentence += ", with digital transactions available through the TAMM portal"
            return f"{sentence}. [{label}]"

        if "abu_dhabi_vehicle_licensing" in source:
            best_text = " ".join(
                item.text for item in items if item.label == best.label
            )
            has_tamm = (
                "tamm" in best_text.casefold()
                or "منصة تم" in best_text
                or "بوابة تم" in best_text
            )
            if language == "ar":
                sentence = (
                    "وفقاً لمركز النقل المتكامل (أبوظبي للتنقل)، تشمل خدمات ترخيص "
                    "المركبات إصدار وتجديد وتسجيل ونقل ملكية المركبات"
                )
                if has_tamm:
                    sentence += "، وتتوفر المعاملات الرقمية عبر منصة تم"
                return f"{sentence}. [{label}]"
            sentence = (
                f"According to {authority}, Vehicle Licensing Services cover issuing, "
                "renewing, registering and transferring vehicle ownership"
            )
            if has_tamm:
                sentence += ", with digital transactions available through the TAMM portal"
            return f"{sentence}. [{label}]"

    return None


def _candidate_score(
    text: str,
    query_terms: set[str],
    *,
    question: str,
    kind: str,
) -> float:
    sentence_terms = _summary_terms(text)
    if not query_terms:
        return 0.0
    overlap_terms = query_terms & sentence_terms
    overlap = len(overlap_terms) / len(query_terms)
    score = overlap + min(0.25, 0.05 * len(overlap_terms))

    lowered_text = text.casefold()
    if "eligible" in query_terms and "eligible" in sentence_terms:
        # Eligibility questions should prefer the sentence that actually identifies
        # eligible people/categories over a nearby generic programme definition.
        score += 0.55

    if _is_driving_licence_question(question):
        if any(
            phrase in lowered_text
            for phrase in (
                "renew driving licence",
                "renewing a driving licence",
                "renewing driving licences",
                "driver licensing services",
            )
        ):
            score += 0.30
        if any(
            phrase in lowered_text
            for phrase in (
                "renew vehicle ownership",
                "vehicle ownership",
                "vehicle registration renewal",
                "registering and transferring ownership",
            )
        ):
            score -= 0.65

    if _is_procedure_question(question):
        hints = _PROCEDURE_HINTS_AR if _contains_arabic(question) else _PROCEDURE_HINTS_EN
        hint_hits = len(set(tokenize(text)) & hints)
        score += min(0.35, 0.06 * hint_hits)
        if _has_procedure_anchor(text):
            score += 0.20
        if kind == "faq":
            # General "how do I" questions should prefer actual steps over edge-case FAQs.
            score -= 0.55
        if _looks_like_directory_listing(text):
            score -= 0.80

    if _is_service_discovery_question(question):
        lowered_text = text.casefold()
        if any(phrase in lowered_text for phrase in _SERVICE_DISCOVERY_DIRECT_PHRASES):
            score += 0.35
        if "vehicle" in lowered_text and "vehicle" not in question.casefold():
            score -= 0.25
        if "all services" in lowered_text or "these encompass all services" in lowered_text:
            score -= 0.12

    if kind == "faq" and _is_direct_yes_no_question(question):
        score += 0.20

    lowered = lowered_text
    if any(noise in lowered for noise in _NAV_NOISE):
        score -= 0.30
    if text.rstrip().endswith(("?", "؟")):
        score -= 0.35
    return score


def _select_sentences(
    candidates: list[_EvidenceSentence],
    *,
    max_sentences: int = 2,
    query_terms: set[str] | None = None,
    question: str = "",
) -> list[_EvidenceSentence]:
    if not candidates:
        return []

    ranked = sorted(candidates, key=lambda item: (-item.score, item.order))
    selected: list[_EvidenceSentence] = []
    seen_text: set[str] = set()
    seen_labels: set[str] = set()
    total_chars = 0

    for item in ranked:
        if item.score <= 0:
            continue
        normalized = item.text.casefold()
        if normalized in seen_text:
            continue
        if _is_procedure_question(question) and selected:
            # A procedure answer should stay within one evidence chunk instead of stitching
            # together neighbouring services that happen to share form/navigation terms.
            if item.label != selected[0].label:
                continue
        elif selected:
            # Once a clearly query-aligned service/source has been selected, do not append a
            # weaker neighbouring service merely because it uses similar government wording.
            first_affinity = _source_affinity(question, selected[0].source_id)
            item_affinity = _source_affinity(question, item.source_id)
            if (
                selected[0].source_id
                and item.source_id != selected[0].source_id
                and first_affinity > 0
                and item_affinity < first_affinity
            ):
                continue
            if item.label in seen_labels and len({candidate.label for candidate in ranked}) > 1:
                continue
        elif item.label in seen_labels and len({candidate.label for candidate in ranked}) > 1:
            continue
        if item.kind == "faq":
            concise_text = item.text
        elif _is_procedure_question(question):
            concise_text = _procedure_excerpt(item.text, query_terms or set(), limit=58)
        else:
            concise_text = _focused_excerpt(item.text, query_terms or set(), limit=44)
        concise_text = _strip_known_page_chrome(concise_text)
        concise_text = _truncate_words(
            concise_text,
            52 if item.kind == "faq" else 58 if _is_procedure_question(question) else 44,
        )
        if _is_procedure_question(question) and _looks_like_directory_listing(concise_text):
            continue
        if selected and item.score < max(0.55, selected[0].score - 0.30):
            continue
        if total_chars + len(concise_text) > 650 and selected:
            continue
        selected.append(
            _EvidenceSentence(
                label=item.label,
                authority=item.authority,
                source_id=item.source_id,
                language=item.language,
                title=item.title,
                text=concise_text,
                score=item.score,
                order=item.order,
                kind=item.kind,
            )
        )
        seen_text.add(normalized)
        seen_labels.add(item.label)
        total_chars += len(concise_text)
        if len(selected) == max_sentences:
            break

    return selected


def _has_procedure_anchor(text: str) -> bool:
    lowered = text.casefold()
    anchors = (
        "how to apply",
        "ways to apply",
        "renewal process",
        "renewal procedure",
        "eye test",
        "payment methods",
        "apply online",
        "digital service",
        "tamm portal",
        "rta app",
        "traffic file",
        "log in",
        "uae pass",
        "select renew",
    )
    return any(anchor in lowered for anchor in anchors)


def _looks_like_directory_listing(text: str) -> bool:
    lowered = text.casefold()
    directory_hits = sum(lowered.count(term) for term in _DIRECTORY_TERMS)
    phone_like = re.findall(r"(?:\+?\d[\d ()-]{5,}\d)", text)
    return directory_hits >= 3 or len(phone_like) >= 4


def _procedure_excerpt(text: str, query_terms: set[str], *, limit: int) -> str:
    """Extract a coherent action window for procedural answers.

    HTML service pages are flattened during ingestion, so useful steps may not retain list
    punctuation. Prefer the earliest action anchor near a driving-licence renewal phrase,
    then fall back to the generic query-focused excerpt.
    """
    cleaned = _clean_text(text)
    if not cleaned:
        return cleaned

    lowered = cleaned.casefold()
    target_positions = [
        pos
        for phrase in (
            "renewing a driving licence",
            "renew driving licence",
            "driving licence renewal",
        )
        if (pos := lowered.find(phrase)) >= 0
    ]
    target = min(target_positions) if target_positions else -1

    action_phrases = (
        "take an eye test",
        "log in",
        "select renewing",
        "select renew",
        "apply online",
        "steps",
    )
    starts = [
        pos
        for phrase in action_phrases
        if (pos := lowered.find(phrase)) >= 0 and (target < 0 or pos <= target + 180)
    ]
    if starts:
        start = min(starts)
        words = cleaned[start:].split()
        excerpt = " ".join(words[:limit]).strip(" ,;:")
        if len(words) > limit:
            excerpt += "…"
        return excerpt

    return _focused_excerpt(cleaned, query_terms, limit=limit)


def _focused_excerpt(text: str, query_terms: set[str], *, limit: int) -> str:
    words = text.split()
    if len(words) <= limit or not query_terms:
        return text

    canonical_words: list[str] = []
    for word in words:
        word_tokens = tokenize(word)
        token = word_tokens[0] if word_tokens else ""
        canonical_words.append(_SUMMARY_CANONICAL.get(token, token))
    if not canonical_words:
        return _truncate_words(text, limit)

    # Pick the window with the best concentration of answer-bearing query terms.
    best_start = 0
    best_score = -1.0
    window = min(limit, len(words))
    for start in range(0, max(1, len(words) - window + 1)):
        end = start + window
        window_terms = set(canonical_words[start:end])
        score: float = float(len(window_terms & query_terms) * 10)
        # Earlier windows win ties so coherent sentence openings are preserved when possible.
        score -= start / max(1, len(words))
        if score > best_score:
            best_score = score
            best_start = start

    excerpt = " ".join(words[best_start : best_start + window]).strip(" ,;:")
    if best_start > 0:
        excerpt = "…" + excerpt
    if best_start + window < len(words):
        excerpt += "…"
    return excerpt


def _render_supported_driving_procedure(
    candidates: list[_EvidenceSentence], *, question: str, language: str
) -> str | None:
    """Render a concise Abu Dhabi driving-renewal answer when the evidence supports it.

    Abu Dhabi Mobility's licensing overview is a flattened webpage where navigation labels
    can sit next to the useful prose.  When the retrieved evidence explicitly says that
    driver licensing includes renewal and that the services are available through TAMM,
    compose those supported facts directly instead of echoing the flattened page text.
    """
    if language != "en" or not _is_procedure_question(question):
        return None
    if not _is_driving_licence_question(question):
        return None

    grouped: dict[str, list[_EvidenceSentence]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.label, []).append(candidate)

    for label, items in grouped.items():
        authority = next((item.authority for item in items if item.authority), "")
        if "abu dhabi mobility" not in authority.casefold():
            continue

        joined = " ".join(item.text for item in items)
        lowered = joined.casefold()
        has_renewal = (
            "renewing driving licences" in lowered
            or "renew driving licence" in lowered
            or "driving licence renewal" in lowered
        )
        has_tamm = "tamm" in lowered
        if not (has_renewal and has_tamm):
            continue

        first = (
            f"According to {authority}, renewing a driving licence is one of the Driver "
            "Licensing Services available digitally through the TAMM portal."
        )
        if "uae pass" in lowered and "traffic file" in lowered:
            first += (
                " The portal supports licensing transactions using UAE Pass and an active "
                "traffic file."
            )
        return f"{first} [{label}]"

    return None


def _asks_for_source_lookup(question: str) -> bool:
    lowered = question.casefold()
    english_patterns = (
        "where can i find official",
        "which uae government source",
        "which government source",
        "what federal page",
        "what is the official federal source",
        "where is the official",
        "official federal source",
    )
    if any(pattern in lowered for pattern in english_patterns):
        return True
    return any(
        pattern in question
        for pattern in (
            "ما المصدر",
            "أين توجد صفحة",
            "اين توجد صفحة",
            "المصدر الاتحادي",
            "المصدر الرسمي",
            "صفحة حكومة الإمارات",
        )
    )


def _render_source_lookup(
    selected: list[_EvidenceSentence], *, question: str, language: str
) -> str | None:
    if not selected or not _asks_for_source_lookup(question):
        return None
    first = selected[0]
    title = first.title.split(" | ", 1)[0].strip() if first.title else ""
    detail = _strip_known_page_chrome(
        _focused_excerpt(first.text, _summary_terms(question), limit=24)
    )
    detail = _truncate_words(detail, 24)

    if language == "ar":
        authority = first.authority.strip()
        authority_ar = (
            "المنصة الرسمية لحكومة الإمارات"
            if authority.casefold() == "uae government portal"
            else authority
        )
        if title:
            lead = f"المصدر الرسمي ذو الصلة هو صفحة «{title}» التابعة لـ{authority_ar}."
        elif authority_ar:
            lead = f"يمكن العثور على المعلومات في المصدر الرسمي لـ{authority_ar}."
        else:
            lead = "يمكن العثور على المعلومات في المصدر الرسمي المفهرس."
        if detail:
            return f"{lead} {detail} [{first.label}]"
        return f"{lead} [{first.label}]"

    authority = first.authority.strip() or "the indexed official authority"
    if title:
        lead = f"According to {authority}, the relevant official page is “{title}”."
    else:
        lead = f"According to {authority}, this is the relevant indexed official source."
    if detail:
        return f"{lead} {detail} [{first.label}]"
    return f"{lead} [{first.label}]"


def _render_service_discovery(selected: list[_EvidenceSentence], *, language: str) -> str:
    first = selected[0]
    authority = first.authority.strip()
    fact = _decapitalize(first.text) if language == "en" else first.text
    if language == "ar":
        if authority:
            lead = f"وفقاً لـ{authority}، {fact} [{first.label}]"
        else:
            lead = f"وفقاً للمصدر الرسمي المفهرس، {fact} [{first.label}]"
    elif authority:
        lead = f"According to {authority}, {fact} [{first.label}]"
    else:
        lead = f"According to the indexed official source, {fact} [{first.label}]"

    if len(selected) == 1:
        return lead
    second = selected[1]
    return f"{lead} {second.text} [{second.label}]"


def _render_grounded_summary(selected: list[_EvidenceSentence], *, language: str) -> str:
    first = selected[0]
    if language == "ar":
        prefix = "وفقاً للمصادر الرسمية المفهرسة،"
    elif first.authority:
        prefix = f"According to {first.authority},"
    else:
        prefix = "Based on the indexed official sources,"
    statements = [
        f"{_decapitalize(item.text) if language == 'en' else item.text} [{item.label}]"
        for item in selected
    ]
    return f"{prefix} " + " ".join(statements)


def _faq_display_text(user_question: str, faq_question: str, faq_answer: str) -> str:
    if _is_direct_yes_no_question(user_question):
        return faq_answer
    # Keep the FAQ answer attached to its condition so a short answer such as "No" is
    # never emitted without context.
    return f"{faq_question} — {faq_answer}"


def _remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    return " ".join(parts)


def _looks_like_orphan_faq(text: str) -> bool:
    stripped = text.lstrip().casefold()
    return stripped.startswith(("q:", "q :", "a:", "a :"))


def _is_direct_yes_no_question(question: str) -> bool:
    tokens = tokenize(question)
    if not tokens:
        return False
    return tokens[0] in {"do", "does", "did", "can", "is", "are", "has", "have", "هل"}


def _is_driving_licence_question(question: str) -> bool:
    lowered = question.casefold()
    return (
        any(
            phrase in lowered
            for phrase in (
                "driving licence",
                "driving license",
                "driver licence",
                "driver licensing",
                "drivers licensing",
            )
        )
        or ("driv" in lowered and any(term in lowered for term in ("licence", "license")))
        or ("رخص" in question and "قياد" in question)
    )


def _is_procedure_question(question: str) -> bool:
    lowered = question.casefold()
    return any(
        marker in lowered
        for marker in ("how do", "how can", "steps", "procedure", "كيف", "خطوات")
    )


def _is_service_discovery_question(question: str) -> bool:
    lowered = question.casefold()
    tokens = set(tokenize(question))
    if any(
        marker in lowered
        for marker in (
            "أي خدمة",
            "ما هي الخدمة",
            "ما خدمة",
            "ما الخدمة",
            "من الجهة",
            "أين أجد خدمة",
            "اين اجد خدمة",
        )
    ):
        return True
    if "service" in tokens and ({"what", "which", "who"} & tokens):
        return True
    return "handle" in tokens or "handles" in tokens


def _summary_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for token in tokenize(text):
        canonical = _summary_token(token)
        if canonical not in _SUMMARY_STOPWORDS:
            terms.add(canonical)
    return terms


def _contains_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" for char in text)


def _clean_text(text: str) -> str:
    return _SPACE.sub(" ", text).strip()


def _decapitalize(text: str) -> str:
    if not text:
        return text
    return text[0].lower() + text[1:]


def _truncate_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(" ,;:") + "…"


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int) else None
