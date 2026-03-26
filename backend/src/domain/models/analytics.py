"""Trainee analytics schemas."""

from typing import Optional

from pydantic import BaseModel

from core.time import UTCDateTime


class TraineeSessionAnalytics(BaseModel):
    """Per-session analytics row for the authenticated trainee."""

    session_id: int
    case_id: int
    case_title: str
    empathy_score: float
    communication_score: float
    clinical_score: float
    spikes_completion_score: float
    spikes_coverage_percent: float
    duration_seconds: int
    created_at: UTCDateTime
    eo_addressed_rate: Optional[float] = None
    spikes_stages_covered: Optional[list[str]] = None

