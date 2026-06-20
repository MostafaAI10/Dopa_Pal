from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import dateparser

# Phrases that imply "end of day" rather than the literal moment parsed.
_EOD_HINTS = (
    "night", "midnight", "end of day", "eod", "by tonight", "tonight",
)

#ex:
# dateparser is good at "next Friday", "in 3 days", "tomorrow", "June 26",
# but it sometimes resolves bare weekday names to *today* if today happens
# to be that weekday. We bias it forward to avoid scheduling tasks "in the
# past" relative to the moment they're captured.
_DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "RETURN_AS_TIMEZONE_AWARE": False,
}

# A conservative deadline-phrase extractor: looks for the clause that
# actually carries the date, rather than feeding dateparser the whole
# sentence (which can misfire on unrelated numbers, ex. "6 hours").
_DEADLINE_CLAUSE_RE = re.compile(
    r"(?:by|due|before|on|until)\s+(?P<clause>[A-Za-z0-9 ,]+?)"
    r"(?=(?:,|\.|$|\s+(?:should|which|and|it|that)\b))",
    re.IGNORECASE,
)


@dataclass
class DateParseResult:
    deadline: datetime | None
    confidence: float
    matched_text: str | None


def parse_deadline(text: str, reference: datetime | None = None) -> DateParseResult:
    """
    Extract a deadline datetime from free text.

    Strategy:
    1. Look for an explicit deadline clause ("by next Friday night", "due June 26").
    2. Fall back to scanning the whole string with dateparser.
    3. If nothing parses, return None with confidence 0.0 so the caller can
       decide on a sane default (e.g. +7 days) rather than guessing here.
    """
    reference = reference or datetime.now()
    settings = {**_DATEPARSER_SETTINGS, "RELATIVE_BASE": reference}

    clause_match = _DEADLINE_CLAUSE_RE.search(text)
    if clause_match:
        clause = clause_match.group("clause").strip()
        parsed = dateparser.parse(clause, settings=settings)
        if parsed:
            parsed = _apply_end_of_day_if_hinted(parsed, clause)
            return DateParseResult(deadline=parsed, confidence=0.9, matched_text=clause)

    # Fallback: scan the full sentence for any date-like span.
    parsed = dateparser.parse(text, settings=settings)
    if parsed:
        parsed = _apply_end_of_day_if_hinted(parsed, text)
        return DateParseResult(deadline=parsed, confidence=0.55, matched_text=text)

    return DateParseResult(deadline=None, confidence=0.0, matched_text=None)


def _apply_end_of_day_if_hinted(parsed: datetime, source_text: str) -> datetime:
    lowered = source_text.lower()
    if any(hint in lowered for hint in _EOD_HINTS):
        return parsed.replace(hour=23, minute=59, second=59, microsecond=0)
    return parsed


def default_deadline(reference: datetime | None = None, days_ahead: int = 7) -> datetime:
    """Sane fallback when no deadline can be parsed from the text at all."""
    reference = reference or datetime.now()
    return (reference + timedelta(days=days_ahead)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
