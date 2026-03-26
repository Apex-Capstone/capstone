"""Tests for FeedbackRepository monthly aggregates."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session
from domain.entities.user import User
from repositories.feedback_repo import FeedbackRepository


def _setup_db():
    engine = create_engine("sqlite:///:memory:")
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            table.schema = None
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_session_with_feedback(
    db,
    *,
    created_at: datetime,
    overall_score: float,
) -> None:
    user = User(
        email=f"u{uuid.uuid4().hex}@example.com",        
        role="trainee",
        full_name="T",
    )
    case = Case(title="C", script="s", difficulty_level="beginner")
    db.add_all([user, case])
    db.commit()
    db.refresh(user)
    db.refresh(case)
    session = Session(
        user_id=user.id,
        case_id=case.id,
        state="completed",
        started_at=created_at,
        ended_at=created_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    fb = Feedback(
        session_id=session.id,
        overall_score=overall_score,
        empathy_score=0.0,
        spikes_completion_score=0.0,
    )
    fb.created_at = created_at
    db.add(fb)
    db.commit()


def test_get_average_overall_by_month_averages_and_sorts_chronologically():
    db = _setup_db()
    try:
        jan = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        feb = datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
        _seed_session_with_feedback(db, created_at=jan, overall_score=80.0)
        _seed_session_with_feedback(db, created_at=jan, overall_score=90.0)
        _seed_session_with_feedback(db, created_at=feb, overall_score=70.0)

        repo = FeedbackRepository(db)
        rows = repo.get_average_overall_by_month()

        assert rows == [
            {"month": "2025-01", "score": 85.0},
            {"month": "2025-02", "score": 70.0},
        ]
    finally:
        db.close()
