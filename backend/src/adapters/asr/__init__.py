"""ASR adapters module."""

from adapters.asr.base import ASRAdapter
from adapters.asr.whisper_adapter import WhisperAdapter

__all__ = [
    "ASRAdapter",
    "WhisperAdapter",
]

