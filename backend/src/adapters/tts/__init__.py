"""TTS adapters module."""

from adapters.tts.base import TTSAdapter
from adapters.tts.generic_tts_adapter import GenericTTSAdapter

__all__ = [
    "TTSAdapter",
    "GenericTTSAdapter",
]

