"""Session and turn request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Session creation schema."""
    
    case_id: int


class SessionUpdate(BaseModel):
    """Session update schema."""
    
    state: Optional[str] = None
    current_spikes_stage: Optional[str] = None
    metadata: Optional[str] = None


class TurnCreate(BaseModel):
    """Turn creation schema."""
    
    text: str
    audio_url: Optional[str] = None


class TurnResponse(BaseModel):
    """Turn response schema."""
    
    id: int
    session_id: int
    turn_number: int
    role: str
    text: str
    audio_url: Optional[str]
    metrics_json: Optional[str]
    spikes_stage: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Session response schema."""
    
    id: int
    user_id: int
    case_id: int
    state: str
    current_spikes_stage: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    metadata: Optional[str]
    
    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    """Detailed session response with turns."""
    
    turns: list[TurnResponse] = []


class SessionListResponse(BaseModel):
    """Session list response schema."""
    
    sessions: list[SessionResponse]
    total: int


class FeedbackResponse(BaseModel):
    """Feedback response schema."""
    
    id: int
    session_id: int
    empathy_score: float
    communication_score: float
    spikes_completion_score: float
    overall_score: float
    empathy_spikes: Optional[str]
    question_ratios: Optional[str]
    reassurance_moments: Optional[str]
    spikes_coverage: Optional[str]
    strengths: Optional[str]
    areas_for_improvement: Optional[str]
    detailed_feedback: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    
    type: str  # user_message, assistant_message, system_message, error
    content: str
    metadata: Optional[dict] = None

