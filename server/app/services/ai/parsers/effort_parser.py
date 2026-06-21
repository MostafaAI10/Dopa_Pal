from __future__ import annotations

import re
from dataclasses import dataclass

# Matches patterns like:
#   "6 hours", "about 6 hours", "6 hrs", "2.5 hours", "90 minutes", "45 mins"
_HOURS_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\b", re.IGNORECASE
)
_MINUTES_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:minutes?|mins?)\b", re.IGNORECASE
)

# Vague effort words mapped to conservative hour estimates when no number
# is present at all. Kept deliberately small and conservative.
_VAGUE_EFFORT_HINTS = {
    "quick": 0.5,
    "short": 1.0,
    "small": 1.0,
    "big": 6.0,
    "huge": 10.0,
    "massive": 12.0,
}

DEFAULT_ESTIMATED_HOURS = 2.0


@dataclass
class EffortParseResult:
    estimated_hours: float
    confidence: float


def parse_effort(text: str) -> EffortParseResult:
    """
    Extract an effort/duration estimate from free text.

    Priority: explicit hours > explicit minutes > vague keyword hint > default.
    """
    hours_match = _HOURS_RE.search(text)
    if hours_match:
        return EffortParseResult(
            estimated_hours=round(float(hours_match.group("value")), 2),
            confidence=0.9,
        )

    minutes_match = _MINUTES_RE.search(text)
    if minutes_match:
        minutes = float(minutes_match.group("value"))
        return EffortParseResult(
            estimated_hours=round(minutes / 60.0, 2),
            confidence=0.85,
        )

    lowered = text.lower()
    for keyword, hours in _VAGUE_EFFORT_HINTS.items():
        if keyword in lowered:
            return EffortParseResult(estimated_hours=hours, confidence=0.4)

    return EffortParseResult(estimated_hours=DEFAULT_ESTIMATED_HOURS, confidence=0.2)
