"""
Core mathematical logic engines for dopaPal.

.. deprecated::
    This module is superseded by the AI/NLP integration layer.
    Use the following instead:
    - State scoring  → ``app.services.state_service.calculate_state_score_from_metrics()``
    - PINCH scoring  → ``app.services.ai.pinch.PinchEngine``
    - Task ranking   → ``app.services.ai.service.AIService.score_for_bubble()``

    These classes are kept for backward compatibility during the transition
    period but will be removed in a future version.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Sequence


@dataclass(frozen=True, slots=True)
class StateInputs:
    startup_delta_mins: int
    mood_score: int          # 1-5
    completion_rate_48h: float  # 0.0-1.0
    early_actions: int


@dataclass(frozen=True, slots=True)
class PinchSignals:
    passion: float    # 0.0-1.0
    interest: float   # 0.0-1.0
    novelty: float    # 0.0-1.0
    challenge: float  # 0.0-1.0
    hurry: float      # 0.0-1.0


class UserStateEngine:
    """Deterministic cognitive state scorer.

    Weights (from README spec):
        startup_delta  0.35
        mood           0.30
        completion_48h 0.25
        early_actions  0.10

    Output: 0.0-100.0 rounded to 2 decimal places.
    """

    _DELTA_CEILING_MINS: float = 120.0
    _MOOD_MIN: int = 1
    _MOOD_MAX: int = 5
    _ACTIONS_CAP: int = 3

    _W_DELTA: float = 0.35
    _W_MOOD: float = 0.30
    _W_COMPLETION: float = 0.25
    _W_ACTIONS: float = 0.10

    @staticmethod
    def compute(inputs: StateInputs) -> float:
        normalized_delta = max(
            0.0, 1.0 - (inputs.startup_delta_mins / UserStateEngine._DELTA_CEILING_MINS)
        )
        normalized_mood = (inputs.mood_score - UserStateEngine._MOOD_MIN) / (
            UserStateEngine._MOOD_MAX - UserStateEngine._MOOD_MIN
        )
        normalized_actions = min(
            1.0, inputs.early_actions / UserStateEngine._ACTIONS_CAP
        )

        score = (
            UserStateEngine._W_DELTA * normalized_delta
            + UserStateEngine._W_MOOD * normalized_mood
            + UserStateEngine._W_COMPLETION * inputs.completion_rate_48h
            + UserStateEngine._W_ACTIONS * normalized_actions
        ) * 100.0
        return round(score, 2)


class PinchPriorityEngine:
    """PINCH-based task ranking engine.

    High-energy (state >= 50) default weights:
        Hurry     0.35
        Challenge 0.25
        Novelty   0.15
        Interest  0.15
        Passion   0.10

    Low-energy (state < 50) shifts weights toward low-friction, high-interest
    tasks to bypass execution paralysis:
        Interest  0.30
        Passion   0.25
        Hurry     0.20
        Novelty   0.15
        Challenge 0.10
    """

    _HIGH_ENERGY_WEIGHTS = PinchSignals(
        passion=0.10, interest=0.15, novelty=0.15, challenge=0.25, hurry=0.35
    )
    _LOW_ENERGY_WEIGHTS = PinchSignals(
        passion=0.25, interest=0.30, novelty=0.15, challenge=0.10, hurry=0.20
    )
    _URGENCY_WINDOW_DAYS: int = 30

    @staticmethod
    def extract_signals(
        *,
        deadline: datetime,
        estimated_hours: float,
        interest_tag: str | None,
        created_at: datetime | None,
        state_score: float,
    ) -> PinchSignals:
        today = date.today()
        deadline_date = deadline.date()
        days_left = (deadline_date - today).days

        # Hurry: 0->1 as deadline approaches within the urgency window
        if days_left <= 0:
            hurry = 1.0
        else:
            hurry = max(0.0, min(1.0, 1.0 - days_left / PinchPriorityEngine._URGENCY_WINDOW_DAYS))

        # Interest: presence and specificity of interest tag
        interest = 1.0 if interest_tag else 0.3

        # Passion: same signal as interest (user-tagged alignment)
        passion = 1.0 if interest_tag else 0.2

        # Novelty: tasks created within the last 48 hours score higher
        if created_at:
            hours_since_created = (datetime.now(timezone.utc).replace(tzinfo=None) - created_at).total_seconds() / 3600.0
            novelty = max(0.0, min(1.0, 1.0 - hours_since_created / 48.0))
        else:
            novelty = 0.5

        # Challenge: high-effort tasks score higher when energy permits
        is_high_effort = estimated_hours >= 4.0
        if state_score >= 50.0:
            challenge = 1.0 if is_high_effort else 0.5
        else:
            challenge = 0.2 if is_high_effort else 0.9  # low energy: prefer easy wins

        return PinchSignals(
            passion=passion,
            interest=interest,
            novelty=novelty,
            challenge=challenge,
            hurry=hurry,
        )

    @staticmethod
    def score(signals: PinchSignals, state_score: float) -> float:
        """Compute weighted priority score (0-100)."""
        weights = (
            PinchPriorityEngine._HIGH_ENERGY_WEIGHTS
            if state_score >= 50.0
            else PinchPriorityEngine._LOW_ENERGY_WEIGHTS
        )
        raw = (
            weights.passion * signals.passion
            + weights.interest * signals.interest
            + weights.novelty * signals.novelty
            + weights.challenge * signals.challenge
            + weights.hurry * signals.hurry
        )
        return round(raw * 100.0, 2)

    @staticmethod
    def rank_tasks(
        tasks: Sequence,
        state_score: float,
    ) -> list[tuple[object, float]]:
        """Sort tasks descending by PINCH priority score.

        Each task must have: deadline, estimated_hours, interest_tag attributes.
        Returns list of (task, score) tuples.
        """
        scored: list[tuple[object, float]] = []
        for task in tasks:
            created_at = getattr(task, "created_at", None)
            signals = PinchPriorityEngine.extract_signals(
                deadline=task.deadline,
                estimated_hours=task.estimated_hours,
                interest_tag=task.interest_tag,
                created_at=created_at,
                state_score=state_score,
            )
            scored.append((task, PinchPriorityEngine.score(signals, state_score)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
