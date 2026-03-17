"""Tests for audio turn submission."""

import os
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers, UploadFile

os.environ.setdefault("database_url", "sqlite:///./test_audio.db")
os.environ.setdefault("secret_key", "test-secret")
os.environ.setdefault("gemini_api_key", "test-gemini-key")
os.environ.setdefault("aws_access_key_id", "test-access-key")
os.environ.setdefault("aws_secret_access_key", "test-secret-key")
os.environ.setdefault("s3_bucket_name", "test-bucket")
os.environ.setdefault("openai_api_key", "test-openai-key")

from controllers.sessions_controller import submit_audio_turn, transcribe_audio_turn
from core.errors import AuthorizationError, ConflictError, ExternalServiceError, ValidationError
from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from domain.models.sessions import TurnResponse
from services.dialogue_service import DialogueService
from services.session_service import SessionService
from adapters.asr.whisper_adapter import WhisperAdapter
from adapters.storage.s3_storage import S3StorageAdapter


@pytest.fixture
def test_db():
    """Create a test database session."""
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
def owner_user(test_db):
    """Create the session owner."""
    user = User(
        email="owner@example.com",
        hashed_password="hashed_password",
        role="trainee",
        full_name="Owner User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def other_user(test_db):
    """Create another user."""
    user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        role="trainee",
        full_name="Other User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    """Create a test case."""
    case = Case(
        title="Audio Test Case",
        script="Test case script",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.fixture
def active_session(test_db, owner_user, test_case):
    """Create an active session."""
    session = SessionEntity(
        user_id=owner_user.id,
        case_id=test_case.id,
        state="active",
        current_spikes_stage="setting",
        duration_seconds=0,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def completed_session(test_db, owner_user, test_case):
    """Create a completed session."""
    session = SessionEntity(
        user_id=owner_user.id,
        case_id=test_case.id,
        state="completed",
        current_spikes_stage="summary",
        duration_seconds=120,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


def make_upload_file(filename: str, payload: bytes, content_type: str) -> UploadFile:
    """Create an UploadFile for testing."""
    return UploadFile(
        file=BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.asyncio
async def test_submit_audio_turn_success(monkeypatch, test_db, owner_user, active_session):
    """Audio uploads should return transcript, patient reply, and stored audio URL."""

    async def fake_transcribe_audio(self, audio_data: bytes, audio_format: str) -> str:
        assert audio_data == b"fake-audio"
        assert audio_format == "webm"
        return "I wanted to ask about my results."

    async def fake_put_file(self, file_data: bytes, file_name: str, content_type: str) -> str:
        assert file_data == b"fake-audio"
        assert file_name.startswith(f"sessions/{active_session.id}/")
        assert content_type == "audio/webm"
        return "https://example.com/audio.webm"

    async def fake_process_user_turn(self, session_id: int, turn_data) -> TurnResponse:
        assert session_id == active_session.id
        assert turn_data.text == "I wanted to ask about my results."
        assert turn_data.audio_url == "https://example.com/audio.webm"
        return TurnResponse(
            id=42,
            session_id=session_id,
            turn_number=2,
            role="assistant",
            text="Of course. Tell me what is on your mind.",
            audio_url=None,
            metrics_json=None,
            spikes_stage="perception",
            timestamp=datetime.utcnow(),
        )

    async def fake_get_session(self, session_id: int):
        assert session_id == active_session.id
        return SimpleNamespace(current_spikes_stage="perception")

    monkeypatch.setattr(WhisperAdapter, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(S3StorageAdapter, "put_file", fake_put_file)
    monkeypatch.setattr(DialogueService, "process_user_turn", fake_process_user_turn)
    monkeypatch.setattr(SessionService, "get_session", fake_get_session)

    response = await submit_audio_turn(
        active_session.id,
        make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
        test_db,
        owner_user,
    )

    assert response.transcript == "I wanted to ask about my results."
    assert response.patient_reply == "Of course. Tell me what is on your mind."
    assert response.audio_url == "https://example.com/audio.webm"
    assert response.spikes_stage == "perception"


@pytest.mark.asyncio
async def test_transcribe_audio_turn_success(monkeypatch, test_db, owner_user, active_session):
    """Audio transcription endpoint should return transcript before patient reply generation."""

    async def fake_transcribe_audio(self, audio_data: bytes, audio_format: str) -> str:
        assert audio_data == b"fake-audio"
        assert audio_format == "webm"
        return "I wanted to ask about my results."

    async def fake_put_file(self, file_data: bytes, file_name: str, content_type: str) -> str:
        assert file_data == b"fake-audio"
        assert file_name.startswith(f"sessions/{active_session.id}/")
        assert content_type == "audio/webm"
        return "https://example.com/audio.webm"

    monkeypatch.setattr(WhisperAdapter, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(S3StorageAdapter, "put_file", fake_put_file)

    response = await transcribe_audio_turn(
        active_session.id,
        make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
        test_db,
        owner_user,
    )

    assert response.transcript == "I wanted to ask about my results."
    assert response.audio_url == "https://example.com/audio.webm"


@pytest.mark.asyncio
async def test_submit_audio_turn_unauthorized_user(test_db, other_user, active_session):
    """Users should not be able to upload audio into another user's session."""
    with pytest.raises(AuthorizationError):
        await submit_audio_turn(
            active_session.id,
            make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
            test_db,
            other_user,
        )


@pytest.mark.asyncio
async def test_submit_audio_turn_rejects_completed_session(test_db, owner_user, completed_session):
    """Completed sessions should reject new audio turns."""
    with pytest.raises(ConflictError):
        await submit_audio_turn(
            completed_session.id,
            make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
            test_db,
            owner_user,
        )


@pytest.mark.asyncio
async def test_submit_audio_turn_rejects_invalid_audio_format(test_db, owner_user, active_session):
    """Unsupported file types should fail validation before ASR runs."""
    with pytest.raises(ValidationError):
        await submit_audio_turn(
            active_session.id,
            make_upload_file("voice.txt", b"not-audio", "text/plain"),
            test_db,
            owner_user,
        )


@pytest.mark.asyncio
async def test_submit_audio_turn_survives_storage_failure(monkeypatch, test_db, owner_user, active_session):
    """Storage failures should not block transcript processing for input-only mode."""

    async def fake_transcribe_audio(self, audio_data: bytes, audio_format: str) -> str:
        return "This should still go through."

    async def fake_put_file(self, file_data: bytes, file_name: str, content_type: str) -> str:
        raise RuntimeError("storage unavailable")

    async def fake_process_user_turn(self, session_id: int, turn_data) -> TurnResponse:
        assert turn_data.audio_url is None
        return TurnResponse(
            id=43,
            session_id=session_id,
            turn_number=2,
            role="assistant",
            text="I understand. Please continue.",
            audio_url=None,
            metrics_json=None,
            spikes_stage="perception",
            timestamp=datetime.utcnow(),
        )

    async def fake_get_session(self, session_id: int):
        return SimpleNamespace(current_spikes_stage="perception")

    monkeypatch.setattr(WhisperAdapter, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(S3StorageAdapter, "put_file", fake_put_file)
    monkeypatch.setattr(DialogueService, "process_user_turn", fake_process_user_turn)
    monkeypatch.setattr(SessionService, "get_session", fake_get_session)

    response = await submit_audio_turn(
        active_session.id,
        make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
        test_db,
        owner_user,
    )

    assert response.transcript == "This should still go through."
    assert response.audio_url is None


@pytest.mark.asyncio
async def test_submit_audio_turn_propagates_asr_failure(monkeypatch, test_db, owner_user, active_session):
    """ASR failures should bubble up as service errors."""

    async def fake_transcribe_audio(self, audio_data: bytes, audio_format: str) -> str:
        raise ExternalServiceError("Audio transcription failed")

    monkeypatch.setattr(WhisperAdapter, "transcribe_audio", fake_transcribe_audio)

    with pytest.raises(ExternalServiceError):
        await submit_audio_turn(
            active_session.id,
            make_upload_file("voice.webm", b"fake-audio", "audio/webm"),
            test_db,
            owner_user,
        )
