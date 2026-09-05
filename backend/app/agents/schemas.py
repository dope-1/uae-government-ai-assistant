from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ServiceSummary(BaseModel):
    id: str
    service_name: str
    authority: str
    jurisdiction: str
    category: str | None = None
    description: str | None = None
    official_url: HttpUrl


class ServiceDetails(ServiceSummary):
    requirements: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    fees: list[str] = Field(default_factory=list)
    last_verified: datetime | None = None
    source_id: str | None = None


class SourceMetadata(BaseModel):
    id: str
    url: HttpUrl
    authority: str
    jurisdiction: str
    language: str
    document_type: str


class RetrievedDocument(BaseModel):
    id: str
    source_id: str
    title: str
    language: str
    content: str
    retrieved_at: datetime


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    name: str
    ok: bool
    data: Any | None = None
    error: str | None = None


class AgentRun(BaseModel):
    intent: str
    calls: list[ToolCall]
    results: list[ToolResult]
    stopped_reason: str
