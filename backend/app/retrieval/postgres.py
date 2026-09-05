from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingProvider
from app.ingestion.schemas import DocumentChunk


class PgVectorRetriever:
    """Database-backed cosine retrieval over the pgvector chunk index."""

    def __init__(self, session: AsyncSession, provider: EmbeddingProvider) -> None:
        self.session = session
        self.provider = provider

    async def search(
        self,
        query: str,
        *,
        k: int = 10,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        query_vector = self.provider.embed([query])[0]
        filters = ["dc.embedding IS NOT NULL"]
        params: dict[str, object] = {
            "embedding": json.dumps(query_vector),
            "limit": k,
        }
        if jurisdiction:
            filters.append("dc.jurisdiction = :jurisdiction")
            params["jurisdiction"] = jurisdiction
        where_clause = " AND ".join(filters)
        statement = text(
            f"""
            SELECT
                dc.id,
                dc.document_id,
                dc.source_id,
                s.url AS source_url,
                s.authority,
                dc.jurisdiction,
                d.title,
                dc.language,
                dc.text,
                dc.chunk_index,
                d.retrieved_at,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            JOIN sources AS s ON s.id = dc.source_id
            WHERE {where_clause}
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        result = await self.session.execute(statement, params)
        return [self._to_result(row) for row in result.mappings()]

    @staticmethod
    def _to_result(row: RowMapping) -> tuple[DocumentChunk, float]:
        chunk = DocumentChunk(
            id=str(row["id"]),
            document_id=str(row["document_id"]),
            source_id=str(row["source_id"]),
            source_url=str(row["source_url"]),
            authority=str(row["authority"]),
            jurisdiction=str(row["jurisdiction"]),
            title=str(row["title"]),
            language=str(row["language"]),
            text=str(row["text"]),
            chunk_index=int(row["chunk_index"]),
            retrieved_at=row.get("retrieved_at"),
        )
        return chunk, float(row["score"])
