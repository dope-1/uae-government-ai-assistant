from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_cache, get_db_session, get_telemetry
from app.core.config import Settings, get_settings
from app.production.cache import RedisJSONCache
from app.production.telemetry import TelemetryRegistry
from app.rag.citations import build_citations
from app.rag.factory import get_embedding_provider
from app.rag.schemas import Citation
from app.retrieval.postgres_hybrid import PgHybridRetriever

router = APIRouter(tags=["retrieval"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"] | None = None
    k: int = Field(default=5, ge=1, le=20)


class SearchHit(BaseModel):
    chunk_id: str
    text: str
    score: float
    citation: Citation


_SEARCH_HITS = TypeAdapter(list[SearchHit])


@router.post("/search", response_model=list[SearchHit])
async def search(
    request: SearchRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[RedisJSONCache, Depends(get_cache)],
    telemetry: Annotated[TelemetryRegistry, Depends(get_telemetry)],
) -> list[SearchHit]:
    cache_key = cache.make_key(
        "search",
        {
            "query": request.query,
            "jurisdiction": request.jurisdiction,
            "k": request.k,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
        },
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        telemetry.record_cache("search", hit=True)
        return _SEARCH_HITS.validate_json(cached)

    response.headers["X-Cache"] = "MISS" if settings.cache_enabled else "BYPASS"
    if settings.cache_enabled:
        telemetry.record_cache("search", hit=False)
    embedding = get_embedding_provider(settings.embedding_provider, settings.embedding_model)
    ranked = await PgHybridRetriever(session, embedding).search(
        request.query,
        k=request.k,
        candidate_k=max(20, request.k * 4),
        jurisdiction=request.jurisdiction,
    )
    chunks = [chunk for chunk, _ in ranked]
    citations = build_citations(chunks)
    hits = [
        SearchHit(chunk_id=chunk.id, text=chunk.text, score=score, citation=citation)
        for (chunk, score), citation in zip(ranked, citations, strict=True)
    ]
    await cache.set(cache_key, _SEARCH_HITS.dump_json(hits).decode("utf-8"))
    return hits
