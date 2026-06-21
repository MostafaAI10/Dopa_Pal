from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from openai import OpenAI, APIError

logger = logging.getLogger(__name__)

DEFAULT_NVIDIA_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_TIMEOUT_SECONDS = 15.0


class NvidiaUnavailableError(Exception):
    """Raised when Nvidia API can't be reached or returns an unusable response.

    Callers MUST catch this and fall back to deterministic parsing,
    the AI module's core promise is that task capture
    never breaks just because the model isn't reachable.
    """


@dataclass
class NvidiaConfig:
    api_key: str
    base_url: str = DEFAULT_NVIDIA_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


class NvidiaClient:
    """
    Thin wrapper around Nvidia's OpenAI-compatible API, scoped to exactly
    what this module needs: structured JSON enrichment of an already-parsed
    task, never raw task creation. The deterministic pipeline stays the
    source of truth for title/deadline/effort; this client only ever
    *adds* optional semantic signal on top.
    """

    def __init__(self, config: Optional[NvidiaConfig] = None):
        self._config = config or NvidiaConfig(api_key="")
        self._client = None
        if self._config.api_key:
            self._client = OpenAI(
                base_url=self._config.base_url,
                api_key=self._config.api_key,
                timeout=self._config.timeout_seconds,
            )

    def is_available(self) -> bool:
        # We can't really "ping" the Nvidia API without cost, but we can assume
        # it's available if an API key is provided, or do a cheap models request.
        if not self._client:
            return False
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def enrich_task(self, raw_text: str, deterministic_title: str) -> dict[str, Any]:
        """
        Ask the model for optional refinements: a cleaner title and
        a difficulty assessment with a one-line rationale. Returns a dict
        with only the keys the model actually produced, callers should
        treat every key as optional and fall back to deterministic values
        for anything missing.

        Raises NvidiaUnavailableError on any failure, by design, never
        returns a partially-broken/garbage result silently.
        """
        if not self._client:
            raise NvidiaUnavailableError("No API key provided for Nvidia API")
            
        prompt = self._build_prompt(raw_text, deterministic_title)

        try:
            # According to Nvidia Nemotron specs requested:
            # temperature=1, top_p=0.95, extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384}
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                top_p=0.95,
                max_tokens=16384,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": True},
                    "reasoning_budget": 16384
                },
                stream=False
            )
            
            raw_model_output = completion.choices[0].message.content
            
            # The model might output markdown code blocks (e.g., ```json ... ```)
            # We strip them for robust JSON parsing.
            if raw_model_output.startswith("```json"):
                raw_model_output = raw_model_output.replace("```json", "", 1)
            if raw_model_output.startswith("```"):
                raw_model_output = raw_model_output.replace("```", "", 1)
            if raw_model_output.endswith("```"):
                raw_model_output = raw_model_output.rsplit("```", 1)[0]
                
            raw_model_output = raw_model_output.strip()

            parsed = json.loads(raw_model_output)
        except APIError as exc:
            raise NvidiaUnavailableError(f"Nvidia API request failed: {exc}") from exc
        except (json.JSONDecodeError, AttributeError, KeyError, IndexError) as exc:
            raise NvidiaUnavailableError(
                f"Nvidia returned unparseable output: {exc}"
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
