from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.repository import GovernmentRepository
from app.agents.schemas import ToolCall, ToolResult

logger = logging.getLogger(__name__)


class SearchGovernmentSourcesArgs(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    jurisdiction: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchServicesArgs(SearchGovernmentSourcesArgs):
    pass


class GetServiceDetailsArgs(BaseModel):
    service_id: str = Field(min_length=1, max_length=120)


class CompareServicesArgs(BaseModel):
    service_ids: list[str] = Field(min_length=2, max_length=4)


class RetrieveDocumentArgs(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)
    max_chars: int = Field(default=5000, ge=200, le=20_000)


class GetSourceMetadataArgs(BaseModel):
    source_id: str = Field(min_length=1, max_length=120)


Handler = Callable[[BaseModel], Awaitable[Any]]


class GovernmentToolset:
    """Allow-listed, typed read-only tools. No arbitrary execution is exposed."""

    def __init__(self, repository: GovernmentRepository) -> None:
        self.repository = repository
        self._tools: dict[str, tuple[type[BaseModel], Handler]] = {
            "search_government_sources": (SearchGovernmentSourcesArgs, self._search_sources),
            "search_services": (SearchServicesArgs, self._search_services),
            "get_service_details": (GetServiceDetailsArgs, self._get_service),
            "compare_services": (CompareServicesArgs, self._compare_services),
            "retrieve_document": (RetrieveDocumentArgs, self._retrieve_document),
            "get_source_metadata": (GetSourceMetadataArgs, self._get_source_metadata),
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    async def execute(self, call: ToolCall) -> ToolResult:
        definition = self._tools.get(call.name)
        if definition is None:
            return ToolResult(name=call.name, ok=False, error="Tool is not allow-listed.")
        schema, handler = definition
        try:
            arguments = schema.model_validate(call.arguments)
            data = await handler(arguments)
            logger.info("government_tool_call", extra={"tool": call.name, "ok": True})
            return ToolResult(name=call.name, ok=True, data=data)
        except ValidationError as exc:
            logger.warning("government_tool_validation_error", extra={"tool": call.name})
            return ToolResult(name=call.name, ok=False, error=str(exc))
        except Exception as exc:  # tool boundary must convert failures into structured errors
            logger.exception("government_tool_error", extra={"tool": call.name})
            return ToolResult(name=call.name, ok=False, error=f"{type(exc).__name__}: {exc}")

    async def _search_sources(self, args: BaseModel) -> Any:
        assert isinstance(args, SearchGovernmentSourcesArgs)
        parsed = args
        return await self.repository.search_sources(
            parsed.query, jurisdiction=parsed.jurisdiction, limit=parsed.limit
        )

    async def _search_services(self, args: BaseModel) -> Any:
        assert isinstance(args, SearchServicesArgs)
        parsed = args
        return await self.repository.search_services(
            parsed.query, jurisdiction=parsed.jurisdiction, limit=parsed.limit
        )

    async def _get_service(self, args: BaseModel) -> Any:
        assert isinstance(args, GetServiceDetailsArgs)
        parsed = args
        return await self.repository.get_service(parsed.service_id)

    async def _compare_services(self, args: BaseModel) -> Any:
        assert isinstance(args, CompareServicesArgs)
        parsed = args
        results = []
        for service_id in parsed.service_ids:
            service = await self.repository.get_service(service_id)
            if service is not None:
                results.append(service)
        return results

    async def _retrieve_document(self, args: BaseModel) -> Any:
        assert isinstance(args, RetrieveDocumentArgs)
        parsed = args
        document = await self.repository.get_document(parsed.document_id)
        if document is None:
            return None
        if len(document.content) <= parsed.max_chars:
            return document
        return document.model_copy(update={"content": document.content[: parsed.max_chars]})

    async def _get_source_metadata(self, args: BaseModel) -> Any:
        assert isinstance(args, GetSourceMetadataArgs)
        parsed = args
        return await self.repository.get_source(parsed.source_id)
