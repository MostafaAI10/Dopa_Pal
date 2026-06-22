#This is the orchestrator it takes raw text & source type, runs it through the four parsers, 
#and produces one validated ParsedTask.

from __future__ import annotations

from datetime import datetime
import logging
from typing import Optional

from app.services.ai.llm.nvidia_client import NvidiaClient, NvidiaUnavailableError
from app.services.ai.parsers.challenge_estimator import estimate_challenge
from app.services.ai.parsers.date_parser import parse_deadline, default_deadline
from app.services.ai.parsers.effort_parser import parse_effort
from app.services.ai.parsers.interest_tagger import tag_interest
from app.services.ai.parsers.title_sanitizer import sanitize_title
from app.services.ai.schemas import ParsedTask, SourceType

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.35


class IngestionPipeline:
    """
    Deterministic-first NLP ingestion pipeline, with optional LLM enrichment.

    Matches the README diagram:
        Raw Text Input -> Rule-Based Date & Duration Parsers ->
        Enriched Context Framework -> Deterministic Task Title & Effort
        Refinement -> Strict Pydantic Validation JSON Output

    The deterministic path ALWAYS runs and ALWAYS produces a valid
    ParsedTask on its own. The Ollama enrichment step, if enabled, can only
    ever *refine* title/challenge_hint on top of that - it can never block,
    delay past its timeout, or cause ingestion to fail. This is the
    contract the rest of the system (and your demo) depends on.
    """

    def __init__(
        self,
        reference_time: datetime | None = None,
        llm_client: Optional[NvidiaClient] = None,
        use_llm: bool = False,
    ):
        self._reference_time = reference_time
        self._llm_client = llm_client or (NvidiaClient(config=None) if use_llm else None)  # Note: config is required, but usually passed via service.py
        self._use_llm = use_llm

    def parse(self, raw_text: str, source_type: SourceType | str) -> ParsedTask:
        if not raw_text or not raw_text.strip():
            raise ValueError("raw_text must be non-empty")

        if isinstance(source_type, str):
            source_type = SourceType(source_type)

        reference = self._reference_time or datetime.now()

        date_result = parse_deadline(raw_text, reference=reference)
        effort_result = parse_effort(raw_text)
        interest_result = tag_interest(raw_text)
        title = sanitize_title(raw_text)
        challenge = estimate_challenge(raw_text)

        deadline = date_result.deadline or default_deadline(reference)

        combined_confidence = round(
            (date_result.confidence * 0.45)
            + (effort_result.confidence * 0.40)
            + (interest_result.confidence * 0.15),
            3,
        )

        if combined_confidence < LOW_CONFIDENCE_THRESHOLD:
            logger.info(
                "Low-confidence ingestion (score=%.2f) for source_type=%s: %r",
                combined_confidence, source_type.value, raw_text[:120],
            )

        parsed = ParsedTask(
            title=title,
            raw_source_text=raw_text,
            source_type=source_type,
            deadline=deadline,
            estimated_hours=effort_result.estimated_hours,
            interest_tag=interest_result.tag,
            confidence=combined_confidence,
        )

        # Enhanced LLM integration for more comprehensive parsing
        if self._use_llm and self._llm_client is not None:
            parsed = self._try_enrich(parsed, title, challenge.hint)

        return parsed

    def _try_enrich(self, parsed: ParsedTask, deterministic_title: str, challenge_hint: str) -> ParsedTask:
        """
        Best-effort LLM pass. Any failure (timeout, Ollama down, bad JSON)
        is caught and logged — the deterministic ParsedTask is returned
        unchanged. Never let an LLM hiccup break task capture.
        """
        if self._llm_client is None:
            return parsed

        try:
            enrichment = self._llm_client.enrich_task(
                raw_text=parsed.raw_source_text, deterministic_title=deterministic_title
            )
        except NvidiaUnavailableError as exc:
            logger.warning("Nvidia enrichment skipped (unavailable): %s", exc)
            return parsed

        updates: dict = {}

        refined_title = enrichment.get("refined_title")
        if refined_title and isinstance(refined_title, str) and refined_title.strip():
            updates["title"] = refined_title.strip()[:255]

    
        difficulty = enrichment.get("difficulty")
        if difficulty:
            logger.info("LLM difficulty assessment for %r: %s (deterministic: %s)",
                         parsed.title[:60], difficulty, challenge_hint)

        # Refine estimated_hours with LLM's better understanding of context
        estimated_hours = enrichment.get("estimated_hours")
        if estimated_hours and isinstance(estimated_hours, (int, float)) and estimated_hours > 0:
            # Validate reasonable range (0.25 to 200 hours)
            if 0.25 <= estimated_hours <= 200:
                updates["estimated_hours"] = round(float(estimated_hours), 2)
                logger.info("LLM refined estimated_hours for %r: %.2f (deterministic: %.2f)",
                           parsed.title[:60], updates["estimated_hours"], parsed.estimated_hours)

        # Refine interest_tag with LLM's semantic understanding
        interest_tag = enrichment.get("interest_tag")
        if interest_tag and isinstance(interest_tag, str) and interest_tag.strip():
            # Validate reasonable length
            if 1 <= len(interest_tag.strip()) <= 100:
                updates["interest_tag"] = interest_tag.strip()[:100]
                logger.info("LLM refined interest_tag for %r: %s (deterministic: %s)",
                           parsed.title[:60], updates["interest_tag"], parsed.interest_tag or "None")

        # Pass along the AI chunked sub tasks
        ai_sub_tasks = enrichment.get("ai_sub_tasks")
        if ai_sub_tasks:
            updates["ai_sub_tasks"] = ai_sub_tasks
            logger.info("LLM provided %d custom sub tasks for %r", len(ai_sub_tasks), parsed.title[:60])

        if updates:
            parsed = parsed.model_copy(update=updates)

        return parsed
