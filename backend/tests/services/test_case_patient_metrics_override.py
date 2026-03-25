"""Tests for case-level patient model and metrics plugin override at session creation."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import SessionCreate
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator  # noqa: F401 - register on import
from plugins.metrics.apex_metrics import ApexMetrics  # noqa: F401 - register on import
from plugins.patient_models.default_llm_patient import DefaultLLMPatientModel  # noqa: F401 - register on import
from plugins.registry import PluginRegistry
from services.session_service import SessionService
from tests.utils.transcript_runner import create_all_for_test_engine


EVALUATOR_KEY = "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"
PATIENT_MODEL_KEY = DefaultLLMPatientModel.name
METRICS_KEY = ApexMetrics.name


@pytest.fixture(autouse=True)
def _ensure_plugins_registered():
    """Ensure evaluator, patient model, and metrics are in the registry."""
    if EVALUATOR_KEY not in PluginRegistry.evaluators:
        PluginRegistry.register_evaluator(EVALUATOR_KEY, ApexHybridEvaluator)
    if PATIENT_MODEL_KEY not in PluginRegistry.patient_models:
        PluginRegistry.register_patient_model(PATIENT_MODEL_KEY, DefaultLLMPatientModel)
    if METRICS_KEY not in PluginRegistry.metrics_plugins:
        PluginRegistry.register_metrics_plugin(METRICS_KEY, ApexMetrics)
    yield


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
    user = User(
        email="patient_metrics_tester@example.com",        
        role="trainee",
        full_name="Patient Metrics Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_session_uses_case_patient_model_override(test_db, test_user, monkeypatch: pytest.MonkeyPatch):
    """When a case has patient_model_plugin set, session creation freezes that plugin name and version."""
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(
            evaluator_plugin=EVALUATOR_KEY,
            patient_model_plugin="other:OtherPatient",
            metrics_plugins=[],
        ),
    )

    case = Case(
        title="Case With Patient Override",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin=EVALUATOR_KEY,
        patient_model_plugin=PATIENT_MODEL_KEY,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)
    session_response = await service.create_session(test_user.id, session_data)

    assert session_response.patient_model_plugin == PATIENT_MODEL_KEY
    assert session_response.patient_model_version == "1.0"


@pytest.mark.asyncio
async def test_session_stores_case_metrics_plugins(test_db, test_user, monkeypatch: pytest.MonkeyPatch):
    """When a case has metrics_plugins set, session creation stores that list on the session."""
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(
            evaluator_plugin=EVALUATOR_KEY,
            patient_model_plugin=PATIENT_MODEL_KEY,
            metrics_plugins=[],
        ),
    )

    case = Case(
        title="Case With Metrics Override",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin=EVALUATOR_KEY,
        metrics_plugins=json.dumps([METRICS_KEY]),
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)
    session_response = await service.create_session(test_user.id, session_data)

    assert session_response.metrics_plugins is not None
    assert METRICS_KEY in session_response.metrics_plugins


@pytest.mark.asyncio
async def test_create_session_raises_400_for_invalid_patient_model(test_db, test_user):
    """When case.patient_model_plugin is set to a plugin not in the registry, create_session raises 400."""
    case = Case(
        title="Case With Bad Patient Override",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin=EVALUATOR_KEY,
        patient_model_plugin="nonexistent.module:NonExistentPatient",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_session(test_user.id, session_data)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid plugin configuration"


@pytest.mark.asyncio
async def test_create_session_raises_400_for_invalid_metrics_plugin(test_db, test_user):
    """When case.metrics_plugins contains a plugin not in the registry, create_session raises 400."""
    case = Case(
        title="Case With Bad Metrics Override",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin=EVALUATOR_KEY,
        metrics_plugins=json.dumps(["nonexistent.module:NonExistentMetrics"]),
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_session(test_user.id, session_data)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid plugin configuration"
