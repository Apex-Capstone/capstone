from __future__ import annotations

from datetime import timezone
import sys
import types
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

google_module = sys.modules.setdefault("google", types.ModuleType("google"))
genai_module = types.ModuleType("google.genai")
genai_module.Client = object
genai_types_module = types.ModuleType("google.genai.types")
genai_types_module.GenerateContentConfig = object
genai_module.types = genai_types_module
google_module.genai = genai_module
sys.modules["google.genai"] = genai_module
sys.modules["google.genai.types"] = genai_types_module

from adapters.llm.base import LLMAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from adapters.tts.base import TTSAudioResult
from core.time import utc_now
from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from domain.models.sessions import TurnCreate, TurnResponse
from plugins.registry import PluginRegistry
from services.dialogue_service import DialogueService

DIALOGUE_TEST_PATIENT_KEY = "dialogue_test_dummy_patient"


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

    PluginRegistry.register_patient_model(DIALOGUE_TEST_PATIENT_KEY, _DummyPatientModel)
    session = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="active",
        current_spikes_stage="setting",
        patient_model_plugin=DIALOGUE_TEST_PATIENT_KEY,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    try:
        yield session
    finally:
        PluginRegistry.patient_models.pop(DIALOGUE_TEST_PATIENT_KEY, None)


@pytest.mark.asyncio
async def test_dialogue_service_uses_patient_model_plugin(test_db, seeded_session):
    # Use a simple NLU adapter; DialogueService wraps it in NLUPipeline
    nlu = SimpleRuleNLU()
    llm_adapter = _DummyLLMAdapter()

    service = DialogueService(test_db, llm_adapter=llm_adapter, nlu_adapter=nlu)

    turn = TurnCreate(text="Hello, how are you feeling today?", audio_url=None)
    response = await service.process_user_turn(seeded_session.id, turn)

    assert isinstance(response, TurnResponse)
    # The assistant's text should come from the plugin reply
    assert response.text == "plugin patient reply"


class _OtherDummyPatientModel:
    async def generate_response(self, state, clinician_input: str) -> str:
        return "other patient reply"


@pytest.mark.asyncio
async def test_dialogue_resolves_patient_model_from_session_plugin(test_db, seeded_session):
    """Changing session.patient_model_plugin changes which model runs (reproducibility)."""
    other_key = "dialogue_test_other_patient"
    PluginRegistry.register_patient_model(other_key, _OtherDummyPatientModel)
    try:
        seeded_session.patient_model_plugin = other_key
        test_db.commit()

        service = DialogueService(
            test_db,
            llm_adapter=_DummyLLMAdapter(),
            nlu_adapter=SimpleRuleNLU(),
        )
        response = await service.process_user_turn(
            seeded_session.id,
            TurnCreate(text="Hello?", audio_url=None),
        )
        assert response.text == "other patient reply"
    finally:
        PluginRegistry.patient_models.pop(other_key, None)


@pytest.mark.asyncio
async def test_dialogue_invalid_patient_model_plugin_raises(test_db, seeded_session):
    seeded_session.patient_model_plugin = "nonexistent.module.path:NoSuchClass"
    test_db.commit()

    service = DialogueService(
        test_db,
        llm_adapter=_DummyLLMAdapter(),
        nlu_adapter=SimpleRuleNLU(),
    )
    with pytest.raises(RuntimeError, match="Invalid patient model plugin: nonexistent.module.path:NoSuchClass"):
        await service.process_user_turn(
            seeded_session.id,
            TurnCreate(text="Hello?", audio_url=None),
        )


@pytest.mark.asyncio
async def test_dialogue_service_generates_assistant_audio_when_enabled(
    test_db,
    seeded_session,
):
    tts = _DummyTTSAdapter()
    storage = _DummyStorageAdapter()
    service = DialogueService(
        test_db,
        llm_adapter=_DummyLLMAdapter(),
        nlu_adapter=SimpleRuleNLU(),
        tts_adapter=tts,
        storage_adapter=storage,
    )

    seeded_session.case.patient_background = "A 78-year-old man who is retired and anxious about his prognosis."
    seeded_session.case.script = "He speaks carefully and is worried about what happens next."
    test_db.commit()

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
    assert tts.calls[0]["voice_id"] == "sage"
    assert "older man" in (tts.calls[0]["instructions"] or "")


@pytest.mark.asyncio
async def test_dialogue_service_leaves_tts_off_by_default(
    test_db,
    seeded_session,
):
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
):
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

