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
    pinch_score: float = Field(..., ge=0.0, le=100.0)


class PinchInput(BaseModel):
    """Inputs the scoring engine needs to compute a Selection Priority Score."""

    deadline: datetime
    created_at: datetime
    interest_tag: Optional[str]
    user_interest_tags: list[str] = Field(default_factory=list)
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
