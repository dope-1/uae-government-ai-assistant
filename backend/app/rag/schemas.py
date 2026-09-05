from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class GroundingLevel(StrEnum):
    SUFFICIENT = "sufficient"
    LIMITED = "limited"
    INSUFFICIENT = "insufficient"


class Citation(BaseModel):
    id: str
    chunk_id: str
    title: str
    authority: str
    url: HttpUrl
    jurisdiction: str
    retrieved_at: datetime | None = None
    relevant_excerpt: str
    source_id: str
    document_id: str


class GroundingAssessment(BaseModel):
    level: GroundingLevel
    support_score: float = Field(ge=0.0, le=1.0)
    focus_score: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_sources: int = Field(ge=0)
    focus_terms: list[str] = Field(default_factory=list)
    missing_focus_terms: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class RAGAnswer(BaseModel):
    answer: str
    language: str
    jurisdiction: str | None
    intent: str
    status: str
    grounding: GroundingAssessment
    citations: list[Citation]
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
