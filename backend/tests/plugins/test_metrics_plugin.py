from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.user import User
from plugins.metrics.apex_metrics import ApexMetrics
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_GOOD
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
def scored_session_id(test_db):
    """Seed a GOOD transcript and return the scored session_id.

    Scoring uses the session's frozen evaluator (or settings fallback);
    no patch needed since PluginRegistry resolves the default evaluator.
    """
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

    result = asyncio.run(
        run_fixture_seeded_transcript_through_scoring(
            test_db, user, case, TEST_CONVERSATION_GOOD
        )
    )
    return result["session_id"]


def test_metrics_compute_returns_expected_keys(test_db, scored_session_id):
    metrics_plugin = ApexMetrics()

    metrics = metrics_plugin.compute(test_db, scored_session_id)

    assert isinstance(metrics, dict)
    assert "eo_counts_by_dimension" in metrics
    assert "response_counts_by_type" in metrics
    assert "spikes_coverage" in metrics

