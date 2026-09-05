from __future__ import annotations

import re

from pydantic import HttpUrl

from app.ingestion.schemas import DocumentChunk
from app.rag.schemas import Citation
from app.retrieval.tokenization import tokenize

_CITATION = re.compile(r"\[S(\d+)\]")


_EXCERPT_CANONICAL = {
    "renewal": "renew",
    "renewing": "renew",
    "renewed": "renew",
    "renews": "renew",
    "driving": "drive",
    "driver": "drive",
    "drivers": "drive",
    "licensing": "licence",
    "license": "licence",
    "licenses": "licence",
    "licences": "licence",
    "تجديد": "renew",
    "يجدد": "renew",
    "اجدد": "renew",
    "أجدد": "renew",
    "رخصة": "licence",
    "رخص": "licence",
    "ترخيص": "licence",
    "القيادة": "drive",
    "المركبة": "vehicle",
    "المركبات": "vehicle",
    "مركبة": "vehicle",
}


def _excerpt_terms(text: str) -> set[str]:
    return {_EXCERPT_CANONICAL.get(token, token) for token in tokenize(text)}


def _relevant_excerpt(text: str, query: str | None, max_chars: int) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    if not query:
        return cleaned[: max_chars - 1].rstrip() + "…"

    query_terms = _excerpt_terms(query)
    if not query_terms:
        return cleaned[: max_chars - 1].rstrip() + "…"

    words = cleaned.split()
    if len(words) <= 16:
        return cleaned[: max_chars - 1].rstrip() + "…"

    window = min(46, len(words))
    stride = max(1, window // 5)
    starts = list(range(0, max(1, len(words) - window + 1), stride))
    final_start = max(0, len(words) - window)
    if final_start not in starts:
        starts.append(final_start)

    best_start = 0
    best_score = -1.0
    for start in starts:
        segment = " ".join(words[start : start + window])
        segment_terms = _excerpt_terms(segment)
        overlap = len(query_terms & segment_terms)
        score = overlap / max(1, len(query_terms))
        # Prefer earlier windows only when factual overlap is tied.
        score -= start / max(1, len(words)) * 0.001
        if score > best_score:
            best_score = score
            best_start = start

    excerpt_words = words[best_start : best_start + window]
    while excerpt_words and len(" ".join(excerpt_words)) > max_chars - 2:
        excerpt_words.pop()
    excerpt = " ".join(excerpt_words).strip()
    if best_start > 0:
        excerpt = "…" + excerpt
    if best_start + len(excerpt_words) < len(words):
        excerpt = excerpt.rstrip("…") + "…"
    return excerpt


def build_citations(
    chunks: list[DocumentChunk],
    *,
    query: str | None = None,
    max_excerpt_chars: int = 360,
) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int]] = set()
    for chunk in chunks:
        key = (chunk.document_id, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        excerpt = _relevant_excerpt(chunk.text, query, max_excerpt_chars)
        citations.append(
            Citation(
                id=f"S{len(citations) + 1}",
                chunk_id=chunk.id,
                title=chunk.title,
                authority=chunk.authority,
                url=HttpUrl(chunk.source_url),
                jurisdiction=chunk.jurisdiction,
                retrieved_at=chunk.retrieved_at,
                relevant_excerpt=excerpt,
                source_id=chunk.source_id,
                document_id=chunk.document_id,
            )
        )
    return citations


def sanitize_citation_markers(answer: str, citation_count: int) -> str:
    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        return match.group(0) if 1 <= index <= citation_count else ""

    cleaned = _CITATION.sub(replace, answer).strip()
    if citation_count > 0 and not _CITATION.search(cleaned):
        cleaned = f"{cleaned} [S1]".strip()
    return cleaned


def select_referenced_citations(answer: str, citations: list[Citation]) -> list[Citation]:
    referenced = {f"S{match}" for match in _CITATION.findall(answer)}
    return [citation for citation in citations if citation.id in referenced]
