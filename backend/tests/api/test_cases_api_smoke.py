# backend/tests/api/test_cases_api_smoke.py
import pytest
from httpx import AsyncClient, ASGITransport

from app import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from core.deps import get_db, get_current_user, require_admin
from types import SimpleNamespace
from tests.utils.transcript_runner import create_all_for_test_engine

# --- thread-safe in-memory SQLite for async tests ---
engine = create_engine(
    "sqlite://",                      # note: no :memory: with StaticPool
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
create_all_for_test_engine(engine)

@pytest.fixture(autouse=True)
def _overrides():
    # DB override (one session per request)
    def _get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_db

    # Auth overrides: act as admin
    dummy_admin = SimpleNamespace(
        id=1,
        email="admin@test.local",
        full_name="Test Admin",
        role="admin",
    )

    async def _as_user():
        return dummy_admin

    async def _as_admin():
        return dummy_admin

    app.dependency_overrides[get_current_user] = _as_user
    app.dependency_overrides[require_admin] = _as_admin

    yield
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_cases_api_smoke():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # CREATE (requires admin)
        r = await ac.post("/v1/cases", json={"title": "T1", "script": "S1"})
        assert r.status_code == 201, r.text
        cid = r.json()["id"]

        # LIST (requires user)
        r = await ac.get("/v1/cases", params={"skip": 0, "limit": 10})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "cases" in body and "total" in body

        # GET
        r = await ac.get(f"/v1/cases/{cid}")
        assert r.status_code == 200, r.text

        # PATCH (requires admin)
        r = await ac.patch(f"/v1/cases/{cid}", json={"title": "T1-updated"})
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "T1-updated"

        # DELETE (requires admin)
        r = await ac.delete(f"/v1/cases/{cid}")
        assert r.status_code == 204, r.text

        # 404 after delete
        r = await ac.get(f"/v1/cases/{cid}")
        assert r.status_code == 404, r.text
