"""Base TTS (Text-to-Speech) adapter protocol."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TTSAudioResult:
    """Synthesized audio payload plus metadata needed for storage."""

    audio_data: bytes
    content_type: str
    file_extension: str


class TTSAdapter(Protocol):
    """Protocol for TTS adapters."""
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = "default",
        instructions: str | None = None,
    ) -> TTSAudioResult:
        """Convert text to speech audio.
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            instructions: Optional provider-specific style instructions
            
        Returns:
            Synthesized audio payload and metadata
        """
        ...

