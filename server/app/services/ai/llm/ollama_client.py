from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"
DEFAULT_TIMEOUT_SECONDS = 8.0


class OllamaUnavailableError(Exception):
    """Raised when Ollama can't be reached or returns an unusable response.

    Callers MUST catch this and fall back to deterministic parsing,
    the AI module's core promise is that task capture
    never breaks just because a local model isn't running.
    """


@dataclass
class OllamaConfig:
    base_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/generate endpoint, scoped to exactly
    what this module needs: structured JSON enrichment of an already-parsed
    task, never raw task creation. The deterministic pipeline stays the
    source of truth for title/deadline/effort; this client only ever
    *adds* optional semantic signal on top.
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        self._config = config or OllamaConfig()

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self._config.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def enrich_task(self, raw_text: str, deterministic_title: str) -> dict[str, Any]:
        """
        Ask the local model for optional refinements: a cleaner title and
        a difficulty assessment with a one-line rationale. Returns a dict
        with only the keys the model actually produced, callers should
        treat every key as optional and fall back to deterministic values
        for anything missing.

        Raises OllamaUnavailableError on any failure, by design, never
        returns a partially-broken/garbage result silently.
        """
        prompt = self._build_prompt(raw_text, deterministic_title)

        try:
            with httpx.Client(timeout=self._config.timeout_seconds) as client:
                resp = client.post(
                    f"{self._config.base_url}/api/generate",
                    json={
                        "model": self._config.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(f"Ollama request failed: {exc}") from exc

        try:
            body = resp.json()
            raw_model_output = body.get("response", "")
            parsed = json.loads(raw_model_output)
        except (json.JSONDecodeError, AttributeError, KeyError) as exc:
            raise OllamaUnavailableError(
                f"Ollama returned unparseable output: {exc}"
            ) from exc

        return self._validate_enrichment(parsed)

    def _build_prompt(self, raw_text: str, deterministic_title: str) -> str:
        return (
            "You refine task descriptions for an ADHD productivity app. "
            "Respond ONLY with JSON, no prose, matching exactly this shape: "
            '{"refined_title": string or null, "difficulty": "low"|"medium"|"high" or null, '
            '"difficulty_reason": string or null, "estimated_hours": number or null, '
            '"interest_tag": string or null}\n\n'
            f"Deterministically-parsed title (for reference, may already be good): {deterministic_title!r}\n"
            f"Original task text: {raw_text!r}\n"
            f"Deterministic estimated_hours: {deterministic_title!r}\n"
        )

    def _validate_enrichment(self, parsed: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {"refined_title", "difficulty", "difficulty_reason", "estimated_hours", "interest_tag"}
        cleaned = {k: v for k, v in parsed.items() if k in allowed_keys}

        if "difficulty" in cleaned and cleaned["difficulty"] not in {"low", "medium", "high", None}:
            cleaned.pop("difficulty")

        # Validate estimated_hours if present
        if "estimated_hours" in cleaned:
            try:
                val = float(cleaned["estimated_hours"])
                if not (0.25 <= val <= 200):
                    cleaned.pop("estimated_hours")
                else:
                    cleaned["estimated_hours"] = val
            except (ValueError, TypeError):
                cleaned.pop("estimated_hours")

        # Validate interest_tag if present
        if "interest_tag" in cleaned:
            val = str(cleaned["interest_tag"]).strip()
            if not val or len(val) > 100:
                cleaned.pop("interest_tag")
            else:
                cleaned["interest_tag"] = val

        return cleaned
