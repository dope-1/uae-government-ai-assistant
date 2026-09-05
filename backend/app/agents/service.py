from __future__ import annotations

from app.agents.intent import Intent, RuleBasedIntentClassifier
from app.agents.schemas import AgentRun, ServiceSummary, ToolCall
from app.agents.tools import GovernmentToolset
from app.rag.query import analyse_query


class BoundedServiceAgent:
    """Deterministic, bounded orchestration over read-only government-service tools."""

    def __init__(self, tools: GovernmentToolset, *, max_tool_calls: int = 3) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1")
        self.tools = tools
        self.max_tool_calls = max_tool_calls
        self.classifier = RuleBasedIntentClassifier()

    async def run(self, query: str, *, jurisdiction: str | None = None) -> AgentRun:
        context = analyse_query(query, jurisdiction)
        intent = self.classifier.classify(query)
        calls: list[ToolCall] = []
        results = []

        first = ToolCall(
            name="search_services",
            arguments={"query": query, "jurisdiction": context.jurisdiction, "limit": 5},
        )
        calls.append(first)
        first_result = await self.tools.execute(first)
        results.append(first_result)
        if len(calls) >= self.max_tool_calls or not first_result.ok:
            return AgentRun(
                intent=intent.value,
                calls=calls,
                results=results,
                stopped_reason="tool_limit" if len(calls) >= self.max_tool_calls else "tool_error",
            )

        services = _service_summaries(first_result.data)
        if intent == Intent.COMPARISON and len(services) >= 2:
            call = ToolCall(
                name="compare_services",
                arguments={"service_ids": [service.id for service in services[:4]]},
            )
            calls.append(call)
            results.append(await self.tools.execute(call))
        elif services and intent in {
            Intent.PROCEDURE_INFORMATION,
            Intent.DOCUMENT_REQUIREMENTS,
            Intent.ELIGIBILITY,
            Intent.FEES,
            Intent.DEADLINES,
        }:
            call = ToolCall(
                name="get_service_details",
                arguments={"service_id": services[0].id},
            )
            calls.append(call)
            results.append(await self.tools.execute(call))

        return AgentRun(
            intent=intent.value,
            calls=calls,
            results=results,
            stopped_reason="completed",
        )


def _service_summaries(value: object) -> list[ServiceSummary]:
    if not isinstance(value, list):
        return []
    services: list[ServiceSummary] = []
    for item in value:
        if isinstance(item, ServiceSummary):
            services.append(item)
        elif isinstance(item, dict):
            services.append(ServiceSummary.model_validate(item))
    return services
