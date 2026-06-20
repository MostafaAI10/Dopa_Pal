from app.services.ai.parsers.effort_parser import DEFAULT_ESTIMATED_HOURS, parse_effort


def test_parses_explicit_hours():
    result = parse_effort("should take about 6 hours total")
    assert result.estimated_hours == 6.0
    assert result.confidence >= 0.85


def test_parses_decimal_hours():
    result = parse_effort("roughly 2.5 hrs of work")
    assert result.estimated_hours == 2.5


def test_parses_minutes_and_converts_to_hours():
    result = parse_effort("only takes 90 minutes")
    assert result.estimated_hours == 1.5


def test_vague_keyword_fallback():
    result = parse_effort("quick task, just reply to the email")
    assert result.estimated_hours == 0.5
    assert result.confidence < 0.5


def test_no_signal_uses_default():
    result = parse_effort("organize the project files")
    assert result.estimated_hours == DEFAULT_ESTIMATED_HOURS
    assert result.confidence < 0.3
