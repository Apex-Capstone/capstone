from __future__ import annotations

from datetime import timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.llm.base import LLMAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from adapters.tts.base import TTSAudioResult
from core.time import utc_now
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


class _DummyTTSAdapter:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = "default",
        instructions: str | None = None,
    ) -> TTSAudioResult:
        self.calls.append(
            {
                "text": text,
                "voice_id": voice_id,
                "instructions": instructions,
            }
        )
        if self.should_fail:
            raise RuntimeError("tts unavailable")
        return TTSAudioResult(
            audio_data=b"assistant-audio",
            content_type="audio/mpeg",
            file_extension="mp3",
        )


class _DummyStorageAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def put_file(self, file_data: bytes, file_name: str, content_type: str = "application/octet-stream") -> str:
        self.calls.append(
            {
                "file_data": file_data,
                "file_name": file_name,
                "content_type": content_type,
            }
        )
        return file_name


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    connection = engine.connect()
    connection.exec_driver_sql("ATTACH DATABASE ':memory:' AS core")
    Base.metadata.create_all(connection)
    TestingSessionLocal = sessionmaker(bind=connection)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        connection.close()


@pytest.fixture
def seeded_session(test_db):
    user = User(
        email="dialogue_plugin_tester@example.com",        
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
    import services.dialogue_service as dialogue_service_module

    dummy_patient_model = _DummyPatientModel()
    # Patch where get_patient_model is used (dialogue_service imports it at load time)
    monkeypatch.setattr(dialogue_service_module, "get_patient_model", lambda: dummy_patient_model)

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


@pytest.mark.asyncio
async def test_dialogue_service_generates_assistant_audio_when_enabled(
    test_db,
    seeded_session,
    monkeypatch: pytest.MonkeyPatch,
):
    import services.dialogue_service as dialogue_service_module

    dummy_patient_model = _DummyPatientModel()
    monkeypatch.setattr(dialogue_service_module, "get_patient_model", lambda: dummy_patient_model)

    tts = _DummyTTSAdapter()
    storage = _DummyStorageAdapter()
    service = DialogueService(
        test_db,
        llm_adapter=_DummyLLMAdapter(),
        nlu_adapter=SimpleRuleNLU(),
        tts_adapter=tts,
        storage_adapter=storage,
    )

    response = await service.process_user_turn(
        seeded_session.id,
        TurnCreate(text="Can you tell me what the results mean?", enable_tts=True),
    )

    assert response.audio_url is not None
    assert response.audio_url.startswith("sessions/")
    assert response.audio_expires_at is not None
    assert response.audio_expires_at.tzinfo == timezone.utc
    assert response.audio_expires_at > utc_now()
    assert tts.calls
    assert storage.calls


@pytest.mark.asyncio
async def test_dialogue_service_leaves_tts_off_by_default(
    test_db,
    seeded_session,
    monkeypatch: pytest.MonkeyPatch,
):
    import services.dialogue_service as dialogue_service_module

    dummy_patient_model = _DummyPatientModel()
    monkeypatch.setattr(dialogue_service_module, "get_patient_model", lambda: dummy_patient_model)

    tts = _DummyTTSAdapter()
    storage = _DummyStorageAdapter()
    service = DialogueService(
        test_db,
        llm_adapter=_DummyLLMAdapter(),
        nlu_adapter=SimpleRuleNLU(),
        tts_adapter=tts,
        storage_adapter=storage,
    )

    response = await service.process_user_turn(
        seeded_session.id,
        TurnCreate(text="Hello, I wanted to check in about my diagnosis."),
    )

    assert response.audio_url is None
    assert tts.calls == []
    assert storage.calls == []


@pytest.mark.asyncio
async def test_dialogue_service_skips_assistant_audio_when_tts_fails(
    test_db,
    seeded_session,
    monkeypatch: pytest.MonkeyPatch,
):
    import services.dialogue_service as dialogue_service_module

    dummy_patient_model = _DummyPatientModel()
    monkeypatch.setattr(dialogue_service_module, "get_patient_model", lambda: dummy_patient_model)

    tts = _DummyTTSAdapter(should_fail=True)
    storage = _DummyStorageAdapter()
    service = DialogueService(
        test_db,
        llm_adapter=_DummyLLMAdapter(),
        nlu_adapter=SimpleRuleNLU(),
        tts_adapter=tts,
        storage_adapter=storage,
    )

    response = await service.process_user_turn(
        seeded_session.id,
        TurnCreate(text="I am worried about what happens next.", enable_tts=True),
    )

    assert response.audio_url is None
    assert tts.calls
    assert storage.calls == []

