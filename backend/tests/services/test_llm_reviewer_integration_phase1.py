import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from schemas.llm_reviewer import LLMReviewerOutput
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_BAD
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)


import services.scoring_service as scoring_service_module


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    """Create a minimal test user."""
    user = User(
        email="apex_llm_reviewer_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="APEX LLM Reviewer Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    """Create a minimal test case."""
    case = Case(
        title="APEX Seeded Fixture Case (LLM Reviewer Phase1)",
        description="Case for seeded transcript scoring tests.",
        script="Script content is not used directly in scoring for these tests.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


class DummyOpenAIAdapter:
    """Placeholder to avoid initializing OpenAIAdapter in tests."""


class DummyLLMReviewerServiceSuccess:
    """Mock evaluator returning fixed transcript-only scores (enables hybrid merge)."""

    def __init__(self, llm_adapter):
        self.llm_adapter = llm_adapter

    async def review(self, payload):
        # Fixed LLM component scores; overall matches rubric in prompt
        e, c, s = 50.0, 50.0, 50.0
        o = 0.5 * e + 0.2 * c + 0.3 * s
        return LLMReviewerOutput(
            reviewer_version="v1",
            empathy_score=e,
            communication_score=c,
            spikes_completion_score=s,
            overall_score=o,
            missed_opportunities=[],
            spikes_annotations=[],
            strengths=["mock"],
            areas_for_improvement=["mock"],
            notes=None,
        )


class DummyLLMReviewerServiceNone:
    """Mock evaluator that simulates failure (returns None)."""

    def __init__(self, llm_adapter):
        self.llm_adapter = llm_adapter

    async def review(self, payload):
        return None


def _scores_tuple(feedback: FeedbackResponse):
    return (
        feedback.empathy_score,
        feedback.communication_score,
        feedback.spikes_completion_score,
        feedback.overall_score,
    )


@pytest.mark.asyncio
async def test_hybrid_llm_success_merges_scores(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.delenv("LLM_REVIEWER_REAL_CALLS", raising=False)
    baseline = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    baseline_feedback: FeedbackResponse = baseline["feedback"]
    baseline_scores = _scores_tuple(baseline_feedback)
    assert baseline_feedback.evaluator_meta is None

    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", DummyOpenAIAdapter)
    monkeypatch.setattr(
        "services.llm_reviewer_service.LLMReviewerService",
        DummyLLMReviewerServiceSuccess,
    )

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    feedback: FeedbackResponse = result["feedback"]

    assert _scores_tuple(feedback) != baseline_scores
    assert feedback.evaluator_meta is not None
    assert feedback.evaluator_meta.get("phase") == "hybrid_llm_v1"
    assert feedback.evaluator_meta.get("status") == "success"
    assert feedback.evaluator_meta.get("rule_scores") is not None
    assert feedback.evaluator_meta.get("llm_scores") is not None
    merged = feedback.evaluator_meta.get("merged_scores") or {}
    assert "empathy_score" in merged
    # LLM components fixed at 50 -> merged empathy = 0.7 * rule + 15
    r_emp = feedback.evaluator_meta["rule_scores"]["empathy_score"]
    assert merged["empathy_score"] == pytest.approx(0.7 * r_emp + 0.3 * 50.0, rel=1e-4)
    assert merged["overall_score"] == pytest.approx(
        0.5 * merged["empathy_score"]
        + 0.2 * merged["communication_score"]
        + 0.3 * merged["spikes_completion_score"],
        rel=1e-4,
    )
    lo = feedback.evaluator_meta.get("llm_output") or {}
    assert "empathy_score" in lo
    assert "missed_opportunities" in lo
    assert "spikes_annotations" in lo
    assert "strengths" in lo
    assert "areas_for_improvement" in lo


@pytest.mark.asyncio
async def test_textual_feedback_uses_rule_component_scores_not_merged(
    test_db, test_user, test_case, monkeypatch
):
    """Strengths/improvements follow rule-based components while displayed scores can be hybrid."""
    captured: list[tuple[float, float, float]] = []

    def _capture_textual_scores(self, e, c, s, eo_spans=None):
        captured.append((e, c, s))
        return ("s", "i")

    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", DummyOpenAIAdapter)
    monkeypatch.setattr(
        "services.llm_reviewer_service.LLMReviewerService",
        DummyLLMReviewerServiceSuccess,
    )
    monkeypatch.setattr(
        scoring_service_module.ScoringService,
        "_generate_textual_feedback",
        _capture_textual_scores,
    )

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    feedback: FeedbackResponse = result["feedback"]
    assert len(captured) == 1
    rs = feedback.evaluator_meta["rule_scores"]
    assert captured[0][0] == pytest.approx(rs["empathy_score"])
    assert captured[0][1] == pytest.approx(rs["communication_score"])
    assert captured[0][2] == pytest.approx(rs["spikes_completion_score"])


@pytest.mark.asyncio
async def test_hybrid_llm_failure_falls_back_to_rule_scores(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.delenv("LLM_REVIEWER_REAL_CALLS", raising=False)
    baseline = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    baseline_feedback: FeedbackResponse = baseline["feedback"]
    baseline_scores = _scores_tuple(baseline_feedback)

    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", DummyOpenAIAdapter)
    monkeypatch.setattr(
        "services.llm_reviewer_service.LLMReviewerService",
        DummyLLMReviewerServiceNone,
    )

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    feedback: FeedbackResponse = result["feedback"]

    assert _scores_tuple(feedback) == baseline_scores
    assert feedback.evaluator_meta is not None
    assert feedback.evaluator_meta.get("phase") == "hybrid_llm_v1"
    assert feedback.evaluator_meta.get("status") == "failed"
    assert feedback.evaluator_meta.get("llm_scores") is None
    assert feedback.evaluator_meta.get("merged_scores") is None
    assert feedback.evaluator_meta.get("rule_scores") is not None
