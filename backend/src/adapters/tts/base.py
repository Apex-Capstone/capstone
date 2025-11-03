"""Base TTS (Text-to-Speech) adapter protocol."""

from typing import Protocol


class TTSAdapter(Protocol):
    """Protocol for TTS adapters."""
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = "default",
    ) -> bytes:
        """Convert text to speech audio.
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            
        Returns:
            Audio data as bytes
        """
        ...

