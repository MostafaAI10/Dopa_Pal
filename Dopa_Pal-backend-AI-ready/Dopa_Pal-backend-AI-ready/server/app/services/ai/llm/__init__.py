"""
Local LLM integration layer (Ollama).

Everything in the rest of the AI module works without this — see the
deterministic parsers in services/ai/parsers/. This package exists purely
as a clean seam for optional semantic enrichment (e.g. better title
sanitization, smarter interest tagging, real difficulty assessment instead
of the keyword heuristic) without touching ingestion.py, chunking.py, or
pinch.py's public contracts.
"""

from app.services.ai.llm.ollama_client import OllamaClient, OllamaConfig, OllamaUnavailableError

__all__ = ["OllamaClient", "OllamaConfig", "OllamaUnavailableError"]
