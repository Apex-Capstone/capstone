from __future__ import annotations

from pathlib import Path

from config.settings import get_settings
from services.audio_cache_service import AudioCacheService


def test_audio_cache_service_reads_cached_file(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    get_settings.cache_clear()

    service = AudioCacheService()
    cached_path = service.cache_file("sessions/1/assistant/reply.mp3", b"hello")

    assert cached_path.exists()
    assert service.get_cached_path("sessions/1/assistant/reply.mp3") == cached_path

    get_settings.cache_clear()


def test_audio_cache_service_evicts_lru_files(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("audio_cache_path", str(tmp_path))
    monkeypatch.setenv("audio_cache_max_bytes", "5")
    get_settings.cache_clear()

    service = AudioCacheService()
    old_path = service.cache_file("sessions/1/assistant/old.mp3", b"1234")
    _ = service.get_cached_path("sessions/1/assistant/old.mp3")
    new_path = service.cache_file("sessions/1/assistant/new.mp3", b"1234")

    assert not old_path.exists()
    assert new_path.exists()

    get_settings.cache_clear()
