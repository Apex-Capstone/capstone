"""Hybrid LLM v2: three-call merge, partial failure, and meta shape."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from plugins.evaluators.apex_hybrid_v2_evaluator import ApexHybridV2Evaluator
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_BAD
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)

import services.scoring_service as scoring_service_module


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
        email="hybrid_v2_tester@example.com",
        hashed_password="not_used",
        role="trainee",
        full_name="Hybrid V2 Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Hybrid V2 Case",
        description="d",
        script="s",
        difficulty_level="intermediate",
        category="test",
        patient_background="bg",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


def _empathy_json(score: float = 50.0) -> str:
    return json.dumps(
        {
            "reviewer_version": "v2",
            "empathy_score": score,
            "missed_opportunities": [],
            "empathic_opportunities": ["Acknowledged worry"],
            "empathy_review_reasoning": "test",
            "empathy_confidence": None,
        }
    )


def _spikes_json(score: float = 52.0) -> str:
    return json.dumps(
        {
            "reviewer_version": "v2",
            "spikes_completion_score": score,
            "spikes_annotations": [],
            "stage_turn_mapping": [],
            "spikes_sequencing_notes": None,
            "spikes_confidence": None,
        }
    )


def _comm_json(score: float = 54.0) -> str:
    return json.dumps(
        {
            "reviewer_version": "v2",
            "communication_score": score,
            "strengths": ["clear"],
            "areas_for_improvement": ["pace"],
            "clarity_observation": None,
            "organization_observation": None,
            "professionalism_observation": None,
            "question_quality_observation": None,
            "communication_confidence": None,
        }
    )


class RoutingV2MockAdapter:
    """Returns valid JSON per prompt flavor; counts adapter invocations."""

    def __init__(
        self,
        empathy_body: str | None = None,
        spikes_body: str | None = None,
        comm_body: str | None = None,
    ):
        self.calls = 0
        self.empathy_body = empathy_body if empathy_body is not None else _empathy_json()
        self.spikes_body = spikes_body if spikes_body is not None else _spikes_json()
        self.comm_body = comm_body if comm_body is not None else _comm_json()

    async def generate_response(self, prompt: str, context: str = "", **kwargs) -> str:
        self.calls += 1
        if "Empathy-only review" in prompt:
            return self.empathy_body
        if "SPIKES-only review" in prompt:
            return self.spikes_body
        if "Communication-only review" in prompt:
            return self.comm_body
        raise AssertionError("unexpected prompt routing")


V2_PLUGIN = ApexHybridV2Evaluator.name


def _scores_tuple(fb: FeedbackResponse):
    return (
        fb.empathy_score,
        fb.communication_score,
        fb.spikes_completion_score,
        fb.overall_score,
    )


@pytest.mark.asyncio
async def test_hybrid_v2_plugin_smoke(test_db, test_user, test_case):
    evaluator = ApexHybridV2Evaluator()
    s = SessionEntity(
        user_id=test_user.id,
        case_id=test_case.id,
        state="completed",
        evaluator_plugin=V2_PLUGIN,
    )
    test_db.add(s)
    test_db.commit()
    test_db.refresh(s)
    fb = await evaluator.evaluate(test_db, s.id)
    assert isinstance(fb, FeedbackResponse)
    assert 0.0 <= fb.overall_score <= 100.0


@pytest.mark.asyncio
async def test_hybrid_v2_success_three_calls_and_meta(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.delenv("LLM_REVIEWER_REAL_CALLS", raising=False)
    baseline = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    base_scores = _scores_tuple(baseline["feedback"])
    assert baseline["feedback"].evaluator_meta is None

    mock = RoutingV2MockAdapter(
        _empathy_json(40.0),
        _spikes_json(41.0),
        _comm_json(42.0),
    )
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    fb = result["feedback"]
    assert mock.calls == 3
    assert _scores_tuple(fb) != base_scores
    meta = fb.evaluator_meta
    assert meta is not None
    assert meta.get("phase") == "hybrid_llm_v2"
    assert meta.get("status") == "success"
    assert meta.get("prompt_status") == {
        "empathy": "success",
        "spikes": "success",
        "communication": "success",
    }
    assert meta.get("llm_adapter_calls") == 3
    llm_scores = meta.get("llm_scores") or {}
    assert llm_scores.get("empathy_score") == 40.0
    assert llm_scores.get("spikes_completion_score") == 41.0
    assert llm_scores.get("communication_score") == 42.0
    assert "overall_score" in llm_scores
    lo = meta.get("llm_output") or {}
    assert lo.get("reviewer_version") == "v2"
    assert "missed_opportunities" in lo
    assert "empathic_opportunities" in lo
    assert lo.get("llm_score_source") == {
        "empathy": "llm",
        "communication": "llm",
        "spikes": "llm",
    }

    merged = meta.get("merged_scores") or {}
    rs = meta["rule_scores"]
    assert merged["empathy_score"] == pytest.approx(0.7 * rs["empathy_score"] + 0.3 * 40.0)


@pytest.mark.asyncio
async def test_hybrid_v2_empathy_prompt_failure_partial(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    mock = RoutingV2MockAdapter(
        empathy_body="not valid json {{{",
        spikes_body=_spikes_json(45.0),
        comm_body=_comm_json(46.0),
    )
    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    fb = result["feedback"]
    meta = fb.evaluator_meta
    assert meta.get("phase") == "hybrid_llm_v2"
    assert meta.get("status") == "partial"
    assert meta["prompt_status"]["empathy"] == "failed"
    assert meta["prompt_status"]["spikes"] == "success"
    assert meta["prompt_status"]["communication"] == "success"
    llm_scores = meta.get("llm_scores") or {}
    assert llm_scores.get("empathy_score") is None
    assert llm_scores.get("spikes_completion_score") == 45.0
    lo = meta.get("llm_output") or {}
    assert lo.get("llm_score_source", {}).get("empathy") == "rule_fallback"


@pytest.mark.asyncio
async def test_hybrid_v2_spikes_prompt_failure_partial(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    mock = RoutingV2MockAdapter(
        empathy_body=_empathy_json(44.0),
        spikes_body="{",
        comm_body=_comm_json(46.0),
    )
    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    meta = result["feedback"].evaluator_meta
    assert meta.get("status") == "partial"
    assert meta["prompt_status"]["spikes"] == "failed"
    assert (meta.get("llm_scores") or {}).get("spikes_completion_score") is None


@pytest.mark.asyncio
async def test_hybrid_v2_communication_prompt_failure_partial(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    mock = RoutingV2MockAdapter(
        empathy_body=_empathy_json(44.0),
        spikes_body=_spikes_json(45.0),
        comm_body="{",
    )
    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    meta = result["feedback"].evaluator_meta
    assert meta.get("status") == "partial"
    assert meta["prompt_status"]["communication"] == "failed"


@pytest.mark.asyncio
async def test_hybrid_v2_total_failure(
    test_db, test_user, test_case, monkeypatch
):
    monkeypatch.delenv("LLM_REVIEWER_REAL_CALLS", raising=False)
    baseline = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    base_scores = _scores_tuple(baseline["feedback"])

    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    mock = RoutingV2MockAdapter(
        empathy_body="{",
        spikes_body="{",
        comm_body="{",
    )
    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    fb = result["feedback"]
    assert _scores_tuple(fb) == base_scores
    meta = fb.evaluator_meta
    assert meta.get("phase") == "hybrid_llm_v2"
    assert meta.get("status") == "failed"
    assert meta.get("llm_scores") is None
    assert meta.get("merged_scores") is None


@pytest.mark.asyncio
async def test_hybrid_v2_textual_feedback_still_rule_based(
    test_db, test_user, test_case, monkeypatch
):
    captured: list[tuple[float, float, float]] = []

    def _capture_textual_scores(self, e, c, s, eo_spans=None):
        captured.append((e, c, s))
        return ("s", "i")

    monkeypatch.setenv("LLM_REVIEWER_REAL_CALLS", "true")
    import adapters.llm.openai_adapter as openai_adapter_module

    mock = RoutingV2MockAdapter()
    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", lambda: mock)
    monkeypatch.setattr(
        scoring_service_module.ScoringService,
        "_generate_textual_feedback",
        _capture_textual_scores,
    )

    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD, evaluator_plugin=V2_PLUGIN
    )
    fb = result["feedback"]
    assert len(captured) == 1
    rs = fb.evaluator_meta["rule_scores"]
    assert captured[0][0] == pytest.approx(rs["empathy_score"])
    assert captured[0][1] == pytest.approx(rs["communication_score"])
    assert captured[0][2] == pytest.approx(rs["spikes_completion_score"])
