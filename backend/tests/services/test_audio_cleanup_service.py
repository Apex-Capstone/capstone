from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings
from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from services.audio_cache_service import AudioCacheService
from services.audio_cleanup_service import AudioCleanupService


class _DummyStorageAdapter:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.deleted_files: list[str] = []

    async def put_file(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        return file_name

    async def get_file(self, file_name: str) -> bytes:
        return b""

    async def delete_file(self, file_name: str) -> bool:
        self.deleted_files.append(file_name)
        if self.should_fail:
            raise RuntimeError("storage unavailable")
        return True

    async def get_presigned_url(self, file_name: str, expiration: int = 3600) -> str:
        return f"https://example.com/{file_name}"


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


def _seed_turns(test_db):
    user = User(
        email="cleanup_tester@example.com",        
        role="trainee",
        full_name="Cleanup Tester",
    )
    case = Case(
        title="Cleanup Case",
        description="Case for cleanup tests.",
        script="Script",
        difficulty_level="beginner",
        category="test",
        patient_background="Background",
        expected_spikes_flow=None,
    )
    test_db.add_all([user, case])
    test_db.commit()

    session = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="active",
        current_spikes_stage="setting",
    )
    test_db.add(session)
    test_db.commit()

    expired_assistant_turn = Turn(
        session_id=session.id,
        turn_number=1,
        role="assistant",
        text="Expired reply",
        audio_url="sessions/1/assistant/expired.mp3",
        audio_expires_at=datetime.utcnow() - timedelta(minutes=5),
    )
    fresh_assistant_turn = Turn(
        session_id=session.id,
        turn_number=2,
        role="assistant",
        text="Fresh reply",
        audio_url="sessions/1/assistant/fresh.mp3",
        audio_expires_at=datetime.utcnow() + timedelta(minutes=5),
    )
    user_turn = Turn(
        session_id=session.id,
        turn_number=3,
        role="user",
        text="User text",
        audio_url="sessions/1/user/input.mp3",
        audio_expires_at=datetime.utcnow() - timedelta(minutes=5),
    )
    test_db.add_all([expired_assistant_turn, fresh_assistant_turn, user_turn])
    test_db.commit()

    return expired_assistant_turn, fresh_assistant_turn, user_turn


@pytest.mark.asyncio
async def test_audio_cleanup_service_clears_expired_assistant_audio(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_db,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    expired_turn, fresh_turn, user_turn = _seed_turns(test_db)
    cache_service = AudioCacheService()
    cached_path = cache_service.cache_file(expired_turn.audio_url, b"expired-audio")
    fresh_cached_path = cache_service.cache_file(fresh_turn.audio_url, b"fresh-audio")

    storage = _DummyStorageAdapter()
    service = AudioCleanupService(
        db=test_db,
        storage_adapter=storage,
        cache_service=cache_service,
    )

    cleaned_count = await service.cleanup_expired_audio()

    test_db.refresh(expired_turn)
    test_db.refresh(fresh_turn)
    test_db.refresh(user_turn)

    assert cleaned_count == 1
    assert storage.deleted_files == ["sessions/1/assistant/expired.mp3"]
    assert expired_turn.audio_url is None
    assert expired_turn.audio_expires_at is None
    assert not cached_path.exists()
    assert fresh_turn.audio_url == "sessions/1/assistant/fresh.mp3"
    assert fresh_turn.audio_expires_at is not None
    assert fresh_cached_path.exists()
    assert user_turn.audio_url == "sessions/1/user/input.mp3"
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_audio_cleanup_service_keeps_db_reference_when_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_db,
):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    expired_turn, _, _ = _seed_turns(test_db)
    cache_service = AudioCacheService()
    cached_path = cache_service.cache_file(expired_turn.audio_url, b"expired-audio")

    storage = _DummyStorageAdapter(should_fail=True)
    service = AudioCleanupService(
        db=test_db,
        storage_adapter=storage,
        cache_service=cache_service,
    )

    cleaned_count = await service.cleanup_expired_audio()

    test_db.refresh(expired_turn)

    assert cleaned_count == 0
    assert storage.deleted_files == ["sessions/1/assistant/expired.mp3"]
    assert expired_turn.audio_url == "sessions/1/assistant/expired.mp3"
    assert expired_turn.audio_expires_at is not None
    assert cached_path.exists()
    get_settings.cache_clear()
