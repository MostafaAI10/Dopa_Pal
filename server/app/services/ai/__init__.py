"""
AI / NLP service layer for dopaPal.

This package owns:
- Deterministic parsing of raw text/voice input into structured tasks
- Deadline/effort/interest extraction
- Task chunking into sub-blocks (pacing engine input)
- PINCH-based engageability scoring
- A local-LLM (Ollama) extension point for future semantic enrichment

Everything here is deterministic-first by design: regex/dateparser do the
heavy lifting so task creation never depends on an LLM being up, and the
Ollama client is a clean, swappable seam for later upgrades.
"""

from app.services.ai.schemas import ParsedTask, SubBlockPlan, IngestResult
from app.services.ai.service import AIService

__all__ = [
    "ParsedTask",
    "SubBlockPlan",
    "IngestResult",
    "AIService",
]
