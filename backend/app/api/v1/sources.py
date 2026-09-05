from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.repository import PostgresGovernmentRepository
from app.agents.schemas import SourceMetadata
from app.api.dependencies import get_db_session

router = APIRouter(tags=["sources"])


@router.get("/sources", response_model=list[SourceMetadata])
async def list_sources(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    q: str = Query(default="", max_length=300),
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SourceMetadata]:
    return await PostgresGovernmentRepository(session).search_sources(
        q, jurisdiction=jurisdiction, limit=limit
    )


@router.get("/sources/{source_id}", response_model=SourceMetadata)
async def get_source(
    source_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SourceMetadata:
    source = await PostgresGovernmentRepository(session).get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source
