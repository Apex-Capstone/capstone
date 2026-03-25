"""Quick offline evaluation for seeded BAD / MEDIUM / GOOD transcripts.

Usage (from backend/):
    poetry run python -m src.scripts.evaluate_seeded_fixtures
"""

from __future__ import annotations

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from domain.entities.user import User
from domain.entities.case import Case
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


async def main() -> None:
    # Use in-memory SQLite for repeatable, side-effect-free eval runs.
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()

    try:
        # Shared user and case for all three transcripts
        user = User(
            email="apex_eval@example.com",
            role="trainee",
            full_name="APEX Eval User",
        )
        db.add(user)

        case = Case(
            title="APEX Seeded Fixture Case",
            description="Case for seeded transcript offline evaluation.",
            script="Script content is not used directly in scoring for this evaluation.",
            difficulty_level="intermediate",
            category="test",
            patient_background="Test patient background.",
            expected_spikes_flow=None,
        )
        db.add(case)
        db.commit()
        db.refresh(user)
        db.refresh(case)

        fixtures = [
            TEST_CONVERSATION_BAD,
            TEST_CONVERSATION_MEDIUM,
            TEST_CONVERSATION_GOOD,
        ]

        for fx in fixtures:
            label = fx.get("label", fx.get("name", "UNKNOWN"))
            result = await run_fixture_seeded_transcript_through_scoring(
                db, user, case, fx, include_pipeline_preview=True
            )

            feedback = result["feedback"]
            turn_debug = result.get("turn_debug") or []
            scoring_debug = result.get("scoring_debug") or {}

            missed_count = len(feedback.missed_opportunities or [])
            suggested_count = len(feedback.suggested_responses or [])

            print(f"=== {label} ===")
            print(f"  empathy_score:           {feedback.empathy_score}")
            print(f"  communication_score:     {feedback.communication_score}")
            print(f"  clinical_reasoning_score:{feedback.clinical_reasoning_score}")
            print(f"  professionalism_score:   {feedback.professionalism_score}")
            print(f"  overall_score:           {feedback.overall_score}")
            print(f"  spikes_completion_score: {feedback.spikes_completion_score}")
            print(f"  missed_opportunities:    {missed_count}")
            print(f"  suggested_responses:     {suggested_count}")
            print()

            for entry in turn_debug:
                print(format_turn_debug_entry(entry))
                print()

            print("=== Scoring debug ===")
            print(format_scoring_debug(scoring_debug))
            print()

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

