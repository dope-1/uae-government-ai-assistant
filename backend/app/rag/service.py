from __future__ import annotations

from typing import Protocol

from app.agents.intent import RuleBasedIntentClassifier
from app.ingestion.schemas import DocumentChunk
from app.llm.base import LLMProvider
from app.rag.citations import (
    build_citations,
    sanitize_citation_markers,
    select_referenced_citations,
)
from app.rag.grounding import assess_grounding
from app.rag.prompting import SYSTEM_PROMPT, build_user_prompt
from app.rag.query import (
    analyse_query,
    requests_unofficial_bypass_guidance,
    requires_local_jurisdiction,
)
from app.rag.schemas import GroundingAssessment, GroundingLevel, RAGAnswer


class RAGRetriever(Protocol):
    async def search(
        self,
        query: str,
        *,
        k: int = 6,
        candidate_k: int = 24,
        jurisdiction: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]: ...


class GroundedRAGService:
    def __init__(
        self,
        retriever: RAGRetriever,
        llm: LLMProvider,
        *,
        minimum_support: float = 0.20,
        minimum_focus_support: float = 0.60,
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.minimum_support = minimum_support
        self.minimum_focus_support = minimum_focus_support
        self.intent_classifier = RuleBasedIntentClassifier()

    async def answer(self, query: str, *, jurisdiction: str | None = None) -> RAGAnswer:
        context = analyse_query(query, jurisdiction)
        intent = self.intent_classifier.classify(query).value

        if requests_unofficial_bypass_guidance(query):
            assessment = GroundingAssessment(
                level=GroundingLevel.INSUFFICIENT,
                support_score=0.0,
                focus_score=0.0,
                supporting_sources=0,
                reasons=[
                    "The request asks for undocumented or rule-bypassing guidance that "
                    "cannot be grounded in the indexed official sources."
                ],
            )
            return RAGAnswer(
                answer=_unverified_message(context.language),
                language=context.language,
                jurisdiction=context.jurisdiction,
                intent=intent,
                status="unverified",
                grounding=assessment,
                citations=[],
            )

        if (
            jurisdiction is None
            and context.jurisdiction is None
            and requires_local_jurisdiction(query)
        ):
            assessment = GroundingAssessment(
                level=GroundingLevel.LIMITED,
                support_score=0.0,
                focus_score=0.0,
                supporting_sources=0,
                reasons=[
                    "This transport service is emirate-specific and no single jurisdiction "
                    "was specified."
                ],
            )
            return RAGAnswer(
                answer=_clarification_message(context.language),
                language=context.language,
                jurisdiction=None,
                intent=intent,
                status="needs_clarification",
                grounding=assessment,
                citations=[],
            )

        ranked = await self.retriever.search(
            query,
            k=6,
            candidate_k=24,
            jurisdiction=context.jurisdiction,
        )
        assessment = assess_grounding(
            query,
            ranked,
            explicit_jurisdiction=context.jurisdiction,
            minimum_support=self.minimum_support,
            minimum_focus_support=self.minimum_focus_support,
        )
        if assessment.level == GroundingLevel.INSUFFICIENT:
            return RAGAnswer(
                answer=_unverified_message(context.language),
                language=context.language,
                jurisdiction=context.jurisdiction,
                intent=intent,
                status="unverified",
                grounding=assessment,
                citations=[],
            )
        if assessment.level == GroundingLevel.LIMITED and context.jurisdiction is None:
            return RAGAnswer(
                answer=_clarification_message(context.language),
                language=context.language,
                jurisdiction=None,
                intent=intent,
                status="needs_clarification",
                grounding=assessment,
                citations=[],
            )

        chunks = [chunk for chunk, _ in ranked]
        citations = build_citations(chunks, query=query)
        generation = await self.llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(query, context.language, chunks),
        )
        answer = sanitize_citation_markers(generation.text, len(citations))
        citations = select_referenced_citations(answer, citations)
        if not answer:
            return RAGAnswer(
                answer=_unverified_message(context.language),
                language=context.language,
                jurisdiction=context.jurisdiction,
                intent=intent,
                status="unverified",
                grounding=assessment,
                citations=[],
                model=generation.model,
            )
        return RAGAnswer(
            answer=answer,
            language=context.language,
            jurisdiction=context.jurisdiction,
            intent=intent,
            status="answered",
            grounding=assessment,
            citations=citations,
            model=generation.model,
            prompt_tokens=generation.prompt_tokens,
            completion_tokens=generation.completion_tokens,
        )


def _unverified_message(language: str) -> str:
    if language == "ar":
        return "لم أتمكن من التحقق من هذه المعلومة من المصادر الرسمية المفهرسة حالياً."
    return "I couldn't verify this from the currently indexed official sources."


def _clarification_message(language: str) -> str:
    if language == "ar":
        return "تختلف المعلومات المسترجعة بين إمارات متعددة. يرجى تحديد الإمارة المطلوبة."
    return (
        "The retrieved information differs across emirates. "
        "Please specify the jurisdiction you need."
    )
