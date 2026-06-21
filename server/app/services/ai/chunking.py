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
    
    Enhanced to intelligently break down complex tasks into logical, manageable steps
    based on task content, estimated duration, and natural work patterns.
    """

    def __init__(self, block_minutes: int = DEFAULT_BLOCK_MINUTES):
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
        Intelligently split total_minutes into logical sub-blocks based on:
        - Task complexity (from title/interest/source text)
        - Natural work patterns and breaks
        - Estimated duration
        """
        # Base split on total duration
        base_durations = self._split_durations(total_minutes)
        
        # Enhance based on task characteristics
        if total_minutes >= 240:  # 4+ hours - complex task
            base_durations = self._enhance_complex_task_durations(base_durations, title, interest_tag, raw_source_text)
        elif total_minutes >= 120:  # 2-4 hours - medium task
            base_durations = self._enhance_medium_task_durations(base_durations, title, interest_tag)
        
        return base_durations

    def _enhance_complex_task_durations(
        self,
        base_durations: list[int],
        title: str,
        interest_tag: str,
        raw_source_text: str,
    ) -> list[int]:
        """
        For complex tasks (4+ hours), break into more, shorter, logical steps.
        """
        # Analyze task complexity
        complexity_score = self._calculate_task_complexity(title, interest_tag, raw_source_text)
        
        # Start with more granular base durations
        enhanced = []
        for i, duration in enumerate(base_durations):
            # Split large blocks into smaller, more manageable chunks
            if duration >= 120:  # Split blocks of 2+ hours
                # Number of splits based on complexity and duration
                num_splits = min(3, max(2, int(duration / 90) if complexity_score > 0.7 else 2))
                split_duration = max(45, duration // num_splits)  # Minimum 45 minutes per chunk
                
                for j in range(num_splits):
                    remaining = duration - (j * split_duration)
                    if j == num_splits - 1:
                        enhanced.append(remaining)
                    else:
                        enhanced.append(split_duration)
            else:
                enhanced.append(duration)
        
        return enhanced

    def _enhance_medium_task_durations(
        self,
        base_durations: list[int],
        title: str,
        interest_tag: str,
    ) -> list[int]:
        """
        For medium tasks (2-4 hours), optimize for flow and natural breaks.
        """
        enhanced = []
        for i, duration in enumerate(base_durations):
            # Split longer blocks into more manageable chunks
            if duration >= 120:  # Split blocks of 2+ hours
                # Split into 2 chunks for better flow
                split1 = max(60, duration // 2)
                split2 = duration - split1
                enhanced.extend([split1, split2])
            else:
                enhanced.append(duration)
        
        return enhanced

    def _calculate_task_complexity(
        self,
        title: str,
        interest_tag: str,
        raw_source_text: str,
    ) -> float:
        """
        Calculate a complexity score (0.0-1.0) based on task characteristics.
        Higher complexity = more sub-blocks needed.
        """
        complexity = 0.0
        
        # Title complexity (keywords that suggest complexity)
        complex_keywords = [
            "architecture", "design", "implementation", "integration", "system",
            "database", "api", "server", "framework", "library", "algorithm",
            "research", "analysis", "optimization", "configuration", "deployment"
        ]
        title_lower = title.lower()
        for kw in complex_keywords:
            if kw in title_lower:
                complexity += 0.2
        
        # Interest tag complexity (technical tags suggest more complexity)
        if interest_tag:
            technical_tags = [
                "programming", "coding", "development", "software", "hardware",
                "network", "security", "database", "api", "architecture",
                "engineering", "technical", "scientific", "mathematical"
            ]
            for tag in technical_tags:
                if tag in interest_tag.lower():
                    complexity += 0.15
        
        # Source text complexity (longer, more detailed text suggests complexity)
        if raw_source_text:
            word_count = len(raw_source_text.split())
            if word_count > 200:
                complexity += 0.2
            elif word_count > 100:
                complexity += 0.1
        
        # Cap at 1.0
        return min(1.0, complexity)

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
