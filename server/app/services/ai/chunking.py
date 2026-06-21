from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.services.ai.schemas import SubBlockPlan

DEFAULT_BLOCK_MINUTES = 120

# Remainder chunks shorter than this get merged into the preceding block
# rather than existing as their own awkward 10-minute sub-block.
MIN_STANDALONE_REMAINDER_MINUTES = 30


@dataclass
class ChunkingResult:
    sub_blocks: list[SubBlockPlan]
    was_compressed: bool  # True if the deadline window was too tight to space ideally


class ChunkingEngine:
    """
    Splits a task's estimated effort into sub-blocks and distributes them
    across the window between "now" and the deadline.
    """

    def __init__(self, block_minutes: int = DEFAULT_BLOCK_MINUTES):
        self._block_minutes = block_minutes

    def plan_sub_blocks(
        self,
        estimated_hours: float,
        deadline: datetime,
        reference_time: datetime | None = None,
    ) -> ChunkingResult:
        reference_time = reference_time or datetime.now()
        total_minutes = round(estimated_hours * 60)

        durations = self._split_durations(total_minutes)
        window_start = reference_time.date()
        window_end = deadline.date()

        was_compressed = window_end < window_start
        if was_compressed:
            window_end = window_start

        dates = self._distribute_dates(len(durations), window_start, window_end)

        sub_blocks = [
            SubBlockPlan(sequence=i + 1, duration_minutes=duration, scheduled_date=d)
            for i, (duration, d) in enumerate(zip(durations, dates))
        ]
        return ChunkingResult(sub_blocks=sub_blocks, was_compressed=was_compressed)

    def _split_durations(self, total_minutes: int) -> list[int]:
        """
        Break total_minutes into a list of block durations, each capped at
        self._block_minutes. The remainder either becomes its own shorter
        final block, or if it's too small to be useful on its own gets
        folded into the previous block instead.
        """
        if total_minutes <= self._block_minutes:
            return [max(total_minutes, 1)]

        full_blocks, remainder = divmod(total_minutes, self._block_minutes)
        durations = [self._block_minutes] * full_blocks

        if remainder == 0:
            return durations

        if remainder < MIN_STANDALONE_REMAINDER_MINUTES:
            durations[-1] += remainder  # fold into last full block
        else:
            durations.append(remainder)

        return durations

    def _distribute_dates(
        self, num_blocks: int, window_start: date, window_end: date
    ) -> list[date]:
        """
        Spread `num_blocks` dates across [window_start, window_end].

        Block 0 lands on window_start - we want the user starting today,
        not waiting. Blocks are then spaced evenly so the LAST block lands
        *before* the deadline day itself wherever the window allows,
        preserving a buffer rather than clustering right at the cutoff
        (this is the literal anti-procrastination rule from the README).
        """
        if num_blocks == 1:
            return [window_start]

        window_days = (window_end - window_start).days

        if window_days <= 0:
            return [window_start] * num_blocks

        dates: list[date] = []
        for i in range(num_blocks):
            offset_days = round(i * window_days / num_blocks)
            dates.append(window_start + timedelta(days=offset_days))

        return dates
