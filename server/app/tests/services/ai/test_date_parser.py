from datetime import datetime

from app.services.ai.parsers.date_parser import default_deadline, parse_deadline


def test_parses_explicit_by_clause(fixed_now):
    result = parse_deadline("Finish the report by next Friday night", reference=fixed_now)
    assert result.deadline is not None
    assert result.deadline.weekday() == 4  # Friday
    assert result.deadline.hour == 23 and result.deadline.minute == 59
    assert result.confidence > 0.5


def test_parses_due_clause(fixed_now):
    result = parse_deadline("Project due June 26", reference=fixed_now)
    assert result.deadline is not None
    assert result.deadline.month == 6 and result.deadline.day == 26


def test_no_date_in_text_returns_none(fixed_now):
    result = parse_deadline("Buy groceries and clean the kitchen", reference=fixed_now)
    assert result.deadline is None
    assert result.confidence == 0.0


def test_default_deadline_is_future(fixed_now):
    deadline = default_deadline(reference=fixed_now, days_ahead=7)
    assert deadline > fixed_now
    assert (deadline.date() - fixed_now.date()).days == 7


def test_tonight_hint_forces_end_of_day(fixed_now):
    result = parse_deadline("Submit the form tonight", reference=fixed_now)
    assert result.deadline is not None
    assert result.deadline.hour == 23
