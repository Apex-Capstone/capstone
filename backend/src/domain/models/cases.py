"""Case request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class CaseResponse(CaseBase):
    """Case response schema."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class CaseListResponse(BaseModel):
    """Case list response schema."""
    
    cases: list[CaseResponse]
    total: int

