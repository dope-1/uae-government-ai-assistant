from __future__ import annotations

import secrets
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.config import Settings, get_settings
from app.production.telemetry import TelemetryRegistry

router = APIRouter(tags=["operations"])


@router.get("/ops/metrics")
async def operational_metrics(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    if not settings.ops_metrics_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if settings.app_env.casefold() == "production":
        _require_bearer_token(authorization, settings.ops_metrics_token)
    telemetry = cast(TelemetryRegistry, request.app.state.telemetry)
    return telemetry.snapshot()


def _require_bearer_token(authorization: str | None, expected: str | None) -> None:
    if expected is None:
        raise HTTPException(status_code=503, detail="Operations token is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    valid = (
        scheme.casefold() == "bearer"
        and bool(supplied)
        and secrets.compare_digest(supplied, expected)
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid operations token")
