"""Tests for case-level evaluator override at session creation."""

from __future__ import annotations

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
from services.session_service import SessionService
from tests.utils.transcript_runner import create_all_for_test_engine


EVALUATOR_REGISTRY_KEY = "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"


@pytest.fixture(autouse=True)
def _ensure_evaluator_registered():
    """Ensure ApexHybridEvaluator is in the registry (other tests may clear it)."""
    from plugins.registry import PluginRegistry
    if EVALUATOR_REGISTRY_KEY not in PluginRegistry.evaluators:
        PluginRegistry.register_evaluator(EVALUATOR_REGISTRY_KEY, ApexHybridEvaluator)
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
        email="case_override_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Case Override Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_session_uses_case_evaluator_override(test_db, test_user, monkeypatch: pytest.MonkeyPatch):
    """
    When a case has evaluator_plugin set, session creation uses it and freezes
    that plugin name and version on the session.
    """
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin="other:OtherEvaluator"),
    )

    case = Case(
        title="Case With Override",
        script="Script for override test.",
        difficulty_level="intermediate",
        evaluator_plugin=EVALUATOR_REGISTRY_KEY,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)
    session_response = await service.create_session(test_user.id, session_data)

    # Session must store the case's evaluator (resolved from registry), not settings.
    assert session_response.evaluator_plugin == EVALUATOR_REGISTRY_KEY
    assert session_response.evaluator_version == "1.0"


@pytest.mark.asyncio
async def test_create_session_raises_400_for_invalid_case_evaluator(test_db, test_user):
    """When case.evaluator_plugin is set to a plugin not in the registry, create_session raises 400."""
    case = Case(
        title="Case With Bad Override",
        script="Script.",
        difficulty_level="intermediate",
        evaluator_plugin="nonexistent.module:NonExistentEvaluator",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=case.id)

    with pytest.raises(HTTPException) as exc_info:
        await service.create_session(test_user.id, session_data)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid evaluator plugin"
