"""V&V-oriented tests: scoring performance (no network) and multi-metrics execution."""

from __future__ import annotations

import importlib
import json
import sys
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession, sessionmaker

from domain.entities.case import Case
from domain.entities.session import Session
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from plugins.registry import PluginRegistry
from services.scoring_service import ScoringService
from tests.utils.transcript_runner import create_all_for_test_engine


def _metrics_plugin_results_from_session(session: Session) -> dict[str, Any] | None:
    raw = getattr(session, "metrics_json", None)
    if not raw:
        return None
    return json.loads(raw)


class _PerfDummyMetrics:
    name = "tests.plugins.test_plugin_scoring_vv:_PerfDummyMetrics"

    def compute(self, db: OrmSession, session_id: int) -> dict[str, Any]:
        return {"perf_metrics": True}


class _DummyMetricsA:
    name = "tests.plugins.test_plugin_scoring_vv:_DummyMetricsA"

    def compute(self, db: OrmSession, session_id: int) -> dict[str, Any]:
        return {"plugin": "A", "value": 1}


class _DummyMetricsB:
    name = "tests.plugins.test_plugin_scoring_vv:_DummyMetricsB"

    def compute(self, db: OrmSession, session_id: int) -> dict[str, Any]:
        return {"plugin": "B", "value": 2}


class _VVDummyEvaluator:
    """No external calls; returns minimal feedback immediately."""

    name = "tests.plugins.test_plugin_scoring_vv:_VVDummyEvaluator"
    version = "vv-test-1.0"

    async def evaluate(self, db: OrmSession, session_id: int) -> FeedbackResponse:
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
        email="vv_plugin_tester@example.com",
        role="trainee",
        full_name="VV Plugin Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="VV Plugin Scoring Case",
        script="Minimal script for VV plugin tests.",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
async def test_plugin_scoring_performance(test_db, test_user, test_case, monkeypatch):
    """Scoring with dummy evaluator + metrics completes quickly without external APIs."""
    session = Session(
        user_id=test_user.id,
        case_id=test_case.id,
        state="active",
        current_spikes_stage="setting",
    )
    session.evaluator_plugin = _VVDummyEvaluator.name
    session.evaluator_version = _VVDummyEvaluator.version
    session.metrics_plugins = json.dumps([_PerfDummyMetrics.name])
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    PluginRegistry.register_evaluator(_VVDummyEvaluator.name, _VVDummyEvaluator)
    PluginRegistry.register_metrics_plugin(_PerfDummyMetrics.name, _PerfDummyMetrics)

    monkeypatch.setattr(
        "services.scoring_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=_VVDummyEvaluator.name),
    )

    service = ScoringService(test_db)
    t0 = time.perf_counter()
    feedback = await service.generate_feedback(session.id)
    elapsed = time.perf_counter() - t0

    assert isinstance(feedback, FeedbackResponse)
    assert elapsed < 1.0, f"scoring took {elapsed:.3f}s, expected < 1.0s"

    test_db.refresh(session)
    stored = _metrics_plugin_results_from_session(session)
    assert stored is not None
    assert stored[_PerfDummyMetrics.name] == {"perf_metrics": True}


@pytest.mark.asyncio
async def test_multiple_metrics_plugins_execution(test_db, test_user, test_case, monkeypatch):
    """Two metrics plugins both persist under distinct keys in session.metrics_json."""
    session = Session(
        user_id=test_user.id,
        case_id=test_case.id,
        state="active",
        current_spikes_stage="setting",
    )
    session.evaluator_plugin = _VVDummyEvaluator.name
    session.evaluator_version = _VVDummyEvaluator.version
    session.metrics_plugins = json.dumps([_DummyMetricsA.name, _DummyMetricsB.name])
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    PluginRegistry.register_evaluator(_VVDummyEvaluator.name, _VVDummyEvaluator)
    PluginRegistry.register_metrics_plugin(_DummyMetricsA.name, _DummyMetricsA)
    PluginRegistry.register_metrics_plugin(_DummyMetricsB.name, _DummyMetricsB)

    monkeypatch.setattr(
        "services.scoring_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=_VVDummyEvaluator.name),
    )

    service = ScoringService(test_db)
    await service.generate_feedback(session.id)

    test_db.refresh(session)
    stored = _metrics_plugin_results_from_session(session)
    assert stored is not None
    assert _DummyMetricsA.name in stored
    assert _DummyMetricsB.name in stored
    assert stored[_DummyMetricsA.name] == {"plugin": "A", "value": 1}
    assert stored[_DummyMetricsB.name] == {"plugin": "B", "value": 2}
    assert stored[_DummyMetricsA.name] != stored[_DummyMetricsB.name]
