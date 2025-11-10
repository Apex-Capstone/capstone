# tests/test_cases_service.py
import pytest
from core.errors import NotFoundError

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case  # ORM entity
from domain.models.cases import CaseCreate, CaseUpdate  # Pydantic
from services.case_service import CaseService  # your service

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

@pytest.mark.asyncio
async def test_create_case_minimal(test_db):
    svc = CaseService(test_db)
    created = await svc.create_case(CaseCreate(title="T1", script="S1"))
    assert created.id is not None
    assert created.title == "T1"
    assert created.script == "S1"

@pytest.mark.asyncio
async def test_get_list_count(test_db):
    svc = CaseService(test_db)
    await svc.create_case(CaseCreate(title="A", script="S"))
    await svc.create_case(CaseCreate(title="B", script="S"))
    result = await svc.list_cases(skip=0, limit=10)  # expect a struct with cases + total
    assert result.total >= 2
    assert len(result.cases) >= 2
    assert result.cases[0].id is not None

@pytest.mark.asyncio
async def test_get_update_delete(test_db):
    svc = CaseService(test_db)
    c = await svc.create_case(CaseCreate(title="X", script="Y"))
    got = await svc.get_case(c.id)
    assert got.id == c.id

    updated = await svc.update_case(c.id, CaseUpdate(title="X2"))
    assert updated.title == "X2"
    assert updated.updated_at >= got.updated_at

    await svc.delete_case(c.id)

    # was: missing = await svc.get_case(c.id)  # expecting None
    # now assert the service's contract (raises NotFoundError)
    with pytest.raises(NotFoundError):
        await svc.get_case(c.id)
