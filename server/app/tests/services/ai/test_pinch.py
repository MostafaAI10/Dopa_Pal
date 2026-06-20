from datetime import timedelta

from app.services.ai.pinch import HIGH_ENERGY_WEIGHTS, LOW_ENERGY_WEIGHTS, PinchEngine
from app.services.ai.schemas import PinchInput


def _make_input(fixed_now, **overrides) -> PinchInput:
    defaults = dict(
        deadline=fixed_now + timedelta(days=3),
        created_at=fixed_now,
        interest_tag="ai_ml",
        user_interest_tags=["ai_ml"],
        is_novel=True,
        challenge_hint=None,
        estimated_hours=2.0,
        raw_source_text="Train the model on the new dataset",
    )
    defaults.update(overrides)
    return PinchInput(**defaults)


def test_high_energy_uses_readme_literal_weights(fixed_now):
    engine = PinchEngine()
    breakdown = engine.score(_make_input(fixed_now), state_score=80.0, now=fixed_now)
    assert breakdown.weights == HIGH_ENERGY_WEIGHTS
    assert breakdown.weights.interest == 0.0


def test_low_energy_shifts_weight_toward_interest(fixed_now):
    engine = PinchEngine()
    breakdown = engine.score(_make_input(fixed_now), state_score=30.0, now=fixed_now)
    assert breakdown.weights == LOW_ENERGY_WEIGHTS
    assert breakdown.weights.interest > breakdown.weights.urgency


def test_near_deadline_with_no_slack_maxes_urgency(fixed_now):
    engine = PinchEngine()
    task = _make_input(fixed_now, deadline=fixed_now + timedelta(hours=1), estimated_hours=2.0)
    breakdown = engine.score(task, state_score=80.0, now=fixed_now)
    assert breakdown.urgency == 1.0


def test_far_deadline_has_low_urgency(fixed_now):
    engine = PinchEngine()
    task = _make_input(fixed_now, deadline=fixed_now + timedelta(days=30), estimated_hours=1.0)
    breakdown = engine.score(task, state_score=80.0, now=fixed_now)
    assert breakdown.urgency < 0.3


def test_user_favorited_tag_scores_full_interest(fixed_now):
    engine = PinchEngine()
    matched = _make_input(fixed_now, interest_tag="ai_ml", user_interest_tags=["ai_ml"])
    unmatched = _make_input(fixed_now, interest_tag="ai_ml", user_interest_tags=["cybersecurity"])
    assert engine._interest_alignment(matched) == 1.0
    assert engine._interest_alignment(unmatched) == 0.3


def test_no_tag_scores_zero_interest(fixed_now):
    engine = PinchEngine()
    task = _make_input(fixed_now, interest_tag=None)
    assert engine._interest_alignment(task) == 0.0


def test_explicit_challenge_hint_overrides_heuristic(fixed_now):
    engine = PinchEngine()
    task = _make_input(fixed_now, challenge_hint="intricate", raw_source_text="reply to email")
    # raw_source_text alone would estimate "low", but explicit hint wins
    assert engine._challenge(task) == 0.9


def test_rank_orders_highest_score_first(fixed_now):
    engine = PinchEngine()
    urgent = _make_input(fixed_now, deadline=fixed_now + timedelta(hours=2), estimated_hours=1.0)
    distant = _make_input(fixed_now, deadline=fixed_now + timedelta(days=60), estimated_hours=1.0)
    ranked = engine.rank({1: distant, 2: urgent}, state_score=80.0, now=fixed_now)
    assert ranked[0][0] == 2  # urgent task ranks first at high energy
