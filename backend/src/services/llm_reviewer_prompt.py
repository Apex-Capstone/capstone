"""Prompt builder for the LLM reviewer.

This module converts a structured `LLMReviewerInput` payload into a pair of
chat messages (system + user) suitable for a STRICT JSON-only reviewer call.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from schemas.llm_reviewer import LLMReviewerInput


def _build_output_schema_instructions() -> str:
    """Describe the expected JSON output schema matching `LLMReviewerOutput`."""
    # This description is intentionally compact but explicit, to constrain the model.
    return """
You MUST return a single JSON object with this exact shape:

{
  "reviewer_version": "v1",
  "reviewed_events": [
    {
      "target_id": "<string>",
      "acknowledged_emotion": <boolean>,
      "validated_feeling": <boolean>,
      "missed_opportunity": <boolean>,
      "empathy_quality_score_0_to_4": <integer 0-4>,
      "disposition": "confirm" | "upgrade" | "downgrade" | "uncertain",
      "confidence": <float 0-1>,
      "rationale": "<string>",
      "suggested_response": "<string or null>"
    },
    ...
  ],
  "session_assessment": {
    "empathy_quality_score_0_to_4": <integer 0-4>,
    "clarity_quality_score_0_to_4": <integer 0-4>,
    "supportiveness_quality_score_0_to_4": <integer 0-4>,
    "confidence": <float 0-1>,
    "rationale": "<string>",
    "strengths": ["<string>", ...],
    "improvement_points": ["<string>", ...]
  },
  "overall_confidence": <float 0-1>,
  "notes": "<string or null>"
}

Do NOT add or remove top-level keys. Do NOT change key names or value types.
""".strip()


def _serialize_payload(payload: LLMReviewerInput) -> str:
    """Serialize payload to JSON for inclusion in the user message."""
    data = payload.model_dump(mode="python")
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_llm_reviewer_messages(payload: LLMReviewerInput) -> List[Dict[str, str]]:
    """Build system + user messages for the LLM reviewer.

    Returns:
        A list of exactly two messages:
        - messages[0]: {"role": "system", "content": ...}
        - messages[1]: {"role": "user", "content": ...}
    """
    system_content = (
        "You are reviewing a clinician's communication in a medical training conversation. "
        "You are NOT generating patient dialogue or acting as the patient. "
        "You MUST review the provided rule-based evidence and transcript only. "
        "You MUST return STRICT JSON ONLY that matches the specified output schema. "
        "Do not invent transcript content that is not present in the input. "
        "Focus your review on:\n"
        "1) whether clinician responses acknowledged emotion,\n"
        "2) whether feelings were validated,\n"
        "3) whether flagged missed opportunities were truly missed,\n"
        "4) session-level empathy, clarity, and supportiveness quality."
    )

    schema_instructions = _build_output_schema_instructions()
    payload_json = _serialize_payload(payload)

    user_content = (
        "You are given structured rule-based annotations for a single training session.\n\n"
        "TRANSCRIPT_CONTEXT (ordered turns):\n"
        f"{payload_json}\n\n"
        "OUTPUT_SCHEMA (you MUST follow this exactly):\n"
        f"{schema_instructions}\n\n"
        "Remember:\n"
        "- Use ONLY information from the provided transcript_context and rule_* fields.\n"
        "- Do NOT invent new utterances or events.\n"
        "- Return exactly one JSON object with the specified keys, no explanations.\n"
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

