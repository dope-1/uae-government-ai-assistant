from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.repository import PostgresGovernmentRepository
from app.agents.schemas import AgentRun
from app.agents.service import BoundedServiceAgent
from app.agents.tools import GovernmentToolset
from app.api.dependencies import get_db_session
from app.core.config import Settings, get_settings

router = APIRouter(tags=["agent"])


class AgentRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"] | None = None


@router.post("/agent/service-discovery", response_model=AgentRun)
async def service_discovery(
    request: AgentRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentRun:
    repository = PostgresGovernmentRepository(session)
    agent = BoundedServiceAgent(
        GovernmentToolset(repository),
        max_tool_calls=settings.agent_max_tool_calls,
    )
    return await agent.run(request.message, jurisdiction=request.jurisdiction)
