from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.agents.repository import rank_service_summaries
from app.agents.schemas import (
    RetrievedDocument,
    ServiceDetails,
    ServiceSummary,
    SourceMetadata,
    ToolCall,
)
from app.agents.service import BoundedServiceAgent
from app.agents.tools import GovernmentToolset


class FakeRepository:
    def __init__(self) -> None:
        self.services = [
            ServiceDetails(
                id="dubai-renew",
                service_name="Renew Driving Licence",
                authority="RTA",
                jurisdiction="Dubai",
                category="Transport",
                description="Renew a Dubai driving licence.",
                official_url="https://example.gov/dubai",
                requirements=["Eye test"],
                documents=[],
                fees=[],
                source_id="source-dubai",
            ),
            ServiceDetails(
                id="abu-renew",
                service_name="Renew Driving Licence",
                authority="Abu Dhabi Authority",
                jurisdiction="Abu Dhabi",
                category="Transport",
                description="Renew an Abu Dhabi driving licence.",
                official_url="https://example.gov/abu",
                requirements=[],
                documents=[],
                fees=[],
                source_id="source-abu",
            ),
        ]

    async def search_services(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[ServiceSummary]:
        del query
        items = self.services
        if jurisdiction:
            items = [item for item in items if item.jurisdiction == jurisdiction]
        return [ServiceSummary(**item.model_dump()) for item in items[:limit]]

    async def get_service(self, service_id: str) -> ServiceDetails | None:
        return next((item for item in self.services if item.id == service_id), None)

    async def search_sources(
        self, query: str, *, jurisdiction: str | None, limit: int
    ) -> list[SourceMetadata]:
        del query, jurisdiction, limit
        return []

    async def get_source(self, source_id: str) -> SourceMetadata | None:
        return SourceMetadata(
            id=source_id,
            url="https://example.gov/source",
            authority="Authority",
            jurisdiction="Dubai",
            language="en",
            document_type="html",
        )

    async def get_document(self, document_id: str) -> RetrievedDocument | None:
        return RetrievedDocument(
            id=document_id,
            source_id="source-dubai",
            title="Title",
            language="en",
            content="Official content",
            retrieved_at=datetime(2026, 9, 2, tzinfo=UTC),
        )


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected() -> None:
    result = await GovernmentToolset(FakeRepository()).execute(
        ToolCall(name="run_shell", arguments={"command": "rm -rf /"})
    )
    assert result.ok is False
    assert "allow-listed" in (result.error or "")


@pytest.mark.asyncio
async def test_tool_arguments_are_validated() -> None:
    result = await GovernmentToolset(FakeRepository()).execute(
        ToolCall(name="search_services", arguments={"query": "x", "limit": 1000})
    )
    assert result.ok is False


@pytest.mark.asyncio
async def test_agent_uses_service_details_for_procedure_query() -> None:
    agent = BoundedServiceAgent(GovernmentToolset(FakeRepository()), max_tool_calls=3)
    run = await agent.run("How do I renew my driving licence in Dubai?")
    assert [call.name for call in run.calls] == ["search_services", "get_service_details"]
    assert len(run.calls) <= 3
    assert run.stopped_reason == "completed"


@pytest.mark.asyncio
async def test_agent_never_exceeds_tool_limit() -> None:
    agent = BoundedServiceAgent(GovernmentToolset(FakeRepository()), max_tool_calls=1)
    run = await agent.run("Compare driving licence renewal services")
    assert len(run.calls) == 1
    assert run.stopped_reason == "tool_limit"


def test_arabic_service_ranking_prefers_driving_licence_over_vehicle() -> None:
    services = [
        ServiceSummary(
            id="vehicle",
            service_name="تجديد وتعديل بيانات ملكية مركبة في دبي",
            authority="RTA",
            jurisdiction="Dubai",
            category="Transport",
            description="دليل خدمات تجديد ملكية المركبات في دبي.",
            official_url="https://example.gov/vehicle",
        ),
        ServiceSummary(
            id="driving",
            service_name="طلب أو إدارة رخصة قيادة في دبي",
            authority="RTA",
            jurisdiction="Dubai",
            category="Transport",
            description="دليل خدمات رخص القيادة في دبي بما فيها التجديد.",
            official_url="https://example.gov/driving",
        ),
    ]

    ranked = rank_service_summaries("كيف أجدد رخصة القيادة في دبي؟", services)

    assert ranked[0].id == "driving"


def test_english_service_ranking_prefers_driving_licence_over_vehicle() -> None:
    services = [
        ServiceSummary(
            id="vehicle",
            service_name="Renew Vehicle Ownership",
            authority="RTA",
            jurisdiction="Dubai",
            category="Transport",
            description="Renew vehicle ownership in Dubai.",
            official_url="https://example.gov/vehicle",
        ),
        ServiceSummary(
            id="driving",
            service_name="Renew Driving Licence",
            authority="RTA",
            jurisdiction="Dubai",
            category="Transport",
            description="Renew a Dubai driving licence.",
            official_url="https://example.gov/driving",
        ),
    ]

    ranked = rank_service_summaries("How do I renew my driving licence in Dubai?", services)

    assert ranked[0].id == "driving"
