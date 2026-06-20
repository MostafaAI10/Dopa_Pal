from __future__ import annotations

from dataclasses import dataclass

# Starter taxonomy. This directly feeds two features from the README:
# 1. PINCH's "Interest" signal (tasks tagged by curiosity-driven domains)
# 2. The Interest Vault (curated facts/resources matched to these same tags)

INTEREST_KEYWORDS: dict[str, list[str]] = {
    "architecture": ["specification", "schema", "system design", "blueprint", "diagram"],
    "cybersecurity": ["security", "encryption", "firewall", "vulnerability", "pentest", "network"],
    "programming": ["code", "refactor", "bug", "function", "api", "backend", "frontend"],
    "writing": ["essay", "report", "document", "draft", "article", "summary"],
    "language_learning": ["german", "vocabulary", "grammar", "translation", "language"],
    "ai_ml": ["model", "training", "dataset", "neural", "llm", "nlp", "machine learning"],
    "design": ["ui", "ux", "mockup", "wireframe", "figma", "layout"],
    "research": ["research", "paper", "literature review", "study", "analysis"],
}

DEFAULT_TAG = None


@dataclass
class InterestTagResult:
    tag: str | None
    confidence: float


def tag_interest(text: str) -> InterestTagResult:
    """
    Keyword-match free text against the interest taxonomy.

    Picks the tag with the most keyword hits. Ties are broken by
    dict insertion order (first match wins), which is fine for a
    deterministic v1 - an LLM pass can refine this later via the
    Ollama extension point without changing this function's contract.
    """
    lowered = text.lower()
    best_tag = DEFAULT_TAG
    best_hits = 0

    for tag, keywords in INTEREST_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lowered)
        if hits > best_hits:
            best_hits = hits
            best_tag = tag

    if best_hits == 0:
        return InterestTagResult(tag=None, confidence=0.0)

    confidence = min(0.4 + 0.2 * best_hits, 0.95)
    return InterestTagResult(tag=best_tag, confidence=confidence)
