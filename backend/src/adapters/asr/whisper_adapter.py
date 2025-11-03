"""Whisper ASR adapter implementation."""

import tempfile
from pathlib import Path

import openai

from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class WhisperAdapter:
    """Adapter for OpenAI Whisper ASR."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        openai.api_key = self.api_key
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
    ) -> str:
        """Transcribe audio using Whisper API."""
        try:
            # Write audio to temporary file (Whisper API requires file input)
            with tempfile.NamedTemporaryFile(
                suffix=f".{audio_format}",
                delete=False,
            ) as temp_audio:
                temp_audio.write(audio_data)
                temp_path = Path(temp_audio.name)
            
            try:
                # Transcribe using Whisper
                with open(temp_path, "rb") as audio_file:
                    transcript = await openai.Audio.atranscribe(
                        model="whisper-1",
                        file=audio_file,
                    )
                
                return transcript.text.strip()
            finally:
                # Clean up temporary file
                temp_path.unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise

