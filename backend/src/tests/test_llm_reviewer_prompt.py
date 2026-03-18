import json

from schemas.llm_reviewer import (
    LLMReviewerInput,
    RuleLinkEvidence,
    RuleScoreSnapshot,
    RuleStageEvent,
    TranscriptTurnLite,
    ReviewTarget,
)
from services.llm_reviewer_prompt import build_llm_reviewer_messages


def test_build_llm_reviewer_messages_basic_shape():
    payload = LLMReviewerInput(
        session_id=1,
        case_id=42,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="clinician", text="Hello, how are you feeling today?"),
            TranscriptTurnLite(turn_number=2, speaker="patient", text="I'm feeling anxious about my symptoms."),
        ],
        rule_spans=[],
        rule_links=[
            RuleLinkEvidence(
                eo_span_id="eo-1",
                linked_response_span_ids=[],
                linked_elicitation_span_ids=[],
                rule_addressed=False,
                rule_missed_opportunity=True,
            )
        ],
        rule_stages=[
            RuleStageEvent(turn_number=1, stage="setting"),
        ],
        rule_scores=RuleScoreSnapshot(
            empathy_score=50.0,
            communication_score=60.0,
            clinical_reasoning_score=55.0,
            professionalism_score=70.0,
            spikes_completion_score=40.0,
            overall_score=55.0,
        ),
        review_targets=[
            ReviewTarget(
                target_id="t1",
                target_type="missed_opportunity",
                eo_span_id="eo-1",
                response_span_ids=[],
                elicitation_span_ids=[],
                context_turn_numbers=[1, 2],
                rule_summary="Rule-based system flagged this as a missed opportunity.",
            )
        ],
    )

    messages = build_llm_reviewer_messages(payload)

    # Exactly two messages: system and user
    assert isinstance(messages, list)
    assert len(messages) == 2

    system_msg, user_msg = messages

    assert system_msg["role"] == "system"
    assert "STRICT JSON ONLY" in system_msg["content"]

    assert user_msg["role"] == "user"
    content = user_msg["content"]
    assert "TRANSCRIPT_CONTEXT" in content
    assert "review_targets" in content or "review_targets".upper() in content.lower()
    assert "session_assessment" in content

    # Ensure user content includes a valid JSON payload section
    # We find the first '{' and try to parse until the matching end.
    start_idx = content.find("{")
    assert start_idx != -1
