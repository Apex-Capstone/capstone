import json

from schemas.llm_reviewer import LLMReviewerInput, TranscriptTurnLite
from services.llm_reviewer_prompt import build_llm_reviewer_messages


def test_build_llm_reviewer_messages_basic_shape():
    payload = LLMReviewerInput(
        session_id=1,
        case_id=42,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="clinician", text="Hello, how are you feeling today?"),
            TranscriptTurnLite(turn_number=2, speaker="patient", text="I'm feeling anxious about my symptoms."),
        ],
    )

    messages = build_llm_reviewer_messages(payload)

    assert isinstance(messages, list)
    assert len(messages) == 2

    system_msg, user_msg = messages

    assert system_msg["role"] == "system"
    assert "STRICT JSON" in system_msg["content"]

    assert user_msg["role"] == "user"
    content = user_msg["content"]
    assert "SESSION_PAYLOAD" in content
    assert "transcript_context" in content
    assert "empathy_score" in content
    assert "missed_opportunities" in content
    assert "spikes_annotations" in content


def test_prompt_payload_excludes_rule_derived_fields():
    """Transcript-only evaluator must not embed rule/audit artifacts in the prompt."""
    payload = LLMReviewerInput(
        session_id=99,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="patient", text="I am scared."),
        ],
    )
    user_content = build_llm_reviewer_messages(payload)[1]["content"]
    lower = user_content.lower()
    for forbidden in (
        "rule_spans",
        "rule_links",
        "rule_scores",
        "rule_stages",
        "review_targets",
        "span_id",
        "eo_span",
    ):
        assert forbidden not in lower, f"unexpected token in prompt: {forbidden}"


def test_spikes_completion_rubric_avoids_ordering_language():
    """SPIKES completion should align with stage coverage, not an 'ordering' construct."""
    payload = LLMReviewerInput(
        session_id=1,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="clinician", text="Hi."),
        ],
    )
    system_content = build_llm_reviewer_messages(payload)[0]["content"].lower()
    assert "ordering" not in system_content
    assert "sensible ordering" not in system_content


def test_session_payload_json_has_no_case_title():
    payload = LLMReviewerInput(
        session_id=7,
        case_id=3,
        transcript_context=[
            TranscriptTurnLite(turn_number=1, speaker="patient", text="Hello."),
        ],
    )
    user = build_llm_reviewer_messages(payload)[1]["content"]
    start = user.find("{")
    assert start != -1
    # First JSON object in user message is SESSION_PAYLOAD
    depth = 0
    end = start
    for i in range(start, len(user)):
        if user[i] == "{":
            depth += 1
        elif user[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    blob = json.loads(user[start:end])
    assert "case_title" not in blob
    assert blob.get("session_id") == 7
    assert blob.get("case_id") == 3
