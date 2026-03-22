"""Mirrored tests for session service behaviour (non-src tree).

These tests intentionally duplicate backend/src/tests/test_sessions.py so that
they are picked up when pytest is pointed at the top-level backend/tests/
directory. Keep them in sync with the source-tree tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.session import Session
from domain.entities.user import User
from domain.models.sessions import SessionCreate
from services.session_service import SessionService


@pytest.fixture(autouse=True)
def _ensure_plugin_registry_for_session_service(test_db):
    """After SQLite schema is prepared, load plugins so create_session validation matches production."""
    import plugins.evaluators.apex_baseline_evaluator  # noqa: F401
    import plugins.evaluators.apex_hybrid_evaluator  # noqa: F401
    import plugins.metrics.apex_metrics  # noqa: F401
    import plugins.patient_models.default_llm_patient  # noqa: F401


@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            table.schema = None
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        role="trainee",
        full_name="Test User",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    """Create a test case."""
    case = Case(
        title="Test Case",
        script="Test case script",
        difficulty_level="intermediate",
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
async def test_create_session(test_db, test_user, test_case):
    """Test creating a session."""
    session_service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)

    session = await session_service.create_session(test_user.id, session_data)

    assert session.user_id == test_user.id
    assert session.case_id == test_case.id
    assert session.state == "active"


@pytest.mark.asyncio
async def test_create_session_reuses_active(test_db, test_user, test_case):
    """Creating a session twice while the first is still active should return the same session."""
    session_service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)

    first_session = await session_service.create_session(test_user.id, session_data)
    second_session = await session_service.create_session(test_user.id, session_data)

    assert second_session.id == first_session.id
    assert second_session.state == "active"
    assert second_session.started_at == first_session.started_at


@pytest.mark.asyncio
async def test_create_session_force_new(test_db, test_user, test_case):
    """Passing force_new should create a new session even if one is already active."""
    session_service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)
    first_session = await session_service.create_session(test_user.id, session_data)

    forced_session_data = SessionCreate(case_id=test_case.id, force_new=True)
    new_session = await session_service.create_session(test_user.id, forced_session_data)

    assert new_session.id != first_session.id
    assert new_session.state == "active"


@pytest.mark.asyncio
async def test_create_session_repeated_calls_do_not_duplicate(test_db, test_user, test_case):
    """Repeated non-forced create_session calls return the same open session."""
    session_service = SessionService(test_db)
    session_data = SessionCreate(case_id=test_case.id)

    first_session = await session_service.create_session(test_user.id, session_data)
    second_session = await session_service.create_session(test_user.id, session_data)
    third_session = await session_service.create_session(test_user.id, session_data)

    assert first_session.id == second_session.id == third_session.id


@pytest.mark.asyncio
async def test_close_session(test_db, test_user, test_case):
    """Test closing a session."""
    session_service = SessionService(test_db)

    # Create session
    session_data = SessionCreate(case_id=test_case.id)
    created_session = await session_service.create_session(test_user.id, session_data)

    # Close session
    closed_session = await session_service.close_session(created_session.id)

    assert closed_session.state == "completed"
    assert closed_session.ended_at is not None

