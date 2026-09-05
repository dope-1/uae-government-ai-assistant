from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.repository import PostgresGovernmentRepository
from app.agents.schemas import ServiceDetails, ServiceSummary
from app.api.dependencies import get_db_session

router = APIRouter(tags=["services"])


@router.get("/services", response_model=list[ServiceSummary])
async def list_services(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    q: str = Query(default="", max_length=300),
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"] | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ServiceSummary]:
    return await PostgresGovernmentRepository(session).search_services(
        q, jurisdiction=jurisdiction, limit=limit
    )


@router.get("/services/{service_id}", response_model=ServiceDetails)
async def get_service(
    service_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceDetails:
    service = await PostgresGovernmentRepository(session).get_service(service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
