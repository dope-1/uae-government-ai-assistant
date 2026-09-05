import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.db.checks import check_postgres, check_redis

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class DependencyStatus(BaseModel):
    postgres: bool
    redis: bool


class ReadinessResponse(BaseModel):
    status: str
    dependencies: DependencyStatus


@router.get("/health", response_model=HealthResponse)
async def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def ready(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    postgres_ok, redis_ok = await asyncio.gather(
        check_postgres(settings), check_redis(settings)
    )
    is_ready = postgres_ok and redis_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        dependencies=DependencyStatus(postgres=postgres_ok, redis=redis_ok),
    )
