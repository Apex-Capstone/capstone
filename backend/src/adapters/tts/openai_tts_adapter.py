"""OpenAI TTS adapter implementation."""

from openai import AsyncOpenAI

from adapters.tts.base import TTSAudioResult
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class OpenAITTSAdapter:
    """Adapter for OpenAI's text-to-speech API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model_id = settings.openai_tts_model_id
        self.default_voice = settings.openai_tts_voice
        self.response_format = settings.openai_tts_response_format
        self.default_instructions = settings.openai_tts_instructions
        self.speed = settings.openai_tts_speed

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str = "default",
        instructions: str | None = None,
    ) -> TTSAudioResult:
        """Generate speech bytes from text."""
        resolved_voice = self.default_voice if voice_id == "default" else voice_id
        resolved_instructions = instructions or self.default_instructions or None

        logger.info(
            "Synthesizing OpenAI TTS with model=%s voice=%s format=%s",
            self.model_id,
            resolved_voice,
            self.response_format,
        )

        response = await self.client.audio.speech.create(
            model=self.model_id,
            voice=resolved_voice,
            input=text,
            instructions=resolved_instructions,
            response_format=self.response_format,
            speed=self.speed,
        )

        return TTSAudioResult(
            audio_data=response.read(),
            content_type=f"audio/{self.response_format}",
            file_extension=self.response_format,
        )
