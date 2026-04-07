"""Unit tests for demo seeding helpers (reseed idempotency and demo-only matching)."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.user import User
from scripts.seed_demo_sessions import (
    DEMO_SEED_SOURCE,
    _find_all_mapped_demo_seed_sessions,
    _is_mapped_demo_seed_session,
)
from tests.utils.transcript_runner import create_all_for_test_engine


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(e)
    return e


@pytest.fixture
def db(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def user_case(db):
    user = User(
        email=f"u_{uuid.uuid4().hex[:10]}@test.com",
        role="trainee",
        full_name="T",
    )
    case = Case(title="C", script="s", difficulty_level="easy")
    db.add_all([user, case])
    db.commit()
    db.refresh(user)
    db.refresh(case)
    return user, case


def test_is_mapped_demo_seed_session_requires_seed_source_or_legacy_fixture():
    assert _is_mapped_demo_seed_session(
        {"seed_key": "k1", "seed_source": DEMO_SEED_SOURCE, "fixture_name": "f1"},
        seed_key="k1",
        fixture_name="f1",
    )
    assert not _is_mapped_demo_seed_session(
        {"seed_key": "k1", "seed_source": "other", "fixture_name": "f1"},
        seed_key="k1",
        fixture_name="f1",
    )
    assert _is_mapped_demo_seed_session(
        {"seed_key": "k1", "fixture_name": "f1"},
        seed_key="k1",
        fixture_name="f1",
    )
    assert not _is_mapped_demo_seed_session(
        {"seed_key": "k1", "fixture_name": "other"},
        seed_key="k1",
        fixture_name="f1",
    )


def test_find_all_mapped_demo_seed_sessions_returns_duplicates(db, user_case):
    """--force must delete every matching demo row; finder must see all duplicates."""
    user, case = user_case
    meta = json.dumps(
        {"seed_key": "dup_key", "seed_source": DEMO_SEED_SOURCE, "fixture_name": "bad_missed_empathy_sparse_spikes"}
    )
    s1 = SessionEntity(user_id=user.id, case_id=case.id, state="completed", session_metadata=meta)
    s2 = SessionEntity(user_id=user.id, case_id=case.id, state="completed", session_metadata=meta)
    db.add_all([s1, s2])
    db.commit()

    found = _find_all_mapped_demo_seed_sessions(
        db,
        user_id=user.id,
        case_id=case.id,
        seed_key="dup_key",
        fixture_name="bad_missed_empathy_sparse_spikes",
    )
    assert len(found) == 2
    assert {s.id for s in found} == {s1.id, s2.id}


def test_find_all_ignores_non_demo_completed_sessions(db, user_case):
    user, case = user_case
    real = SessionEntity(user_id=user.id, case_id=case.id, state="completed", session_metadata=None)
    demo = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="completed",
        session_metadata=json.dumps(
            {
                "seed_key": "only_demo",
                "seed_source": DEMO_SEED_SOURCE,
                "fixture_name": "good_strong_empathy_complete_spikes",
            }
        ),
    )
    db.add_all([real, demo])
    db.commit()

    found = _find_all_mapped_demo_seed_sessions(
        db,
        user_id=user.id,
        case_id=case.id,
        seed_key="only_demo",
        fixture_name="good_strong_empathy_complete_spikes",
    )
    assert len(found) == 1
    assert found[0].id == demo.id
