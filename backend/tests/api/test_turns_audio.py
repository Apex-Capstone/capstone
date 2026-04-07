"""Tests for GET /v1/turns/{turn_id}/audio (assistant audio streaming)."""

import os
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("database_url", "sqlite:///./test_turns_audio.db")
os.environ.setdefault("secret_key", "test-secret")
os.environ.setdefault("supabase_jwt_secret", "test-supabase-jwt")
os.environ.setdefault("gemini_api_key", "test-gemini-key")
os.environ.setdefault("openai_api_key", "test-openai-key")

from config.settings import get_settings
from controllers.turns_controller import get_turn_audio
from core.errors import AuthorizationError, NotFoundError
from core.time import utc_now
from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from services.audio_cache_service import AudioCacheService


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
def owner_user(test_db):
    user = User(
        email="owner@example.com",
        role="trainee",
        full_name="Owner User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def other_user(test_db):
    user = User(
        email="other@example.com",
        role="trainee",
        full_name="Other User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db):
    user = User(
        email="admin@example.com",
        role="admin",
        full_name="Admin User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Turn Audio Case",
        script="Script",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.fixture
def active_session(test_db, owner_user, test_case):
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


def _add_assistant_turn(
    test_db,
    session_id: int,
    *,
    audio_url: str,
    expires_at,
    role: str = "assistant",
) -> Turn:
    turn = Turn(
        session_id=session_id,
        turn_number=1,
        role=role,
        text="Assistant reply",
        audio_url=audio_url,
        audio_expires_at=expires_at,
    )
    test_db.add(turn)
    test_db.commit()
    test_db.refresh(turn)
    return turn


@pytest.mark.asyncio
async def test_get_turn_audio_fetches_from_storage_on_cache_miss(
    monkeypatch,
    tmp_path,
    test_db,
    owner_user,
    active_session,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    key = "sessions/1/assistant/out.mp3"
    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=key,
        expires_at=utc_now() + timedelta(hours=1),
    )

    calls: list[str] = []

    class _FakeStorage:
        async def get_file(self, file_name: str) -> bytes:
            calls.append(file_name)
            return b"mp3-bytes"

    monkeypatch.setattr(
        "controllers.turns_controller.get_storage_adapter",
        lambda: _FakeStorage(),
    )

    response = await get_turn_audio(turn.id, test_db, owner_user)

    assert isinstance(response, FileResponse)
    assert response.media_type == "audio/mpeg"
    assert calls == [key]
    cached = Path(response.path)
    assert cached.read_bytes() == b"mp3-bytes"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_turn_audio_uses_cache_without_hitting_storage(
    monkeypatch,
    tmp_path,
    test_db,
    owner_user,
    active_session,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    key = "sessions/1/assistant/cached.mp3"
    AudioCacheService().cache_file(key, b"already-here")

    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=key,
        expires_at=utc_now() + timedelta(hours=1),
    )

    async def _boom(_self, _key: str) -> bytes:
        raise AssertionError("storage should not be called on cache hit")

    class _FakeStorage:
        get_file = _boom

    monkeypatch.setattr(
        "controllers.turns_controller.get_storage_adapter",
        lambda: _FakeStorage(),
    )

    response = await get_turn_audio(turn.id, test_db, owner_user)

    assert isinstance(response, FileResponse)
    assert Path(response.path).read_bytes() == b"already-here"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_turn_audio_allows_admin_for_any_session(
    monkeypatch,
    tmp_path,
    test_db,
    admin_user,
    active_session,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    key = "sessions/1/assistant/admin.mp3"
    AudioCacheService().cache_file(key, b"admin-audio")

    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=key,
        expires_at=utc_now() + timedelta(hours=1),
    )

    class _FakeStorage:
        async def get_file(self, _file_name: str) -> bytes:
            raise AssertionError("storage should not be called on cache hit")

    monkeypatch.setattr(
        "controllers.turns_controller.get_storage_adapter",
        lambda: _FakeStorage(),
    )

    response = await get_turn_audio(turn.id, test_db, admin_user)
    assert isinstance(response, FileResponse)
    assert Path(response.path).read_bytes() == b"admin-audio"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_turn_audio_forbidden_for_other_trainee(
    monkeypatch,
    tmp_path,
    test_db,
    other_user,
    active_session,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    key = "sessions/1/assistant/private.mp3"
    AudioCacheService().cache_file(key, b"secret")

    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=key,
        expires_at=utc_now() + timedelta(hours=1),
    )

    with pytest.raises(AuthorizationError):
        await get_turn_audio(turn.id, test_db, other_user)

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_turn_audio_not_found_unknown_id(test_db, owner_user):
    with pytest.raises(NotFoundError):
        await get_turn_audio(999_999, test_db, owner_user)


@pytest.mark.asyncio
async def test_get_turn_audio_not_found_user_turn(test_db, owner_user, active_session):
    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url="sessions/1/user/x.mp3",
        expires_at=utc_now() + timedelta(hours=1),
        role="user",
    )
    with pytest.raises(NotFoundError):
        await get_turn_audio(turn.id, test_db, owner_user)


@pytest.mark.asyncio
async def test_get_turn_audio_not_found_without_audio_url(test_db, owner_user, active_session):
    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=None,
        expires_at=None,
    )
    with pytest.raises(NotFoundError):
        await get_turn_audio(turn.id, test_db, owner_user)


@pytest.mark.asyncio
async def test_get_turn_audio_succeeds_when_expiration_not_set(
    monkeypatch,
    tmp_path,
    test_db,
    owner_user,
    active_session,
):
    """Assistant audio without audio_expires_at should still be served."""
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    key = "sessions/1/assistant/no-ttl.mp3"
    AudioCacheService().cache_file(key, b"evergreen")

    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url=key,
        expires_at=None,
    )

    class _FakeStorage:
        async def get_file(self, _file_name: str) -> bytes:
            raise AssertionError("storage should not be called on cache hit")

    monkeypatch.setattr(
        "controllers.turns_controller.get_storage_adapter",
        lambda: _FakeStorage(),
    )

    response = await get_turn_audio(turn.id, test_db, owner_user)
    assert isinstance(response, FileResponse)
    assert Path(response.path).read_bytes() == b"evergreen"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_turn_audio_not_found_when_expired(test_db, owner_user, active_session):
    turn = _add_assistant_turn(
        test_db,
        active_session.id,
        audio_url="sessions/1/assistant/old.mp3",
        expires_at=utc_now() - timedelta(minutes=1),
    )
    with pytest.raises(NotFoundError):
        await get_turn_audio(turn.id, test_db, owner_user)
