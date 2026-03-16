"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
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

    # Research export anonymization (deterministic session IDs)
    research_anon_salt: str = Field(default="research-anon-salt-change-in-production")

    # Plugin configuration
    patient_model_plugin: str = Field(
        default="plugins.patient_models.default_llm_patient:DefaultLLMPatientModel"
    )
    evaluator_plugin: str = Field(
        default="plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"
    )
    metrics_plugins: list[str] = Field(
        default_factory=lambda: ["plugins.metrics.apex_metrics:ApexMetrics"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("patient_model_plugin")
    @classmethod
    def _validate_patient_model_plugin(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(
                f"Invalid plugin path '{v}'. Expected format 'module.path:ClassName'"
            )
        return v

    @field_validator("evaluator_plugin")
    @classmethod
    def _validate_evaluator_plugin(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(
                f"Invalid plugin path '{v}'. Expected format 'module.path:ClassName'"
            )
        return v

    @field_validator("metrics_plugins")
    @classmethod
    def _validate_metrics_plugins(cls, v: list[str]) -> list[str]:
        for path in v:
            if ":" not in path:
                raise ValueError(
                    f"Invalid plugin path '{path}'. Expected format 'module.path:ClassName'"
                )
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
 
