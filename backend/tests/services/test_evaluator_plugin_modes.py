"""Plugin-selected baseline vs hybrid behavior at session close."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.user import User
from plugins.evaluators.apex_baseline_evaluator import ApexBaselineEvaluator  # noqa: F401
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator  # noqa: F401
from schemas.llm_reviewer import LLMReviewerOutput
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_BAD
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)


@pytest.fixture
def test_db():
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
    user = User(
        email="eval_mode_tester@example.com",
        hashed_password="x",
        role="trainee",
        full_name="Eval Mode Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Eval Mode Case",
        description="d",
        script="s",
        difficulty_level="intermediate",
        category="test",
        patient_background="pb",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
async def test_baseline_plugin_never_calls_llm_even_when_env_on(
    test_db, test_user, test_case, monkeypatch
):
    from unittest.mock import MagicMock

    mock_llm_cls = MagicMock()
    monkeypatch.setattr("services.llm_reviewer_service.LLMReviewerService", mock_llm_cls)
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db,
        test_user,
        test_case,
        TEST_CONVERSATION_BAD,
        evaluator_plugin=ApexBaselineEvaluator.name,
    )
    assert mock_llm_cls.call_count == 0
    fb = result["feedback"]
    assert fb.evaluator_meta is not None
    assert fb.evaluator_meta.get("phase") == "baseline_rule_v1"


@pytest.mark.asyncio
async def test_hybrid_plugin_calls_llm_when_env_on(test_db, test_user, test_case, monkeypatch):
    review_calls: list = []

    class _MockLLM:
        def __init__(self, adapter):
            pass

        async def review(self, payload):
            review_calls.append(payload)
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
                strengths=["m"],
                areas_for_improvement=["m"],
                notes=None,
            )

    monkeypatch.setattr("services.llm_reviewer_service.LLMReviewerService", _MockLLM)
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", object)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db,
        test_user,
        test_case,
        TEST_CONVERSATION_BAD,
        evaluator_plugin=ApexHybridEvaluator.name,
    )
    assert len(review_calls) == 1
    assert review_calls[0].session_id is not None
    fb = result["feedback"]
    assert fb.evaluator_meta is not None
    assert fb.evaluator_meta.get("phase") == "hybrid_llm_v1"
    assert fb.evaluator_meta.get("status") == "success"
    merged = fb.evaluator_meta.get("merged_scores") or {}
    r_emp = fb.evaluator_meta["rule_scores"]["empathy_score"]
    assert merged["empathy_score"] == pytest.approx(0.7 * r_emp + 0.3 * 50.0, rel=1e-4)


@pytest.mark.asyncio
async def test_hybrid_plugin_skips_llm_when_env_off(test_db, test_user, test_case, monkeypatch):
    review_calls: list = []

    class _MockLLM:
        def __init__(self, adapter):
            pass

        async def review(self, payload):
            review_calls.append(payload)
            return None

    monkeypatch.setattr("services.llm_reviewer_service.LLMReviewerService", _MockLLM)
    monkeypatch.delenv("LLM_REVIEWER_REAL_CALLS", raising=False)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db,
        test_user,
        test_case,
        TEST_CONVERSATION_BAD,
        evaluator_plugin=ApexHybridEvaluator.name,
    )
    assert review_calls == []
    assert result["feedback"].evaluator_meta is None
