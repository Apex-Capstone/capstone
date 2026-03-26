"""Three-call LLM orchestration for hybrid evaluator v2."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type

from config.logging import get_logger
from pydantic import BaseModel

from schemas.llm_reviewer import (
    HybridV2CommunicationPromptOutput,
    HybridV2CompiledLLMReview,
    HybridV2EmpathyPromptOutput,
    HybridV2SpikesPromptOutput,
    LLMReviewerInput,
)
from services.llm_reviewer_prompt_v2 import (
    build_hybrid_v2_communication_messages,
    build_hybrid_v2_empathy_messages,
    build_hybrid_v2_spikes_messages,
)
from services.llm_reviewer_service import extract_llm_json_dict, safe_preview_llm_raw


logger = get_logger(__name__)

_V2_MAX_TOKENS = 2000


@dataclass
class HybridV2LLMRunOutcome:
    """Raw results from the three LLM prompt calls."""

    empathy: Optional[HybridV2EmpathyPromptOutput]
    spikes: Optional[HybridV2SpikesPromptOutput]
    communication: Optional[HybridV2CommunicationPromptOutput]
    prompt_status: dict[str, str]


def compute_hybrid_v2_llm_overall(
    eff_empathy: float,
    eff_communication: float,
    eff_spikes: float,
) -> float:
    """LLM-side overall from components (same weights as v1 rubric); not blended with rule."""
    return round(0.5 * eff_empathy + 0.2 * eff_communication + 0.3 * eff_spikes, 2)


def build_compiled_review_and_llm_scores(
    rule_snapshot: dict[str, float],
    empathy: Optional[HybridV2EmpathyPromptOutput],
    spikes: Optional[HybridV2SpikesPromptOutput],
    communication: Optional[HybridV2CommunicationPromptOutput],
) -> Tuple[HybridV2CompiledLLMReview, dict[str, Any]]:
    """
    Merge partial LLM outputs into a full compiled review payload and llm_scores for evaluator_meta.

    For each component, if the prompt failed, the compiled numeric field uses the rule score
    (rule_fallback) so the object stays complete; llm_scores uses null for that component.
    """
    rule_e = float(rule_snapshot["empathy_score"])
    rule_c = float(rule_snapshot["communication_score"])
    rule_s = float(rule_snapshot["spikes_completion_score"])

    src: dict[str, str] = {}
    eff_e = float(empathy.empathy_score) if empathy else rule_e
    eff_c = float(communication.communication_score) if communication else rule_c
    eff_s = float(spikes.spikes_completion_score) if spikes else rule_s
    if empathy:
        src["empathy"] = "llm"
    else:
        src["empathy"] = "rule_fallback"
    if communication:
        src["communication"] = "llm"
    else:
        src["communication"] = "rule_fallback"
    if spikes:
        src["spikes"] = "llm"
    else:
        src["spikes"] = "rule_fallback"

    overall = compute_hybrid_v2_llm_overall(eff_e, eff_c, eff_s)

    compiled = HybridV2CompiledLLMReview(
        reviewer_version="v2",
        empathy_score=eff_e,
        communication_score=eff_c,
        spikes_completion_score=eff_s,
        overall_score=overall,
        missed_opportunities=list(empathy.missed_opportunities) if empathy else [],
        spikes_annotations=list(spikes.spikes_annotations) if spikes else [],
        strengths=list(communication.strengths) if communication else [],
        areas_for_improvement=list(communication.areas_for_improvement) if communication else [],
        empathic_opportunities=list(empathy.empathic_opportunities) if empathy else [],
        empathy_review_reasoning=empathy.empathy_review_reasoning if empathy else None,
        spikes_sequencing_notes=spikes.spikes_sequencing_notes if spikes else None,
        stage_turn_mapping=list(spikes.stage_turn_mapping) if spikes else [],
        clarity_observation=communication.clarity_observation if communication else None,
        organization_observation=communication.organization_observation if communication else None,
        professionalism_observation=communication.professionalism_observation if communication else None,
        question_quality_observation=communication.question_quality_observation if communication else None,
        empathy_confidence=empathy.empathy_confidence if empathy else None,
        communication_confidence=communication.communication_confidence if communication else None,
        spikes_confidence=spikes.spikes_confidence if spikes else None,
        overall_confidence=None,
        notes=None,
        llm_score_source=src,
    )

    llm_scores: dict[str, Any] = {
        "empathy_score": float(empathy.empathy_score) if empathy else None,
        "communication_score": float(communication.communication_score) if communication else None,
        "spikes_completion_score": float(spikes.spikes_completion_score) if spikes else None,
        "overall_score": overall,
    }

    return compiled, llm_scores


def overall_v2_status(prompt_status: dict[str, str]) -> str:
    successes = sum(1 for v in prompt_status.values() if v == "success")
    if successes == 0:
        return "failed"
    if successes == 3:
        return "success"
    return "partial"


class HybridV2LLMOrchestrator:
    """Runs three focused LLM reviews in parallel."""

    def __init__(self, llm_adapter: Any):
        self.llm_adapter = llm_adapter
        self._adapter_calls = 0

    @property
    def adapter_call_count(self) -> int:
        return self._adapter_calls

    async def _run_single(
        self,
        messages: list[dict[str, str]],
        model_cls: Type[BaseModel],
        log_label: str,
    ) -> Tuple[str, Optional[BaseModel]]:
        system_msg = messages[0]["content"]
        user_msg = messages[1]["content"]
        self._adapter_calls += 1
        try:
            raw = await self.llm_adapter.generate_response(
                prompt=user_msg,
                context=system_msg,
                max_tokens=_V2_MAX_TOKENS,
                temperature=0.0,
            )
        except Exception as e:
            logger.warning("HybridV2: adapter error during %s: %s", log_label, e)
            return log_label, None

        data, diag = extract_llm_json_dict(raw)
        if data is None:
            logger.warning(
                "HybridV2: JSON parse failed for %s diag=%s preview=%s",
                log_label,
                diag,
                safe_preview_llm_raw(raw),
            )
            return log_label, None
        try:
            parsed = model_cls.model_validate(data)
            return log_label, parsed
        except Exception as e:
            logger.warning(
                "HybridV2: validation failed for %s error=%s keys=%s",
                log_label,
                e,
                list(data.keys()) if isinstance(data, dict) else "non-dict",
            )
            return log_label, None

    async def run(self, payload: LLMReviewerInput) -> HybridV2LLMRunOutcome:
        emp_msgs = build_hybrid_v2_empathy_messages(payload)
        sp_msgs = build_hybrid_v2_spikes_messages(payload)
        com_msgs = build_hybrid_v2_communication_messages(payload)

        results = await asyncio.gather(
            self._run_single(emp_msgs, HybridV2EmpathyPromptOutput, "empathy"),
            self._run_single(sp_msgs, HybridV2SpikesPromptOutput, "spikes"),
            self._run_single(com_msgs, HybridV2CommunicationPromptOutput, "communication"),
        )

        by_label: dict[str, Optional[BaseModel]] = {}
        for label, model in results:
            by_label[label] = model

        emp = by_label.get("empathy")
        sp = by_label.get("spikes")
        com = by_label.get("communication")

        prompt_status = {
            "empathy": "success" if isinstance(emp, HybridV2EmpathyPromptOutput) else "failed",
            "spikes": "success" if isinstance(sp, HybridV2SpikesPromptOutput) else "failed",
            "communication": "success" if isinstance(com, HybridV2CommunicationPromptOutput) else "failed",
        }

        return HybridV2LLMRunOutcome(
            empathy=emp if isinstance(emp, HybridV2EmpathyPromptOutput) else None,
            spikes=sp if isinstance(sp, HybridV2SpikesPromptOutput) else None,
            communication=com if isinstance(com, HybridV2CommunicationPromptOutput) else None,
            prompt_status=prompt_status,
        )
