"""TTS adapters module."""

from adapters.tts.base import TTSAdapter
from adapters.tts.generic_tts_adapter import GenericTTSAdapter
from adapters.tts.openai_tts_adapter import OpenAITTSAdapter
from config.settings import get_settings


def get_tts_adapter() -> TTSAdapter:
    """Return the configured TTS adapter implementation."""
    settings = get_settings()
    provider = settings.tts_provider.lower().strip()

    if provider == "openai":
        return OpenAITTSAdapter()
    if provider == "generic":
        return GenericTTSAdapter()

    raise ValueError(f"Unsupported TTS provider: {settings.tts_provider}")

__all__ = [
    "TTSAdapter",
    "GenericTTSAdapter",
    "OpenAITTSAdapter",
    "get_tts_adapter",
]

