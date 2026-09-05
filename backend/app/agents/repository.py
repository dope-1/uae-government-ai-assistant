from __future__ import annotations

from typing import Protocol

from pydantic import HttpUrl, TypeAdapter
from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.schemas import RetrievedDocument, ServiceDetails, ServiceSummary, SourceMetadata
from app.retrieval.tokenization import tokenize

_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class GovernmentRepository(Protocol):
    async def search_services(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[ServiceSummary]: ...

    async def get_service(self, service_id: str) -> ServiceDetails | None: ...

    async def search_sources(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[SourceMetadata]: ...

    async def get_source(self, source_id: str) -> SourceMetadata | None: ...

    async def get_document(self, document_id: str) -> RetrievedDocument | None: ...


class PostgresGovernmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search_services(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[ServiceSummary]:
        tokens = [token for token in tokenize(query) if len(token) >= 3][:8]
        candidate_limit = max(limit * 5, 25)
        params: dict[str, object] = {"candidate_limit": candidate_limit}
        where: list[str] = []
        if tokens:
            token_clauses: list[str] = []
            for index, token in enumerate(tokens):
                key = f"pattern_{index}"
                params[key] = f"%{token}%"
                token_clauses.append(
                    f"(service_name ILIKE :{key} OR COALESCE(description, '') ILIKE :{key})"
                )
            where.append("(" + " OR ".join(token_clauses) + ")")
        if jurisdiction:
            where.append("jurisdiction = :jurisdiction")
            params["jurisdiction"] = jurisdiction
        where_clause = " AND ".join(where) if where else "TRUE"
        result = await self.session.execute(
            text(
                f"""
                SELECT id, service_name, authority, jurisdiction, category,
                       description, official_url
                FROM services
                WHERE {where_clause}
                ORDER BY service_name
                LIMIT :candidate_limit
                """
            ),
            params,
        )
        services = [_service_summary(row) for row in result.mappings()]
        return rank_service_summaries(query, services)[:limit]

    async def get_service(self, service_id: str) -> ServiceDetails | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, service_name, authority, jurisdiction, category,
                       description, requirements, documents, fees, official_url,
                       last_verified, source_id
                FROM services WHERE id = :id
                """
            ),
            {"id": service_id},
        )
        row = result.mappings().first()
        return _service_details(row) if row is not None else None

    async def search_sources(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[SourceMetadata]:
        tokens = [token for token in tokenize(query) if len(token) >= 3][:8]
        params: dict[str, object] = {"limit": limit}
        where: list[str] = []
        if tokens:
            token_clauses: list[str] = []
            for index, token in enumerate(tokens):
                key = f"pattern_{index}"
                params[key] = f"%{token}%"
                token_clauses.append(
                    f"(id ILIKE :{key} OR authority ILIKE :{key} OR url ILIKE :{key})"
                )
            where.append("(" + " OR ".join(token_clauses) + ")")
        if jurisdiction:
            where.append("jurisdiction = :jurisdiction")
            params["jurisdiction"] = jurisdiction
        where_clause = " AND ".join(where) if where else "TRUE"
        result = await self.session.execute(
            text(
                f"""
                SELECT id, url, authority, jurisdiction, language, document_type
                FROM sources
                WHERE {where_clause}
                ORDER BY id
                LIMIT :limit
                """
            ),
            params,
        )
        return [_source_metadata(row) for row in result.mappings()]

    async def get_source(self, source_id: str) -> SourceMetadata | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, url, authority, jurisdiction, language, document_type
                FROM sources WHERE id = :id
                """
            ),
            {"id": source_id},
        )
        row = result.mappings().first()
        return _source_metadata(row) if row is not None else None

    async def get_document(self, document_id: str) -> RetrievedDocument | None:
        result = await self.session.execute(
            text(
                """
                SELECT id, source_id, title, language, content, retrieved_at
                FROM documents WHERE id = :id
                """
            ),
            {"id": document_id},
        )
        row = result.mappings().first()
        return _document(row) if row is not None else None


def _service_summary(row: RowMapping) -> ServiceSummary:
    return ServiceSummary(
        id=str(row["id"]),
        service_name=str(row["service_name"]),
        authority=str(row["authority"]),
        jurisdiction=str(row["jurisdiction"]),
        category=str(row["category"]) if row["category"] is not None else None,
        description=str(row["description"]) if row["description"] is not None else None,
        official_url=_HTTP_URL_ADAPTER.validate_python(str(row["official_url"])),
    )


def _service_details(row: RowMapping) -> ServiceDetails:
    return ServiceDetails(
        **_service_summary(row).model_dump(),
        requirements=list(row["requirements"] or []),
        documents=list(row["documents"] or []),
        fees=list(row["fees"] or []),
        last_verified=row["last_verified"],
        source_id=str(row["source_id"]) if row["source_id"] is not None else None,
    )


def _source_metadata(row: RowMapping) -> SourceMetadata:
    return SourceMetadata(
        id=str(row["id"]),
        url=_HTTP_URL_ADAPTER.validate_python(str(row["url"])),
        authority=str(row["authority"]),
        jurisdiction=str(row["jurisdiction"]),
        language=str(row["language"]),
        document_type=str(row["document_type"]),
    )


def _document(row: RowMapping) -> RetrievedDocument:
    return RetrievedDocument(
        id=str(row["id"]),
        source_id=str(row["source_id"]),
        title=str(row["title"]),
        language=str(row["language"]),
        content=str(row["content"]),
        retrieved_at=row["retrieved_at"],
    )


def rank_service_summaries(
    query: str, services: list[ServiceSummary]
) -> list[ServiceSummary]:
    """Rank service matches by bilingual lexical overlap instead of database sort order."""
    query_tokens = {token for token in tokenize(query) if len(token) >= 3}

    def score(service: ServiceSummary) -> tuple[int, int, str]:
        name_tokens = set(tokenize(service.service_name))
        description_tokens = set(tokenize(service.description or ""))
        name_overlap = len(query_tokens & name_tokens)
        description_overlap = len(query_tokens & description_tokens)
        weighted = name_overlap * 3 + description_overlap
        return (-weighted, -name_overlap, service.service_name)

    return sorted(services, key=score)
