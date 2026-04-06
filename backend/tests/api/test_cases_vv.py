"""Validation-oriented tests for case management (V&V)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from core.deps import get_db, get_current_user, require_admin
from core.errors import NotFoundError
from db.base import Base
from domain.models.cases import CaseCreate
from services.case_service import CaseService
from tests.utils.transcript_runner import create_all_for_test_engine

_MISSING_CASE_ID = 999_999

# Thread-safe in-memory SQLite for API checks (matches test_cases_api_smoke pattern)
_api_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_ApiSessionLocal = sessionmaker(bind=_api_engine, autocommit=False, autoflush=False)
create_all_for_test_engine(_api_engine)


@pytest.fixture
def test_db():
    """Fresh in-memory DB per test for CaseService."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def _cases_vv_api_overrides():
    """Wire FastAPI to the shared API test engine (empty unless a test seeds it)."""

    def _get_db():
        db = _ApiSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db

    dummy_user = SimpleNamespace(
        id=1,
        email="vv_cases@test.local",
        full_name="VV Cases User",
        role="trainee",
    )

    async def _as_user():
        return dummy_user

    async def _as_admin():
        return dummy_user

    app.dependency_overrides[get_current_user] = _as_user
    app.dependency_overrides[require_admin] = _as_admin

    yield

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.usefixtures("_cases_vv_api_overrides")
async def test_case_invalid_id_returns_error(test_db):
    """Non-existent case: service raises NotFoundError; API returns 404."""
    svc = CaseService(test_db)
    with pytest.raises(NotFoundError, match="not found"):
        await svc.get_case(_MISSING_CASE_ID)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(f"/v1/cases/{_MISSING_CASE_ID}")
    assert response.status_code == 404
    body = response.json()
    assert body.get("error") == "NotFoundError"


@pytest.mark.asyncio
async def test_case_metadata_persistence(test_db):
    """Optional case fields round-trip through create and get."""
    metrics_plugins = [
        "plugins.metrics.apex_metrics:ApexMetrics",
        "research.demo:DemoMetrics",
    ]
    payload = CaseCreate(
        title="VV metadata case",
        script="Scenario script for VV.",
        objectives='{"goals": ["SPIKES", "empathy"]}',
        difficulty_level="advanced",
        category="oncology",
        patient_background="Anxious patient; prefers plain language.",
        expected_spikes_flow='{"focus": ["setting", "knowledge"]}',
        metrics_plugins=metrics_plugins,
    )
    svc = CaseService(test_db)
    created = await svc.create_case(payload)
    got = await svc.get_case(created.id)

    assert got.title == payload.title
    assert got.script == payload.script
    assert got.objectives == payload.objectives
    assert got.difficulty_level == payload.difficulty_level
    assert got.category == payload.category
    assert got.patient_background == payload.patient_background
    assert got.expected_spikes_flow == payload.expected_spikes_flow
    assert got.metrics_plugins == metrics_plugins


@pytest.mark.asyncio
async def test_case_default_difficulty(test_db):
    """Minimal create uses schema default difficulty."""
    svc = CaseService(test_db)
    created = await svc.create_case(CaseCreate(title="Default diff", script="S"))
    assert created.difficulty_level == "intermediate"


@pytest.mark.asyncio
async def test_case_list_filtering(test_db):
    """list_cases respects category and difficulty filters."""
    svc = CaseService(test_db)
    await svc.create_case(
        CaseCreate(
            title="Cardio beginner",
            script="s1",
            category="cardiology",
            difficulty_level="beginner",
        )
    )
    await svc.create_case(
        CaseCreate(
            title="Oncology advanced",
            script="s2",
            category="oncology",
            difficulty_level="advanced",
        )
    )
    await svc.create_case(
        CaseCreate(
            title="Oncology beginner",
            script="s3",
            category="oncology",
            difficulty_level="beginner",
        )
    )

    oncology = await svc.list_cases(category="oncology")
    assert oncology.total == 2
    assert {c.title for c in oncology.cases} == {"Oncology advanced", "Oncology beginner"}

    beginner = await svc.list_cases(difficulty="beginner")
    assert beginner.total == 2
    assert {c.title for c in beginner.cases} == {"Cardio beginner", "Oncology beginner"}

    filtered = await svc.list_cases(difficulty="beginner", category="oncology")
    assert filtered.total == 1
    assert {c.title for c in filtered.cases} == {"Oncology beginner"}
