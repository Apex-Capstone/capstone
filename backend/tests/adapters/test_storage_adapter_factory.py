from __future__ import annotations

from pathlib import Path

import pytest

from adapters.storage import SupabaseStorageAdapter, get_storage_adapter
from adapters.storage.local_storage import LocalStorageAdapter
from config.settings import get_settings


def test_get_storage_adapter_returns_supabase_storage_adapter(monkeypatch):
    monkeypatch.setenv("supabase_url", "https://example.supabase.co")
    monkeypatch.setenv("supabase_service_role_key", "service-role-key")
    monkeypatch.setenv("supabase_storage_bucket", "assistant-audio")
    get_settings.cache_clear()

    adapter = get_storage_adapter()

    assert isinstance(adapter, SupabaseStorageAdapter)

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_local_storage_adapter_writes_file_and_returns_media_url(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("local_storage_path", str(tmp_path))
    monkeypatch.setenv("public_base_url", "http://localhost:8000")
    get_settings.cache_clear()

    adapter = LocalStorageAdapter()
    url = await adapter.put_file(
        b"hello",
        "sessions/12/assistant/reply.mp3",
        content_type="audio/mpeg",
    )

    assert url == "http://localhost:8000/media/sessions/12/assistant/reply.mp3"
    assert (tmp_path / "sessions" / "12" / "assistant" / "reply.mp3").read_bytes() == b"hello"

    get_settings.cache_clear()
