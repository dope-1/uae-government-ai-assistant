from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingProvider
from app.ingestion.schemas import DocumentChunk
from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.postgres import PgVectorRetriever
from app.retrieval.reranking import TokenOverlapReranker


class PgHybridRetriever:
    """PostgreSQL lexical + pgvector retrieval fused with reciprocal-rank fusion."""

    def __init__(self, session: AsyncSession, provider: EmbeddingProvider) -> None:
        self.session = session
        self.vector = PgVectorRetriever(session, provider)
        self.reranker = TokenOverlapReranker()

    async def search(
        self,
        query: str,
        *,
        k: int = 6,
        candidate_k: int = 24,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        dense = await self.vector.search(query, k=candidate_k, jurisdiction=jurisdiction)
        lexical = await self._lexical(query, k=candidate_k, jurisdiction=jurisdiction)
        fused = reciprocal_rank_fusion([lexical, dense], k=candidate_k)
        reranked = self.reranker.rerank(
            _rerank_query(query),
            fused,
            min(candidate_k, max(k * 3, k)),
        )
        adjusted = [
            (chunk, score + _intent_adjustment(query, chunk))
            for chunk, score in reranked
        ]
        return sorted(adjusted, key=lambda pair: (-pair[1], pair[0].id))[:k]

    async def _lexical(
        self,
        query: str,
        *,
        k: int,
        jurisdiction: str | None,
    ) -> list[tuple[DocumentChunk, float]]:
        filters = [
            "to_tsvector('simple', dc.text) @@ plainto_tsquery('simple', :query)"
        ]
        params: dict[str, object] = {"query": query, "limit": k}
        if jurisdiction:
            filters.append("dc.jurisdiction = :jurisdiction")
            params["jurisdiction"] = jurisdiction
        statement = text(
            f"""
            SELECT dc.id, dc.document_id, dc.source_id, s.url AS source_url,
                   s.authority, dc.jurisdiction, d.title, dc.language, dc.text,
                   dc.chunk_index, d.retrieved_at,
                   ts_rank_cd(
                       to_tsvector('simple', dc.text),
                       plainto_tsquery('simple', :query)
                   ) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            JOIN sources s ON s.id = dc.source_id
            WHERE {' AND '.join(filters)}
            ORDER BY score DESC, dc.id
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
            retrieved_at=row["retrieved_at"],
        )
        return chunk, float(row["score"])


def _rerank_query(query: str) -> str:
    """Add intent hints only for reranking; candidate retrieval keeps the original query.

    PostgreSQL lexical search uses plainto_tsquery (AND semantics), so expanding the
    retrieval query itself could accidentally exclude useful chunks. Expanding only the
    reranker helps procedural chunks rise without reducing recall.
    """
    lowered = query.casefold()
    if any(marker in lowered for marker in ("how do", "how can", "steps", "procedure")):
        return query + " steps apply online portal eye test payment traffic file"
    if any(marker in query for marker in ("كيف", "خطوات")):
        return query + " خطوات تقديم طلب منصة فحص دفع رسوم ملف مروري"
    return query


_PHONE_LIKE = re.compile(r"(?:\+?\d[\d ()-]{5,}\d)")


def _intent_adjustment(query: str, chunk: DocumentChunk) -> float:
    """Adjust reranked candidates using procedure quality and service-entity consistency.

    UAE portal pages reuse navigation and form vocabulary, so a neighbouring service can
    look semantically relevant. Keep candidate recall broad, then demote source pages whose
    service identity conflicts with the user's requested entity.
    """
    lowered_query = query.casefold()
    lowered = chunk.text.casefold()
    source_key = f"{chunk.source_id} {chunk.source_url} {chunk.title}".casefold()
    bonus = 0.0

    driving_query = _is_driving_licence_query(lowered_query)
    vehicle_query = _is_vehicle_query(lowered_query)

    if driving_query:
        if any(
            marker in source_key
            for marker in (
                "vehicle_ownership",
                "vehicle-ownership",
                "vehicle_registration",
                "vehicle-registration",
                "vehicle_licensing",
                "vehicle-licensing",
            )
        ):
            bonus -= 1.10
        if any(
            marker in source_key
            for marker in (
                "driving_licence",
                "driving-licence",
                "driver_licensing",
                "driver-licensing",
            )
        ):
            bonus += 0.35
        if any(
            phrase in lowered
            for phrase in (
                "renew driving licence",
                "renewing a driving licence",
                "renewing driving licences",
                "driver licensing services",
            )
        ):
            bonus += 0.20

    if vehicle_query:
        if any(
            marker in source_key
            for marker in (
                "driving_licence",
                "driving-licence",
                "driver_licensing",
                "driver-licensing",
            )
        ):
            bonus -= 0.85
        if any(
            marker in source_key
            for marker in (
                "vehicle_ownership",
                "vehicle-ownership",
                "vehicle_registration",
                "vehicle-registration",
                "vehicle_licensing",
                "vehicle-licensing",
            )
        ):
            bonus += 0.30

    is_procedure = any(
        marker in lowered_query
        for marker in ("how do", "how can", "steps", "procedure", "كيف", "خطوات")
    )
    if not is_procedure:
        return bonus

    if "steps" in lowered or "خطوات" in lowered:
        bonus += 0.35
    if "ways to apply" in lowered or "apply online" in lowered:
        bonus += 0.20
    action_phrases = (
        "take an eye test",
        "log in",
        "select renewing",
        "renew driving licence",
        "pay all fines and fees",
        "receive the licence",
        "uae pass",
    )
    bonus += min(0.35, 0.08 * sum(phrase in lowered for phrase in action_phrases))

    directory_terms = ("medical centre", "medical center", "polyclinic", "hospital", "clinic")
    directory_hits = sum(lowered.count(term) for term in directory_terms)
    if directory_hits >= 3 or len(_PHONE_LIKE.findall(chunk.text)) >= 4:
        bonus -= 0.85
    return bonus


def _is_driving_licence_query(query: str) -> bool:
    return (
        any(token in query for token in ("driving licence", "driving license", "driver licence"))
        or ("driv" in query and any(token in query for token in ("licence", "license")))
        or ("رخص" in query and "قياد" in query)
    )


def _is_vehicle_query(query: str) -> bool:
    return any(
        token in query
        for token in (
            "vehicle",
            "car registration",
            "vehicle registration",
            "vehicle ownership",
            "مركبة",
            "مركبات",
            "ملكية",
        )
    )
