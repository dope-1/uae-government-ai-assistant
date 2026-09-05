from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceSpec(BaseModel):
    id: str
    url: HttpUrl
    authority: str
    jurisdiction: Literal["Federal", "Abu Dhabi", "Dubai"]
    language: Literal["en", "ar"]
    document_type: Literal["html", "pdf"]
    enabled: bool = True
    notes: str | None = None


class ParsedDocument(BaseModel):
    source_id: str
    source_url: str
    authority: str
    jurisdiction: str
    title: str
    language: str
    document_type: str
    retrieved_at: datetime
    content: str
    publication_or_update_date: str | None = None


class DocumentChunk(BaseModel):
    id: str
    document_id: str
    source_id: str
    source_url: str
    authority: str
    jurisdiction: str
    title: str
    language: str
    text: str
    chunk_index: int
    retrieved_at: datetime | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
