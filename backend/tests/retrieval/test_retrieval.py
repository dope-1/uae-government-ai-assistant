from app.embeddings.local_baseline import HashingEmbeddingProvider
from app.ingestion.schemas import DocumentChunk
from app.retrieval.pipeline import RetrievalPipeline


def _chunk(chunk_id: str, text: str, jurisdiction: str = "Dubai") -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id=f"doc-{chunk_id}",
        source_id=f"source-{chunk_id}",
        source_url="https://example.test",
        authority="Authority",
        jurisdiction=jurisdiction,
        title=chunk_id,
        language="en",
        text=text,
        chunk_index=0,
    )


def test_bm25_and_hybrid_retrieve_relevant_chunk() -> None:
    chunks = [
        _chunk("licence", "renew Dubai driving licence eye test RTA"),
        _chunk("visa", "Golden visa residence investors students"),
        _chunk("vehicle", "renew Dubai vehicle ownership insurance inspection"),
    ]
    pipeline = RetrievalPipeline(chunks, HashingEmbeddingProvider(dimension=128))
    for method in ["bm25", "dense", "hybrid", "hybrid_rerank"]:
        results = pipeline.search("Dubai driving licence renewal eye test", method=method, k=1)
        assert results[0][0].id == "licence"


def test_jurisdiction_filter_prevents_cross_emirate_mix() -> None:
    chunks = [
        _chunk("dubai", "renew driving licence eye test", jurisdiction="Dubai"),
        _chunk("abudhabi", "renew driving licence eye test", jurisdiction="Abu Dhabi"),
    ]
    pipeline = RetrievalPipeline(chunks, HashingEmbeddingProvider(dimension=128))
    results = pipeline.search(
        "renew driving licence",
        method="hybrid_rerank",
        k=2,
        jurisdiction="Dubai",
    )
    assert [chunk.id for chunk, _ in results] == ["dubai"]
