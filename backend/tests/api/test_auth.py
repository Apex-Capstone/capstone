"""Tests for Supabase-oriented auth endpoints (/v1/auth/*)."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from core.deps import get_current_user, get_db
from domain.entities.user import User
from tests.utils.transcript_runner import create_all_for_test_engine

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
create_all_for_test_engine(_engine)


@pytest.fixture(autouse=True)
def _auth_api_db_override():
    """Use in-memory SQLite; drop any get_current_user override from other API tests."""

    def _get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    saved_user_override = app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    if saved_user_override is not None:
        app.dependency_overrides[get_current_user] = saved_user_override


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        db.execute(delete(User))
        db.commit()
        yield db
    finally:
        db.close()


@pytest.mark.anyio
async def test_email_exists_false_when_missing(db_session) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/email-exists",
            params={"email": "nobody@example.com"},
        )
        assert r.status_code == 200
        assert r.json() == {"exists": False}


@pytest.mark.anyio
async def test_email_exists_true_when_user_present(db_session) -> None:
    db_session.add(
        User(
            email="taken@example.com",
            role="trainee",
            full_name="Taken User",
        )
    )
    db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/email-exists",
            params={"email": "taken@example.com"},
        )
        assert r.status_code == 200
        assert r.json() == {"exists": True}


@pytest.mark.anyio
async def test_email_exists_normalizes_email_case(db_session) -> None:
    db_session.add(
        User(
            email="lower@example.com",
            role="trainee",
            full_name="Lower",
        )
    )
    db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/email-exists",
            params={"email": "LOWER@EXAMPLE.COM"},
        )
        assert r.status_code == 200
        assert r.json() == {"exists": True}


@pytest.mark.anyio
async def test_me_missing_authorization() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/v1/auth/me")
        assert r.status_code == 403


@pytest.mark.anyio
@patch("core.deps.decode_supabase_token", return_value=None)
async def test_me_invalid_jwt_payload(_mock_decode, db_session) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert r.status_code == 401
        body = r.json()
        assert body.get("error") == "AuthenticationError"


@pytest.mark.anyio
@patch(
    "core.deps.decode_supabase_token",
    return_value={"sub": "not-a-valid-uuid"},
)
async def test_me_invalid_sub_uuid(_mock_decode, db_session) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer x"},
        )
        assert r.status_code == 401
        assert r.json().get("message") == "User not found"


@pytest.mark.anyio
@patch(
    "core.deps.decode_supabase_token",
    return_value={"sub": str(uuid4())},
)
async def test_me_user_not_in_database(_mock_decode, db_session) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer any.valid-shaped"},
        )
        assert r.status_code == 401
        assert r.json().get("message") == "User not found"


@pytest.mark.anyio
async def test_me_success_when_sub_matches_user(db_session) -> None:
    uid = uuid4()
    db_session.add(
        User(
            supabase_auth_id=uid,
            email="me@example.com",
            role="trainee",
            full_name="Me User",
        )
    )
    db_session.commit()

    with patch(
        "core.deps.decode_supabase_token",
        return_value={"sub": str(uid)},
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                "/v1/auth/me",
                headers={"Authorization": "Bearer mocked-jwt"},
            )
            assert r.status_code == 200
            data = r.json()
            assert data["email"] == "me@example.com"
            assert data["role"] == "trainee"
            assert data["full_name"] == "Me User"
            assert data["id"] >= 1
