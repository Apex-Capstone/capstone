"""
Seed dev data: users (admin/instructor/students) + cases.

Usage:
  uvicorn app:app --reload   # run your app normally
  python -m src.scripts.seed         # seed once
  python -m src.scripts.seed --reset # (optional) wipe & reseed (dev only)
"""
import argparse
import asyncio
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

# Reuse your project internals
from core.errors import ConflictError
from db.base import SessionLocal  # adjust if your session factory lives elsewhere
from services.auth_service import AuthService
from services.case_service import CaseService
from domain.models.auth import UserCreate
from domain.models.cases import CaseCreate

# ---- Defaults (you can tweak) ----
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "admin123"

INSTRUCTOR_EMAIL = "instructor@example.com"
INSTRUCTOR_PASS = "instructor123"

STUDENTS = [
    ("alice.trainee@example.com", "changeme"),
    ("bob.trainee@example.com", "changeme"),
    ("charlie.trainee@example.com", "changeme"),
]

CASES: Sequence[CaseCreate] = [
    CaseCreate(
        title="Delivering a Difficult Diagnosis",
        description="Practice SPIKES to deliver a cancer diagnosis to a 52-year-old patient.",
        script=(
            "Setting: Ensure privacy, sit down.\n"
            "Perception: 'What is your understanding of the tests so far?'\n"
            "Invitation: 'Would you like me to go into details now?'\n"
            "Knowledge: Share results in clear, non-technical language.\n"
            "Emotions: Pause, allow silence, name emotion, validate.\n"
            "Strategy: Summarize and outline next steps, confirm understanding."
        ),
        objectives="Demonstrate SPIKES coverage; use open-ended questions; acknowledge emotions.",
        difficulty_level="intermediate",
        category="Breaking Bad News",
        patient_background="52F with recent biopsy; worried about malignancy.",
        expected_spikes_flow="setting, perception, invitation, knowledge, emotions, strategy",
    ),
    CaseCreate(
        title="Responding to Patient Distress",
        description="Navigate anger and fear when discussing treatment options with a 34-year-old.",
        script=(
            "Setting: Minimize interruptions.\n"
            "Perception: Explore concerns driving anger.\n"
            "Invitation: Ask permission to share clarifications.\n"
            "Knowledge: Correct misconceptions succinctly.\n"
            "Emotions: Reflective listening, validate feelings.\n"
            "Strategy: Agree on next steps and resources."
        ),
        objectives="Defuse anger; reflect emotions; correct misconceptions.",
        difficulty_level="advanced",
        category="Emotions",
        patient_background="34M upset about surgery recommendation.",
        expected_spikes_flow="setting, perception, invitation, knowledge, emotions, strategy",
    ),
    CaseCreate(
        title="Breaking Bad News to Family",
        description="Communicate prognosis with family; check understanding & values.",
        script=(
            "Setting: Invite support persons.\n"
            "Perception: 'What have the doctors already shared?'\n"
            "Invitation: 'How much detail would you like right now?'\n"
            "Knowledge: Deliver key facts gently.\n"
            "Emotions: Empathize; allow silence.\n"
            "Strategy: Align plan with family's values."
        ),
        objectives="Family-centered communication; values-aligned plan.",
        difficulty_level="beginner",
        category="Family Meetings",
        patient_background="Elderly patient with declining status.",
        expected_spikes_flow="setting, perception, invitation, knowledge, emotions, strategy",
    ),
]


async def seed(db: Session, do_reset: bool = False) -> None:
    # Optional destructive dev reset
    if do_reset:
        # WARNING: dev only - wipe tables
        # Adjust table names if needed
        db.execute(text("DELETE FROM cases"))
        db.execute(text("DELETE FROM users"))
        db.commit()

    auth = AuthService(db)
    cases = CaseService(db)

    # ---- Users ----
    async def ensure_user(email: str, password: str, role: str, full_name: str | None = None):
        try:
            user = await auth.register_user(UserCreate(
                email=email,
                password=password,
                role=role,
                full_name=full_name or email.split("@")[0].title(),
            ))
            print(f"[seed] created {role} -> {email}")
            return user
        except ConflictError:
            # already exists; fine
            print(f"[seed] {role} exists -> {email}")
            return None

    await ensure_user(ADMIN_EMAIL, ADMIN_PASS, role="admin", full_name="Admin User")
    await ensure_user(INSTRUCTOR_EMAIL, INSTRUCTOR_PASS, role="instructor", full_name="Instructor User")
    for email, pwd in STUDENTS:
        await ensure_user(email, pwd, role="student")

    # ---- Cases ----
    async def ensure_case(c: CaseCreate):
        # naive upsert by title
        # try to find existing by title; CaseService currently exposes list/get; use repo via service approach:
        try:
            created = await cases.create_case(c)
            print(f"[seed] created case -> {created.title}")
        except ConflictError:
            print(f"[seed] case exists -> {c.title}")

    for c in CASES:
        await ensure_case(c)


async def amain(reset: bool):
    db = SessionLocal()
    try:
        await seed(db, do_reset=reset)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed dev database with users and cases.")
    parser.add_argument("--reset", action="store_true", help="Danger: wipe users & cases before seeding (dev only)")
    args = parser.parse_args()
    asyncio.run(amain(reset=args.reset))


if __name__ == "__main__":
    main()
