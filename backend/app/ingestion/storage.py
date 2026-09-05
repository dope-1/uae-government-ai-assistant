from __future__ import annotations

import hashlib
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingProvider
from app.ingestion.chunking import document_id_for
from app.ingestion.schemas import DocumentChunk, ParsedDocument, SourceSpec


class PostgresIngestionStore:
    """Persist parsed documents and chunks; vector writes use pgvector's text input format."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        source: SourceSpec,
        document: ParsedDocument,
        chunks: list[DocumentChunk],
        embedding_provider: EmbeddingProvider | None,
    ) -> None:
        document_id = document_id_for(document)
        content_hash = hashlib.sha256(document.content.encode("utf-8")).hexdigest()
        await self.session.execute(
            text(
                """
                INSERT INTO sources
                    (id, url, authority, jurisdiction, language, document_type, created_at)
                VALUES
                    (:id, :url, :authority, :jurisdiction, :language, :document_type, :created_at)
                ON CONFLICT (id) DO UPDATE SET
                    url = EXCLUDED.url,
                    authority = EXCLUDED.authority,
                    jurisdiction = EXCLUDED.jurisdiction,
                    language = EXCLUDED.language,
                    document_type = EXCLUDED.document_type
                """
            ),
            {
                "id": source.id,
                "url": str(source.url),
                "authority": source.authority,
                "jurisdiction": source.jurisdiction,
                "language": source.language,
                "document_type": source.document_type,
                "created_at": document.retrieved_at,
            },
        )
        await self.session.execute(
            text(
                """
                INSERT INTO documents
                    (id, source_id, title, content, language, retrieved_at, content_sha256)
                VALUES
                    (:id, :source_id, :title, :content, :language, :retrieved_at, :content_sha256)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    language = EXCLUDED.language,
                    retrieved_at = EXCLUDED.retrieved_at,
                    content_sha256 = EXCLUDED.content_sha256
                """
            ),
            {
                "id": document_id,
                "source_id": source.id,
                "title": document.title,
                "content": document.content,
                "language": document.language,
                "retrieved_at": document.retrieved_at,
                "content_sha256": content_hash,
            },
        )
        await self.session.execute(
            text("DELETE FROM document_chunks WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        for chunk in chunks:
            embedding_text = json.dumps(chunk.embedding) if chunk.embedding is not None else None
            await self.session.execute(
                text(
                    """
                    INSERT INTO document_chunks
                        (id, document_id, source_id, chunk_index, text, language, jurisdiction,
                         embedding_model, embedding)
                    VALUES
                        (:id, :document_id, :source_id, :chunk_index, :text, :language,
                         :jurisdiction,
                         :embedding_model, CAST(:embedding AS vector))
                    """
                ),
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "source_id": chunk.source_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "language": chunk.language,
                    "jurisdiction": chunk.jurisdiction,
                    "embedding_model": embedding_provider.name if embedding_provider else None,
                    "embedding": embedding_text,
                },
            )
        await self.session.commit()
