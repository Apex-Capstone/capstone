import pytest

from schemas.llm_reviewer import LLMReviewerInput, LLMReviewerOutput, TranscriptTurnLite
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
    )


def _valid_output() -> LLMReviewerOutput:
    return LLMReviewerOutput(
        reviewer_version="v1",
        empathy_score=72.0,
        communication_score=65.0,
        spikes_completion_score=58.0,
        overall_score=0.5 * 72.0 + 0.2 * 65.0 + 0.3 * 58.0,
        missed_opportunities=[],
        spikes_annotations=[],
        strengths=["Clear opening"],
        areas_for_improvement=["Explore emotions further"],
        empathy_confidence=0.7,
        communication_confidence=0.7,
        spikes_confidence=0.6,
        overall_confidence=0.65,
        notes=None,
    )


@pytest.mark.asyncio
async def test_llm_reviewer_service_success_path():
    payload = _minimal_payload()
    valid_output = _valid_output()
    adapter = FakeAdapter(raw_response=valid_output.model_dump_json())
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert isinstance(result, LLMReviewerOutput)
    assert result.empathy_score == pytest.approx(72.0)
    assert result.spikes_completion_score == pytest.approx(58.0)


@pytest.mark.asyncio
async def test_llm_reviewer_service_fenced_json():
    payload = _minimal_payload()
    valid_output = _valid_output()
    fenced = f"```json\n{valid_output.model_dump_json()}\n```"
    adapter = FakeAdapter(raw_response=fenced)
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert isinstance(result, LLMReviewerOutput)
    assert result.notes is None


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
    bad_json = '{"foo": "bar"}'
    adapter = FakeAdapter(raw_response=bad_json)
    service = LLMReviewerService(adapter)

    result = await service.review(payload)
    assert result is None


@pytest.mark.asyncio
async def test_llm_reviewer_service_uses_prompt_builder():
    payload = _minimal_payload()
    minimal_json = _valid_output().model_dump_json()
    adapter = FakeAdapter(raw_response=minimal_json)
    service = LLMReviewerService(adapter)

    await service.review(payload)

    messages = build_llm_reviewer_messages(payload)
    assert adapter.last_context == messages[0]["content"]
    assert adapter.last_prompt == messages[1]["content"]
