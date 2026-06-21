from app.services.ai.parsers.title_sanitizer import sanitize_title


def test_strips_leading_filler_and_trailing_deadline():
    raw = "Need to complete the system specification document by next Friday night"
    assert sanitize_title(raw) == "Complete the system specification document"


def test_strips_trailing_effort_clause():
    raw = "Write the proposal, should take about 3 hours"
    assert sanitize_title(raw) == "Write the proposal"


def test_capitalizes_first_letter_only_preserves_acronyms():
    raw = "fix the API integration bug"
    result = sanitize_title(raw)
    assert result.startswith("Fix")
    assert "API" in result  


def test_empty_after_stripping_falls_back_to_raw():
    raw = "by next Friday"
    result = sanitize_title(raw)
    assert result  # never empty


def test_truncates_to_max_length():
    raw = "x" * 400
    result = sanitize_title(raw)
    assert len(result) <= 255
