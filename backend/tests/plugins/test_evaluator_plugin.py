from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator
from tests.utils.transcript_runner import create_all_for_test_engine


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
def seeded_session(test_db):
    """Create a minimal user, case, and empty session for scoring."""
    user = User(
        email="evaluator_plugin_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Evaluator Plugin Tester",
    )
    test_db.add(user)

    case = Case(
        title="Evaluator Plugin Case",
        description="Case for evaluator plugin tests.",
        script="Script content is not used directly in scoring for these tests.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()

    session = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="completed",
        current_spikes_stage="setting",
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    return session


@pytest.mark.asyncio
async def test_evaluator_returns_feedback_response(test_db, seeded_session, monkeypatch: pytest.MonkeyPatch):
    evaluator = ApexHybridEvaluator()

    # Ensure ScoringService.generate_feedback resolves this evaluator via its local import
    import services.scoring_service as scoring_service_module

    monkeypatch.setattr(scoring_service_module, "get_evaluator", lambda: evaluator)

    feedback = await evaluator.evaluate(test_db, seeded_session.id)

    assert isinstance(feedback, FeedbackResponse)


@pytest.mark.asyncio
async def test_evaluator_scores_within_expected_range(test_db, seeded_session, monkeypatch: pytest.MonkeyPatch):
    evaluator = ApexHybridEvaluator()

    import services.scoring_service as scoring_service_module

    monkeypatch.setattr(scoring_service_module, "get_evaluator", lambda: evaluator)

    feedback = await evaluator.evaluate(test_db, seeded_session.id)

    # All top-level scores should be in [0, 100]
    for score in (
        feedback.empathy_score,
        feedback.communication_score,
        feedback.clinical_reasoning_score,
        feedback.professionalism_score,
        feedback.overall_score,
        feedback.spikes_completion_score,
    ):
        assert 0.0 <= score <= 100.0

