"""Pydantic schemas for the transcript-only LLM evaluator and hybrid score merge."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TranscriptTurnLite(BaseModel):
    """Minimal representation of a single transcript turn for review."""

    turn_number: int = Field(ge=1)
    speaker: Literal["clinician", "patient"]
    text: str


class LLMReviewerInput(BaseModel):
    """Transcript-only input to the LLM evaluator (no rule-based artifacts)."""

    session_id: int
    case_id: Optional[int] = None

    transcript_context: List[TranscriptTurnLite]

    reviewer_version: str = Field(
        default="v1",
        description="Version string for the evaluator prompt/format.",
    )


class LLMMissedOpportunityItem(BaseModel):
    """LLM-identified empathy opportunity (likely missed or weakly handled)."""

    turn_number: int = Field(ge=1)
    patient_emotional_cue: str = Field(
        description="Short paraphrase of the patient emotional cue (from transcript).",
    )
    clinician_response_summary: Optional[str] = Field(
        default=None,
        description="What the clinician did next in brief, if applicable.",
    )
    why_missed_or_weak: str = Field(
        description="Why this was a missed or weak empathy opportunity.",
    )
    suggested_response: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class LLMSpikesAnnotationItem(BaseModel):
    """LLM annotation of SPIKES-relevant content on a turn."""

    turn_number: int = Field(ge=1)
    stage: Literal[
        "setting",
        "perception",
        "invitation",
        "knowledge",
        "emotion",
        "strategy",
    ]
    evidence_snippet: str = Field(
        max_length=2000,
        description="Short quote or paraphrase from the transcript for this turn.",
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class LLMReviewerOutput(BaseModel):
    """Structured output from the transcript-only LLM evaluator."""

    reviewer_version: str = Field(default="v1")

    empathy_score: float = Field(ge=0.0, le=100.0)
    communication_score: float = Field(ge=0.0, le=100.0)
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)

    missed_opportunities: List[LLMMissedOpportunityItem] = Field(default_factory=list)
    spikes_annotations: List[LLMSpikesAnnotationItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)

    empathy_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    communication_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    spikes_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    notes: Optional[str] = None


class HybridScoreBundle(BaseModel):
    """Bundle of scores (0–100) for rule-only, LLM-only, or merged display."""

    empathy_score: float = Field(ge=0.0, le=100.0)
    communication_score: float = Field(ge=0.0, le=100.0)
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)


# --- Hybrid LLM v2: one prompt per focus area (strict partial schemas) ---


class HybridV2EmpathyPromptOutput(BaseModel):
    """Empathy-only LLM response (hybrid_v2)."""

    model_config = ConfigDict(extra="forbid")

    reviewer_version: str = Field(default="v2", description="Must be v2 for this prompt.")
    empathy_score: float = Field(ge=0.0, le=100.0)
    missed_opportunities: List[LLMMissedOpportunityItem] = Field(default_factory=list)
    empathic_opportunities: List[str] = Field(
        default_factory=list,
        description="Brief bullets of empathic moments or openings the clinician used well.",
    )
    empathy_review_reasoning: Optional[str] = None
    empathy_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HybridV2SpikesStageTurnItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_number: int = Field(ge=1)
    stage: Literal[
        "setting",
        "perception",
        "invitation",
        "knowledge",
        "emotion",
        "strategy",
    ]


class HybridV2SpikesPromptOutput(BaseModel):
    """SPIKES-only LLM response (hybrid_v2)."""

    model_config = ConfigDict(extra="forbid")

    reviewer_version: str = Field(default="v2")
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    spikes_annotations: List[LLMSpikesAnnotationItem] = Field(default_factory=list)
    stage_turn_mapping: List[HybridV2SpikesStageTurnItem] = Field(default_factory=list)
    spikes_sequencing_notes: Optional[str] = None
    spikes_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HybridV2CommunicationPromptOutput(BaseModel):
    """Communication-only LLM response (hybrid_v2)."""

    model_config = ConfigDict(extra="forbid")

    reviewer_version: str = Field(default="v2")
    communication_score: float = Field(ge=0.0, le=100.0)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    clarity_observation: Optional[str] = None
    organization_observation: Optional[str] = None
    professionalism_observation: Optional[str] = None
    question_quality_observation: Optional[str] = None
    communication_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HybridV2CompiledLLMReview(BaseModel):
    """Merged transcript-only LLM review for hybrid_v2 (persists under evaluator_meta['llm_output'])."""

    reviewer_version: str = Field(default="v2")
    empathy_score: float = Field(ge=0.0, le=100.0)
    communication_score: float = Field(ge=0.0, le=100.0)
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)

    missed_opportunities: List[LLMMissedOpportunityItem] = Field(default_factory=list)
    spikes_annotations: List[LLMSpikesAnnotationItem] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)

    empathic_opportunities: List[str] = Field(default_factory=list)
    empathy_review_reasoning: Optional[str] = None
    spikes_sequencing_notes: Optional[str] = None
    stage_turn_mapping: List[HybridV2SpikesStageTurnItem] = Field(default_factory=list)
    clarity_observation: Optional[str] = None
    organization_observation: Optional[str] = None
    professionalism_observation: Optional[str] = None
    question_quality_observation: Optional[str] = None

    empathy_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    communication_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    spikes_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    notes: Optional[str] = None
    llm_score_source: Dict[str, str] = Field(
        default_factory=dict,
        description="Per component empathy|communication|spikes: 'llm' or 'rule_fallback'.",
    )
