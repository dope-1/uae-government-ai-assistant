import httpx
import pytest

from app.ingestion.downloader import PublicSourceDownloader, SourceDownloadError
from app.ingestion.schemas import SourceSpec


def _source() -> SourceSpec:
    return SourceSpec(
        id="test",
        url="https://gov.example/service",
        authority="Example Authority",
        jurisdiction="Federal",
        language="en",
        document_type="html",
    )


async def test_downloader_checks_robots_and_fetches_source() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, content=b"<main>Government service</main>")

    downloader = PublicSourceDownloader(
        min_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    payload = await downloader.download(_source())
    assert payload == b"<main>Government service</main>"
    assert requested == ["https://gov.example/robots.txt", "https://gov.example/service"]


async def test_downloader_refuses_robots_disallowed_source() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /service")
        return httpx.Response(200, content=b"should not be fetched")

    downloader = PublicSourceDownloader(
        min_interval_seconds=0,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(SourceDownloadError, match="robots.txt disallows"):
        await downloader.download(_source())
