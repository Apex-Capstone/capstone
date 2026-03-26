"""LLM adapters module."""

from adapters.llm.base import LLMAdapter
from adapters.llm.openai_adapter import OpenAIAdapter

try:
    from adapters.llm.gemini_adapter import GeminiAdapter
except ImportError:  # pragma: no cover - optional dependency resolution
    GeminiAdapter = None

__all__ = [
    "LLMAdapter",
    "OpenAIAdapter",
    "GeminiAdapter",
]

