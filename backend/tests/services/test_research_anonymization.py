"""Data integrity and anonymization validation tests for ResearchService.

Validation of:
  - No PII leakage: all export methods scrub email, phone, names, IDs
  - Deterministic anonymization: two exports of the same session produce identical anon IDs
  - Salt sensitivity: changing the salt produces different anon IDs
  - Score consistency: exported scores match stored Feedback row values
  - Export completeness: session count in export matches the DB count
  - Anon ID never contains the raw session integer ID
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from services.research_service import ResearchService, generate_anon_session_id
from tests.utils.transcript_runner import create_all_for_test_engine

TEST_SALT = "anon-validation-salt-2024"

# Known PII patterns used in the seeded test data
_PII_PATTERNS = [
    re.compile(r"john\.doe@hospital\.org", re.IGNORECASE),
    re.compile(r"\b416[-.\s]?555[-.\s]?1234\b"),
    re.compile(r"\b\(416\)\s*555[-.\s]?1234\b"),
    re.compile(r"\bJohn Smith\b"),
    re.compile(r"\bDr\. Williams\b"),
    re.compile(r"\bMr\. Johnson\b"),
]

_PII_TURN_TEXTS = [
    "Please email me at john.doe@hospital.org for results.",
    "Call me at 416-555-1234 for follow-up.",
    "My name is John Smith and I am concerned.",
    "You should speak to Dr. Williams about this.",
    "Mr. Johnson is the attending physician.",
    "Patient number is 1234567890.",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(e)
    return e


@pytest.fixture(scope="module")
def db_factory(engine):
    return sessionmaker(bind=engine)


@pytest.fixture(scope="module")
def pii_session(db_factory):
    """A session whose turns contain PII across all known patterns."""
    db = db_factory()

    user = User(email=f"anon_test_user_{uuid.uuid4().hex[:12]}@test.com", role="trainee")
    db.add(user)
    db.commit()
    db.refresh(user)

    case = Case(title="PII Test Case", script="Script")
    db.add(case)
    db.commit()
    db.refresh(case)

    session = SessionEntity(
        user_id=user.id, case_id=case.id, state="completed", duration_seconds=180
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    db.add(
        Feedback(
            session_id=session.id,
            empathy_score=73.0,
            communication_score=68.0,
            spikes_completion_score=55.0,
            overall_score=65.0,
        )
    )
    for i, text in enumerate(_PII_TURN_TEXTS, start=1):
        db.add(Turn(session_id=session.id, turn_number=i, role="user", text=text))

    db.commit()
    sid = session.id
    db.close()
    return SimpleNamespace(session_id=sid)


@pytest.fixture
def research_service(db_factory):
    db = db_factory()
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(db)
        yield svc
    db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scan_for_pii(content: str) -> list[str]:
    """Return descriptions of any PII patterns found in `content`."""
    found = []
    for pattern in _PII_PATTERNS:
        if pattern.search(content):
            found.append(pattern.pattern)
    return found


# ---------------------------------------------------------------------------
# No PII leakage
# ---------------------------------------------------------------------------


def test_json_export_contains_no_pii(research_service):
    """get_export_json_content must redact all PII in turn texts."""
    content = research_service.get_export_json_content()
    leaked = _scan_for_pii(content)
    assert leaked == [], f"PII leaked in JSON export: {leaked}"


def test_csv_export_contains_no_pii(research_service):
    """get_export_csv_content must redact all PII."""
    content = research_service.get_export_csv_content()
    leaked = _scan_for_pii(content)
    assert leaked == [], f"PII leaked in CSV export: {leaked}"


def test_metrics_csv_stream_contains_no_pii(research_service):
    """stream_metrics_csv does not include turn text, but must not leak PII in case/plugin names."""
    content = b"".join(research_service.stream_metrics_csv()).decode("utf-8")
    leaked = _scan_for_pii(content)
    assert leaked == [], f"PII leaked in metrics CSV: {leaked}"


def test_transcripts_csv_stream_contains_no_pii(research_service):
    """stream_transcripts_csv must anonymize all turn text."""
    content = b"".join(research_service.stream_transcripts_csv()).decode("utf-8")
    leaked = _scan_for_pii(content)
    assert leaked == [], f"PII leaked in transcripts CSV: {leaked}"


def test_session_detail_contains_no_pii(research_service, pii_session):
    """get_session_by_anon must return redacted turn texts."""
    anon_id = generate_anon_session_id(pii_session.session_id)
    data = research_service.get_session_by_anon(anon_id)
    dumped = json.dumps(data)
    leaked = _scan_for_pii(dumped)
    assert leaked == [], f"PII leaked in session detail: {leaked}"


def test_session_transcript_csv_stream_contains_no_pii(research_service, pii_session):
    anon_id = generate_anon_session_id(pii_session.session_id)
    content = b"".join(
        research_service.stream_session_transcript_csv(anon_id)
    ).decode("utf-8")
    leaked = _scan_for_pii(content)
    assert leaked == [], f"PII leaked in session transcript CSV: {leaked}"


# ---------------------------------------------------------------------------
# Anon ID does not embed raw session ID
# ---------------------------------------------------------------------------


def test_anon_id_does_not_contain_raw_session_id(pii_session):
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon_id = generate_anon_session_id(pii_session.session_id)
    assert str(pii_session.session_id) not in anon_id


# ---------------------------------------------------------------------------
# Deterministic anonymization
# ---------------------------------------------------------------------------


def test_anon_id_same_for_two_exports_of_same_session(pii_session):
    """The anon ID must be identical across multiple calls with the same salt."""
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        first = generate_anon_session_id(pii_session.session_id)
        second = generate_anon_session_id(pii_session.session_id)
    assert first == second


def test_json_export_anon_ids_stable_across_calls(research_service, pii_session):
    """Two JSON exports must produce the same anon_session_id for the same session."""
    first_content = research_service.get_export_json_content()
    second_content = research_service.get_export_json_content()

    first_ids = {s["session_id"] for s in json.loads(first_content)}
    second_ids = {s["session_id"] for s in json.loads(second_content)}
    assert first_ids == second_ids


def test_redacted_text_is_stable_across_calls(research_service):
    """_anonymize_text is a pure function — same input always produces same output."""
    svc = research_service
    text = "Please email john.doe@hospital.org or call 416-555-1234."
    assert svc._anonymize_text(text) == svc._anonymize_text(text)


# ---------------------------------------------------------------------------
# Salt sensitivity
# ---------------------------------------------------------------------------


def test_different_salt_produces_different_anon_ids(pii_session):
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = "salt-alpha"
        id_alpha = generate_anon_session_id(pii_session.session_id)

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = "salt-beta"
        id_beta = generate_anon_session_id(pii_session.session_id)

    assert id_alpha != id_beta


def test_all_sessions_get_different_anon_ids_with_same_salt(db_factory):
    """Each session must map to a unique anon ID (no collisions for distinct IDs)."""
    db = db_factory()
    user = User(email=f"salt_test_{uuid.uuid4().hex[:12]}@test.com", role="trainee")
    db.add(user)
    db.commit()
    db.refresh(user)

    case = Case(title="Salt Test Case", script="Script")
    db.add(case)
    db.commit()
    db.refresh(case)

    session_ids = []
    for _ in range(20):
        s = SessionEntity(user_id=user.id, case_id=case.id, state="completed")
        db.add(s)
        db.flush()
        session_ids.append(s.id)

    db.commit()
    db.close()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon_ids = [generate_anon_session_id(sid) for sid in session_ids]

    assert len(set(anon_ids)) == 20, "Anon ID collision detected"


# ---------------------------------------------------------------------------
# Score consistency
# ---------------------------------------------------------------------------


def test_exported_scores_match_stored_feedback(research_service, pii_session, db_factory):
    """Scores in the JSON export must exactly match what's in the Feedback table."""
    db = db_factory()
    stored_feedback = (
        db.query(Feedback).filter(Feedback.session_id == pii_session.session_id).first()
    )
    assert stored_feedback is not None
    em = stored_feedback.empathy_score
    comm = stored_feedback.communication_score
    overall = stored_feedback.overall_score
    db.close()

    content = research_service.get_export_json_content()
    sessions = json.loads(content)

    anon_id = generate_anon_session_id(pii_session.session_id)
    exported = next(s for s in sessions if s["session_id"] == anon_id)

    feedback_block = exported.get("feedback")
    assert feedback_block is not None, "Feedback block missing from JSON export"
    assert feedback_block["empathy_score"] == pytest.approx(em)
    assert feedback_block["communication_score"] == pytest.approx(comm)
    assert feedback_block["overall_score"] == pytest.approx(overall)


