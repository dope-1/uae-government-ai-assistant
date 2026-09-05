from app.ingestion.arabic import normalize_arabic
from app.ingestion.language import detect_language


def test_arabic_normalisation_removes_diacritics_and_normalises_alef() -> None:
    assert normalize_arabic("إِمَارَات ـ أبوظبي") == "امارات ابوظبي"


def test_language_detection_handles_arabic_and_english() -> None:
    assert detect_language("تجديد رخصة القيادة") == "ar"
    assert detect_language("renew driving licence") == "en"
