from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.ai.chunking import ChunkingEngine
from app.services.ai.ingestion import IngestionPipeline
from app.services.ai.llm.nvidia_client import NvidiaClient, NvidiaConfig, NvidiaUnavailableError
from app.services.ai.parsers.challenge_estimator import estimate_challenge
from app.services.ai.pinch import PinchEngine, PinchScoreBreakdown
from app.services.ai.schemas import IngestResult, ParsedTask, PinchInput, SourceType


@dataclass
class IngestOptions:
    use_llm: bool = False
    block_minutes: int = 120


class AIService:
    """
    Single entry point for the AI module. This is the only class outside
    of services/ai/ that anyone (FastAPI routes, BE1/BE2's services) should
    ever import directly.

    Two responsibilities, matching the two API contracts in the README:
      1. ingest()        -> POST /api/v1/tasks/ingest
      2. score_for_bubble() -> the ranking step behind GET /api/v1/bubble/next
    """

    def __init__(
        self,
        options: Optional[IngestOptions] = None,
        nvidia_config: Optional[NvidiaConfig] = None,
    ):
        self._options = options or IngestOptions()
        
        # If no config is passed but use_llm is true, try to load from settings
        if self._options.use_llm and not nvidia_config:
            from app.core.config import settings
            if settings.NVIDIA_API_KEY:
                nvidia_config = NvidiaConfig(
                    api_key=settings.NVIDIA_API_KEY,
                    base_url=settings.NVIDIA_BASE_URL,
                    model=settings.NVIDIA_MODEL
                )
                
        self._llm_client = (
            NvidiaClient(config=nvidia_config) if self._options.use_llm and nvidia_config else None
        )
        self._chunker = ChunkingEngine(block_minutes=self._options.block_minutes)
        self._pinch = PinchEngine()

    def ingest(
        self,
        raw_text: str,
        source_type: SourceType | str,
        now: Optional[datetime] = None,
    ) -> IngestResult:
        """
        Full ingestion: parse raw text -> ParsedTask -> chunk into sub-blocks
        -> compute an initial PINCH score (state-neutral, since the task
        doesn't have a daily energy context yet at creation time).

        This does NOT touch the database. The caller (task service) is
        responsible for persisting the `tasks` and `sub_blocks` rows using
        the values on the returned IngestResult.
        """
        now = now or datetime.now()
        pipeline = IngestionPipeline(reference_time=now, llm_client=self._llm_client, use_llm=self._options.use_llm)

        parsed = pipeline.parse(raw_text, source_type)
        llm_challenge_hint = self._llm_challenge_hint(parsed) if self._options.use_llm else None

        chunk_result = self._chunker.plan_sub_blocks(
            estimated_hours=parsed.estimated_hours,
            deadline=parsed.deadline,
            reference_time=now,
            title=parsed.title,
            interest_tag=parsed.interest_tag or "",
            raw_source_text=parsed.raw_source_text,
        )

        pinch_input = PinchInput(
            deadline=parsed.deadline,
            created_at=now,
            interest_tag=parsed.interest_tag,
            user_interest_tags=[],  # caller can re-score later once user profile is loaded
            user_passion_tags=[],   # caller can re-score later once user profile is loaded
            is_novel=True,           # freshly ingested task is novel by definition
            challenge_hint=llm_challenge_hint,
            estimated_hours=parsed.estimated_hours,
            raw_source_text=parsed.raw_source_text,
        )
        
        # Use a more dynamic default state score based on task characteristics
        # Higher complexity tasks get higher initial scores to ensure they don't get buried
        default_state_score = 60.0
        if parsed.interest_tag:
            # Tasks with interest tags might be more engaging, give them a boost
            default_state_score = min(75.0, default_state_score + 10.0)
        if parsed.estimated_hours >= 8.0:
            # Complex, long tasks need more initial priority
            default_state_score = min(80.0, default_state_score + 15.0)
        
        breakdown = self._pinch.score(pinch_input, state_score=default_state_score, now=now)

        return IngestResult(
            title=parsed.title,
            deadline=parsed.deadline,
            estimated_hours=parsed.estimated_hours,
            interest_tag=parsed.interest_tag,
            sub_blocks=chunk_result.sub_blocks,
            pinch_score=breakdown.total,
        )

    def score_for_bubble(
        self,
        candidates: dict[int, PinchInput],
        state_score: float,
        now: Optional[datetime] = None,
    ) -> list[tuple[int, PinchScoreBreakdown]]:
        """
        Rank candidate task/sub-block IDs against today's real state_score.
        Returns highest-priority first. The caller (BE2's bubble endpoint)
        decides how many bonus_blocks to surface based on Design Rule #1
        (only show bonus blocks when state_score >= 50) that's a display
        policy, not an AI scoring concern, so it stays out of this module.
        """
        now = now or datetime.now()
        return self._pinch.rank(candidates, state_score, now)

    def _llm_challenge_hint(self, parsed: ParsedTask) -> Optional[str]:
        """
        Best-effort LLM difficulty call, used only to set PINCH's
        challenge_hint at ingest time. Falls back to None on any failure,
        letting PinchEngine's own estimate_challenge() heuristic take over
        instead - ingestion never blocks or errors because of this.
        """
        if self._llm_client is None:
            return None
        try:
            enrichment = self._llm_client.enrich_task(
                raw_text=parsed.raw_source_text, deterministic_title=parsed.title
            )
            return enrichment.get("difficulty")
        except NvidiaUnavailableError:
            return None
