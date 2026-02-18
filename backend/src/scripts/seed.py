"""
Seed dev data: users (admins/trainees) + cases.

Usage:
  uvicorn app:app --reload   # run your app normally
  python -m src.scripts.seed         # seed once
  python -m src.scripts.seed --reset # (optional) wipe & reseed (dev only)
"""
import argparse
import asyncio
from datetime import datetime
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

# Reuse your project internals
from core.errors import ConflictError
from db.base import SessionLocal  # adjust if your session factory lives elsewhere
from services.auth_service import AuthService
from services.case_service import CaseService
from services.session_service import SessionService
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from domain.entities.case import Case
from domain.entities.turn import Turn
from domain.entities.user import User
from domain.models.auth import UserCreate
from domain.models.cases import CaseCreate
from domain.models.sessions import SessionCreate

# ---- Defaults (you can tweak) ----
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "admin123"

SECOND_ADMIN_EMAIL = "admin2@example.com"
SECOND_ADMIN_PASS = "admin123"

TRAINEES = [
    ("alice.trainee@example.com", "changeme"),
    ("bob.trainee@example.com", "changeme"),
    ("charlie.trainee@example.com", "changeme"),
]

CASES: Sequence[CaseCreate] = [
    CaseCreate(
        title="Delivering a Difficult Diagnosis",
        description="Practice SPIKES to deliver a cancer diagnosis to a 52-year-old patient.",
        script="""[Persona]

You are a 52-year-old woman who recently had a breast biopsy. You value honesty but are very anxious about cancer. You ask follow-up questions and prefer a calm environment so you can absorb difficult news.


[ClinicalContext]

You know a biopsy was taken for a suspicious lump and have been told results are pending. Today the clinician will disclose that it is early-stage cancer and explain the next steps.


[SPIKES]

Setting: You appreciate a private, calm room with the clinician sitting close.

Perception: You say you have tried not to worry but thoughts about the diagnosis dominate your mind.

Invitation: You want full transparency and need the clinician to speak directly with you.

Knowledge: The word cancer makes you emotional, so clear non-technical language helps you stay present.

Emotions: You may well up and need pauses; empathy keeps you connected.

Strategy: You need a concrete plan with follow-up and support resources.


[BehaviorRules]

- If the clinician avoids naming 'cancer', you ask directly, "Is it cancer?"
- If the clinician uses jargon, you ask, "Can you explain that more simply?"
- If the clinician shows empathy, you calm down and respond more openly.
""",
        objectives="Demonstrate SPIKES coverage; use open-ended questions; acknowledge emotions.",
        difficulty_level="intermediate",
        category="Breaking Bad News",
        patient_background="52F with recent biopsy; worried about malignancy.",
        expected_spikes_flow="setting, perception, invitation, knowledge, emotions, strategy",
    ),
    CaseCreate(
        title="Responding to Patient Distress",
        description="Navigate anger and fear when discussing treatment options with a 34-year-old.",
        script="""[Persona]

You are a 34-year-old man who feels the surgery recommendation threatens your independence. You speak quickly when upset, demand fairness, but can settle once you feel heard.


[ClinicalContext]

You are angry and scared about the upcoming treatment options and uncertain how much the doctor is considering your goals. Today the discussion will focus on clarifying misconceptions and next steps.


[SPIKES]

Setting: You expect a focused, uninterrupted conversation where the clinician faces you directly.

Perception: You say you feel like your concerns are being dismissed and you want to be part of the decision.

Invitation: Ask if you can explain what you worry about before hearing recommendations.

Knowledge: You need concise corrections of the misconceptions driving your anger.

Emotions: You show frustration but calm down when emotions are reflected and validated.

Strategy: You want an agreed plan with clear roles in follow-up.


[BehaviorRules]

- If the clinician avoids naming 'cancer', you ask directly, "Is it cancer?"
- If the clinician uses jargon, you ask, "Can you explain that more simply?"
- If the clinician shows empathy, you calm down and respond more openly.
""",
        objectives="Defuse anger; reflect emotions; correct misconceptions.",
        difficulty_level="advanced",
        category="Emotions",
        patient_background="34M upset about surgery recommendation.",
        expected_spikes_flow="setting, perception, invitation, knowledge, emotions, strategy",
    ),
    CaseCreate(
        title="Breaking Bad News to Family",
        description="Communicate prognosis with family; check understanding & values.",
        script="""[Persona]

You are the adult child of an elderly patient with declining status. You prefer when clinicians are direct but also want reassurance that values guide the care plan.


[ClinicalContext]

The family has seen the latest tests and is bracing for a difficult prognosis. Today the clinician must share the situation, check understanding, and align care with the patient's values.


[SPIKES]

Setting: You want a comfortable conference room with all decision-makers present.

Perception: You ask what your loved one already understands and whether their wishes were discussed.

Invitation: Request a summary of what the clinician thinks is most important right now.

Knowledge: You need gentle yet truthful delivery of key facts about prognosis.

Emotions: You need empathy, space for silence, and acknowledgement of grief.

Strategy: You want to outline a next step plan that respects the patient's goals and family's capacity.


[BehaviorRules]

- If the clinician avoids naming 'cancer', you ask directly, "Is it cancer?"
- If the clinician uses jargon, you ask, "Can you explain that more simply?"
- If the clinician shows empathy, you calm down and respond more openly.
""",
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
    await ensure_user(SECOND_ADMIN_EMAIL, SECOND_ADMIN_PASS, role="admin", full_name="Second Admin")
    for email, pwd in TRAINEES:
        await ensure_user(email, pwd, role="trainee")

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

    async def seed_sessions():
        session_service = SessionService(db)
        session_repo = SessionRepository(db)
        turn_repo = TurnRepository(db)

        def strong_user(email: str) -> User | None:
            return db.query(User).filter(User.email == email).first()

        def case_by_title(title: str) -> Case | None:
            return db.query(Case).filter(Case.title == title).first()

        def already_has_session(user_id: int, case_id: int, must_be_completed: bool) -> bool:
            existing = session_repo.get_by_user(user_id)
            for session in existing:
                if session.case_id == case_id:
                    if must_be_completed and session.state == "completed":
                        return True
                    if not must_be_completed and session.state != "completed":
                        return True
            return False

        async def create_demo_session(
            user: User,
            case_title: str,
            dialogue: list[tuple[str, str]],
            close_after: bool,
            force_new: bool = False,
        ):
            case = case_by_title(case_title)
            if not case:
                print(f"[seed] missing case for session {case_title}")
                return
            if already_has_session(user.id, case.id, must_be_completed=close_after):
                return
            session_data = SessionCreate(case_id=case.id, force_new=force_new)
            session = await session_service.create_session(user.id, session_data)
            for idx, (role, text) in enumerate(dialogue, start=1):
                turn = Turn(
                    session_id=session.id,
                    user_id=user.id if role == "user" else None,
                    turn_number=idx,
                    role=role,
                    text=text,
                    audio_url=None,
                    metrics_json=None,
                    spikes_stage=None,
                    timestamp=datetime.utcnow(),
                )
                turn_repo.create(turn)
            if close_after:
                await session_service.close_session(session.id)
            status = "closed" if close_after else "open"
            print(f"[seed] session -> {user.email} | {case.title} | {status} | id={session.id}")

        trainee = strong_user(TRAINEES[0][0])
        admin = strong_user(ADMIN_EMAIL)
        if not trainee or not admin:
            return

        await create_demo_session(
            trainee,
            "Delivering a Difficult Diagnosis",
            [
                ("user", "I want to be honest but keep the tone gentle; can you tell me what you're most afraid of hearing?"),
                ("assistant", "I appreciate the calm room. Please just tell me what the biopsy showed—I'm anxious but ready for the truth."),
                ("user", "That makes sense. If you ask how bad it is, I'll say early stage while acknowledging fear."),
                ("assistant", "Hearing 'early stage' helps, but I need you to say cancer so I don't keep guessing."),
            ],
            close_after=False,
        )

        await create_demo_session(
            trainee,
            "Responding to Patient Distress",
            [
                ("user", "I'm hearing that you feel I’m pushing surgery—tell me what you’ve heard so far."),
                ("assistant", "I'm scared of losing independence, and surgery feels final."),
                ("user", "Let me reflect that and correct anything you've been told so we can decide together."),
                ("assistant", "Once you hear my concerns, I can relax and we can decide together."),
            ],
            close_after=True,
            force_new=True,
        )

        await create_demo_session(
            admin,
            "Breaking Bad News to Family",
            [
                ("user", "I want to give you clarity while honoring what matters most to your family."),
                ("assistant", "We're bracing for a difficult prognosis. Be direct but tell us how this aligns with Mom’s values."),
                ("user", "I will gently acknowledge your grief and check in before we discuss next steps."),
                ("assistant", "That makes me feel seen; now share the plan so we can make decisions together."),
            ],
            close_after=False,
        )

        await create_demo_session(
            admin,
            "Delivering a Difficult Diagnosis",
            [
                ("user", "I need to ensure you hear the diagnosis while also understanding the support plan."),
                ("assistant", "I already feel the weight of it. Tell me what you found and how we can handle it."),
                ("user", "I’ll highlight your emotions, then summarize the treatment path and referrals."),
                ("assistant", "Knowing the support people and follow-up keeps me grounded."),
            ],
            close_after=True,
            force_new=True,
        )

    await seed_sessions()


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
