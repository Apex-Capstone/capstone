"""Base ASR (Automatic Speech Recognition) adapter protocol."""

from typing import Protocol


class ASRAdapter(Protocol):
    """Protocol for ASR adapters."""
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> str:
        """Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, etc.)
            
        Returns:
            Transcribed text
        """
        ...

