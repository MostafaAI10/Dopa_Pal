from __future__ import annotations

import re
from dataclasses import dataclass

_HIGH_CHALLENGE_KEYWORDS = (
    "refactor", "redesign", "architecture", "debug", "optimize", "research",
    "design", "integrate", "migrate", "algorithm", "fix the", "rebuild",
    "from scratch", "investigate", "prove", "derive",
)

_LOW_CHALLENGE_KEYWORDS = (
    "reply", "email", "send", "review", "read", "update the", "rename",
    "schedule", "call", "remind", "check", "confirm", "format",
)

_CLAUSE_CONNECTOR_RE = re.compile(
    r"\b(and then|after that|which requires|once|before that|depends on)\b",
    re.IGNORECASE,
)

WORD_COUNT_HIGH_THRESHOLD = 18  # longer descriptions correlate with more moving parts


@dataclass
class ChallengeEstimate:
    hint: str          
    score: float        
    confidence: float


def estimate_challenge(text: str) -> ChallengeEstimate:

    lowered = text.lower()

    high_hits = sum(1 for kw in _HIGH_CHALLENGE_KEYWORDS if kw in lowered)
    low_hits = sum(1 for kw in _LOW_CHALLENGE_KEYWORDS if kw in lowered)
    clause_hits = len(_CLAUSE_CONNECTOR_RE.findall(text))
    word_count = len(text.split())

    signal = (high_hits * 2) + clause_hits - (low_hits * 2)
    if word_count > WORD_COUNT_HIGH_THRESHOLD:
        signal += 1

    if signal >= 2:
        return ChallengeEstimate(hint="high", score=0.85, confidence=0.6)
    if signal <= -2:
        return ChallengeEstimate(hint="low", score=0.2, confidence=0.6)
    return ChallengeEstimate(hint="medium", score=0.5, confidence=0.3)
