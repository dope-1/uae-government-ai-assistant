from pathlib import Path

from app.ingestion.parsers import parse_html, parse_pdf

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_html_parser_prefers_main_and_drops_script() -> None:
    payload = b"""
    <html><head><title>Service Page</title><script>ignore()</script></head>
    <body><nav>Navigation</nav><main><h1>Renew licence</h1>
    <p>Take an eye test.</p></main></body></html>
    """
    title, text = parse_html(payload)
    assert title == "Service Page"
    assert "Renew licence" in text
    assert "eye test" in text
    assert "ignore" not in text


def test_pdf_parser_extracts_text_and_title() -> None:
    title, text = parse_pdf((FIXTURES / "sample.pdf").read_bytes())
    assert title == "Sample Government PDF"
    assert "Driving licence information" in text
