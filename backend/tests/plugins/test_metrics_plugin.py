from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.user import User
from plugins.metrics.apex_metrics import ApexMetrics
from tests.test_conversation_fixture import TEST_CONVERSATION_GOOD
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database session compatible with core.* schemas."""
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def scored_session_id(test_db, monkeypatch: pytest.MonkeyPatch):
    """Seed a GOOD transcript and return the scored session_id."""
    user = User(
        email="metrics_plugin_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Metrics Plugin Tester",
    )
    test_db.add(user)

    case = Case(
        title="Metrics Plugin Case",
        description="Case for metrics plugin tests.",
        script="Script content is not used directly in scoring for these tests.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()

    # Patch scoring service to provide a no-op evaluator so scoring can run
    import services.scoring_service as scoring_service_module
    from domain.models.sessions import FeedbackResponse
    from datetime import datetime

    class _NoOpEvaluator:
        async def evaluate(self, db, session_id: int) -> FeedbackResponse:  # type: ignore[override]
            return FeedbackResponse(
                id=0,
                session_id=session_id,
                empathy_score=0.0,
                communication_score=0.0,
                clinical_reasoning_score=0.0,
                professionalism_score=0.0,
                spikes_completion_score=0.0,
                overall_score=0.0,
                latency_ms_avg=0.0,
                created_at=datetime.utcnow(),
            )

    monkeypatch.setattr(scoring_service_module, "get_evaluator", lambda: _NoOpEvaluator())

    result = asyncio.run(
        run_fixture_seeded_transcript_through_scoring(
            test_db, user, case, TEST_CONVERSATION_GOOD
        )
    )
    # result is a dict with 'session_id'
    return result["session_id"]


def test_metrics_compute_returns_expected_keys(test_db, scored_session_id):
    metrics_plugin = ApexMetrics()

    metrics = metrics_plugin.compute(test_db, scored_session_id)

    assert isinstance(metrics, dict)
    assert "eo_counts_by_dimension" in metrics
    assert "response_counts_by_type" in metrics
    assert "spikes_coverage" in metrics

