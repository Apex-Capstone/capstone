"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    
    # Database
    database_url: str = Field(...)
    
    # JWT
    secret_key: str = Field(...)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    
    # CORS
    cors_origins: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])
    
    # OpenAI
    openai_api_key: str = Field(...)
    openai_model_id: str = Field(default="gpt-4")
    
    # Google Gemini
    gemini_api_key: str = Field(...)
    gemini_model_id: str = Field(default="gemini-pro")
    
    # AWS S3
    aws_access_key_id: str = Field(...)
    aws_secret_access_key: str = Field(...)
    aws_region: str = Field(default="us-east-1")
    s3_bucket_name: str = Field(...)
    
    # LLM Configuration
    default_llm_provider: str = Field(default="openai")
    
    # TTS/ASR Configuration
    tts_provider: str = Field(default="generic")
    asr_provider: str = Field(default="whisper")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

