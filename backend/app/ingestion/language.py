import re

_ARABIC = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_language(text: str) -> str:
    arabic = len(_ARABIC.findall(text))
    latin = len(_LATIN.findall(text))
    if arabic == 0 and latin == 0:
        return "unknown"
    return "ar" if arabic > latin else "en"
