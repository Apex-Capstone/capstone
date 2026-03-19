from __future__ import annotations

from pathlib import Path

import pytest

from adapters.storage import LocalStorageAdapter, get_storage_adapter
from config.settings import get_settings


def test_get_storage_adapter_returns_local_storage_adapter(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setenv("local_storage_path", str(tmp_path))
    get_settings.cache_clear()

    adapter = get_storage_adapter()

    assert isinstance(adapter, LocalStorageAdapter)

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
