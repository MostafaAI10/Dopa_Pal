from __future__ import annotations

import re

# Strips the leading filler/intent phrases users naturally speak or type.
_LEADING_FILLER_RE = re.compile(
    r"^(i\s+)?(need|have|want|got|gotta)\s+to\s+", re.IGNORECASE
)

# Trailing clauses that belong to deadline/effort parsing, not the title.
_TRAILING_CLAUSE_RE = re.compile(
    r"\s*(,?\s*(by|due|before|until)\s+.+)$", re.IGNORECASE
)
_TRAILING_EFFORT_RE = re.compile(
    r"\s*(,?\s*(should|will|it)?\s*take\s+about\s+.+)$", re.IGNORECASE
)

_MAX_TITLE_LENGTH = 255


def sanitize_title(raw_text: str) -> str:
    """
    Produce a clean, capitalized task title from raw captured text.

    This intentionally does Not try to be clever about summarizing long
    paragraphs  that's a job for the (optional, future) LLM enrichment
    step. Here we just strip filler and trailing date/effort clauses so
    the deterministic title stays accurate to what the user wrote.
    """
    text = raw_text.strip()
    text = _LEADING_FILLER_RE.sub("", text)
    text = _TRAILING_CLAUSE_RE.sub("", text)
    text = _TRAILING_EFFORT_RE.sub("", text)
    text = text.strip().rstrip(".,;:")

    if not text:
        text = raw_text.strip()[:_MAX_TITLE_LENGTH] or "Untitled task"

    # Capitalize first letter only - don't title-case the whole thing,
    # that mangles acronyms like "API" or "NLP".
    if text:
        text = text[0].upper() + text[1:]

    return text[:_MAX_TITLE_LENGTH]
