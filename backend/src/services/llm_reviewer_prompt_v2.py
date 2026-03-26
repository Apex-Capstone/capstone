"""Prompt builders for hybrid LLM v2 (three focused transcript-only reviews)."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from schemas.llm_reviewer import LLMReviewerInput


def _serialize_evaluator_payload(payload: LLMReviewerInput) -> str:
    data: Dict[str, Any] = {
        "session_id": payload.session_id,
        "case_id": payload.case_id,
        "reviewer_version": payload.reviewer_version,
        "transcript_context": [t.model_dump(mode="python") for t in payload.transcript_context],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _empathy_schema_block() -> str:
    return """
You MUST return a single JSON object with EXACTLY these keys (no others):

{
  "reviewer_version": "v2",
  "empathy_score": <float 0-100>,
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
  "empathic_opportunities": ["<string>", ...],
  "empathy_review_reasoning": "<string or null>",
  "empathy_confidence": <float 0-1 or null>
}

Rules:
- Do NOT include communication_score, spikes_completion_score, or overall_score.
- Base judgments only on transcript_context.
- missed_opportunities and empathic_opportunities may be empty arrays.
""".strip()


def _spikes_schema_block() -> str:
    return """
You MUST return a single JSON object with EXACTLY these keys (no others):

{
  "reviewer_version": "v2",
  "spikes_completion_score": <float 0-100>,
  "spikes_annotations": [
    {
      "turn_number": <int >= 1>,
      "stage": "setting" | "perception" | "invitation" | "knowledge" | "emotion" | "strategy",
      "evidence_snippet": "<string, short quote or paraphrase>",
      "confidence": <float 0-1 or null>
    }
  ],
  "stage_turn_mapping": [
    { "turn_number": <int >= 1>, "stage": "setting" | "perception" | "invitation" | "knowledge" | "emotion" | "strategy" }
  ],
  "spikes_sequencing_notes": "<string or null>",
  "spikes_confidence": <float 0-1 or null>
}

Rules:
- Do NOT include empathy_score or communication_score or overall_score.
- SPIKES stage literals must match exactly: setting, perception, invitation, knowledge, emotion, strategy.
- stage_turn_mapping may be empty if unclear; prefer one row per turn where a stage is clearly in play.
""".strip()


def _communication_schema_block() -> str:
    return """
You MUST return a single JSON object with EXACTLY these keys (no others):

{
  "reviewer_version": "v2",
  "communication_score": <float 0-100>,
  "strengths": ["<string>", ...],
  "areas_for_improvement": ["<string>", ...],
  "clarity_observation": "<string or null>",
  "organization_observation": "<string or null>",
  "professionalism_observation": "<string or null>",
  "question_quality_observation": "<string or null>",
  "communication_confidence": <float 0-1 or null>
}

Rules:
- Do NOT include empathy_score, spikes_completion_score, or overall_score.
- strengths and areas_for_improvement are about communication only (clarity, organization, professionalism, questions).
""".strip()


def build_hybrid_v2_empathy_messages(payload: LLMReviewerInput) -> List[Dict[str, str]]:
    system = (
        "You are an expert evaluator of clinician empathy in medical training transcripts. "
        "You are NOT role-playing the patient. Use ONLY transcript_context; do not invent dialogue. "
        "Return STRICT JSON ONLY matching the schema; no markdown outside JSON.\n"
        "Evaluate: acknowledgment/validation of emotions, responsiveness to emotional cues, missed or weak "
        "empathy moments, and notable empathic opportunities the clinician handled well."
    )
    user = (
        "Empathy-only review for this training session.\n\n"
        f"SESSION_PAYLOAD (JSON):\n{_serialize_evaluator_payload(payload)}\n\n"
        f"OUTPUT_SCHEMA:\n{_empathy_schema_block()}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_hybrid_v2_spikes_messages(payload: LLMReviewerInput) -> List[Dict[str, str]]:
    system = (
        "You are an expert evaluator of SPIKES structure in medical training transcripts. "
        "Use ONLY transcript_context. Return STRICT JSON ONLY; no markdown outside JSON.\n"
        "Assess coverage and sequencing of: setting, perception, invitation, knowledge, emotion, strategy."
    )
    user = (
        "SPIKES-only review for this training session.\n\n"
        f"SESSION_PAYLOAD (JSON):\n{_serialize_evaluator_payload(payload)}\n\n"
        f"OUTPUT_SCHEMA:\n{_spikes_schema_block()}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_hybrid_v2_communication_messages(payload: LLMReviewerInput) -> List[Dict[str, str]]:
    system = (
        "You are an expert evaluator of clinical communication quality in training transcripts. "
        "Use ONLY transcript_context. Return STRICT JSON ONLY; no markdown outside JSON.\n"
        "Focus on clarity, organization, professionalism, and question quality—not SPIKES stage labels "
        "and not empathy scoring (separate reviewer)."
    )
    user = (
        "Communication-only review for this training session.\n\n"
        f"SESSION_PAYLOAD (JSON):\n{_serialize_evaluator_payload(payload)}\n\n"
        f"OUTPUT_SCHEMA:\n{_communication_schema_block()}\n"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
