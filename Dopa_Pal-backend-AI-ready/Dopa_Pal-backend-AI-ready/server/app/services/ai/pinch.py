from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.ai.parsers.challenge_estimator import estimate_challenge
from app.services.ai.schemas import PinchInput

LOW_ENERGY_THRESHOLD = 50.0

# Urgency horizon: how much slack (hours_remaining - hours_needed) counts
# as "zero urgency" Beyond two weeks of slack, a task reads as not urgent.
MAX_SLACK_HOURS = 14 * 24

# Recency horizon for the continuous novelty decay.
NOVELTY_DECAY_HOURS = 72

_CHALLENGE_KEYWORDS_HIGH = ("intricate", "complex", "hard", "challenging", "advanced")
_CHALLENGE_KEYWORDS_LOW = ("quick", "simple", "easy", "trivial")


@dataclass(frozen=True)
class PinchWeights:
    urgency: float
    novelty: float
    challenge: float
    interest: float

HIGH_ENERGY_WEIGHTS = PinchWeights(urgency=0.6, novelty=0.2, challenge=0.2, interest=0.0)

LOW_ENERGY_WEIGHTS = PinchWeights(urgency=0.25, novelty=0.15, challenge=0.10, interest=0.50)


@dataclass
class PinchScoreBreakdown:
    """Exposed for debugging/demo purposes - lets the dashboard show *why*
    a task was surfaced, which is good for trust with an ADHD user base."""
    urgency: float
    novelty: float
    challenge: float
    interest: float
    weights: PinchWeights
    total: float  # 0-100


class PinchEngine:
    """
    Computes the README's "Selection Priority Score" for a task, blended
    with the daily energy state per the Density Governor rule.

    Pure function over (PinchInput, state_score) - no DB access, same
    pattern as the rest of the AI module.
    """

    def score(self, task: PinchInput, state_score: float, now: datetime | None = None) -> PinchScoreBreakdown:
        now = now or datetime.now()
        weights = self._weights_for_state(state_score)

        urgency = self._urgency(task, now)
        novelty = self._novelty(task, now)
        challenge = self._challenge(task)
        interest = self._interest_alignment(task)

        total = (
            urgency * weights.urgency
            + novelty * weights.novelty
            + challenge * weights.challenge
            + interest * weights.interest
        ) * 100.0

        return PinchScoreBreakdown(
            urgency=urgency, novelty=novelty, challenge=challenge,
            interest=interest, weights=weights, total=round(max(0.0, min(100.0, total)), 2),
        )

    def rank(
        self, tasks: dict[int, PinchInput], state_score: float, now: datetime | None = None
    ) -> list[tuple[int, PinchScoreBreakdown]]:
        """
        Rank task_id -> PinchInput pairs, highest priority first.
        Used by the bubble's "next task" selection (API contract §2).
        """
        now = now or datetime.now()
        scored = [(tid, self.score(t, state_score, now)) for tid, t in tasks.items()]
        return sorted(scored, key=lambda pair: pair[1].total, reverse=True)

    # da el component calculators

    def _weights_for_state(self, state_score: float) -> PinchWeights:
        return LOW_ENERGY_WEIGHTS if state_score < LOW_ENERGY_THRESHOLD else HIGH_ENERGY_WEIGHTS

    def _urgency(self, task: PinchInput, now: datetime) -> float:
        hours_remaining = max(0.0, (task.deadline - now).total_seconds() / 3600.0)
        slack = hours_remaining - task.estimated_hours

        if slack <= 0:
            return 1.0  
        return max(0.0, min(1.0, 1.0 - (slack / MAX_SLACK_HOURS)))

    def _novelty(self, task: PinchInput, now: datetime) -> float:
        age_hours = max(0.0, (now - task.created_at).total_seconds() / 3600.0)
        recency_decay = max(0.0, 1.0 - (age_hours / NOVELTY_DECAY_HOURS))
        explicit_flag = 1.0 if task.is_novel else 0.0
        return max(recency_decay, explicit_flag)

    def _challenge(self, task: PinchInput) -> float:
        if task.challenge_hint:
            hint = task.challenge_hint.lower()
            if any(kw in hint for kw in _CHALLENGE_KEYWORDS_HIGH):
                return 0.9
            if any(kw in hint for kw in _CHALLENGE_KEYWORDS_LOW):
                return 0.2
            return 0.5
        if task.raw_source_text:
            return estimate_challenge(task.raw_source_text).score
        return 0.5

    def _interest_alignment(self, task: PinchInput) -> float:
        if not task.interest_tag:
            return 0.0
        if task.interest_tag in task.user_interest_tags:
            return 1.0  
        return 0.3  
