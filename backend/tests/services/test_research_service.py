"""Unit tests for ResearchService and its module-level helpers.

Verification of:
  - generate_anon_session_id: determinism, format, uniqueness
  - resolve_anon_to_session_id: correct lookup, invalid inputs, missing sessions
  - _anonymize_text: PII redaction patterns
  - _extract_voice_tone_fields: JSON parsing with fallback
  - _generate_csv: header + rows, empty case
  - _anonymize_session: field mapping, with/without turns/feedback
  - get_all_sessions: flattened scores, clinical == overall, communication fallback
  - get_session_by_anon: valid lookup, missing -> ValueError
  - get_export_json_content: valid JSON array
  - get_export_csv_content: correct columns, one row per turn
  - stream_metrics_csv: header + one row per session
  - stream_transcripts_csv: header + one row per turn
  - stream_session_transcript_csv: single-session streaming, unknown raises ValueError
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.feedback import Feedback
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from domain.models.admin import ResearchExportRequest
from services.research_service import (
    ResearchService,
    generate_anon_session_id,
    resolve_anon_to_session_id,
)
from tests.utils.transcript_runner import create_all_for_test_engine

TEST_SALT = "test-anon-salt-xyz"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    e = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(e)
    return e


@pytest.fixture
def test_db(engine):
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_user(test_db):
    user = User(email=f"researcher_{uuid.uuid4().hex[:12]}@test.com", role="admin")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    case = Case(title="Research Case A", script="Script", difficulty_level="advanced")
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.fixture
def completed_session(test_db, test_user, test_case):
    session = SessionEntity(
        user_id=test_user.id,
        case_id=test_case.id,
        state="completed",
        duration_seconds=240,
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def session_with_feedback(test_db, completed_session):
    feedback = Feedback(
        session_id=completed_session.id,
        empathy_score=77.5,
        communication_score=70.0,
        spikes_completion_score=58.0,
        overall_score=69.0,
    )
    test_db.add(feedback)
    test_db.commit()
    return completed_session


@pytest.fixture
def session_with_turns(test_db, session_with_feedback):
    for i, (role, text) in enumerate(
        [
            ("user", "Hello, how are you feeling today?"),
            ("assistant", "I am very worried about my diagnosis."),
            ("user", "I understand your concern."),
        ],
        start=1,
    ):
        turn = Turn(
            session_id=session_with_feedback.id,
            turn_number=i,
            role=role,
            text=text,
        )
        test_db.add(turn)
    test_db.commit()
    return session_with_feedback


@pytest.fixture
def research_service(test_db):
    with patch("services.research_service.get_settings") as mock_settings:
        mock_settings.return_value.research_anon_salt = TEST_SALT
        yield ResearchService(test_db)


# ---------------------------------------------------------------------------
# generate_anon_session_id
# ---------------------------------------------------------------------------


def test_anon_id_format():
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon = generate_anon_session_id(1)
    assert anon.startswith("anon_")
    suffix = anon[len("anon_"):]
    assert len(suffix) == 12
    assert all(c in "0123456789abcdef" for c in suffix)


def test_anon_id_is_deterministic():
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        first = generate_anon_session_id(42)
        second = generate_anon_session_id(42)
    assert first == second


def test_anon_id_differs_across_session_ids():
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        ids = {generate_anon_session_id(i) for i in range(1, 11)}
    assert len(ids) == 10


def test_anon_id_changes_with_salt():
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = "salt-a"
        id_a = generate_anon_session_id(7)
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = "salt-b"
        id_b = generate_anon_session_id(7)
    assert id_a != id_b


# ---------------------------------------------------------------------------
# resolve_anon_to_session_id
# ---------------------------------------------------------------------------


def test_resolve_returns_none_for_empty_string():
    mock_repo = MagicMock()
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        result = resolve_anon_to_session_id("", mock_repo)
    assert result is None


def test_resolve_returns_none_for_non_anon_prefix():
    mock_repo = MagicMock()
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        result = resolve_anon_to_session_id("session_abc123", mock_repo)
    assert result is None


def test_resolve_returns_none_when_no_sessions():
    mock_repo = MagicMock()
    mock_repo.get_all.return_value = []
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        result = resolve_anon_to_session_id("anon_abcdef123456", mock_repo)
    assert result is None


def test_resolve_finds_matching_session():
    session_mock = MagicMock()
    session_mock.id = 99

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        expected_anon = generate_anon_session_id(99)

    mock_repo = MagicMock()
    mock_repo.get_all.return_value = [session_mock]

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        result = resolve_anon_to_session_id(expected_anon, mock_repo)

    assert result == 99


def test_resolve_returns_none_when_no_match():
    sessions = [MagicMock(id=i) for i in range(1, 6)]
    mock_repo = MagicMock()
    mock_repo.get_all.side_effect = lambda skip, limit: sessions if skip == 0 else []

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        result = resolve_anon_to_session_id("anon_000000000000", mock_repo)

    assert result is None


# ---------------------------------------------------------------------------
# _anonymize_text
# ---------------------------------------------------------------------------


def _make_service_for_text(db=None) -> ResearchService:
    svc = ResearchService.__new__(ResearchService)
    return svc


def test_anonymize_text_redacts_email():
    svc = _make_service_for_text()
    result = svc._anonymize_text("Contact me at john.doe@hospital.org please.")
    assert "[REDACTED_EMAIL]" in result
    assert "@" not in result.replace("[REDACTED_EMAIL]", "")


def test_anonymize_text_redacts_phone_dashes():
    svc = _make_service_for_text()
    result = svc._anonymize_text("Call 416-555-1234 for details.")
    assert "[REDACTED_PHONE]" in result


def test_anonymize_text_redacts_phone_parens():
    svc = _make_service_for_text()
    result = svc._anonymize_text("My number is (416) 555-1234.")
    assert "[REDACTED_PHONE]" in result


def test_anonymize_text_redacts_long_numeric_sequences():
    """Phone regex runs before digit runs; 10 contiguous digits match as phone first."""
    svc = _make_service_for_text()
    result = svc._anonymize_text("Patient ID is 1234567890.")
    assert "[REDACTED_PHONE]" in result or "[REDACTED_NUMBER]" in result
    # Nine digits: too short for the phone pattern, still caught by \\d{5,}
    result2 = svc._anonymize_text("Lab accession 123456789.")
    assert "[REDACTED_NUMBER]" in result2


def test_anonymize_text_short_numbers_not_redacted():
    """Numbers with fewer than 5 digits should not be redacted."""
    svc = _make_service_for_text()
    result = svc._anonymize_text("I am 45 years old.")
    assert "45" in result


def test_anonymize_text_redacts_my_name_is():
    svc = _make_service_for_text()
    result = svc._anonymize_text("My name is John Smith, nice to meet you.")
    assert "[REDACTED_NAME]" in result
    assert "John Smith" not in result


def test_anonymize_text_redacts_i_am_name():
    svc = _make_service_for_text()
    result = svc._anonymize_text("I am Jane from the cardiology unit.")
    assert "[REDACTED_NAME]" in result


def test_anonymize_text_i_am_number_not_redacted():
    """'I am 25' should not have the number redacted by the name pattern."""
    svc = _make_service_for_text()
    result = svc._anonymize_text("I am 25 years old.")
    assert "I am" in result


def test_anonymize_text_redacts_title_prefix():
    svc = _make_service_for_text()
    for text, pattern in [
        ("Please see Dr. Williams.", "Dr."),
        ("Ask Mr. Johnson.", "Mr."),
        ("Mrs. Brown is in room 4.", "Mrs."),
        ("Prof. Lee teaches.", "Prof."),
    ]:
        result = svc._anonymize_text(text)
        assert "[REDACTED_NAME]" in result, f"Expected redaction in: {result!r}"


def test_anonymize_text_clean_text_unchanged():
    svc = _make_service_for_text()
    clean = "The patient presents with chest pain and shortness of breath."
    assert svc._anonymize_text(clean) == clean


def test_anonymize_text_empty_string():
    svc = _make_service_for_text()
    assert svc._anonymize_text("") == ""


def test_anonymize_text_none_passthrough():
    svc = _make_service_for_text()
    assert svc._anonymize_text(None) is None


def test_anonymize_text_non_string_passthrough():
    svc = _make_service_for_text()
    assert svc._anonymize_text(42) == 42


# ---------------------------------------------------------------------------
# _extract_voice_tone_fields
# ---------------------------------------------------------------------------


def test_extract_voice_tone_valid_json():
    svc = _make_service_for_text()
    metrics = {
        "voice_tone": {
            "primary": "calm",
            "confidence": 0.95,
            "dimensions": {
                "valence": 0.7,
                "arousal": 0.3,
                "pace_wpm": 120,
                "pitch_hz": 200,
            },
        }
    }
    result = svc._extract_voice_tone_fields(json.dumps(metrics))

    assert result["voice_tone_primary"] == "calm"
    assert result["voice_tone_confidence"] == 0.95
    assert result["voice_tone_valence"] == 0.7
    assert result["voice_tone_arousal"] == 0.3
    assert result["voice_tone_pace_wpm"] == 120
    assert result["voice_tone_pitch_hz"] == 200


def test_extract_voice_tone_none_input():
    svc = _make_service_for_text()
    result = svc._extract_voice_tone_fields(None)
    assert result == {
        "voice_tone_primary": "",
        "voice_tone_confidence": "",
        "voice_tone_valence": "",
        "voice_tone_arousal": "",
        "voice_tone_pace_wpm": "",
        "voice_tone_pitch_hz": "",
    }


def test_extract_voice_tone_invalid_json_returns_defaults():
    svc = _make_service_for_text()
    result = svc._extract_voice_tone_fields("not-json")
    assert result["voice_tone_primary"] == ""


def test_extract_voice_tone_single_quote_fallback():
    """Metrics stored with single quotes instead of double quotes."""
    svc = _make_service_for_text()
    single_quote_json = "{'voice_tone': {'primary': 'anxious', 'confidence': 0.8, 'dimensions': {}}}"
    result = svc._extract_voice_tone_fields(single_quote_json)
    assert result["voice_tone_primary"] == "anxious"


def test_extract_voice_tone_missing_voice_tone_key():
    svc = _make_service_for_text()
    result = svc._extract_voice_tone_fields(json.dumps({"other_metric": 1}))
    assert result["voice_tone_primary"] == ""


def test_extract_voice_tone_missing_dimensions():
    svc = _make_service_for_text()
    metrics = {"voice_tone": {"primary": "neutral", "confidence": 0.5}}
    result = svc._extract_voice_tone_fields(json.dumps(metrics))
    assert result["voice_tone_primary"] == "neutral"
    assert result["voice_tone_valence"] == ""


# ---------------------------------------------------------------------------
# _generate_csv
# ---------------------------------------------------------------------------


def test_generate_csv_empty_list_returns_empty_string():
    svc = _make_service_for_text()
    assert svc._generate_csv([]) == ""


def test_generate_csv_header_and_rows():
    svc = _make_service_for_text()
    data = [
        {"anon_id": "anon_abc", "score": 75.0, "state": "completed"},
        {"anon_id": "anon_def", "score": 80.0, "state": "completed"},
    ]
    csv_content = svc._generate_csv(data)
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)

    assert len(rows) == 2
    assert rows[0]["anon_id"] == "anon_abc"
    assert rows[1]["score"] == "80.0"


# ---------------------------------------------------------------------------
# _anonymize_session
# ---------------------------------------------------------------------------


def test_anonymize_session_basic_fields(research_service, completed_session):
    request = ResearchExportRequest(anonymize=True, include_turns=False, include_feedback=False)
    data = research_service._anonymize_session(completed_session, request)

    assert data["session_id"].startswith("anon_")
    assert data["case_id"] == completed_session.case_id
    assert data["state"] == "completed"
    assert data["duration_seconds"] == 240
    assert "turns" not in data
    assert "feedback" not in data


def test_anonymize_session_no_anonymization_uses_raw_id(research_service, completed_session):
    request = ResearchExportRequest(anonymize=False, include_turns=False, include_feedback=False)
    data = research_service._anonymize_session(completed_session, request)

    assert data["session_id"] == str(completed_session.id)


def test_anonymize_session_includes_feedback(research_service, session_with_feedback):
    request = ResearchExportRequest(anonymize=True, include_turns=False, include_feedback=True)
    data = research_service._anonymize_session(session_with_feedback, request)

    assert "feedback" in data
    fb = data["feedback"]
    assert fb["empathy_score"] == pytest.approx(77.5)
    assert fb["communication_score"] == pytest.approx(70.0)
    assert fb["spikes_completion_score"] == pytest.approx(58.0)
    assert fb["overall_score"] == pytest.approx(69.0)


def test_anonymize_session_includes_turns(research_service, session_with_turns):
    request = ResearchExportRequest(anonymize=True, include_turns=True, include_feedback=False)
    data = research_service._anonymize_session(session_with_turns, request)

    assert "turns" in data
    assert data["turn_count"] == 3
    turns = data["turns"]
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


def test_anonymize_session_turn_text_not_redacted_when_anon_false(
    research_service, session_with_turns
):
    """With anonymize=False, turn text must be preserved verbatim."""
    request = ResearchExportRequest(anonymize=False, include_turns=True, include_feedback=False)
    data = research_service._anonymize_session(session_with_turns, request)

    texts = [t["text"] for t in data["turns"]]
    assert any("Hello" in t for t in texts)


# ---------------------------------------------------------------------------
# get_all_sessions
# ---------------------------------------------------------------------------


def test_get_all_sessions_returns_list(research_service, session_with_feedback):
    results = research_service.get_all_sessions()
    assert isinstance(results, list)
    assert len(results) >= 1


def test_get_all_sessions_flattens_feedback_scores(research_service, session_with_feedback):
    results = research_service.get_all_sessions()
    row = next(r for r in results if r.get("case_id") == session_with_feedback.case_id)

    assert row["empathy_score"] == pytest.approx(77.5)
    assert row["spikes_completion_score"] == pytest.approx(58.0)


def test_get_all_sessions_clinical_score_equals_overall(research_service, session_with_feedback):
    """Flattened list omits overall_score; clinical_score is copied from overall in service."""
    results = research_service.get_all_sessions()
    row = next(r for r in results if r.get("case_id") == session_with_feedback.case_id)

    assert "overall_score" not in row
    assert row["clinical_score"] == pytest.approx(69.0)


def test_get_all_sessions_communication_fallback_to_overall(test_db, test_user, test_case):
    """When communication_score is NULL, it falls back to overall_score."""
    session = SessionEntity(user_id=test_user.id, case_id=test_case.id, state="completed")
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)

    feedback = Feedback(
        session_id=session.id,
        empathy_score=65.0,
        communication_score=None,
        overall_score=62.0,
    )
    test_db.add(feedback)
    test_db.commit()

    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        svc = ResearchService(test_db)
        results = svc.get_all_sessions()

    row = next(r for r in results if r.get("case_id") == test_case.id)
    assert row["communication_score"] == pytest.approx(62.0)


def test_get_all_sessions_includes_case_name(research_service, session_with_feedback, test_case):
    results = research_service.get_all_sessions()
    row = next(r for r in results if r.get("case_id") == test_case.id)
    assert row["case_name"] == "Research Case A"


# ---------------------------------------------------------------------------
# get_session_by_anon
# ---------------------------------------------------------------------------


def test_get_session_by_anon_returns_detail(research_service, session_with_turns):
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon_id = generate_anon_session_id(session_with_turns.id)

    data = research_service.get_session_by_anon(anon_id)
    assert data["case_id"] == session_with_turns.case_id
    assert "turns" in data


def test_get_session_by_anon_raises_for_unknown(research_service):
    with pytest.raises(ValueError, match="Session not found"):
        research_service.get_session_by_anon("anon_000000000000")


def test_get_session_by_anon_raises_for_non_anon_prefix(research_service):
    with pytest.raises(ValueError):
        research_service.get_session_by_anon("bad_prefix_abc123")


# ---------------------------------------------------------------------------
# get_export_json_content
# ---------------------------------------------------------------------------


def test_get_export_json_content_valid_json(research_service):
    content = research_service.get_export_json_content()
    parsed = json.loads(content)
    assert isinstance(parsed, list)


def test_get_export_json_content_each_session_has_anon_id(research_service, session_with_feedback):
    content = research_service.get_export_json_content()
    sessions = json.loads(content)
    assert all(str(s.get("session_id", "")).startswith("anon_") for s in sessions)


# ---------------------------------------------------------------------------
# get_export_csv_content
# ---------------------------------------------------------------------------


def test_get_export_csv_content_has_required_columns(research_service, session_with_turns):
    content = research_service.get_export_csv_content()
    reader = csv.DictReader(io.StringIO(content))
    expected = {
        "anon_session_id",
        "case_id",
        "started_at",
        "empathy_score",
        "spikes_completion",
        "turn_number",
        "speaker",
        "text",
    }
    assert expected.issubset(set(reader.fieldnames or []))


def test_get_export_csv_content_one_row_per_turn(research_service, session_with_turns):
    content = research_service.get_export_csv_content()
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    # Our session has 3 turns; there might be additional sessions seeded by other tests
    assert len(rows) >= 3


# ---------------------------------------------------------------------------
# stream_metrics_csv
# ---------------------------------------------------------------------------


def test_stream_metrics_csv_header_row(research_service):
    chunks = list(research_service.stream_metrics_csv())
    header_line = chunks[0].decode("utf-8").strip()
    assert "anon_session_id" in header_line
    assert "empathy_score" in header_line
    assert "difficulty_level" in header_line


def test_stream_metrics_csv_yields_incrementally(research_service, session_with_feedback):
    chunks = list(research_service.stream_metrics_csv())
    # Should yield at least a header chunk and one data chunk
    assert len(chunks) >= 1


def test_stream_metrics_csv_data_rows_format(research_service, session_with_feedback):
    all_bytes = b"".join(research_service.stream_metrics_csv())
    content = all_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    assert rows[0][0] == "anon_session_id"
    assert len(rows) >= 2  # header + at least one data row


# ---------------------------------------------------------------------------
# stream_transcripts_csv
# ---------------------------------------------------------------------------


def test_stream_transcripts_csv_header_row(research_service):
    chunks = list(research_service.stream_transcripts_csv())
    header_line = chunks[0].decode("utf-8").strip()
    assert "anon_session_id" in header_line
    assert "speaker" in header_line
    assert "text" in header_line


def test_stream_transcripts_csv_yields_turns(research_service, session_with_turns):
    all_bytes = b"".join(research_service.stream_transcripts_csv())
    content = all_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    # header + at least 3 turn rows from our seeded session
    assert len(rows) >= 4


# ---------------------------------------------------------------------------
# stream_session_transcript_csv
# ---------------------------------------------------------------------------


def test_stream_session_transcript_csv_valid(research_service, session_with_turns):
    with patch("services.research_service.get_settings") as m:
        m.return_value.research_anon_salt = TEST_SALT
        anon_id = generate_anon_session_id(session_with_turns.id)

    all_bytes = b"".join(research_service.stream_session_transcript_csv(anon_id))
    content = all_bytes.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    # header + 3 turns
    assert len(rows) >= 4
    assert rows[0][0] == "anon_session_id"


def test_stream_session_transcript_csv_unknown_raises(research_service):
    with pytest.raises(ValueError, match="Session not found"):
        list(research_service.stream_session_transcript_csv("anon_000000000000"))
