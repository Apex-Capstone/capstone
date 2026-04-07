"""Tests for optional evaluator_plugin on SessionCreate / create_session."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import app
from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import SessionCreate
from plugins.evaluators.apex_baseline_evaluator import ApexBaselineEvaluator  # noqa: F401
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator  # noqa: F401
from services.session_service import SessionService
from tests.utils.transcript_runner import create_all_for_test_engine

BASELINE_KEY = ApexBaselineEvaluator.name
HYBRID_KEY = ApexHybridEvaluator.name


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
        email="req_eval_tester@example.com",
        role="trainee",
        full_name="Request Eval Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Request Eval Case",
        script="Script.",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


def test_session_create_accepts_optional_evaluator_plugin():
    omitted = SessionCreate(case_id=1)
    assert omitted.evaluator_plugin is None
    explicit = SessionCreate(case_id=1, evaluator_plugin=BASELINE_KEY)
    assert explicit.evaluator_plugin == BASELINE_KEY


def test_openapi_session_create_includes_evaluator_plugin():
    schema = app.openapi()
    session_create = schema["components"]["schemas"].get("SessionCreate")
    assert session_create is not None
    assert "evaluator_plugin" in session_create.get("properties", {})


@pytest.mark.asyncio
async def test_create_session_request_baseline_stores_normalized(
    test_db, test_user, test_case, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=HYBRID_KEY),
    )
    service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id, evaluator_plugin=BASELINE_KEY)
    session_response = await service.create_session(test_user.id, session_data)
    assert session_response.evaluator_plugin == BASELINE_KEY
    assert session_response.evaluator_version == ApexBaselineEvaluator.version


@pytest.mark.asyncio
async def test_create_session_request_hybrid_stores_normalized(
    test_db, test_user, test_case, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=BASELINE_KEY),
    )
    service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id, evaluator_plugin=HYBRID_KEY)
    session_response = await service.create_session(test_user.id, session_data)
    assert session_response.evaluator_plugin == HYBRID_KEY
    assert session_response.evaluator_version == ApexHybridEvaluator.version


@pytest.mark.asyncio
async def test_create_session_without_evaluator_plugin_preserves_settings_fallback(
    test_db, test_user, test_case, monkeypatch: pytest.MonkeyPatch
):
    """Omitting evaluator_plugin still uses settings.evaluator_plugin when case has none."""
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=HYBRID_KEY),
    )
    service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)
    session_response = await service.create_session(test_user.id, session_data)
    assert session_response.evaluator_plugin == HYBRID_KEY
    assert session_response.evaluator_version == ApexHybridEvaluator.version


@pytest.mark.asyncio
async def test_create_session_invalid_request_evaluator_returns_400(test_db, test_user, test_case):
    service = SessionService(test_db)
    session_data = SessionCreate(
        case_id=test_case.id,
        evaluator_plugin="nonexistent.module:NonExistentEvaluator",
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_session(test_user.id, session_data)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid evaluator plugin"


@pytest.mark.asyncio
async def test_reuse_active_session_does_not_apply_request_evaluator(
    test_db, test_user, test_case, monkeypatch: pytest.MonkeyPatch
):
    """force_new=False returns the existing open session; request evaluator_plugin is ignored."""
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=HYBRID_KEY),
    )
    service = SessionService(test_db)
    first = await service.create_session(
        test_user.id, SessionCreate(case_id=test_case.id, force_new=False)
    )
    assert first.evaluator_plugin == HYBRID_KEY

    second = await service.create_session(
        test_user.id,
        SessionCreate(
            case_id=test_case.id,
            force_new=False,
            evaluator_plugin=BASELINE_KEY,
        ),
    )
    assert second.id == first.id
    assert second.evaluator_plugin == HYBRID_KEY


@pytest.mark.asyncio
async def test_request_evaluator_overrides_case_evaluator(
    test_db, test_user, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=BASELINE_KEY),
    )
    case = Case(
        title="Case with hybrid",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin=HYBRID_KEY,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_response = await service.create_session(
        test_user.id,
        SessionCreate(case_id=case.id, evaluator_plugin=BASELINE_KEY, force_new=True),
    )
    assert session_response.evaluator_plugin == BASELINE_KEY
