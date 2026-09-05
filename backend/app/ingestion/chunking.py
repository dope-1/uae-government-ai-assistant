from __future__ import annotations

import hashlib

from app.ingestion.schemas import DocumentChunk, ParsedDocument


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def document_id_for(document: ParsedDocument) -> str:
    return _stable_id(document.source_id, document.source_url, document.title)


def chunk_document(
    document: ParsedDocument,
    *,
    chunk_size_words: int = 180,
    overlap_words: int = 30,
) -> list[DocumentChunk]:
    if chunk_size_words <= 0 or overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError("Require chunk_size_words > overlap_words >= 0")
    words = document.content.split()
    document_id = document_id_for(document)
    chunks: list[DocumentChunk] = []
    step = chunk_size_words - overlap_words
    for start in range(0, len(words), step):
        segment = words[start : start + chunk_size_words]
        if not segment:
            break
        text = " ".join(segment)
        index = len(chunks)
        chunks.append(
            DocumentChunk(
                id=_stable_id(document_id, str(index), text),
                document_id=document_id,
                source_id=document.source_id,
                source_url=document.source_url,
                authority=document.authority,
                jurisdiction=document.jurisdiction,
                title=document.title,
                language=document.language,
                text=text,
                chunk_index=index,
            )
        )
        if start + chunk_size_words >= len(words):
            break
    return chunks
