"""Comparison helpers for rule-based and LLM reviewer verdicts (Phase 1 audit only)."""

from __future__ import annotations

from typing import Any, Dict, List

from schemas.llm_reviewer import ReviewedEventAssessment


def compare_rule_and_llm_event(
    *,
    rule_link: Dict[str, Any],
    llm_event: ReviewedEventAssessment,
) -> Dict[str, Any]:
    """Compare a single rule-based verdict with an LLM-reviewed event.

    Args:
        rule_link: JSON-safe dict representing rule-based linking/flags for a target.
                   Expected keys:
                       - "target_id"
                       - "rule_missed_opportunity": bool
                       - "rule_addressed": bool
        llm_event: LLM-reviewed assessment for the same `target_id`.

    Returns:
        JSON-safe dict with rule_verdict, llm_verdict, and agreement flags.
    """
    target_id = llm_event.target_id
    rule_missed_opportunity = bool(rule_link.get("rule_missed_opportunity", False))
    rule_addressed = bool(rule_link.get("rule_addressed", False))

    llm_verdict = {
        "acknowledged_emotion": llm_event.acknowledged_emotion,
        "validated_feeling": llm_event.validated_feeling,
        "missed_opportunity": llm_event.missed_opportunity,
        "empathy_quality_score_0_to_4": llm_event.empathy_quality_score_0_to_4,
        "disposition": llm_event.disposition,
        "confidence": llm_event.confidence,
        "rationale": llm_event.rationale,
        "suggested_response": llm_event.suggested_response,
    }

    missed_opportunity_agree = rule_missed_opportunity == llm_event.missed_opportunity
    addressed_vs_acknowledged_agree = rule_addressed == llm_event.acknowledged_emotion
    overall_agree = missed_opportunity_agree and addressed_vs_acknowledged_agree

    return {
        "target_id": target_id,
        "rule_verdict": {
            "rule_missed_opportunity": rule_missed_opportunity,
            "rule_addressed": rule_addressed,
        },
        "llm_verdict": llm_verdict,
        "agreement": {
            "missed_opportunity_agree": missed_opportunity_agree,
            "addressed_vs_acknowledged_agree": addressed_vs_acknowledged_agree,
            "overall_agree": overall_agree,
        },
    }


def build_llm_reviewer_audit_summary(
    *,
    reviewed_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute simple disagreement statistics across reviewed events.

    Args:
        reviewed_events: List of comparison dicts produced by `compare_rule_and_llm_event`.

    Returns:
        {
          "total_reviewed_events": int,
          "total_disagreements": int,
          "disagreement_rate": float  # 0.0–1.0, rounded to 3 decimals
        }
    """
    total = len(reviewed_events)
    if total == 0:
        return {
            "total_reviewed_events": 0,
            "total_disagreements": 0,
            "disagreement_rate": 0.0,
        }

    disagreements = 0
    for ev in reviewed_events:
        agreement = ev.get("agreement", {})
        if not agreement.get("overall_agree", False):
            disagreements += 1

    rate = disagreements / total if total > 0 else 0.0
    return {
        "total_reviewed_events": total,
        "total_disagreements": disagreements,
        "disagreement_rate": round(rate, 3),
    }

