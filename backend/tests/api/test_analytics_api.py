"""Integration tests for the analytics API endpoints.

GET /v1/analytics/my-sessions

Verification of:
  - Authenticated trainee receives 200 with correct response shape
  - Empty list returned for user with no completed sessions
  - Request without authentication credential header returns 403
    (HTTPBearer rejects missing Authorization header)
"""

from __future__ import annotations

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from core.deps import get_current_user, get_db, require_admin
from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from tests.utils.transcript_runner import create_all_for_test_engine

# ---------------------------------------------------------------------------
# Module-level shared in-memory database
# ---------------------------------------------------------------------------

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
create_all_for_test_engine(_engine)


def _get_test_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _override_db():
    """Wire the FastAPI app to use the in-memory SQLite DB."""
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def db_session():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def trainee_user(db_session):
    user = User(
        email=f"analytics_trainee_{uuid.uuid4().hex[:12]}@test.com",
        role="trainee",
        full_name="Analytics Trainee",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_case(db_session):
    case = Case(title="API Test Case", script="Script", difficulty_level="beginner")
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _override_current_user(user: User):
    """Replace get_current_user dependency with a function returning `user`."""

    async def _fake_current_user():
        return user

    app.dependency_overrides[get_current_user] = _fake_current_user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_my_sessions_returns_200_with_empty_list(trainee_user):
    """Authenticated trainee with no sessions gets 200 + empty list."""
    _override_current_user(trainee_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_my_sessions_returns_session_analytics(trainee_user, test_case, db_session):
    """Completed session with feedback shows up with correct scores."""
    import json as _json

    session = SessionEntity(
        user_id=trainee_user.id,
        case_id=test_case.id,
        state="completed",
        duration_seconds=300,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        empathy_score=82.0,
        communication_score=78.0,
        clinical_reasoning_score=65.0,
        spikes_completion_score=55.0,
        overall_score=72.0,
        spikes_coverage=_json.dumps({"percent": 0.67, "covered": ["S", "P", "I", "K"]}),
        linkage_stats=_json.dumps({"addressed_rate": 0.75}),
    )
    db_session.add(feedback)
    db_session.commit()

    _override_current_user(trainee_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    row = next(r for r in data if r["session_id"] == session.id)
    assert row["case_title"] == "API Test Case"
    assert row["empathy_score"] == pytest.approx(82.0)
    assert row["communication_score"] == pytest.approx(78.0)
    assert row["spikes_coverage_percent"] == pytest.approx(67.0)
    assert row["eo_addressed_rate"] == pytest.approx(75.0)
    assert row["spikes_stages_covered"] == ["S", "P", "I", "K"]
    assert row["duration_seconds"] == 300


@pytest.mark.anyio
async def test_my_sessions_excludes_active_sessions(trainee_user, test_case, db_session):
    """Sessions with state='active' should not appear in analytics."""
    session = SessionEntity(
        user_id=trainee_user.id, case_id=test_case.id, state="active"
    )
    db_session.add(session)
    db_session.commit()

    _override_current_user(trainee_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 200
    data = response.json()
    active_ids = {r["session_id"] for r in data}
    assert session.id not in active_ids


@pytest.mark.anyio
async def test_my_sessions_excludes_another_users_data(test_case, db_session):
    """User B's completed sessions must not appear in User A's analytics."""
    user_a = User(email="user_a_api@test.com", role="trainee")
    user_b = User(email="user_b_api@test.com", role="trainee")
    db_session.add_all([user_a, user_b])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    session_b = SessionEntity(user_id=user_b.id, case_id=test_case.id, state="completed")
    db_session.add(session_b)
    db_session.commit()
    db_session.refresh(session_b)

    db_session.add(Feedback(session_id=session_b.id, empathy_score=90.0))
    db_session.commit()

    _override_current_user(user_a)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 200
    session_ids = {r["session_id"] for r in response.json()}
    assert session_b.id not in session_ids


@pytest.mark.anyio
async def test_my_sessions_requires_authentication():
    """No Authorization header returns 403 (HTTPBearer rejects unauthenticated requests)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_my_sessions_response_schema_fields(trainee_user, test_case, db_session):
    """Verify all expected fields are present in the response schema."""
    import json as _json

    session = SessionEntity(
        user_id=trainee_user.id, case_id=test_case.id, state="completed", duration_seconds=60
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    db_session.add(Feedback(session_id=session.id, empathy_score=50.0))
    db_session.commit()

    _override_current_user(trainee_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/v1/analytics/my-sessions")

    assert response.status_code == 200
    row = response.json()[0]
    required_keys = {
        "session_id",
        "case_id",
        "case_title",
        "empathy_score",
        "communication_score",
        "clinical_score",
        "spikes_completion_score",
        "spikes_coverage_percent",
        "duration_seconds",
        "created_at",
    }
    assert required_keys.issubset(row.keys())
