import asyncio

import pytest

from schemas.llm_reviewer import (
    LLMReviewerInput,
    LLMReviewerOutput,
    RuleLinkEvidence,
    RuleScoreSnapshot,
    RuleStageEvent,
    TranscriptTurnLite,
    ReviewTarget,
)
from services.llm_reviewer_prompt import build_llm_reviewer_messages
from services.llm_reviewer_service import LLMReviewerService


class FakeAdapter:
    def __init__(self, raw_response: str):
        self.raw_response = raw_response
        self.last_prompt = None
        self.last_context = None

    async def generate_response(self, prompt: str, context: str = "", **kwargs):
        self.last_prompt = prompt
        self.last_context = context
        return self.raw_response


def _minimal_payload() -> LLMReviewerInput:
    return LLMReviewerInput(
        session_id=1,
        case_id=42,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="clinician", text="Hello, how are you feeling today?"),
            TranscriptTurnLite(turn_number=2, speaker="patient", text="I'm feeling anxious about my symptoms."),
        ],
        rule_spans=[],
        rule_links=[
            RuleLinkEvidence(
                eo_span_id="eo-1",
                linked_response_span_ids=[],
                linked_elicitation_span_ids=[],
                rule_addressed=False,
                rule_missed_opportunity=True,
            )
        ],
        rule_stages=[
            RuleStageEvent(turn_number=1, stage="setting"),
        ],
        rule_scores=RuleScoreSnapshot(
            empathy_score=50.0,
            communication_score=60.0,
            clinical_reasoning_score=55.0,
            professionalism_score=70.0,
            spikes_completion_score=40.0,
            overall_score=55.0,
        ),
        review_targets=[
            ReviewTarget(
                target_id="t1",
                target_type="missed_opportunity",
                eo_span_id="eo-1",
                response_span_ids=[],
                elicitation_span_ids=[],
                context_turn_numbers=[1, 2],
                rule_summary="Rule-based system flagged this as a missed opportunity.",
            )
        ],
    )


@pytest.mark.asyncio
async def test_llm_reviewer_service_success_path():
    payload = _minimal_payload()

    valid_output = LLMReviewerOutput(
        reviewer_version="v1",
        reviewed_events=[],
        session_assessment={
            "empathy_quality_score_0_to_4": 3,
            "clarity_quality_score_0_to_4": 3,
            "supportiveness_quality_score_0_to_4": 3,
            "confidence": 0.9,
            "rationale": "Good overall communication.",
            "strengths": ["Empathy used appropriately"],
            "improvement_points": ["Could ask more open questions"],
        },
        overall_confidence=0.9,
        notes=None,
    )
    adapter = FakeAdapter(raw_response=valid_output.model_dump_json())
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert isinstance(result, LLMReviewerOutput)
    assert result.session_assessment.empathy_quality_score_0_to_4 == 3
    assert result.overall_confidence == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_llm_reviewer_service_fenced_json():
    payload = _minimal_payload()

    valid_output = LLMReviewerOutput(
        reviewer_version="v1",
        reviewed_events=[],
        session_assessment={
            "empathy_quality_score_0_to_4": 2,
            "clarity_quality_score_0_to_4": 2,
            "supportiveness_quality_score_0_to_4": 2,
            "confidence": 0.8,
            "rationale": "Adequate communication.",
            "strengths": [],
            "improvement_points": [],
        },
        overall_confidence=0.8,
        notes="wrapped in fences",
    )
    fenced = f"```json\n{valid_output.model_dump_json()}\n```"
    adapter = FakeAdapter(raw_response=fenced)
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert isinstance(result, LLMReviewerOutput)
    assert result.session_assessment.empathy_quality_score_0_to_4 == 2
    assert result.notes == "wrapped in fences"


@pytest.mark.asyncio
async def test_llm_reviewer_service_invalid_json_returns_none():
    payload = _minimal_payload()
    adapter = FakeAdapter(raw_response="not valid json")
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert result is None


@pytest.mark.asyncio
async def test_llm_reviewer_service_schema_mismatch_returns_none():
    payload = _minimal_payload()
    # Valid JSON but wrong structure (missing required fields)
    bad_json = '{"foo": "bar"}'
    adapter = FakeAdapter(raw_response=bad_json)
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert result is None


@pytest.mark.asyncio
async def test_llm_reviewer_service_uses_prompt_builder():
    payload = _minimal_payload()
    adapter = FakeAdapter(raw_response='{"reviewer_version":"v1","reviewed_events":[],"session_assessment":{"empathy_quality_score_0_to_4":0,"clarity_quality_score_0_to_4":0,"supportiveness_quality_score_0_to_4":0,"confidence":0.0,"rationale":"","strengths":[],"improvement_points":[]},"overall_confidence":0.0,"notes":null}')
    service = LLMReviewerService(adapter)

    # Run once to capture prompt/context
    await service.review(payload)

    # Rebuild messages independently and ensure they match what adapter saw
    messages = build_llm_reviewer_messages(payload)
    assert adapter.last_context == messages[0]["content"]
    assert adapter.last_prompt == messages[1]["content"]

