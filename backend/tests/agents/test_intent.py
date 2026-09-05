from app.agents.intent import Intent, RuleBasedIntentClassifier


def test_bilingual_intent_baseline() -> None:
    classifier = RuleBasedIntentClassifier()
    assert classifier.classify("What documents do I need?") == Intent.DOCUMENT_REQUIREMENTS
    assert classifier.classify("كم الرسوم المطلوبة؟") == Intent.FEES
    assert classifier.classify("Compare Dubai and Abu Dhabi") == Intent.COMPARISON
