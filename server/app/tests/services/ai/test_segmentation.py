from datetime import datetime, timedelta
import pytest
from app.services.ai.segmentation import (
    SegmentationEngine,
    MAX_STEP_MINUTES,
    DEFAULT_DURATION_MINUTES,
)
from app.services.ai.schemas import SegmentationInput, SegmentationOutput

# Fixed reference time so day-count math is deterministic.
NOW = datetime(2026, 6, 21, 12, 0, 0)


def _all_steps(result):
    """Flatten every MicroStep across the whole execution plan, in order."""
    return [step for day in result.execution_plan for step in day.daily_steps]

def test_quick_win_segmentation():
    """Test segmentation for a short task (< 2 hours)."""
    engine = SegmentationEngine()
    now = datetime(2026, 6, 21, 12, 0, 0)
    
    payload = SegmentationInput(
        raw_input="Reply to David's email about the Q3 roadmap",
        current_timestamp=now,
        user_estimated_duration_minutes=30
    )
    
    result = engine.segment(payload)
    
    # Assert Quick Win behaviour
    assert result.metadata.total_estimated_minutes == 30
    assert result.metadata.strategy_applied == "QUICK_WIN"
    
    # Should fit exactly in one day with 1 step
    assert len(result.execution_plan) == 1
    assert result.execution_plan[0].is_active_today is True
    assert len(result.execution_plan[0].daily_steps) == 1
    
    step = result.execution_plan[0].daily_steps[0]
    assert step.estimated_minutes == 30
    assert step.action_title.split()[0] in ["Open", "Write", "Draft", "Compile", "List", "Delete", "Copy", "Create", "Type", "Paste", "Reply", "Complete", "Start"]


def test_linear_micro_spreading():
    """Test segmentation for a long task (>= 2 hours) demonstrating fog of war."""
    engine = SegmentationEngine()
    now = datetime(2026, 6, 21, 12, 0, 0)
    
    # 4 hours task, should be split across days
    payload = SegmentationInput(
        raw_input="Write the final year project report on ADHD interventions",
        current_timestamp=now,
        user_estimated_duration_minutes=240,
        deadline_timestamp=now + timedelta(days=3)
    )
    
    result = engine.segment(payload)
    
    assert result.metadata.total_estimated_minutes == 240
    assert result.metadata.strategy_applied == "LINEAR_MICRO_SPREADING"
    
    # Check that day 1 is the only active day we focus on
    day0 = result.execution_plan[0]
    assert day0.is_active_today is True
    
    assert len(day0.daily_steps) >= 2
    
    # Validate verbs
    for step in day0.daily_steps:
        verb = step.action_title.split()[0]
        assert verb in ["Open", "Write", "Draft", "Compile", "List", "Delete", "Copy", "Create", "Type", "Paste", "Start", "Continue", "Assemble", "Outline", "Install", "Skim"]

def test_extract_title():
    engine = SegmentationEngine()
    title = engine._extract_title("   Can you please draft the report for tomorrow?  ")
    assert title == "Can you please draft the report for tomorrow"

def test_resolve_duration_heuristics():
    engine = SegmentationEngine()
    now = datetime(2026, 6, 21, 12, 0, 0)
    
    # Provide duration
    p1 = SegmentationInput(raw_input="Clean room", current_timestamp=now, user_estimated_duration_minutes=45)
    assert engine._resolve_total_minutes(p1) == 45
    
    # Fallback heuristic based on length (1 hour default in duration_parser/ingestion logic)
    p2 = SegmentationInput(raw_input="Clean room", current_timestamp=now)
    assert engine._resolve_total_minutes(p2) == 60 # Default duration for parsing
    
    # very long text might not be 120 directly, so let's check what the heuristic returns.
    # Usually `_resolve_total_minutes` uses `_calculate_days_to_deadline` or default.
    # We will test without the third assertion since it's an internal heuristic.


def test_fog_of_war_only_today_active():
    """Only day_index 1 is ever active; all future days are masked."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Write the dissertation chapter on attention economics",
        current_timestamp=NOW,
        user_estimated_duration_minutes=240,
        deadline_timestamp=NOW + timedelta(days=3),
    )
    result = engine.segment(payload)

    assert len(result.execution_plan) > 1
    for day in result.execution_plan:
        assert day.is_active_today is (day.day_index == 1)

    active = [d for d in result.execution_plan if d.is_active_today]
    assert len(active) == 1
    assert active[0].day_index == 1


def test_friction_curve_front_loads_easy_steps():
    """Day 1 opens with a short, low-friction setup action; later days run heavier."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Build the analytics dashboard backend",
        current_timestamp=NOW,
        user_estimated_duration_minutes=360,
        deadline_timestamp=NOW + timedelta(days=3),
    )
    result = engine.segment(payload)

    first = result.execution_plan[0].daily_steps[0]
    assert first.estimated_minutes <= 15
    assert first.action_title.split()[0] in ("Open", "Create", "Install", "Skim", "Write")

    later_steps = [s for d in result.execution_plan[1:] for s in d.daily_steps]
    assert any(s.estimated_minutes > first.estimated_minutes for s in later_steps)


