"""Service wrapper for calling the LLM reviewer and parsing strict JSON output."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from config.logging import get_logger
from schemas.llm_reviewer import LLMReviewerInput, LLMReviewerOutput
from services.llm_reviewer_prompt import build_llm_reviewer_messages


logger = get_logger(__name__)


def _strip_markdown_fence(text: str) -> str:
    """Remove surrounding ```...``` fences if present."""
    fenced = re.match(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of the first JSON object from raw_text.

    1. Try json.loads(raw_text) directly (after stripping fences).
    2. If that fails, find the first '{' and last '}' and try to load substring.
    3. If parsing still fails, return None.
    """
    cleaned = _strip_markdown_fence(raw_text)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = cleaned[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


class LLMReviewerService:
    """Adapter-agnostic service for running the LLM reviewer."""

    def __init__(self, llm_adapter: Any):
        """
        Args:
            llm_adapter: Any object exposing a `generate_response(prompt: str, context: str = "", ...) -> str`
                         or compatible signature.
        """
        self.llm_adapter = llm_adapter

    async def review(self, payload: LLMReviewerInput) -> Optional[LLMReviewerOutput]:
        """Run the LLM reviewer on the given payload.

        Returns:
            LLMReviewerOutput on success, or None on adapter/JSON/schema failure.
        """
        try:
            messages = build_llm_reviewer_messages(payload)
            system_msg = messages[0]["content"]
            user_msg = messages[1]["content"]
        except Exception as e:
            logger.warning(f"LLMReviewerService: error building prompt messages: {e}")
            return None

        try:
            # Pass system content as context and user content as prompt.
            raw = await self.llm_adapter.generate_response(
                prompt=user_msg,
                context=system_msg,
                max_tokens=800,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"LLMReviewerService: adapter error during review: {e}")
            return None

        data = _extract_json_object(raw)
        if data is None:
            logger.warning("LLMReviewerService: failed to parse JSON from LLM output.")
            return None

        try:
            output = LLMReviewerOutput.model_validate(data)
        except Exception as e:
            logger.warning(f"LLMReviewerService: schema validation error: {e}")
            return None

        return output

