from app.services.ai.parsers.challenge_estimator import estimate_challenge


def test_high_challenge_keywords_detected():
    result = estimate_challenge("Refactor the entire authentication architecture from scratch")
    assert result.hint == "high"
    assert result.score >= 0.8


def test_low_challenge_keywords_detected():
    result = estimate_challenge("Reply to the email and confirm the meeting")
    assert result.hint == "low"
    assert result.score <= 0.3


def test_neutral_text_defaults_to_medium():
    result = estimate_challenge("Walk the dog")
    assert result.hint == "medium"
    assert result.confidence < 0.5


def test_clause_connectors_increase_signal():
    result = estimate_challenge(
        "Set up the database and then migrate the schema once the backup completes"
    )
    assert result.hint in {"high", "medium"}
