from __future__ import annotations

import time
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_cache, get_db_session, get_telemetry
from app.core.config import Settings, get_settings
from app.production.cache import RedisJSONCache
from app.production.costs import estimate_request_cost_usd
from app.production.telemetry import TelemetryRegistry
from app.rag.factory import build_rag_service
from app.rag.schemas import RAGAnswer

router = APIRouter(tags=["assistant"])
logger = structlog.get_logger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"] | None = None


@router.post("/chat", response_model=RAGAnswer)
async def chat(
    request_data: ChatRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    cache: Annotated[RedisJSONCache, Depends(get_cache)],
    telemetry: Annotated[TelemetryRegistry, Depends(get_telemetry)],
) -> RAGAnswer:
    cache_key = cache.make_key(
        "chat",
        {
            "message": request_data.message,
            "jurisdiction": request_data.jurisdiction,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "rag_minimum_support": settings.rag_minimum_support,
            "rag_minimum_focus_support": settings.rag_minimum_focus_support,
        },
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        telemetry.record_cache("chat", hit=True)
        return RAGAnswer.model_validate_json(cached)

    response.headers["X-Cache"] = "MISS" if settings.cache_enabled else "BYPASS"
    if settings.cache_enabled:
        telemetry.record_cache("chat", hit=False)
    started = time.perf_counter()
    try:
        service = build_rag_service(session, settings)
        answer = await service.answer(
            request_data.message,
            jurisdiction=request_data.jurisdiction,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    generation_ms = (time.perf_counter() - started) * 1000
    cost: float | None = None
    if answer.model is not None:
        cost = estimate_request_cost_usd(
            settings,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
        )
        telemetry.record_model(
            provider=settings.llm_provider,
            model=answer.model,
            prompt_tokens=answer.prompt_tokens,
            completion_tokens=answer.completion_tokens,
            estimated_cost_usd=cost,
        )
    logger.info(
        "rag.completed",
        request_id=getattr(request.state, "request_id", None),
        status=answer.status,
        language=answer.language,
        jurisdiction=answer.jurisdiction,
        model=answer.model or settings.llm_model,
        provider=settings.llm_provider,
        prompt_tokens=answer.prompt_tokens,
        completion_tokens=answer.completion_tokens,
        estimated_cost_usd=cost,
        rag_latency_ms=round(generation_ms, 3),
        citations=len(answer.citations),
    )
    await cache.set(cache_key, answer.model_dump_json())
    return answer
