from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"
    app_name: str = "UAE Government AI Assistant API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://uae_ai:uae_ai_local@localhost:5432/uae_ai"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    trusted_hosts: Annotated[list[str], NoDecode] = [
        "localhost",
        "127.0.0.1",
        "testserver",
        "backend",
    ]
    ready_check_timeout_seconds: float = 2.0

    embedding_provider: Literal["e5", "hashing"] = "e5"
    embedding_model: str = "intfloat/multilingual-e5-small"
    llm_provider: Literal["extractive", "openai_compatible", "ollama"] = "extractive"
    llm_model: str = "qwen2.5:7b"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: str | None = None
    llm_timeout_seconds: float = 120.0
    llm_prompt_cost_per_million_usd: float | None = Field(default=None, ge=0.0)
    llm_completion_cost_per_million_usd: float | None = Field(default=None, ge=0.0)
    rag_minimum_support: float = 0.20
    rag_minimum_focus_support: float = 0.60
    agent_max_tool_calls: int = 3

    cache_enabled: bool = True
    cache_namespace: str = "uae-ai-assistant"
    cache_version: str = "m8-v1"
    cache_ttl_seconds: int = Field(default=300, ge=1, le=86_400)

    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=60, ge=1, le=100_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86_400)
    rate_limit_fail_open: bool = True
    rate_limit_trust_forwarded_for: bool = False

    max_request_body_bytes: int = Field(default=16_384, ge=1024, le=1_048_576)
    security_headers_enabled: bool = True
    ops_metrics_enabled: bool = True
    ops_metrics_token: str | None = None

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_csv_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
