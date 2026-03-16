from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.llm.base import LLMAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from domain.models.sessions import TurnCreate, TurnResponse
from services.dialogue_service import DialogueService


class _DummyLLMAdapter(LLMAdapter):
    async def generate_response(self, prompt: str, context: str = "", max_tokens: int = 500, temperature: float = 0.7) -> str:
        return "dummy"

    async def generate_patient_response(
        self,
        case_script: str,
        conversation_history: list[dict[str, str]],
        current_spikes_stage: str,
    ) -> str:
        return "dummy patient reply"

    async def analyze_turn(
        self,
        user_text: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, any]:
        return {}


class _DummyPatientModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def generate_response(self, state, clinician_input: str) -> str:
        self.calls.append(
            {
                "state": state,
                "clinician_input": clinician_input,
            }
        )
        # Return a recognizable reply
        return "plugin patient reply"


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def seeded_session(test_db):
    user = User(
        email="dialogue_plugin_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Dialogue Plugin Tester",
    )
    test_db.add(user)

    case = Case(
        title="Dialogue Plugin Case",
        description="Case for dialogue service plugin integration test.",
        script="Script content for dialogue plugin test.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()

    session = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="active",
        current_spikes_stage="setting",
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    return session


@pytest.mark.asyncio
async def test_dialogue_service_uses_patient_model_plugin(test_db, seeded_session, monkeypatch: pytest.MonkeyPatch):
    from core import plugin_manager

    dummy_patient_model = _DummyPatientModel()
    # Ensure DialogueService gets our dummy plugin instance
    monkeypatch.setattr(plugin_manager, "get_patient_model", lambda: dummy_patient_model)

    # Use a simple NLU adapter; DialogueService wraps it in NLUPipeline
    nlu = SimpleRuleNLU()
    llm_adapter = _DummyLLMAdapter()

    service = DialogueService(test_db, llm_adapter=llm_adapter, nlu_adapter=nlu)

    turn = TurnCreate(text="Hello, how are you feeling today?", audio_url=None)
    response = await service.process_user_turn(seeded_session.id, turn)

    assert isinstance(response, TurnResponse)
    # The assistant's text should come from the plugin reply
    assert response.text == "plugin patient reply"
    # And our dummy plugin should have been called at least once
    assert dummy_patient_model.calls

