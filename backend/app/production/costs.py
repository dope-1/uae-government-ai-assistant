from __future__ import annotations

from app.core.config import Settings


def estimate_request_cost_usd(
    settings: Settings,
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float | None:
    """Estimate hosted-model cost only when the price inputs are explicitly configured."""

    if settings.llm_provider in {"extractive", "ollama"}:
        return 0.0
    if prompt_tokens is None or completion_tokens is None:
        return None
    if (
        settings.llm_prompt_cost_per_million_usd is None
        or settings.llm_completion_cost_per_million_usd is None
    ):
        return None
    prompt_cost = (
        prompt_tokens / 1_000_000 * settings.llm_prompt_cost_per_million_usd
    )
    completion_cost = (
        completion_tokens / 1_000_000 * settings.llm_completion_cost_per_million_usd
    )
    return prompt_cost + completion_cost
