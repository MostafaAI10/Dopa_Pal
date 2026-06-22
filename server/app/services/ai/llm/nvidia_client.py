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

    def chat(self, messages: list[dict[str, str]], system_prompt: str) -> str:
        """
        Send a conversation to the LLM and return the assistant's reply.
        """
        if not self._client:
            raise NvidiaUnavailableError("No API key provided for Nvidia API")
            
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=full_messages,
                temperature=0.7,
                top_p=0.95,
                max_tokens=4096,
                stream=False
            )
            return completion.choices[0].message.content
        except APIError as exc:
            raise NvidiaUnavailableError(f"Nvidia API request failed: {exc}") from exc

    def _build_prompt(self, raw_text: str, deterministic_title: str) -> str:
        return (
            "You analyze task descriptions for an ADHD productivity app and intelligently chunk them. "
            "Respond ONLY with JSON, no prose, matching exactly this shape: "
            '{"refined_title": string or null, "difficulty": "low"|"medium"|"high" or null, '
            '"difficulty_reason": string or null, "estimated_hours": number or null, '
            '"interest_tag": string or null, '
            '"ai_sub_tasks": [{"title": string, "duration_minutes": number}] or null}\n\n'
            "CRITICAL RULES FOR ai_sub_tasks AND refined_title:\n"
            "1. You MUST divide the large task into smaller subtasks, each with its own specific title/name.\n"
            "2. Subtasks MUST be clear instructions/actionable steps so that executing them sequentially guarantees completion of the overall task.\n"
            "3. Each sub-task MUST have a 'duration_minutes' strictly between 15 and 45 minutes. Never exceed 45 minutes.\n"
            "4. The sum of all 'duration_minutes' in the array MUST equal 'estimated_hours' * 60.\n"
            "5. Base the percentages (chunk sizes) on the difficulty of each part. Give complex parts shorter bursts (e.g. 25 mins) and easier parts longer flows (e.g. 40-45 mins).\n"
            "6. The 'refined_title' MUST be a clear, concise title that clarifies the task itself, and MUST NOT be the raw text given to it.\n\n"
            f"Deterministically-parsed title (for reference, may already be good): {deterministic_title!r}\n"
            f"Original task text: {raw_text!r}\n"
        )

    def _validate_enrichment(self, parsed: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {"refined_title", "difficulty", "difficulty_reason", "estimated_hours", "interest_tag", "ai_sub_tasks"}
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

        # Validate ai_sub_tasks if present
        if "ai_sub_tasks" in cleaned:
            sub_tasks = cleaned["ai_sub_tasks"]
            if not isinstance(sub_tasks, list):
                cleaned.pop("ai_sub_tasks")
            else:
                valid_tasks = []
                for st in sub_tasks:
                    if isinstance(st, dict) and "title" in st and "duration_minutes" in st:
                        t = str(st["title"]).strip()
                        try:
                            d = int(st["duration_minutes"])
                            if 15 <= d <= 45 and t:
                                valid_tasks.append({"title": t[:255], "duration_minutes": d})
                        except (ValueError, TypeError):
                            pass
                if valid_tasks:
                    cleaned["ai_sub_tasks"] = valid_tasks
                else:
                    cleaned.pop("ai_sub_tasks")

        return cleaned

    # ── Task Segmentation micro-step generation ──────────────────────

    def generate_micro_steps(
        self,
        raw_text: str,
        parsed_title: str,
        total_minutes: int,
        days_to_deadline: int | None,
    ) -> list[dict[str, Any]]:
        """
        Ask the model to produce hyper-concrete micro-steps for the
        Task Segmentation Engine.  Each step must use concrete action
        verbs and include a behavioral tip.

        Returns a list of dicts with keys:
            action_title, estimated_minutes, behavioral_tip, day_index

        Raises NvidiaUnavailableError on any failure — the segmentation
        engine has a full deterministic fallback so this is safe.
        """
        if not self._client:
            raise NvidiaUnavailableError("No API key provided for Nvidia API")

        prompt = self._build_segmentation_prompt(
            raw_text, parsed_title, total_minutes, days_to_deadline,
        )

        try:
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

            raw_output = completion.choices[0].message.content

            # Strip markdown code fences
            if raw_output.startswith("```json"):
                raw_output = raw_output.replace("```json", "", 1)
            if raw_output.startswith("```"):
                raw_output = raw_output.replace("```", "", 1)
            if raw_output.endswith("```"):
                raw_output = raw_output.rsplit("```", 1)[0]

            raw_output = raw_output.strip()
            parsed = json.loads(raw_output)
        except APIError as exc:
            raise NvidiaUnavailableError(f"Nvidia API request failed: {exc}") from exc
        except (json.JSONDecodeError, AttributeError, KeyError, IndexError) as exc:
            raise NvidiaUnavailableError(
                f"Nvidia returned unparseable segmentation output: {exc}"
            ) from exc

        return self._validate_micro_steps(parsed, total_minutes, days_to_deadline)

    def _build_segmentation_prompt(
        self,
        raw_text: str,
        parsed_title: str,
        total_minutes: int,
        days_to_deadline: int | None,
    ) -> str:
        days_str = str(days_to_deadline) if days_to_deadline else "1 (no deadline given, treat as today)"
        return (
            "You are the Task Segmentation Agent for dopaPal, an ADHD productivity app. "
            "Your job is to break a task into hyper-concrete, non-intimidating micro-steps. "
            "Respond ONLY with a JSON array, no prose.\n\n"
            "CRITICAL COPYWRITING RULES:\n"
            "1. NEVER use vague verbs: 'Work on', 'Plan', 'Research', 'Fix', 'Study', 'Handle'.\n"
            "2. USE single-focus verbs: 'Open', 'Write', 'Draft', 'Compile', 'List', 'Delete', 'Copy', 'Create', 'Type', 'Paste'.\n"
            "3. ISOLATE friction transitions: separate writing from testing, reading from implementing.\n"
            "4. Each step must be 10-45 minutes.\n"
            "5. The sum of all estimated_minutes MUST equal " + str(total_minutes) + ".\n"
            "6. Distribute steps across " + days_str + " day(s) using day_index (1-based).\n"
            "7. Day 1 MUST have the lowest-friction, physical actions (setup, file creation, tool config).\n"
            "8. Each behavioral_tip should be warm, ADHD-friendly, and reduce cognitive dread.\n\n"
            "JSON shape: [{\"action_title\": string, \"estimated_minutes\": int, "
            "\"behavioral_tip\": string, \"day_index\": int}]\n\n"
            f"Task title: {parsed_title!r}\n"
            f"Total effort: {total_minutes} minutes across {days_str} day(s)\n"
            f"Original task text: {raw_text[:2000]!r}\n"
        )

    def _validate_micro_steps(
        self,
        parsed: Any,
        total_minutes: int,
        days_to_deadline: int | None,
    ) -> list[dict[str, Any]]:
        """Validate and sanitise LLM micro-step output."""
        if not isinstance(parsed, list):
            raise NvidiaUnavailableError("Expected a JSON array of micro-steps")

        validated: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            title = str(item.get("action_title", "")).strip()
            if not title:
                continue

            try:
                minutes = int(item.get("estimated_minutes", 25))
            except (ValueError, TypeError):
                minutes = 25
            minutes = max(10, min(45, minutes))

            tip = item.get("behavioral_tip")
            if tip:
                tip = str(tip).strip()[:500] or None

            day_idx = item.get("day_index", 1)
            try:
                day_idx = int(day_idx)
            except (ValueError, TypeError):
                day_idx = 1

            validated.append({
                "action_title": title[:500],
                "estimated_minutes": minutes,
                "behavioral_tip": tip,
                "day_index": max(1, day_idx),
            })

        if not validated:
            raise NvidiaUnavailableError("LLM produced zero valid micro-steps")

        return validated
