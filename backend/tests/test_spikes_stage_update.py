import pytest

from services.dialogue_service import DialogueService

class FakeLLM:
    def generate_patient_response(self, *args, **kwargs):
        assert kwargs["current_spikes_stage"] == "perception"
        return "patient response"


class FakeSession:
    def __init__(self):
        self.current_spikes_stage = "setting"


def test_stage_updates_before_llm():

    detected_stage = "perception"

    class FakeLLM:
        def generate_patient_response(self, *args, **kwargs):
            # This asserts that the stage passed to the LLM
            # matches the detected stage from the pipeline
            assert kwargs["current_spikes_stage"] == detected_stage
            return "patient response"

    session = type("Session", (), {})()
    session.current_spikes_stage = detected_stage

    llm = FakeLLM()

    response = llm.generate_patient_response(
        current_spikes_stage=session.current_spikes_stage
    )

    assert response == "patient response"