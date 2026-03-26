"""Prompt builder for the transcript-only LLM evaluator.

Converts `LLMReviewerInput` (transcript + minimal session metadata) into
system + user chat messages with STRICT JSON-only output instructions.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from schemas.llm_reviewer import LLMReviewerInput


def _build_output_schema_instructions() -> str:
    """Describe the expected JSON output schema matching `LLMReviewerOutput`."""
    return """
You MUST return a single JSON object with this exact shape:

{
  "reviewer_version": "v1",
  "empathy_score": <float 0-100>,
  "communication_score": <float 0-100>,
  "spikes_completion_score": <float 0-100>,
  "overall_score": <float 0-100>,
  "missed_opportunities": [
    {
      "turn_number": <int >= 1>,
      "patient_emotional_cue": "<string>",
      "clinician_response_summary": "<string or null>",
      "why_missed_or_weak": "<string>",
      "suggested_response": "<string or null>",
      "confidence": <float 0-1 or null>
    }
  ],
  "spikes_annotations": [
    {
      "turn_number": <int >= 1>,
      "stage": "setting" | "perception" | "invitation" | "knowledge" | "emotion" | "strategy",
      "evidence_snippet": "<string, short quote or paraphrase from transcript>",
      "confidence": <float 0-1 or null>
    }
  ],
  "strengths": ["<string>", ...],
  "areas_for_improvement": ["<string>", ...],
  "empathy_confidence": <float 0-1 or null>,
  "communication_confidence": <float 0-1 or null>,
  "spikes_confidence": <float 0-1 or null>,
  "overall_confidence": <float 0-1 or null>,
  "notes": "<string or null>"
}

Primary numeric judgments are empathy_score, communication_score, and spikes_completion_score (each 0–100).
overall_score is derived ONLY from those three—do not treat overall_score as an independent judgment.
Set overall_score to exactly:
  0.5 * empathy_score + 0.2 * communication_score + 0.3 * spikes_completion_score
(rounded to one decimal if needed, but keep numeric JSON values.)

Do NOT add or remove top-level keys. Do NOT change key names or required value types.
""".strip()


def _serialize_evaluator_payload(payload: LLMReviewerInput) -> str:
    """JSON for the user message: transcript and harmless session identifiers only (no case copy)."""
    data: Dict[str, Any] = {
        "session_id": payload.session_id,
        "case_id": payload.case_id,
        "reviewer_version": payload.reviewer_version,
        "transcript_context": [t.model_dump(mode="python") for t in payload.transcript_context],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_llm_reviewer_messages(payload: LLMReviewerInput) -> List[Dict[str, str]]:
    """Build system + user messages for the transcript-only LLM evaluator.

    Returns:
        Exactly two messages: [system, user].
    """
    system_content = (
        "You are an expert evaluator of clinician–patient communication in medical training. "
        "You are NOT role-playing the patient and you must not invent dialogue. "
        "Use ONLY the provided transcript turns (with speaker labels and turn numbers). "
        "You MUST return STRICT JSON ONLY matching the schema; no markdown outside JSON.\n\n"
        "Evaluate independently (you have NO access to any automated detectors or rule-based scores):\n"
        "1) Empathy (empathy_score): acknowledgment and validation of emotions, responsiveness to cues.\n"
        "2) Communication (communication_score): clarity, question strategy, pacing, partnership language.\n"
        "3) SPIKES completion (spikes_completion_score): coverage of the six canonical SPIKES stages in the "
        "transcript—setting, perception, invitation, knowledge, emotion, strategy. Score how many of these stages "
        "are meaningfully represented in the dialogue (0–100), aligned with stage coverage (not a separate "
        "construct beyond which stages appear in the conversation).\n"
        "4) Missed opportunities: patient emotional cues where the clinician could have responded more empathically; "
        "use turn_number and short evidence from the transcript.\n"
        "5) SPIKES annotations: for turns where a SPIKES stage is clearly in play, note stage + brief evidence_snippet.\n"
        "6) strengths and areas_for_improvement: concise, actionable bullets.\n\n"
        "SPIKES stage literals must match: setting, perception, invitation, knowledge, emotion, strategy."
    )

    schema_instructions = _build_output_schema_instructions()
    payload_json = _serialize_evaluator_payload(payload)

    user_content = (
        "Evaluate this single training session from the transcript alone.\n\n"
        "SESSION_PAYLOAD (JSON):\n"
        f"{payload_json}\n\n"
        "OUTPUT_SCHEMA (follow exactly):\n"
        f"{schema_instructions}\n\n"
        "Rules:\n"
        "- Base every judgment on transcript_context only.\n"
        "- missed_opportunities and spikes_annotations may be empty arrays if none apply.\n"
        "- Return exactly one JSON object; no prose outside JSON.\n"
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
