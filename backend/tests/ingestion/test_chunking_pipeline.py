from datetime import UTC, datetime

from app.embeddings.local_baseline import HashingEmbeddingProvider
from app.ingestion.chunking import chunk_document
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.schemas import ParsedDocument, SourceSpec


class NoNetworkDownloader:
    async def download(self, source: SourceSpec) -> bytes:
        return (
            "<html><title>Arabic</title><main>تجديد رخصة القيادة</main></html>"
        ).encode()


def test_chunk_metadata_is_stable() -> None:
    doc = ParsedDocument(
        source_id="source",
        source_url="https://example.test",
        authority="Authority",
        jurisdiction="Dubai",
        title="Title",
        language="en",
        document_type="html",
        retrieved_at=datetime.now(UTC),
        content=" ".join(f"word{i}" for i in range(30)),
    )
    first = chunk_document(doc, chunk_size_words=10, overlap_words=2)
    second = chunk_document(doc, chunk_size_words=10, overlap_words=2)
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert len(first) == 4


async def test_pipeline_generates_embeddings() -> None:
    source = SourceSpec(
        id="ar-test",
        url="https://example.test/ar",
        authority="Authority",
        jurisdiction="Abu Dhabi",
        language="ar",
        document_type="html",
    )
    provider = HashingEmbeddingProvider(dimension=64)
    pipeline = IngestionPipeline(NoNetworkDownloader(), provider)  # type: ignore[arg-type]
    document, chunks = await pipeline.ingest(source)
    assert document.language == "ar"
    assert chunks
    assert len(chunks[0].embedding or []) == 64
