from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.ingestion.schemas import SourceSpec

logger = logging.getLogger(__name__)


class SourceDownloadError(RuntimeError):
    pass


class PublicSourceDownloader:
    """Rate-limited downloader that respects robots.txt where it can be fetched."""

    def __init__(
        self,
        *,
        user_agent: str = "uae-government-ai-assistant-research/0.2",
        min_interval_seconds: float = 1.0,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.min_interval_seconds = min_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self._last_request: dict[str, float] = defaultdict(float)
        self._robots: dict[str, RobotFileParser] = {}

    async def _respect_rate_limit(self, host: str) -> None:
        elapsed = time.monotonic() - self._last_request[host]
        if elapsed < self.min_interval_seconds:
            await asyncio.sleep(self.min_interval_seconds - elapsed)
        self._last_request[host] = time.monotonic()

    async def _allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser = RobotFileParser()
            robots_url = f"{origin}/robots.txt"
            try:
                response = await client.get(robots_url)
                if response.status_code < 400:
                    parser.parse(response.text.splitlines())
                else:
                    parser.parse([])
            except httpx.HTTPError as exc:
                # Network failure is distinct from an explicit robots prohibition.
                logger.warning("robots.txt could not be retrieved for %s: %s", origin, exc)
                parser.parse([])
            self._robots[origin] = parser
        return self._robots[origin].can_fetch(self.user_agent, url)

    async def download(self, source: SourceSpec) -> bytes:
        url = str(source.url)
        host = urlparse(url).netloc
        headers = {"User-Agent": self.user_agent, "Accept-Language": source.language}
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers=headers,
            transport=self.transport,
        ) as client:
            if not await self._allowed(client, url):
                raise SourceDownloadError(f"robots.txt disallows retrieval: {url}")
            await self._respect_rate_limit(host)
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise SourceDownloadError(f"failed to download {url}: {exc}") from exc
            return response.content
