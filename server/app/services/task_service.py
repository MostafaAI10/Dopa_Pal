"""
Task persistence and scheduling service.

All NLP parsing, chunking, and scoring logic is delegated to the AI module
(``app.services.ai``).  This service owns **only** DB persistence and
schedule reflow — the boundary is intentional so that the AI module stays
pure (no SQLAlchemy dependency) and can be tested/iterated independently.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.state import StateLog
from app.models.task import Task, SubBlock
from app.services.ai.llm.nvidia_client import NvidiaConfig
from app.services.ai.schemas import IngestResult, PinchInput, SourceType
from app.services.ai.service import AIService, IngestOptions
from app.services.duration_parser import parse_duration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level AI service singleton — initialised once, reused across requests
# ---------------------------------------------------------------------------

def _build_ai_service() -> AIService:
    """Construct the AIService with settings from the app config."""
    nvidia_cfg = NvidiaConfig(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        model=settings.NVIDIA_MODEL,
    )
    options = IngestOptions(
        use_llm=settings.AI_USE_LLM,
        block_minutes=120,
    )
    return AIService(options=options, nvidia_config=nvidia_cfg)


_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    """Lazy singleton so the config is read after app startup."""
    global _ai_service
    if _ai_service is None:
        _ai_service = _build_ai_service()
    return _ai_service


# ---------------------------------------------------------------------------
# Ingestion: raw text → AI parsing → DB persistence
# ---------------------------------------------------------------------------

def ingest_from_raw_text(
    db: Session,
    user_id: int,
    raw_text: str,
    source_type: str,
    interest_tag_override: str | None = None,
) -> Task:
    """
    Full NLP-powered ingestion: parse raw text through the AI pipeline,
    then persist the resulting task and sub-blocks to the database.

    If ``interest_tag_override`` is provided it replaces whatever tag the
    AI pipeline extracted (used by Google sync to honour user-configured tags).
    """
    ai = get_ai_service()
    ingest_result = ai.ingest(raw_text=raw_text, source_type=source_type)
    if interest_tag_override:
        ingest_result.interest_tag = interest_tag_override
    return persist_ingested_task(
        db=db,
        user_id=user_id,
        ingest_result=ingest_result,
        raw_source_text=raw_text,
        source_type=source_type,
    )


def persist_ingested_task(
    db: Session,
    user_id: int,
    ingest_result: IngestResult,
    raw_source_text: Optional[str],
    source_type: str,
) -> Task:
    """
    Persist an ``IngestResult`` (produced by ``AIService.ingest()``) into
    the ``tasks`` and ``sub_blocks`` tables.  This is the single point
    where AI output meets the database.
    """
    task = Task(
        user_id=user_id,
        title=ingest_result.title,
        raw_source_text=raw_source_text,
        source_type=source_type,
        deadline=ingest_result.deadline,
        estimated_hours=ingest_result.estimated_hours,
        interest_tag=ingest_result.interest_tag,
        status="pending",
        pinch_score=ingest_result.pinch_score,
    )
    db.add(task)
    db.flush()  # get task.id before inserting sub_blocks

    for plan in ingest_result.sub_blocks:
        sub_block = SubBlock(
            task_id=task.id,
            sequence=plan.sequence,
            title=plan.title,
            duration_minutes=plan.duration_minutes,
            scheduled_date=plan.scheduled_date,
            status="pending",
        )
        db.add(sub_block)

    db.commit()
    db.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Manual task creation (structured input, no NLP parsing needed)
# ---------------------------------------------------------------------------

def create_manual_task(
    db: Session,
    user_id: int,
    title: str,
    deadline: datetime,
    estimated_hours: float,
    interest_tag: Optional[str] = None,
    source_type: str = "manual",
) -> Task:
    """
    Create a task from structured input (e.g. the manual creation form).
    Still uses the AI module for chunking and PINCH scoring, but skips
    the NLP parsing step since the fields are already provided.
    """
    ai = get_ai_service()

    # Build a synthetic raw text for consistent PINCH scoring
    synthetic_text = f"{title}, deadline {deadline.isoformat()}, about {estimated_hours} hours"

    ingest_result = IngestResult(
        title=title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        interest_tag=interest_tag,
        sub_blocks=[],
        pinch_score=0.0,
    )

    # Use the chunking engine directly via a full ingest call
    full_result = ai.ingest(
        raw_text=synthetic_text,
        source_type=source_type,
    )

    # Override with the user-provided structured values, but use the AI-refined title if available
    ingest_result = IngestResult(
        title=full_result.title if full_result.title else title,
        deadline=deadline,
        estimated_hours=estimated_hours,
        interest_tag=interest_tag,
        sub_blocks=full_result.sub_blocks,
        pinch_score=full_result.pinch_score,
    )

    return persist_ingested_task(
        db=db,
        user_id=user_id,
        ingest_result=ingest_result,
        raw_source_text=None,
        source_type=source_type,
    )


# ---------------------------------------------------------------------------
# Bubble endpoint support: ranked pending blocks via PINCH
# ---------------------------------------------------------------------------

def get_ranked_pending_blocks(
    db: Session,
    user_id: int,
    state_score: float,
) -> List[Tuple[SubBlock, float]]:
    """
    Fetch all pending sub-blocks for a user, score them using the AI module's
    PINCH engine, and return them ranked highest-priority-first.

    This is the function backing ``GET /api/v1/bubble/next``.
    """
    # Fetch pending sub-blocks with their parent tasks eagerly loaded
    raw_pending_blocks = (
        db.query(SubBlock)
        .join(Task)
        .filter(
            Task.user_id == user_id,
            Task.status == "pending",
            SubBlock.status == "pending",
        )
        .order_by(SubBlock.task_id, SubBlock.sequence)
        .all()
    )

    if not raw_pending_blocks:
        return []

    # Enforce strict sequence: only surface the FIRST pending step per task
    pending_blocks = []
    seen_tasks = set()
    for block in raw_pending_blocks:
        if block.task_id not in seen_tasks:
            pending_blocks.append(block)
            seen_tasks.add(block.task_id)

    ai = get_ai_service()
    now = datetime.now()

    # Build PinchInput for each sub-block's parent task
    candidates: dict[int, PinchInput] = {}
    block_map: dict[int, SubBlock] = {}

    for block in pending_blocks:
        task = block.task
        # Use the sub_block id as key to rank individual blocks
        block_map[block.id] = block

        # Determine created_at — use task.created_at if available, else now
        created_at = task.created_at if task.created_at else now

        candidates[block.id] = PinchInput(
            deadline=task.deadline,
            created_at=created_at,
            interest_tag=task.interest_tag,
            user_interest_tags=[],  # TODO: load from user profile when implemented
            user_passion_tags=[],   # TODO: load from user profile when implemented
            is_novel=False,
            challenge_hint=None,
            estimated_hours=task.estimated_hours,
            raw_source_text=task.raw_source_text,
        )

    # Score and rank
    ranked = ai.score_for_bubble(
        candidates=candidates,
        state_score=state_score,
        now=now,
    )

    # Map back to (SubBlock, score) pairs
    result: List[Tuple[SubBlock, float]] = []
    for block_id, breakdown in ranked:
        if block_id in block_map:
            result.append((block_map[block_id], breakdown.total))

    return result


# ---------------------------------------------------------------------------
# Schedule reflow (kept from original — this is a DB-level concern)
# ---------------------------------------------------------------------------

def recalculate_schedule(db: Session, user_id: int, start_date: date) -> None:
    """
    Reflow remaining sub-blocks for skipped or missed days without shame triggers.
    Spreads pending subblocks of active tasks starting from start_date.
    """
    # Fetch all tasks of the user that are still pending
    active_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.status == "pending"
    ).all()
    
    for task in active_tasks:
        # Fetch remaining pending subblocks for this task
        pending_blocks = db.query(SubBlock).filter(
            SubBlock.task_id == task.id,
            SubBlock.status == "pending",
            SubBlock.scheduled_date >= start_date
        ).order_by(SubBlock.sequence).all()
        
        if not pending_blocks:
            continue
            
        deadline_date = task.deadline.date()
        total_days_remaining = (deadline_date - start_date).days
        
        if total_days_remaining <= 1:
            # Shift everything to start_date
            for block in pending_blocks:
                block.scheduled_date = start_date
        else:
            interval = max(1, total_days_remaining // len(pending_blocks))
            for idx, block in enumerate(pending_blocks):
                offset_days = min(idx * interval, total_days_remaining - 1)
                block.scheduled_date = start_date + timedelta(days=offset_days)
                
    db.commit()
