from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugins.patient_models.default_llm_patient import DefaultLLMPatientModel


class _DummyLLMAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_patient_response(
        self,
        case_script: str,
        conversation_history: list[dict[str, str]],
        current_spikes_stage: str,
    ) -> str:  # pragma: no cover - trivial passthrough
        self.calls.append(
            {
                "case_script": case_script,
                "conversation_history": conversation_history,
                "current_spikes_stage": current_spikes_stage,
            }
        )
        return "patient reply"


@pytest.fixture
def dummy_state():
    case = SimpleNamespace(
        diagnosis="Test diagnosis",
        emotional_state="anxious",
        knowledge_level="low",
    )
    session = SimpleNamespace(current_spikes_stage="empathy")
    history = [{"role": "user", "content": "Hello"}]
    return SimpleNamespace(case=case, session=session, conversation_history=history)


def test_default_llm_patient_model_can_be_instantiated():
    adapter = _DummyLLMAdapter()
    model = DefaultLLMPatientModel(llm_adapter=adapter)

    assert model is not None


@pytest.mark.asyncio
async def test_generate_response_returns_string(dummy_state):
    adapter = _DummyLLMAdapter()
    model = DefaultLLMPatientModel(llm_adapter=adapter)

    result = await model.generate_response(dummy_state, clinician_input="Hi")

    assert isinstance(result, str)
    assert result == "patient reply"
    # Ensure adapter was called with a non-empty case_script and the expected stage
    assert adapter.calls, "LLM adapter was not called"
    call = adapter.calls[0]
    assert "Test diagnosis" in call["case_script"]
    assert call["current_spikes_stage"] == "empathy"

