from __future__ import annotations

from typing import Any, Tuple

from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from services.nlu_pipeline import NLUPipeline
from domain.entities.turn import Turn


async def analyze_user_input(
    pipeline: NLUPipeline,
    text: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Analyze user (clinician) input for metrics and spans."""
    analysis = await pipeline.analyze(text)

    empathy = analysis["empathy"]
    question_type = analysis["question_type"]
    tone = analysis["tone"]
    empathy_response = empathy.get("has_empathy", False)
    empathy_response_type = analysis["empathy_response_type"]

    # Combine elicitation and response spans for backward compatibility
    all_spans: list[dict[str, Any]] = []
    for span in analysis.get("elicitation_spans", []):
        span["span_type"] = "elicitation"
        all_spans.append(span)
    for span in analysis.get("response_spans", []):
        span["span_type"] = "response"
        all_spans.append(span)

    metrics = {
        "empathy": empathy,
        "question_type": question_type,
        "tone": tone,
        "empathy_response": empathy_response,
        "empathy_response_type": empathy_response_type,
    }

    return metrics, all_spans


async def analyze_assistant_response(
    nlu_adapter: SimpleRuleNLU,
    text: str,
    previous_user_turn: Turn,
    latency_ms: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Analyze assistant (patient) response for metrics and spans."""
    # Legacy EO detection for backward compatibility
    eo_analysis = await nlu_adapter.detect_empathy_opportunity(text)

    # AFCE-aligned EO span detection
    eo_spans = await nlu_adapter.detect_eo_spans(text)

    # Add span_type to each EO span
    all_spans: list[dict[str, Any]] = []
    for span in eo_spans:
        span["span_type"] = "eo"
        all_spans.append(span)

    # Note: Missed opportunity detection is handled in scoring_service
    metrics = {
        "empathy_opportunity_type": eo_analysis.get("empathy_opportunity_type"),
        "empathy_opportunity": eo_analysis.get("empathy_opportunity", False),
        "latency_ms": latency_ms,
    }

    return metrics, all_spans

