from __future__ import annotations

from io import BytesIO

from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.ingestion.cleaning import clean_text


class ParseError(ValueError):
    pass


def parse_html(payload: bytes) -> tuple[str, str]:
    soup = BeautifulSoup(payload, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "form", "button"]):
        tag.decompose()
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else "Untitled"
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = clean_text(main.get_text("\n", strip=True))
    if not text:
        raise ParseError("HTML document contained no extractable text")
    return title, text


def parse_pdf(payload: bytes) -> tuple[str, str]:
    reader = PdfReader(BytesIO(payload))
    pages = [clean_text(page.extract_text() or "") for page in reader.pages]
    text = clean_text("\n\n".join(page for page in pages if page))
    if not text:
        raise ParseError("PDF document contained no extractable text")
    title = "Untitled PDF"
    if reader.metadata and reader.metadata.title:
        title = clean_text(reader.metadata.title)
    return title, text