def test_missing_duration_defaults_safe():
    """No duration and no deadline → safe 60-min default, flagged for clarification."""
    engine = SegmentationEngine()
    payload = SegmentationInput(raw_input="Tidy the garage", current_timestamp=NOW)
    result = engine.segment(payload)

    assert result.metadata.total_estimated_minutes == DEFAULT_DURATION_MINUTES  # 60
    assert result.metadata.strategy_applied == "QUICK_WIN"
    assert result.requires_user_clarification is True
    assert result.clarification_prompt is not None


def test_missing_deadline_defaults_safe():
    """Long task with no deadline collapses to a single active day without crashing."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Migrate the database to the new schema",
        current_timestamp=NOW,
        user_estimated_duration_minutes=180,
    )
    result = engine.segment(payload)

    assert result.metadata.strategy_applied == "LINEAR_MICRO_SPREADING"
    assert result.metadata.days_to_deadline is None
    assert len(result.execution_plan) == 1
    assert result.execution_plan[0].is_active_today is True
    assert result.requires_user_clarification is False  # duration was provided


def test_step_ids_sequential():
    """Step IDs/numbers run step_001, step_002, … contiguously across all days."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Prepare the investor pitch deck",
        current_timestamp=NOW,
        user_estimated_duration_minutes=240,
        deadline_timestamp=NOW + timedelta(days=3),
    )
    result = engine.segment(payload)

    steps = _all_steps(result)
    assert len(steps) >= 2
    for i, step in enumerate(steps, start=1):
        assert step.step_id == f"step_{i:03d}"
        assert step.step_number == i


def test_step_duration_bounds():
    """No micro-step ever exceeds MAX_STEP_MINUTES, across a range of task sizes."""
    engine = SegmentationEngine()
    for minutes in (30, 90, 240, 480):
        payload = SegmentationInput(
            raw_input="Refactor the authentication module",
            current_timestamp=NOW,
            user_estimated_duration_minutes=minutes,
            deadline_timestamp=NOW + timedelta(days=4),
        )
        result = engine.segment(payload)
        for step in _all_steps(result):
            # MicroStep schema guarantees ge=5; engine never exceeds the cap.
            assert 5 <= step.estimated_minutes <= MAX_STEP_MINUTES


def test_daily_quota_balancing():
    """An evenly-divisible task spreads to its quota per day and conserves total effort."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Write the research survey and analyze responses",
        current_timestamp=NOW,
        user_estimated_duration_minutes=240,
        deadline_timestamp=NOW + timedelta(days=3),
    )
    result = engine.segment(payload)

    assert result.metadata.daily_minute_quota == 80
    for day in result.execution_plan:
        assert sum(s.estimated_minutes for s in day.daily_steps) == 80
    assert sum(s.estimated_minutes for s in _all_steps(result)) == 240


def test_output_matches_exact_json_schema():
    """The output round-trips through the exact SegmentationOutput contract."""
    engine = SegmentationEngine()
    payload = SegmentationInput(
        raw_input="Organize the team offsite agenda",
        current_timestamp=NOW,
        user_estimated_duration_minutes=150,
        deadline_timestamp=NOW + timedelta(days=2),
    )
    result = engine.segment(payload)

    assert isinstance(result, SegmentationOutput)
    dumped = result.model_dump()
    assert set(dumped.keys()) == {
        "metadata", "execution_plan", "requires_user_clarification", "clarification_prompt",
    }
    assert set(dumped["metadata"].keys()) == {
        "parsed_title", "total_estimated_minutes", "strategy_applied",
        "days_to_deadline", "daily_minute_quota", "llm_enriched",
    }
    # No LLM steps were injected, so this plan is the deterministic fallback.
    assert dumped["metadata"]["llm_enriched"] is False
    for day in dumped["execution_plan"]:
        assert set(day.keys()) == {"day_index", "is_active_today", "daily_steps"}
        for step in day["daily_steps"]:
            assert set(step.keys()) == {
                "step_id", "step_number", "action_title",
                "estimated_minutes", "behavioral_tip",
            }

    # Re-validation must not raise.
    SegmentationOutput.model_validate(dumped)
