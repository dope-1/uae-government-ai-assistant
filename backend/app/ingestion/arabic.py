import re

_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_ALEF = re.compile(r"[إأآٱ]")


def normalize_arabic(text: str) -> str:
    """Normalize Arabic for retrieval without changing ordinary word boundaries."""
    text = text.replace("ـ", "")
    text = _DIACRITICS.sub("", text)
    text = _ALEF.sub("ا", text)
    text = text.replace("ى", "ي")
    return " ".join(text.split())
