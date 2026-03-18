"""Pydantic schemas for the hybrid LLM reviewer system.

These models are used to structure:
- Input to the LLM reviewer (rule-based context + transcript)
- Output from the LLM reviewer (event-level and session-level assessments)
- Hybrid feedback objects that combine rule-based and LLM-informed scores.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class TranscriptTurnLite(BaseModel):
    """Minimal representation of a single transcript turn for review."""

    turn_number: int = Field(ge=1)
    speaker: Literal["clinician", "patient"]
    text: str


class RuleDetectedSpan(BaseModel):
    """Rule-based detected AFCE / SPIKES-related span."""

    span_id: str
    turn_number: int = Field(ge=1)
    category: Literal["eo", "response", "elicitation"]
    text: str

    dimension: Optional[Literal["Feeling", "Judgment", "Appreciation"]] = None
    explicit_or_implicit: Optional[Literal["explicit", "implicit"]] = None

    # Response/elicitation subtypes (when applicable)
    response_type: Optional[str] = None
    elicitation_type: Optional[str] = None

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional rule-based confidence in [0, 1].",
    )


class RuleLinkEvidence(BaseModel):
    """Rule-based evidence about EO→response / EO→elicitation relationships."""

    eo_span_id: str
    linked_response_span_ids: List[str] = Field(default_factory=list)
    linked_elicitation_span_ids: List[str] = Field(default_factory=list)

    rule_addressed: bool
    rule_missed_opportunity: bool


class RuleStageEvent(BaseModel):
    """Rule-based SPIKES stage assigned to a specific turn."""

    turn_number: int = Field(ge=1)
    stage: Literal["setting", "perception", "invitation", "knowledge", "emotion", "strategy"]


class RuleScoreSnapshot(BaseModel):
    """Snapshot of rule-based scores at the time of review."""

    empathy_score: float = Field(ge=0.0, le=100.0)
    communication_score: float = Field(ge=0.0, le=100.0)
    clinical_reasoning_score: float = Field(ge=0.0, le=100.0)
    professionalism_score: float = Field(ge=0.0, le=100.0)
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)


class ReviewTarget(BaseModel):
    """Unit of review for the LLM (event-level or session-level)."""

    target_id: str
    target_type: Literal["missed_opportunity", "empathy_response", "session_summary"]

    eo_span_id: Optional[str] = None
    response_span_ids: List[str] = Field(default_factory=list)
    elicitation_span_ids: List[str] = Field(default_factory=list)
    context_turn_numbers: List[int] = Field(
        default_factory=list,
        description="Turn numbers providing context for this target.",
    )

    rule_summary: Optional[str] = Field(
        default=None,
        description="Short rule-based summary or rationale provided to the LLM.",
    )


class LLMReviewerInput(BaseModel):
    """Full input payload to the LLM reviewer."""

    session_id: int
    case_id: Optional[int] = None

    transcript_context: List[TranscriptTurnLite]
    rule_spans: List[RuleDetectedSpan]
    rule_links: List[RuleLinkEvidence]
    rule_stages: List[RuleStageEvent]
    rule_scores: RuleScoreSnapshot

    review_targets: List[ReviewTarget]

    reviewer_version: str = Field(
        default="v1",
        description="Version string for the reviewer prompt/format.",
    )


class ReviewedEventAssessment(BaseModel):
    """LLM review assessment for a specific target/event."""

    target_id: str

    acknowledged_emotion: bool
    validated_feeling: bool
    missed_opportunity: bool

    empathy_quality_score_0_to_4: int = Field(ge=0, le=4)

    disposition: Literal["confirm", "upgrade", "downgrade", "uncertain"]
    confidence: float = Field(ge=0.0, le=1.0)

    rationale: str
    suggested_response: Optional[str] = None


class SessionLevelAssessment(BaseModel):
    """Session-level qualitative assessment from the LLM reviewer."""

    empathy_quality_score_0_to_4: int = Field(ge=0, le=4)
    clarity_quality_score_0_to_4: int = Field(ge=0, le=4)
    supportiveness_quality_score_0_to_4: int = Field(ge=0, le=4)

    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

    strengths: List[str] = Field(default_factory=list)
    improvement_points: List[str] = Field(default_factory=list)


class LLMReviewerOutput(BaseModel):
    """Primary output structure from the LLM reviewer."""

    reviewer_version: str = Field(default="v1")

    reviewed_events: List[ReviewedEventAssessment] = Field(default_factory=list)
    session_assessment: SessionLevelAssessment

    overall_confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str] = None


class HybridScoreBundle(BaseModel):
    """Bundle of scores, used for both rule-based and hybrid-adjusted scores."""

    empathy_score: float = Field(ge=0.0, le=100.0)
    communication_score: float = Field(ge=0.0, le=100.0)
    clinical_reasoning_score: float = Field(ge=0.0, le=100.0)
    professionalism_score: float = Field(ge=0.0, le=100.0)
    spikes_completion_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)


class HybridCoachingPoint(BaseModel):
    """Single hybrid coaching point (strength, improvement, or suggested response)."""

    kind: Literal["strength", "improvement", "suggested_response"]
    text: str
    related_turn_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional turn number this coaching point refers to.",
    )


class HybridFeedbackOutput(BaseModel):
    """Final hybrid feedback object combining rule-based and LLM-informed views."""

    session_id: int

    rule_scores: HybridScoreBundle
    hybrid_scores: HybridScoreBundle

    llm_overall_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    coaching_summary: List[HybridCoachingPoint] = Field(default_factory=list)
    reviewed_events: List[ReviewedEventAssessment] = Field(default_factory=list)

    merge_policy_version: str = Field(
        default="v1",
        description="Version of the rule/LLM merge policy used.",
    )
    llm_reviewer_version: Optional[str] = Field(
        default=None,
        description="Version of the LLM reviewer that produced this output.",
    )

