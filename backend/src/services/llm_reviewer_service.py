"""Transcript-only LLM evaluator: build prompt, call adapter, parse strict JSON."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from config.logging import get_logger
from schemas.llm_reviewer import LLMReviewerInput, LLMReviewerOutput
from services.llm_reviewer_prompt import build_llm_reviewer_messages


logger = get_logger(__name__)


def _safe_preview(text: str, max_chars: int = 1200) -> str:
    """Return a truncated, minimally sanitized preview for logs."""
    if text is None:
        return ""
    masked = re.sub(r"sk-[A-Za-z0-9_\-]+", "sk-***REDACTED***", str(text))
    if len(masked) <= max_chars:
        return masked
    return f"{masked[:max_chars]}... [truncated {len(masked) - max_chars} chars]"


def _strip_markdown_fence(text: str) -> str:
    """Remove surrounding ```...``` fences if present."""
    fenced = re.match(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _extract_json_object_with_diagnostics(raw_text: str) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Best-effort first JSON object extraction with diagnostics."""
    diagnostics: Dict[str, Any] = {
        "raw_len": len(raw_text or ""),
    }
    cleaned = _strip_markdown_fence(raw_text)
    diagnostics["cleaned_len"] = len(cleaned or "")
    diagnostics["fence_stripped_changed"] = cleaned != (raw_text or "").strip()

    try:
        return json.loads(cleaned), diagnostics
    except Exception as e:
        diagnostics["direct_json_error"] = str(e)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    diagnostics["first_brace_index"] = start
    diagnostics["last_brace_index"] = end
    if start == -1 or end == -1 or end <= start:
        diagnostics["candidate_parse_error"] = "no_valid_brace_window"
        return None, diagnostics

    candidate = cleaned[start : end + 1]
    diagnostics["candidate_len"] = len(candidate)
    try:
        return json.loads(candidate), diagnostics
    except Exception as e:
        diagnostics["candidate_parse_error"] = str(e)
        return None, diagnostics


def extract_llm_json_dict(raw_text: str) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Parse a best-effort JSON object from raw LLM text (shared by v1 reviewer and hybrid v2)."""
    return _extract_json_object_with_diagnostics(raw_text)


# Shared with hybrid v2 orchestrator for log previews.
safe_preview_llm_raw = _safe_preview


class LLMReviewerService:
    """Adapter-agnostic transcript-only LLM evaluator."""

    def __init__(self, llm_adapter: Any):
        """
        Args:
            llm_adapter: Object exposing
                ``async generate_response(prompt: str, context: str = "", **kwargs) -> str``
        """
        self.llm_adapter = llm_adapter

    async def review(self, payload: LLMReviewerInput) -> Optional[LLMReviewerOutput]:
        """Run the evaluator; returns ``LLMReviewerOutput`` or ``None`` on failure."""
        try:
            messages = build_llm_reviewer_messages(payload)
            system_msg = messages[0]["content"]
            user_msg = messages[1]["content"]
        except Exception as e:
            logger.warning(f"LLMReviewerService: error building prompt messages: {e}")
            return None

        try:
            # ~2.8k tokens: comfortably fits the fixed JSON schema + typical list lengths for
            # missed_opportunities/spikes_annotations without the slack of 4k (reduces runaway verbosity risk).
            raw = await self.llm_adapter.generate_response(
                prompt=user_msg,
                context=system_msg,
                max_tokens=2800,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning(f"LLMReviewerService: adapter error during review: {e}")
            return None

        data, parse_diag = _extract_json_object_with_diagnostics(raw)
        if data is None:
            logger.warning(
                "LLMReviewerService: failed to parse JSON from LLM output. "
                f"parse_diag={parse_diag} "
                f"raw_preview={_safe_preview(raw)} "
                f"cleaned_preview={_safe_preview(_strip_markdown_fence(raw))}"
            )
            return None

        try:
            output = LLMReviewerOutput.model_validate(data)
        except Exception as e:
            logger.warning(
                "LLMReviewerService: schema validation error. "
                f"error={e} "
                f"top_level_keys={list(data.keys()) if isinstance(data, dict) else 'non-dict'} "
                f"raw_preview={_safe_preview(raw)} "
                f"cleaned_preview={_safe_preview(_strip_markdown_fence(raw))}"
            )
            return None

        return output
