"""
Task Segmentation Engine — the Core Behavioral Engine of dopaPal.

Intercepts raw, chaotic task inputs and distills them into a structured,
non-intimidating execution plan optimised for neurodivergent users.

Three operational capabilities:
    1. 2-Hour Threshold Rule (QUICK_WIN vs LINEAR_MICRO_SPREADING)
    2. Linear Micro-Spreading Framework (multi-day distribution)
    3. Micro-Step Copywriting Guidelines (hyper-concrete action verbs)

This module is pure logic — no DB access, no LLM calls.  The LLM
integration is handled by the caller (AIService.segment()) which can
inject enriched micro-steps; this engine always has a deterministic
fallback so task capture never blocks on an LLM being up.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

from app.services.ai.schemas import (
    DayPlan,
    MicroStep,
    SegmentationInput,
    SegmentationMetadata,
    SegmentationOutput,
)

# Duration bounds for individual micro-steps (minutes).
MIN_STEP_MINUTES = 10
MAX_STEP_MINUTES = 45
# The threshold below which a task is treated as a "Quick Win".
QUICK_WIN_THRESHOLD_MINUTES = 120
# Default duration when the user provides neither estimate nor deadline.
DEFAULT_DURATION_MINUTES = 60

# ── Vague-verb blacklist (Micro-Step Copywriting Guideline) ───────────────
_VAGUE_VERBS = frozenset({
    "work on", "plan", "research", "fix", "study", "handle",
    "deal with", "look at", "figure out", "think about",
})

# ── Friction-curve: low-friction setup verbs for Day 1 ────────────────────
_SETUP_TITLES = [
    "Open the project folder and review the current file structure",
    "Create any missing directories or placeholder files needed",
    "Install or verify required tools and dependencies",
    "Skim through existing notes or documentation for context",
    "Write a 3-bullet personal checklist of what 'done' looks like",
]


class SegmentationEngine:
    """
    Deterministic task segmentation engine.

    Accepts a ``SegmentationInput`` and returns a ``SegmentationOutput``
    with the full execution plan, fog-of-war masking, and metadata.
    Optionally accepts LLM-generated micro-steps to replace the
    deterministic fallback titles.
    """

    def segment(
        self,
        payload: SegmentationInput,
        llm_steps: list[dict] | None = None,
    ) -> SegmentationOutput:
        """
        Main entry point.

        Parameters
        ----------
        payload : SegmentationInput
            Raw user input with optional deadline/duration.
        llm_steps : list[dict] | None
            Optional LLM-generated micro-steps, each with keys:
            ``action_title``, ``estimated_minutes``, ``behavioral_tip``,
            ``day_index``.  When provided these replace the deterministic
            fallback titles but are still validated and bounded.
        """
        now = payload.current_timestamp
        total_minutes = self._resolve_total_minutes(payload)
        parsed_title = self._extract_title(payload.raw_input)
        days_to_deadline = self._calculate_days_to_deadline(now, payload.deadline_timestamp)

        # ── Clarification guard ───────────────────────────────────────
        requires_clarification = False
        clarification_prompt: str | None = None

        if payload.user_estimated_duration_minutes is None and payload.deadline_timestamp is None:
            requires_clarification = True
            clarification_prompt = (
                "I couldn't determine the duration or deadline for this task. "
                "Using a safe default of 60 minutes. "
                "Could you provide an estimated duration or a deadline?"
            )

        # ── Strategy selection (2-Hour Threshold Rule) ────────────────
        if total_minutes < QUICK_WIN_THRESHOLD_MINUTES:
            strategy = "QUICK_WIN"
            execution_plan = self._apply_quick_win(
                total_minutes, parsed_title, now, llm_steps,
            )
            daily_quota = None
        else:
            strategy = "LINEAR_MICRO_SPREADING"
            effective_days = max(1, days_to_deadline) if days_to_deadline is not None else 1
            daily_quota = math.ceil(total_minutes / effective_days)
            execution_plan = self._apply_linear_micro_spreading(
                total_minutes, effective_days, daily_quota,
                parsed_title, now, llm_steps,
            )

        metadata = SegmentationMetadata(
            parsed_title=parsed_title,
            total_estimated_minutes=total_minutes,
            strategy_applied=strategy,
            days_to_deadline=days_to_deadline,
            daily_minute_quota=daily_quota,
            llm_enriched=bool(llm_steps),
        )

        return SegmentationOutput(
            metadata=metadata,
            execution_plan=execution_plan,
            requires_user_clarification=requires_clarification,
            clarification_prompt=clarification_prompt,
        )

    # ──────────────────────────────────────────────────────────────────
    # Quick Win (< 2 hours)
    # ──────────────────────────────────────────────────────────────────

    def _apply_quick_win(
        self,
        total_minutes: int,
        title: str,
        now: datetime,
        llm_steps: list[dict] | None,
    ) -> list[DayPlan]:
        """Produce a single-day plan with 2–4 short milestones."""
        steps = self._build_steps_for_day(
            total_minutes, title, llm_steps, day_index=1,
            step_counter_start=1, max_milestones=4,
        )
        return [
            DayPlan(day_index=1, is_active_today=True, daily_steps=steps),
        ]

    # ──────────────────────────────────────────────────────────────────
    # Linear Micro-Spreading (≥ 2 hours, multi-day)
    # ──────────────────────────────────────────────────────────────────

    def _apply_linear_micro_spreading(
        self,
        total_minutes: int,
        effective_days: int,
        daily_quota: int,
        title: str,
        now: datetime,
        llm_steps: list[dict] | None,
    ) -> list[DayPlan]:
        """Distribute micro-steps evenly across days, front-loading Day 1."""
        plan: list[DayPlan] = []
        remaining = total_minutes
        step_counter = 1

        for day_idx in range(1, effective_days + 1):
            is_last_day = day_idx == effective_days
            day_budget = remaining if is_last_day else min(daily_quota, remaining)

            if day_budget <= 0:
                break

            # Friction Curve: Day 1 gets lower-friction setup steps
            if day_idx == 1:
                steps = self._build_friction_curve_steps(
                    day_budget, title, llm_steps, step_counter,
                )
            else:
                # Extract LLM steps for this specific day
                day_llm = None
                if llm_steps:
                    day_llm = [s for s in llm_steps if s.get("day_index") == day_idx]
                    if not day_llm:
                        day_llm = None

                steps = self._build_steps_for_day(
                    day_budget, title, day_llm, day_index=day_idx,
                    step_counter_start=step_counter,
                )

            step_counter += len(steps)
            remaining -= sum(s.estimated_minutes for s in steps)

            plan.append(DayPlan(
                day_index=day_idx,
                is_active_today=(day_idx == 1),  # Fog-of-War
                daily_steps=steps,
            ))

        return plan

    # ──────────────────────────────────────────────────────────────────
    # Step builders
    # ──────────────────────────────────────────────────────────────────

    def _build_friction_curve_steps(
        self,
        day_budget: int,
        title: str,
        llm_steps: list[dict] | None,
        step_counter: int,
    ) -> list[MicroStep]:
        """
        Day-1 friction curve: deliberately produce the easiest, most
        physical actions (open editor, create files, install tools).
        """
        # If LLM provided day-1 steps, use those
        if llm_steps:
            day1_llm = [s for s in llm_steps if s.get("day_index") == 1]
            if day1_llm:
                return self._llm_dicts_to_steps(day1_llm, step_counter, day_budget)

        # Deterministic friction-curve fallback
        steps: list[MicroStep] = []
        remaining = day_budget
        idx = step_counter

        for setup_title in _SETUP_TITLES:
            if remaining <= 0:
                break
            duration = min(MAX_STEP_MINUTES, max(MIN_STEP_MINUTES, remaining))
            # Cap individual setup step at 15 mins (low friction)
            duration = min(15, duration)
            steps.append(MicroStep(
                step_id=f"step_{idx:03d}",
                step_number=idx,
                action_title=setup_title,
                estimated_minutes=duration,
                behavioral_tip="Just get the environment ready. No real thinking required yet.",
            ))
            remaining -= duration
            idx += 1

        # If budget still remains after setup, add a small "review" step
        if remaining > 0:
            chunk_duration = min(MAX_STEP_MINUTES, remaining)
            steps.append(MicroStep(
                step_id=f"step_{idx:03d}",
                step_number=idx,
                action_title=f"Skim the first section of '{title[:60]}' to build mental context",
                estimated_minutes=chunk_duration,
                behavioral_tip="You're done setting up. Just read — no action required yet.",
            ))

        return steps

    def _build_steps_for_day(
        self,
        day_budget: int,
        title: str,
        llm_steps: list[dict] | None,
        day_index: int,
        step_counter_start: int,
        max_milestones: int = 6,
    ) -> list[MicroStep]:
        """Build micro-steps for a single day, using LLM or deterministic."""
        if llm_steps:
            return self._llm_dicts_to_steps(llm_steps, step_counter_start, day_budget)

        return self._deterministic_steps(
            day_budget, title, day_index,
            step_counter_start, max_milestones,
        )

    def _deterministic_steps(
        self,
        day_budget: int,
        title: str,
        day_index: int,
        step_counter_start: int,
        max_milestones: int,
    ) -> list[MicroStep]:
        """
        Fallback step generation when LLM is unavailable.
        Splits the budget into even chunks of 15–45 minutes.
        """
        if day_budget <= MAX_STEP_MINUTES:
            return [MicroStep(
                step_id=f"step_{step_counter_start:03d}",
                step_number=step_counter_start,
                action_title=f"Complete the next chunk of '{title[:80]}'",
                estimated_minutes=max(MIN_STEP_MINUTES, day_budget),
                behavioral_tip="One small step. You've got this.",
            )]

        # Target ~25 min blocks for manageable focus bursts
        target = 25
        num_blocks = min(max_milestones, max(2, round(day_budget / target)))

        # Ensure we don't exceed max step duration
        if day_budget / num_blocks > MAX_STEP_MINUTES:
            num_blocks = math.ceil(day_budget / MAX_STEP_MINUTES)

        base = day_budget // num_blocks
        remainder = day_budget % num_blocks

        steps: list[MicroStep] = []
        idx = step_counter_start

        _generic_verbs = [
            "Draft", "Compile", "List", "Write", "Assemble", "Outline",
        ]

        for i in range(num_blocks):
            duration = base + (1 if i < remainder else 0)
            verb = _generic_verbs[i % len(_generic_verbs)]
            steps.append(MicroStep(
                step_id=f"step_{idx:03d}",
                step_number=idx,
                action_title=f"{verb} the next section of '{title[:60]}'",
                estimated_minutes=max(MIN_STEP_MINUTES, min(MAX_STEP_MINUTES, duration)),
                behavioral_tip=f"Focus block {i + 1} of {num_blocks}. Just this one piece.",
            ))
            idx += 1

        return steps

    def _llm_dicts_to_steps(
        self,
        llm_steps: list[dict],
        step_counter: int,
        day_budget: int,
    ) -> list[MicroStep]:
        """Convert and validate LLM-provided step dicts into MicroStep models."""
        validated: list[MicroStep] = []
        idx = step_counter
        budget_remaining = day_budget

        for raw in llm_steps:
            action_title = str(raw.get("action_title", "")).strip()
            if not action_title:
                continue

            minutes = raw.get("estimated_minutes", 25)
            try:
                minutes = int(minutes)
            except (ValueError, TypeError):
                minutes = 25

            # Enforce step bounds
            minutes = max(MIN_STEP_MINUTES, min(MAX_STEP_MINUTES, minutes))
            # Don't overshoot the day's budget
            minutes = min(minutes, budget_remaining)
            if minutes < MIN_STEP_MINUTES:
                break

            tip = raw.get("behavioral_tip")
            if tip:
                tip = str(tip).strip()[:500] or None

            validated.append(MicroStep(
                step_id=f"step_{idx:03d}",
                step_number=idx,
                action_title=action_title[:500],
                estimated_minutes=minutes,
                behavioral_tip=tip,
            ))
            budget_remaining -= minutes
            idx += 1

        # If LLM produced nothing valid, fall back to a single block
        if not validated:
            validated.append(MicroStep(
                step_id=f"step_{step_counter:03d}",
                step_number=step_counter,
                action_title="Complete the next chunk of this task",
                estimated_minutes=max(MIN_STEP_MINUTES, min(MAX_STEP_MINUTES, day_budget)),
                behavioral_tip="One small step. You've got this.",
            ))

        return validated

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _resolve_total_minutes(self, payload: SegmentationInput) -> int:
        """
        Determine total effort.  Priority:
            1. user_estimated_duration_minutes (explicit)
            2. Safe default (60 minutes)
        """
        if payload.user_estimated_duration_minutes is not None:
            return payload.user_estimated_duration_minutes
        return DEFAULT_DURATION_MINUTES

    def _extract_title(self, raw_input: str) -> str:
        """
        Extract a clean, short title from chaotic raw text.
        Takes the first sentence/line, strips filler words, caps at 255 chars.
        """
        text = raw_input.strip()
        # Take first meaningful line
        for line in text.splitlines():
            cleaned = line.strip()
            if cleaned and len(cleaned) > 3:
                # Remove trailing punctuation clutter
                cleaned = cleaned.rstrip(".,;:!?…")
                return cleaned[:255]
        return text[:255]

    def _calculate_days_to_deadline(
        self, now: datetime, deadline: datetime | None,
    ) -> int | None:
        """Days between now and deadline.  None if no deadline given."""
        if deadline is None:
            return None
        delta = (deadline.date() - now.date()).days
        return max(1, delta)  # At least 1 day even if overdue
