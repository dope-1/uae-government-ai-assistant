from __future__ import annotations

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.local_baseline import HashingEmbeddingProvider
from app.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider
from app.llm.base import LLMProvider
from app.llm.providers import (
    GroundedExtractiveLLMProvider,
    OllamaLLMProvider,
    OpenAICompatibleLLMProvider,
)
from app.rag.service import GroundedRAGService
from app.retrieval.postgres_hybrid import PgHybridRetriever


@lru_cache
def get_embedding_provider(provider_name: str, model_name: str) -> EmbeddingProvider:
    if provider_name == "hashing":
        return HashingEmbeddingProvider()
    return SentenceTransformerEmbeddingProvider(model_name)


@lru_cache
def get_llm_provider(
    provider_name: str,
    model: str,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
) -> LLMProvider:
    if provider_name == "extractive":
        return GroundedExtractiveLLMProvider()
    if provider_name == "ollama":
        return OllamaLLMProvider(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    if provider_name == "openai_compatible":
        if not api_key:
            raise RuntimeError("LLM_API_KEY is required for openai_compatible provider")
        return OpenAICompatibleLLMProvider(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM provider: {provider_name}")


def build_rag_service(session: AsyncSession, settings: Settings) -> GroundedRAGService:
    embedding = get_embedding_provider(settings.embedding_provider, settings.embedding_model)
    llm = get_llm_provider(
        settings.llm_provider,
        settings.llm_model,
        settings.llm_base_url,
        settings.llm_api_key,
        settings.llm_timeout_seconds,
    )
    return GroundedRAGService(
        PgHybridRetriever(session, embedding),
        llm,
        minimum_support=settings.rag_minimum_support,
        minimum_focus_support=settings.rag_minimum_focus_support,
    )
