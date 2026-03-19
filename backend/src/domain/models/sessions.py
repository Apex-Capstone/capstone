"""Session and turn request/response schemas."""

import json
from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TimelineEvent(BaseModel):
    """Single event for conversation feedback timeline."""
    turn_number: int
    type: Literal["eo", "response", "missed", "spikes"]
    label: str


class SuggestedResponse(BaseModel):
    """Suggested empathetic response for a missed opportunity."""
    turn_number: int
    patient_text: str
    suggestion: str


class SessionCreate(BaseModel):
    """Session creation schema."""
    
    case_id: int
    force_new: bool = Field(default=False)


class SessionUpdate(BaseModel):
    """Session update schema."""
    
    state: Optional[str] = None
    current_spikes_stage: Optional[str] = None
    meta: Optional[str] = None


class TurnCreate(BaseModel):
    """Turn creation schema."""
    
    text: str
    audio_url: Optional[str] = None
    enable_tts: bool = False


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
    spans_json: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class TurnResponseWithAudio(BaseModel):
    """Turn response with transcript metadata and optional assistant TTS."""

    turn: TurnResponse
    patient_reply: str
    transcript: str | None = None
    audio_url: str | None = None
    assistant_audio_url: str | None = None
    spikes_stage: str | None = None



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
    meta: Optional[str] = Field(default=None, alias="session_metadata")
    evaluator_plugin: Optional[str] = None
    evaluator_version: Optional[str] = None
    patient_model_plugin: Optional[str] = None
    patient_model_version: Optional[str] = None
    metrics_plugins: Optional[list] = None  # JSON array of plugin names
    case_title: Optional[str] = None
    # Computed: "closed" when ended_at is set, else "active"
    status: Literal["active", "closed"]

    @field_validator("metrics_plugins", mode="before")
    @classmethod
    def _metrics_plugins_from_entity(cls, v: object) -> Optional[list]:
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
    
    model_config = ConfigDict(from_attributes=True, extra="ignore")



class SessionDetailResponse(SessionResponse):
    """Detailed session response with turns."""
    
    turns: list[TurnResponse] = []


class SessionListResponse(BaseModel):
    """Session list response schema."""
    
    sessions: list[SessionResponse]
    total: int


class FeedbackResponse(BaseModel):
    """Feedback response schema with AFCE + SPIKES aligned metrics only."""
    
    # Core scores
    id: int
    session_id: int
    empathy_score: float
    communication_score: float | None = None
    clinical_reasoning_score: float | None = None
    professionalism_score: float | None = None
    spikes_completion_score: float
    overall_score: float
    
    # AFCE-structured empathy metrics
    eo_counts_by_dimension: Optional[dict] = None  # {"Feeling": {"explicit": int, "implicit": int}, "Judgment": {...}, "Appreciation": {...}}
    elicitation_counts_by_type: Optional[dict] = None  # {"direct": {"Feeling": int, "Judgment": int, "Appreciation": int}, "indirect": {...}}
    response_counts_by_type: Optional[dict] = None  # {"understanding": int, "sharing": int, "acceptance": int}
    
    # Placeholders for Part 2 (span-relation linking)
    relations: Optional[list] = None  # list of span relations - will be populated in Part 2
    linkage_stats: Optional[dict] = None  # will be computed in Part 2 with span relations
    missed_opportunities_by_dimension: Optional[dict] = None  # {"Feeling": int, "Judgment": int, "Appreciation": int} - will be computed in Part 2
    eo_to_elicitation_links: Optional[dict] = None  # will be computed in Part 2
    eo_to_response_links: Optional[dict] = None  # will be computed in Part 2
    missed_opportunities: Optional[list] = None  # will be computed in Part 2
    
    # Turn-level span data (for analysis)
    eo_spans: Optional[list] = None  # list of EO spans with dimensions (for turn-level analysis)
    elicitation_spans: Optional[list] = None  # list of elicitation spans with types
    response_spans: Optional[list] = None  # list of response spans with types
    
    # SPIKES coverage
    spikes_coverage: Optional[dict] = None
    spikes_timestamps: Optional[dict] = None
    spikes_strategies: Optional[dict] = None
    
    # Questioning & style
    question_breakdown: Optional[dict] = None
    
    # Metadata (optional, only included if populated)
    bias_probe_info: Optional[dict] = None
    evaluator_meta: Optional[dict] = None
    latency_ms_avg: float = 0.0
    
    # Textual feedback
    strengths: Optional[str] = None
    areas_for_improvement: Optional[str] = None
    detailed_feedback: Optional[str] = None

    # Conversation feedback timeline
    timeline_events: Optional[list[TimelineEvent]] = None
    suggested_responses: Optional[list[SuggestedResponse]] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, extra="ignore", exclude_none=True)
    
    @classmethod
    def _remove_empty_values(cls, data: dict) -> dict:
        """Recursively remove empty values (None, empty lists, empty dicts, empty strings)."""
        if not isinstance(data, dict):
            return data
        
        cleaned = {}
        for key, value in data.items():
            # Skip None values (already handled by exclude_none=True, but keep for safety)
            if value is None:
                continue
            
            # Skip empty strings
            if isinstance(value, str) and value.strip() == "":
                continue
            
            # Handle lists: clean nested structures and skip if empty after cleaning
            if isinstance(value, list):
                cleaned_list = []
                for item in value:
                    if isinstance(item, dict):
                        cleaned_item = cls._remove_empty_values(item)
                        if cleaned_item:  # Only add non-empty dicts
                            cleaned_list.append(cleaned_item)
                    elif item is not None and not (isinstance(item, str) and item.strip() == ""):
                        cleaned_list.append(item)
                if cleaned_list:  # Only include if list has items after cleaning
                    cleaned[key] = cleaned_list
                continue
            
            # Recursively clean nested dicts
            if isinstance(value, dict):
                cleaned_value = cls._remove_empty_values(value)
                # Only include if it's not empty after cleaning
                if cleaned_value:
                    cleaned[key] = cleaned_value
            else:
                cleaned[key] = value
        
        return cleaned
    
    def model_dump(self, **kwargs) -> dict:
        """Override model_dump to remove empty values recursively."""
        # Get default serialized data with exclude_none=True
        kwargs.setdefault('exclude_none', True)
        data = super().model_dump(**kwargs)
        # Remove empty values recursively
        return self._remove_empty_values(data)
    
    def model_dump_json(self, **kwargs) -> str:
        """Override model_dump_json to remove empty values before JSON serialization."""
        import json
        data = self.model_dump(**kwargs)
        return json.dumps(data)



class WebSocketMessage(BaseModel):
    """WebSocket message schema."""
    
    type: str  # user_message, assistant_message, system_message, error
    content: str
    meta: Optional[dict] = None

