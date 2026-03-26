from __future__ import annotations

import importlib
import sys
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession, sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService


class _DummyEvaluator:
    """Dummy evaluator that records calls and returns a minimal FeedbackResponse-like object."""

    name = "tests.dummy:_DummyEvaluator"
    version = "test-1.0"
    invocations: list[tuple[OrmSession, int]] = []

    async def evaluate(self, db: OrmSession, session_id: int) -> FeedbackResponse:
        _DummyEvaluator.invocations.append((db, session_id))
        return FeedbackResponse(
            id=1,
            session_id=session_id,
            empathy_score=0.0,
            communication_score=0.0,
            spikes_completion_score=0.0,
            overall_score=0.0,
            latency_ms_avg=0.0,
            created_at=datetime.utcnow(),
        )


def _reload_builtin_plugins() -> None:
    """Re-run plugin module registration after tests clear PluginRegistry (imports are cached)."""
    for name in (
        "plugins.evaluators.apex_baseline_evaluator",
        "plugins.evaluators.apex_hybrid_evaluator",
        "plugins.patient_models.default_llm_patient",
        "plugins.metrics.apex_metrics",
    ):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


@pytest.fixture(autouse=True)
def clear_registry():
    """Ensure a clean PluginRegistry between tests."""
    PluginRegistry.evaluators.clear()
    PluginRegistry.patient_models.clear()
    PluginRegistry.metrics_plugins.clear()
    yield
    PluginRegistry.evaluators.clear()
    PluginRegistry.patient_models.clear()
    PluginRegistry.metrics_plugins.clear()
    _reload_builtin_plugins()


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    user = User(
        email="scoring_plugin_tester@example.com",        
        role="trainee",
        full_name="Scoring Plugin Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Scoring Plugin Case",
        script="Script not used for scoring registry test.",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
async def test_scoring_service_uses_session_evaluator(test_db, test_user, test_case, monkeypatch):
    """
    ScoringService.generate_feedback should load the evaluator from the session's
    frozen evaluator_plugin field and call it.
    """
    _DummyEvaluator.invocations.clear()

    # Arrange a dummy session with frozen evaluator metadata
    session = Session(
        user_id=test_user.id,
        case_id=test_case.id,
        state="active",
        current_spikes_stage="setting",
    )
    session.evaluator_plugin = _DummyEvaluator.name
    session.evaluator_version = _DummyEvaluator.version
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    # Register the dummy evaluator in the registry and monkeypatch settings
    PluginRegistry.register_evaluator(_DummyEvaluator.name, _DummyEvaluator)

    monkeypatch.setattr(
        "services.scoring_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=_DummyEvaluator.name),
    )

    service = ScoringService(test_db)
    feedback = await service.generate_feedback(session.id)

    assert isinstance(feedback, FeedbackResponse)
    assert len(_DummyEvaluator.invocations) == 1
    assert _DummyEvaluator.invocations[0][1] == session.id

