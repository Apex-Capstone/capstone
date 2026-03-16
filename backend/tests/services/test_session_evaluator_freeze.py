from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import SessionCreate
from services.session_service import SessionService


EVALUATOR_PATH = "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator"


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database session."""
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
        email="freeze_evaluator_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Freeze Evaluator Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(
        title="Evaluator Freeze Case",
        script="Script not used for freeze test.",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
async def test_create_session_freezes_evaluator_on_session(
    test_db, test_user, test_case, monkeypatch: pytest.MonkeyPatch
):
    """
    Creating a session should record the evaluator plugin path and version
    in the persisted session row.
    """

    # Ensure SessionService uses a deterministic evaluator plugin value
    monkeypatch.setattr(
        "services.session_service.get_settings",
        lambda: SimpleNamespace(evaluator_plugin=EVALUATOR_PATH),
    )

    service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)

    session_response = await service.create_session(test_user.id, session_data)

    assert session_response.evaluator_plugin == EVALUATOR_PATH
    # Version is defined on ApexHybridEvaluator in the plugins package
    assert session_response.evaluator_version == "1.0"

