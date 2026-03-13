"""Minimal seeded-transcript tests for the APEX scoring pipeline."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.user import User
from domain.entities.case import Case
from domain.models.sessions import FeedbackResponse
from tests.test_conversation_fixture import (
    TEST_CONVERSATION_BAD,
    TEST_CONVERSATION_MEDIUM,
    TEST_CONVERSATION_GOOD,
)
from tests.utils.transcript_runner import (
    run_fixture_seeded_transcript_through_scoring,
    format_turn_debug_entry,
    format_scoring_debug,
    create_all_for_test_engine,
)


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    """Create a minimal test user."""
    user = User(
        email="apex_tester@example.com",
        hashed_password="not_used_in_tests",
        role="trainee",
        full_name="Apex Tester",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    """Create a minimal test case."""
    case = Case(
        title="APEX Seeded Fixture Case",
        description="Case for seeded transcript scoring tests.",
        script="Script content is not used directly in scoring for these tests.",
        difficulty_level="intermediate",
        category="test",
        patient_background="Test patient background.",
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_data",
    [TEST_CONVERSATION_BAD, TEST_CONVERSATION_MEDIUM, TEST_CONVERSATION_GOOD],
)
async def test_seeded_transcript_scoring_smoke(test_db, test_user, test_case, fixture_data):
    """Smoke test: each seeded transcript runs through scoring and returns feedback."""
    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, fixture_data
    )

    feedback = result["feedback"]
    assert isinstance(feedback, FeedbackResponse)
    assert feedback.empathy_score is not None
    assert feedback.overall_score is not None
    assert feedback.spikes_completion_score is not None


@pytest.mark.asyncio
async def test_seeded_transcript_score_ordering(test_db, test_user, test_case):
    """Score ordering: BAD < MEDIUM < GOOD for key metrics."""
    res_bad = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    res_medium = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_MEDIUM
    )
    res_good = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_GOOD
    )

    fb_bad = res_bad["feedback"]
    fb_medium = res_medium["feedback"]
    fb_good = res_good["feedback"]

    ctx = (
        "Score ordering failed.\n"
        f"BAD   ({TEST_CONVERSATION_BAD['label']}): "
        f"emp={fb_bad.empathy_score}, comm={fb_bad.communication_score}, "
        f"clin={fb_bad.clinical_reasoning_score}, prof={fb_bad.professionalism_score}, "
        f"overall={fb_bad.overall_score}, spikes={fb_bad.spikes_completion_score}, "
        f"missed={len(fb_bad.missed_opportunities or [])}, "
        f"suggested={len(fb_bad.suggested_responses or [])}\n"
        f"MED   ({TEST_CONVERSATION_MEDIUM['label']}): "
        f"emp={fb_medium.empathy_score}, comm={fb_medium.communication_score}, "
        f"clin={fb_medium.clinical_reasoning_score}, prof={fb_medium.professionalism_score}, "
        f"overall={fb_medium.overall_score}, spikes={fb_medium.spikes_completion_score}, "
        f"missed={len(fb_medium.missed_opportunities or [])}, "
        f"suggested={len(fb_medium.suggested_responses or [])}\n"
        f"GOOD  ({TEST_CONVERSATION_GOOD['label']}): "
        f"emp={fb_good.empathy_score}, comm={fb_good.communication_score}, "
        f"clin={fb_good.clinical_reasoning_score}, prof={fb_good.professionalism_score}, "
        f"overall={fb_good.overall_score}, spikes={fb_good.spikes_completion_score}, "
        f"missed={len(fb_good.missed_opportunities or [])}, "
        f"suggested={len(fb_good.suggested_responses or [])}"
    )

    assert fb_bad.empathy_score < fb_medium.empathy_score < fb_good.empathy_score, ctx
    assert fb_bad.overall_score < fb_medium.overall_score < fb_good.overall_score, ctx
    assert (
        fb_bad.spikes_completion_score
        <= fb_medium.spikes_completion_score
        <= fb_good.spikes_completion_score
    ), ctx


@pytest.mark.asyncio
async def test_seeded_transcript_missed_opportunities_and_suggestions(test_db, test_user, test_case):
    """BAD conversation should have more missed opportunities and suggestions than GOOD."""
    res_bad = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_BAD
    )
    res_good = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, TEST_CONVERSATION_GOOD
    )

    fb_bad = res_bad["feedback"]
    fb_good = res_good["feedback"]

    bad_missed = len(fb_bad.missed_opportunities or [])
    good_missed = len(fb_good.missed_opportunities or [])
    bad_suggestions = len(fb_bad.suggested_responses or [])
    good_suggestions = len(fb_good.suggested_responses or [])

    ctx = (
        "Missed opportunity / suggestion expectations failed.\n"
        f"BAD  missed={bad_missed}, suggested={bad_suggestions}\n"
        f"GOOD missed={good_missed}, suggested={good_suggestions}"
    )

    assert bad_missed > good_missed, ctx
    assert bad_suggestions >= good_suggestions, ctx


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_data",
    [TEST_CONVERSATION_BAD, TEST_CONVERSATION_MEDIUM, TEST_CONVERSATION_GOOD],
)
async def test_seeded_transcript_score_ranges(test_db, test_user, test_case, fixture_data):
    """Assert that top-level scores fall within the ranges declared in the fixture."""
    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, fixture_data
    )

    feedback = result["feedback"]
    ranges = fixture_data.get("expected_feedback", {}).get("score_ranges", {})

    def _check_range(name: str, value: float | None):
        if value is None:
            return
        expected = ranges.get(name)
        label = fixture_data.get("label", fixture_data.get("name", "UNKNOWN"))
        ctx = (
            f"Score range check failed for {label}.{name}.\n"
            f"Value: {value}\n"
            f"Expected range: {expected if expected else '[0, 100]'}\n"
            f"All scores: "
            f"emp={feedback.empathy_score}, comm={feedback.communication_score}, "
            f"clin={feedback.clinical_reasoning_score}, prof={feedback.professionalism_score}, "
            f"overall={feedback.overall_score}, spikes={feedback.spikes_completion_score}"
        )

        if not expected:
            # Fallback assumption: global scoring scale is 0–100 for all scores.
            assert 0.0 <= value <= 100.0, ctx
        else:
            low, high = expected
            assert low <= value <= high, ctx

    _check_range("empathy_score", feedback.empathy_score)
    _check_range("communication_score", feedback.communication_score)
    _check_range("clinical_reasoning_score", feedback.clinical_reasoning_score)
    _check_range("professionalism_score", feedback.professionalism_score)
    _check_range("overall_score", feedback.overall_score)
    _check_range("spikes_completion_score", feedback.spikes_completion_score)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fixture_data",
    [TEST_CONVERSATION_BAD, TEST_CONVERSATION_MEDIUM, TEST_CONVERSATION_GOOD],
)
async def test_seeded_transcript_turn_level_debug_view(test_db, test_user, test_case, fixture_data, capsys):
    """Ensure turn-level debug structures are present and printable for inspection."""
    result = await run_fixture_seeded_transcript_through_scoring(
        test_db, test_user, test_case, fixture_data, include_pipeline_preview=True
    )

    turn_debug = result.get("turn_debug")
    assert isinstance(turn_debug, list)
    assert len(turn_debug) == len(fixture_data.get("transcript", []))

    scoring_debug = result.get("scoring_debug")
    assert isinstance(scoring_debug, dict)
    assert any(
        scoring_debug.get(key)
        for key in ("linkage_stats", "missed_opportunities", "timeline_events")
    )

    # Print formatted debug for manual inspection when running tests locally
    label = fixture_data.get("label", fixture_data.get("name", "UNKNOWN"))
    print(f"--- Turn-level debug for {label} ---")
    for entry in turn_debug:
        print(format_turn_debug_entry(entry))
        print()

    print("--- Scoring debug ---")
    print(format_scoring_debug(scoring_debug))
    print()