def test_metrics_csv_scores_match_stored_feedback(research_service, pii_session, db_factory):
    """Scores in the metrics CSV must match the stored Feedback row."""
    db = db_factory()
    stored = db.query(Feedback).filter(Feedback.session_id == pii_session.session_id).first()
    assert stored is not None
    em = stored.empathy_score
    spikes = stored.spikes_completion_score
    db.close()

    content = b"".join(research_service.stream_metrics_csv()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    anon_id = generate_anon_session_id(pii_session.session_id)
    row = next((r for r in rows if r["anon_session_id"] == anon_id), None)
    assert row is not None, f"Session {anon_id} not found in metrics CSV"

    assert float(row["empathy_score"]) == pytest.approx(em)
    assert float(row["spikes_completion"]) == pytest.approx(spikes)


# ---------------------------------------------------------------------------
# Export completeness
# ---------------------------------------------------------------------------


def test_json_export_count_matches_db_session_count(research_service, db_factory):
    """Session count in JSON export must equal the number of sessions in the DB (up to limit)."""
    db = db_factory()
    db_count = db.query(SessionEntity).count()
    db.close()

    content = research_service.get_export_json_content()
    exported_count = len(json.loads(content))

    # The service uses limit=1000; exported count must equal DB count when < 1000
    if db_count <= 1000:
        assert exported_count == db_count
    else:
        assert exported_count == 1000


def test_get_all_sessions_count_matches_db(research_service, db_factory):
    """get_all_sessions with default limit must return all sessions when count < limit."""
    db = db_factory()
    db_count = db.query(SessionEntity).count()
    db.close()

    results = research_service.get_all_sessions(limit=1000)

    if db_count <= 1000:
        assert len(results) == db_count
