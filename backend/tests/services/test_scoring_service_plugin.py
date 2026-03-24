from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from services.scoring_service import ScoringService
from tests.test_conversation_fixture import TEST_CONVERSATION_GOOD
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)


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


@pytest.mark.asyncio
async def test_scoring_service_generate_feedback_uses_plugin(test_db, monkeypatch):
    """Integration test: ScoringService.generate_feedback returns FeedbackResponse via plugin."""

    # Configure a minimal user and case, and seed a GOOD transcript
    user = User(
        email="scoring_plugin_tester@example.com",
        role="trainee",
        full_name="Scoring Plugin Tester",
    )
    test_db.add(user)

    case = Case(
        title="Scoring Plugin Case",
        description="Case for scoring service plugin integration test.",
        script="Script content is not used directly in scoring for these tests.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()

    # Seed a transcript and get feedback via the existing runner (which uses ScoringService)
    seeded_result = await run_fixture_seeded_transcript_through_scoring(
        test_db, user, case, TEST_CONVERSATION_GOOD
    )

    session_id = seeded_result["session_id"]

    service = ScoringService(test_db)
    feedback = await service.generate_feedback(session_id)

    assert isinstance(feedback, FeedbackResponse)
    # Scores should be on the 0–100 scale
    assert 0.0 <= feedback.empathy_score <= 100.0
    assert 0.0 <= feedback.overall_score <= 100.0
    assert 0.0 <= feedback.spikes_completion_score <= 100.0

