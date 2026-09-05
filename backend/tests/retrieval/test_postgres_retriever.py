from typing import Any

from app.embeddings.local_baseline import HashingEmbeddingProvider
from app.retrieval.postgres import PgVectorRetriever


class FakeResult:
    def mappings(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "chunk-1",
                "document_id": "doc-1",
                "source_id": "source-1",
                "source_url": "https://example.test/service",
                "authority": "Authority",
                "jurisdiction": "Dubai",
                "title": "Service",
                "language": "en",
                "text": "renew driving licence",
                "chunk_index": 0,
                "score": 0.91,
            }
        ]


class FakeSession:
    def __init__(self) -> None:
        self.statement = ""
        self.params: dict[str, object] = {}

    async def execute(self, statement: object, params: dict[str, object]) -> FakeResult:
        self.statement = str(statement)
        self.params = params
        return FakeResult()


async def test_pgvector_retriever_builds_filtered_cosine_query() -> None:
    session = FakeSession()
    retriever = PgVectorRetriever(
        session,  # type: ignore[arg-type]
        HashingEmbeddingProvider(dimension=384),
    )
    results = await retriever.search("driving licence", k=3, jurisdiction="Dubai")
    assert "<=> CAST(:embedding AS vector)" in session.statement
    assert "dc.jurisdiction = :jurisdiction" in session.statement
    assert session.params["jurisdiction"] == "Dubai"
    assert session.params["limit"] == 3
    assert results[0][0].id == "chunk-1"
    assert results[0][1] == 0.91
