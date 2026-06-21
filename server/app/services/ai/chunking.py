from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.services.ai.schemas import SubBlockPlan

import math

# The maximum allowed minutes for any single sub-block to maintain focus.
MAX_BLOCK_MINUTES = 45
# The minimum target duration for highly complex tasks (e.g. Pomodoro style).
MIN_TARGET_MINUTES = 25


@dataclass
class ChunkingResult:
    sub_blocks: list[SubBlockPlan]
    was_compressed: bool  # True if the deadline window was too tight to space ideally


class ChunkingEngine:
    """
    Splits a task's estimated effort into sub-blocks and distributes them
    across the window between "now" and the deadline.
    
    Enhanced to intelligently break down complex tasks into logical, manageable steps
    based on task content, estimated duration, and natural work patterns.
    """

    def __init__(self, block_minutes: int = MAX_BLOCK_MINUTES):
        self._block_minutes = block_minutes

    def plan_sub_blocks(
        self,
        estimated_hours: float,
        deadline: datetime,
        reference_time: datetime | None = None,
        title: str = "",
        interest_tag: str = "",
        raw_source_text: str = "",
    ) -> ChunkingResult:
        reference_time = reference_time or datetime.now()
        total_minutes = round(estimated_hours * 60)

        # Intelligently split based on task characteristics
        durations = self._intelligent_split_durations(
            total_minutes, title, interest_tag, raw_source_text
        )
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

    def _intelligent_split_durations(
        self,
        total_minutes: int,
        title: str = "",
        interest_tag: str = "",
        raw_source_text: str = "",
    ) -> list[int]:
        """
        Intelligently split total_minutes into logical sub-blocks between 15 and 45 minutes
        based on task complexity. Never exceeds 45 minutes per block.
        """
        if total_minutes <= self._block_minutes:
            return [max(total_minutes, 1)]

        complexity = self._calculate_task_complexity(title, interest_tag, raw_source_text)
        
        # Target duration between 25 (high complexity) and self._block_minutes (low complexity)
        # Maps complexity (0.0 -> 1.0) to duration (self._block_minutes -> 25)
        duration_range = self._block_minutes - MIN_TARGET_MINUTES
        target_duration = self._block_minutes - int(complexity * duration_range)
        
        # Determine number of blocks needed
        num_blocks = max(1, round(total_minutes / target_duration))
        
        # Enforce max mins strictly (if rounding down caused blocks > max mins)
        if total_minutes / num_blocks > self._block_minutes:
            num_blocks = math.ceil(total_minutes / float(self._block_minutes))
            
        # Distribute evenly
        base_duration = total_minutes // num_blocks
        remainder = total_minutes % num_blocks
        
        durations = []
        for i in range(num_blocks):
            # Distribute the remainder across the first few blocks
            durations.append(base_duration + (1 if i < remainder else 0))
            
        return durations

    def _calculate_task_complexity(
        self,
        title: str,
        interest_tag: str,
        raw_source_text: str,
    ) -> float:
        """
        Calculate a complexity score (0.0-1.0) based on task characteristics.
        Higher complexity = shorter sub-blocks needed (more frequent breaks).
        """
        complexity = 0.0
        
        # Title complexity (keywords that suggest cognitive load)
        complex_keywords = [
            "architecture", "design", "implementation", "integration", "system",
            "database", "api", "server", "framework", "library", "algorithm",
            "research", "analysis", "optimization", "configuration", "deployment",
            "study", "learn", "write", "draft", "plan", "debug"
        ]
        title_lower = title.lower()
        for kw in complex_keywords:
            if kw in title_lower:
                complexity += 0.2
        
        # Interest tag complexity (technical/deep tags suggest more complexity)
        if interest_tag:
            technical_tags = [
                "programming", "coding", "development", "software", "hardware",
                "network", "security", "database", "api", "architecture",
                "engineering", "technical", "scientific", "mathematical",
                "research", "learning", "study", "academic"
            ]
            for tag in technical_tags:
                if tag in interest_tag.lower():
                    complexity += 0.15
        
        # Source text complexity (longer text implies more context/details)
        if raw_source_text:
            word_count = len(raw_source_text.split())
            if word_count > 200:
                complexity += 0.2
            elif word_count > 100:
                complexity += 0.1
        
        # Cap at 1.0
        return min(1.0, complexity)

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
