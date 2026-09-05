import re

from app.ingestion.arabic import normalize_arabic

_TOKEN = re.compile(r"[^\W_]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    normalized = normalize_arabic(text.lower())
    return _TOKEN.findall(normalized)
