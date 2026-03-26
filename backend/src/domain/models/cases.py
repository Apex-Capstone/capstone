"""Case request/response schemas."""

import json
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from core.time import UTCDateTime


class CaseBase(BaseModel):
    """Base case schema."""
    
    title: str
    description: Optional[str] = None
    script: str
    objectives: Optional[str] = None
    difficulty_level: Optional[str] = "intermediate"
    category: Optional[str] = None
    patient_background: Optional[str] = None
    expected_spikes_flow: Optional[str] = None
    evaluator_plugin: Optional[str] = None
    patient_model_plugin: Optional[str] = None
    metrics_plugins: Optional[List[str]] = None


class CaseCreate(CaseBase):
    """Case creation schema."""
    pass


class CaseUpdate(BaseModel):
    """Case update schema."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    script: Optional[str] = None
    objectives: Optional[str] = None
    difficulty_level: Optional[str] = None
    category: Optional[str] = None
    patient_background: Optional[str] = None
    expected_spikes_flow: Optional[str] = None
    evaluator_plugin: Optional[str] = None
    patient_model_plugin: Optional[str] = None
    metrics_plugins: Optional[List[str]] = None


class CaseResponse(CaseBase):
    """Case response schema."""
    
    id: int
    created_at: UTCDateTime
    updated_at: UTCDateTime
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @field_validator("metrics_plugins", mode="before")
    @classmethod
    def _metrics_plugins_from_entity(cls, v: object) -> Optional[List[str]]:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return None


class CaseListResponse(BaseModel):
    """Case list response schema."""
    
    cases: list[CaseResponse]
    total: int

