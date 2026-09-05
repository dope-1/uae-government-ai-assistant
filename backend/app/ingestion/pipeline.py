from __future__ import annotations

from datetime import UTC, datetime

from app.embeddings.base import EmbeddingProvider
from app.ingestion.arabic import normalize_arabic
from app.ingestion.chunking import chunk_document
from app.ingestion.cleaning import clean_text
from app.ingestion.downloader import PublicSourceDownloader
from app.ingestion.language import detect_language
from app.ingestion.parsers import parse_html, parse_pdf
from app.ingestion.schemas import DocumentChunk, ParsedDocument, SourceSpec


class IngestionPipeline:
    def __init__(
        self,
        downloader: PublicSourceDownloader,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.downloader = downloader
        self.embedding_provider = embedding_provider

    def parse_payload(self, source: SourceSpec, payload: bytes) -> ParsedDocument:
        title, content = (
            parse_pdf(payload) if source.document_type == "pdf" else parse_html(payload)
        )
        content = clean_text(content)
        detected = detect_language(content)
        language = source.language if detected == "unknown" else detected
        if language == "ar":
            content = normalize_arabic(content)
        return ParsedDocument(
            source_id=source.id,
            source_url=str(source.url),
            authority=source.authority,
            jurisdiction=source.jurisdiction,
            title=title,
            language=language,
            document_type=source.document_type,
            retrieved_at=datetime.now(UTC),
            content=content,
        )

    async def ingest(self, source: SourceSpec) -> tuple[ParsedDocument, list[DocumentChunk]]:
        payload = await self.downloader.download(source)
        document = self.parse_payload(source, payload)
        chunks = chunk_document(document)
        if self.embedding_provider and chunks:
            vectors = self.embedding_provider.embed([chunk.text for chunk in chunks])
            if len(vectors) != len(chunks):
                raise RuntimeError("embedding provider returned unexpected vector count")
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector
        return document, chunks
