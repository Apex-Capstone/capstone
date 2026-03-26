"""DB-level regression tests for evaluator_meta persistence."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator
from schemas.llm_reviewer import LLMReviewerOutput
from services.scoring_service import ScoringService
from services.session_service import SessionService
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_BAD
from tests.utils.transcript_runner import create_all_for_test_engine


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    testing_session_local = sessionmaker(bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    user = User(
        email="feedback_db_persist_tester@example.com",
        role="trainee",
        full_name="Feedback DB Persist Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Feedback DB Persistence Case",
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


def _seed_active_session_with_fixture_turns(test_db, test_user, test_case) -> SessionEntity:
    session = SessionEntity(
        user_id=test_user.id,
        case_id=test_case.id,
        state="active",
        evaluator_plugin=ApexHybridEvaluator.name,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    for turn_data in TEST_CONVERSATION_BAD.get("transcript", []):
        role = turn_data["role"]
        turn = Turn(
            session_id=session.id,
            user_id=test_user.id if role == "user" else None,
            turn_number=turn_data["turn_number"],
            role=role,
            text=turn_data["text"],
            audio_url=None,
            metrics_json=json.dumps(turn_data.get("metrics_json")) if turn_data.get("metrics_json") is not None else None,
            spans_json=json.dumps(turn_data.get("spans_json")) if turn_data.get("spans_json") is not None else None,
            relations_json=None,
            spikes_stage=turn_data.get("expected_spikes"),
        )
        test_db.add(turn)

    test_db.commit()
    return session


class _MockLLMSuccess:
    def __init__(self, adapter):
        pass

    async def review(self, payload):
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


class _MockLLMNone:
    def __init__(self, adapter):
        pass

    async def review(self, payload):
        return None


@pytest.mark.asyncio
async def test_evaluator_meta_persists_as_json_on_hybrid_success(test_db, test_user, test_case, monkeypatch):
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", object)
    monkeypatch.setattr("services.llm_reviewer_service.LLMReviewerService", _MockLLMSuccess)

    session = _seed_active_session_with_fixture_turns(test_db, test_user, test_case)
    await SessionService(test_db).close_session(session.id)
    response = await ScoringService(test_db).generate_feedback(session.id)

    stored = test_db.query(Feedback).filter(Feedback.session_id == session.id).first()
    assert stored is not None
    assert stored.evaluator_meta is not None
    assert isinstance(stored.evaluator_meta, str)
    raw_meta = json.loads(stored.evaluator_meta)
    assert raw_meta["status"] == "completed"
    assert raw_meta["phase"] == "hybrid_llm_v1"
    assert isinstance(response.evaluator_meta, dict)


@pytest.mark.asyncio
async def test_evaluator_meta_persists_as_json_on_hybrid_failure(test_db, test_user, test_case, monkeypatch):
    import adapters.llm.openai_adapter as openai_adapter_module

    monkeypatch.setattr(openai_adapter_module, "OpenAIAdapter", object)
    monkeypatch.setattr("services.llm_reviewer_service.LLMReviewerService", _MockLLMNone)

    session = _seed_active_session_with_fixture_turns(test_db, test_user, test_case)
    await SessionService(test_db).close_session(session.id)
    response = await ScoringService(test_db).generate_feedback(session.id)

    stored = test_db.query(Feedback).filter(Feedback.session_id == session.id).first()
    assert stored is not None
    assert stored.evaluator_meta is not None
    assert isinstance(stored.evaluator_meta, str)
    raw_meta = json.loads(stored.evaluator_meta)
    assert raw_meta["status"] == "failed"
    assert raw_meta["phase"] == "hybrid_llm_v1"
    assert isinstance(response.evaluator_meta, dict)
