# Ya shapap this is the contract layer. 
#backend teammates and the API route will import these instead of guessing at dict shapes
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SourceType(str, Enum):
    MANUAL = "manual"
    VOICE = "voice"
    HIGHLIGHT = "highlight"
    CALENDAR = "calendar"
    GOOGLE_TASKS = "google_tasks"
    GMAIL = "gmail"


class ParsedTask(BaseModel):
    """
    Output of the NLP ingestion pipeline. Strictly validated — this is the
    JSON Schema boundary mentioned in the README's ingestion pipeline diagram
    ('Strict Pydantic Validation JSON Output').
    """

    title: str = Field(..., min_length=1, max_length=255)
    raw_source_text: str
    source_type: SourceType
    deadline: datetime
    estimated_hours: float = Field(..., gt=0, le=200)
    interest_tag: Optional[str] = Field(default=None, max_length=100)
    ai_sub_tasks: Optional[list[dict]] = Field(default=None)

    # Parsing confidence is not stored in Postgres, but i think it's useful to the
    # service layer (ex. to decide whether to fall back to manual review).
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return v.strip()


class SubBlockPlan(BaseModel):
    """Mirrors the `sub_blocks` table. Produced by the chunking engine."""

    sequence: int = Field(..., ge=1)
    duration_minutes: int = Field(default=120, gt=0, le=480)
    scheduled_date: date
    title: Optional[str] = Field(default=None, max_length=255)


class IngestResult(BaseModel):
    """
    Full payload returned by AIService.ingest(). Matches the
    POST /api/v1/tasks/ingest response shape in the README (minus the
    DB-assigned `id`, which the task service adds after persistence).
    """

    title: str
    deadline: datetime
    estimated_hours: float
    interest_tag: Optional[str]
    sub_blocks: list[SubBlockPlan]
    ai_sub_tasks: Optional[list[dict]] = Field(default=None)
    pinch_score: float = Field(..., ge=0.0, le=100.0)


class PinchInput(BaseModel):
    """Inputs the scoring engine needs to compute a Selection Priority Score."""

    deadline: datetime
    created_at: datetime
    interest_tag: Optional[str]
    user_interest_tags: list[str] = Field(default_factory=list)
    user_passion_tags: list[str] = Field(default_factory=list)  # For distinguishing passion vs interest
    is_novel: bool = False
    challenge_hint: Optional[str] = None 
    estimated_hours: float = Field(default=2.0, gt=0)
    raw_source_text: Optional[str] = None


class StateContext(BaseModel):
    """
    Mirrors the inputs to compute_state_score() in the README, used by the
    chunking/selection layer to decide low-energy vs high-energy behavior.
    """

    startup_delta_mins: int
    mood_score: int = Field(..., ge=1, le=5)
    completion_rate_48h: float = Field(..., ge=0.0, le=1.0)
    early_actions: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Task Segmentation Engine schemas
# ---------------------------------------------------------------------------

class SegmentationInput(BaseModel):
    """
    Raw payload ingested by the Task Segmentation Agent.
    Mirrors the input contract from the system prompt.
    """

    raw_input: str = Field(..., min_length=1)
    current_timestamp: datetime
    deadline_timestamp: Optional[datetime] = None
    user_estimated_duration_minutes: Optional[int] = Field(default=None, gt=0)


class MicroStep(BaseModel):
    """A single hyper-concrete action within a day's plan."""

    step_id: str = Field(..., pattern=r"^step_\d{3}$")
    step_number: int = Field(..., ge=1)
    action_title: str = Field(..., min_length=1, max_length=500)
    estimated_minutes: int = Field(..., ge=5, le=45)
    behavioral_tip: Optional[str] = Field(default=None, max_length=500)


class DayPlan(BaseModel):
    """One day's allocation within the execution plan."""

    day_index: int = Field(..., ge=1)
    is_active_today: bool
    daily_steps: list[MicroStep]


class SegmentationMetadata(BaseModel):
    """Top-level metadata about the segmented task."""

    parsed_title: str = Field(..., min_length=1, max_length=255)
    total_estimated_minutes: int = Field(..., ge=1)
    strategy_applied: str  # "QUICK_WIN" | "LINEAR_MICRO_SPREADING"
    days_to_deadline: Optional[int] = None
    daily_minute_quota: Optional[int] = None
    # False = deterministic fallback was used (LLM unavailable). The UI can
    # surface a subtle "offline fallback mode" hint when this is False.
    llm_enriched: bool = False


class SegmentationOutput(BaseModel):
    """
    Full structured output of the Task Segmentation Agent.
    Matches the exact JSON schema from the system prompt.
    """

    metadata: SegmentationMetadata
    execution_plan: list[DayPlan]
    requires_user_clarification: bool = False
    clarification_prompt: Optional[str] = None
