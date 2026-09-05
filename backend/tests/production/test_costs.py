from app.core.config import Settings
from app.production.costs import estimate_request_cost_usd


def test_local_providers_report_zero_hosted_model_cost() -> None:
    settings = Settings(llm_provider="extractive")
    assert (
        estimate_request_cost_usd(
            settings,
            prompt_tokens=None,
            completion_tokens=None,
        )
        == 0.0
    )


def test_hosted_cost_requires_explicit_prices() -> None:
    settings = Settings(
        llm_provider="openai_compatible",
        llm_api_key="example",
    )
    assert (
        estimate_request_cost_usd(
            settings,
            prompt_tokens=1000,
            completion_tokens=500,
        )
        is None
    )


def test_hosted_cost_uses_configured_prices() -> None:
    settings = Settings(
        llm_provider="openai_compatible",
        llm_api_key="example",
        llm_prompt_cost_per_million_usd=2.0,
        llm_completion_cost_per_million_usd=8.0,
    )
    cost = estimate_request_cost_usd(
        settings,
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
    )
    assert cost == 6.0
