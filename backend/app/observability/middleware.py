from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import cast

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.production.rate_limit import RateLimitDecision, RedisFixedWindowRateLimiter
from app.production.telemetry import TelemetryRegistry

logger = structlog.get_logger(__name__)
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_RATE_LIMITED_PATHS = {
    "/api/v1/chat": "chat",
    "/api/v1/search": "search",
    "/api/v1/agent/service-discovery": "agent",
}


class RequestBodyLimitMiddleware:
    """Buffer small API request bodies and reject oversized payloads with HTTP 413."""

    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            await _send_too_large(send, self.max_body_bytes)
            return

        buffered: list[Message] = []
        total = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                buffered.append(message)
                break
            total += len(message.get("body", b""))
            if total > self.max_body_bytes:
                await _send_too_large(send, self.max_body_bytes)
                return
            buffered.append(message)
            more_body = bool(message.get("more_body", False))

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)


class ProductionRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id(request)
        request.state.request_id = request_id
        telemetry = cast(TelemetryRegistry, request.app.state.telemetry)
        started = time.perf_counter()
        response: Response

        rate_decision = await self._rate_limit(request)
        if rate_decision is not None and not rate_decision.allowed:
            telemetry.record_rate_limited()
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
            )
            _apply_rate_headers(response, rate_decision)
            response.headers["Retry-After"] = str(rate_decision.retry_after_seconds)
            self._finalize_response(response, request_id)
            duration_ms = (time.perf_counter() - started) * 1000
            route_path = _route_path(request, self.settings.api_v1_prefix)
            telemetry.record_request(request.method, route_path, 429, duration_ms)
            logger.warning(
                "http.request_rate_limited",
                request_id=request_id,
                method=request.method,
                path=route_path,
                duration_ms=round(duration_ms, 3),
            )
            return response

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000
            route_path = _route_path(request, self.settings.api_v1_prefix)
            telemetry.record_request(request.method, route_path, 500, duration_ms)
            logger.exception(
                "http.request_failed",
                request_id=request_id,
                method=request.method,
                path=route_path,
                duration_ms=round(duration_ms, 3),
                error_type=type(exc).__name__,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error."},
            )
            if rate_decision is not None:
                _apply_rate_headers(response, rate_decision)
            self._finalize_response(response, request_id)
            return response

        duration_ms = (time.perf_counter() - started) * 1000
        if rate_decision is not None:
            _apply_rate_headers(response, rate_decision)
        self._finalize_response(response, request_id)
        route_path = _route_path(request, self.settings.api_v1_prefix)
        telemetry.record_request(
            request.method,
            route_path,
            response.status_code,
            duration_ms,
        )
        logger.info(
            "http.request_completed",
            request_id=request_id,
            method=request.method,
            path=route_path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 3),
        )
        return response

    async def _rate_limit(self, request: Request) -> RateLimitDecision | None:
        resource = _RATE_LIMITED_PATHS.get(request.url.path)
        content_length = _content_length(request.scope)
        if (
            resource is None
            or request.method != "POST"
            or (
                content_length is not None
                and content_length > self.settings.max_request_body_bytes
            )
        ):
            return None
        limiter = RedisFixedWindowRateLimiter(
            request.app.state.redis,
            namespace=self.settings.cache_namespace,
            limit=self.settings.rate_limit_requests,
            window_seconds=self.settings.rate_limit_window_seconds,
            enabled=self.settings.rate_limit_enabled,
            fail_open=self.settings.rate_limit_fail_open,
        )
        return await limiter.check(_client_identifier(request, self.settings), resource)

    def _finalize_response(self, response: Response, request_id: str) -> None:
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("Cache-Control", "no-store")
        if not self.settings.security_headers_enabled:
            return
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if self.settings.app_env.casefold() == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"



def _route_path(request: Request, api_prefix: str) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        prefix = "/" + api_prefix.strip("/") if api_prefix.strip("/") else ""
        if prefix and request.url.path.startswith(prefix) and not path.startswith(prefix):
            return f"{prefix}{path}"
        return path
    if request.url.path in _RATE_LIMITED_PATHS:
        return request.url.path
    return "<unmatched>"

def _request_id(request: Request) -> str:
    supplied = request.headers.get("x-request-id", "")
    if supplied and _REQUEST_ID.fullmatch(supplied):
        return supplied
    return uuid.uuid4().hex


def _client_identifier(request: Request, settings: Settings) -> str:
    if settings.rate_limit_trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", maxsplit=1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown-client"


def _apply_rate_headers(response: Response, decision: RateLimitDecision) -> None:
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    response.headers["X-RateLimit-Reset"] = str(decision.retry_after_seconds)


def _content_length(scope: Scope) -> int | None:
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == b"content-length":
            try:
                return int(raw_value.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                return None
    return None


async def _send_too_large(send: Send, max_body_bytes: int) -> None:
    body = (
        '{"detail":"Request body exceeds the configured limit of '
        f'{max_body_bytes} bytes."}}'
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
