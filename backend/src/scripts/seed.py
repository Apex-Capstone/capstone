"""
Seed dev data: users (admins/trainees) + cases.

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
from services.session_service import SessionService
from services.scoring_service import ScoringService
from services.demo_transcript_replayer import replay_transcript_into_session
from repositories.session_repo import SessionRepository
from plugins.load_plugins import load_plugins
from domain.entities.case import Case
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
    # Ensure plugin modules are imported so they self-register in PluginRegistry.
    load_plugins()

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
            await replay_transcript_into_session(
                db=db,
                session_id=session.id,
                user_id=user.id,
                transcript=dialogue,
            )
            if close_after:
                await session_service.close_session(session.id)
                scoring_service = ScoringService(db)
                await scoring_service.generate_feedback(session.id)
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
                ("user", "Thanks for coming in today. I've made sure we have a quiet, private space and I’m going to sit here with you so we can talk this through together."),
                ("assistant", "I appreciate that. I’ve been thinking about this appointment all week and I’m pretty nervous about what you’re going to say."),
                ("user", "Before I share any results, can you tell me what you’ve understood so far and what worries have been on your mind?"),
                ("assistant", "I know the biopsy was for a suspicious lump, and I keep going back and forth between hoping it’s nothing and fearing it’s cancer."),
                ("user", "Thank you for sharing that. Would it be okay if I explain clearly what the biopsy showed, in straightforward language, and we pause whenever you need?"),
                ("assistant", "Yes, please. I’d rather you just be direct with me and not dance around it."),
                ("user", "The biopsy shows that the lump is an early-stage breast cancer. I know hearing the word 'cancer' can feel like a shock, even when we catch it early."),
                ("assistant", "Hearing you actually say 'cancer' makes it very real. I feel a bit numb and scared at the same time."),
                ("user", "I can see how heavy this feels. Many people feel stunned at first; it makes sense that this is a lot to take in right now."),
                ("assistant", "I just keep wondering what this means for my life, my work, and whether I’ll be there for my family."),
                ("user", "Would it help if I walked you through, step by step, what early-stage means in your situation and what the treatment options usually look like?"),
                ("assistant", "Yes, that would help. I don’t want every technical detail, but I need to know the big picture and what comes next."),
                ("user", "In brief, early-stage means we’ve found this before it has spread widely, and we have strong treatments like surgery and medicines that aim to remove and control it. After we talk today, we’ll set up visits with the surgical and oncology teams so you’re not navigating this alone."),
                ("assistant", "Hearing there’s a concrete plan and that we’re catching it early gives me a little bit of hope, even though I’m still scared."),
                ("user", "That mix of fear and hope is completely understandable. For today, I’d like us to focus on your top two questions and then agree on a follow-up visit soon so we can keep checking in as you process this—how does that sound?"),
                ("assistant", "That sounds manageable. If we can go at that pace and you keep being this honest with me, I think I can handle the next steps."),
            ],
            close_after=False,
        )

        await create_demo_session(
            trainee,
            "Responding to Patient Distress",
            [
                ("user", "Thanks for sitting down with me; I've made sure we have some quiet time where we won't be interrupted. How are you feeling about being here today?"),
                ("assistant", "Honestly, I'm tense. It feels like this whole surgery idea is being pushed on me and I'm not sure anyone is really listening."),
                ("user", "It sounds like you're feeling both scared and frustrated, and worried that your independence might be taken away."),
                ("assistant", "Yes, exactly. I'm 34, I work, I take care of things. Surgery just sounds like losing all of that."),
                ("user", "Can you tell me in your own words what you understand so far about why surgery was recommended and what it might involve?"),
                ("assistant", "I just heard 'major surgery' and 'possible complications.' It sounds like I'll be laid up for weeks and totally dependent on other people."),
                ("user", "Would it be alright if I share what I'm seeing from the medical side, and then we check together whether it fits with what matters most to you?"),
                ("assistant", "Okay, yes. I want to know, I just don't want to be talked at."),
                ("user", "Medically, we're recommending a laparoscopic resection, which is a keyhole surgery done through a few small cuts with a camera, not a large open operation. I'm concerned that the way this was first described may have felt like a demand instead of a choice."),
                ("assistant", "Hearing that it's smaller helps a bit, but I'm still scared of being out of control and stuck in bed."),
                ("user", "I can hear how heavy this feels and how much you value staying in control of your life; it makes sense that losing independence is what scares you most."),
                ("assistant", "Yes, I just need to know I'm not signing away my whole life for this."),
                ("user", "So to make a plan together, I'd suggest three steps: first, we book a time where you and I go over the risks and benefits in detail; second, we involve physiotherapy early so there is a clear plan to get you moving again; and third, we schedule a follow-up visit within a week after surgery to adjust the plan if it's not working for you. How does that approach land for you?"),
                ("assistant", "That sounds more manageable. If we can do it that way and I'm not just left on my own, I think I can consider the surgery."),
            ],
            close_after=True,
            force_new=True,
        )

        await create_demo_session(
            admin,
            "Breaking Bad News to Family",
            [
                ("user", "Thank you all for coming in. I’ve made sure we’re in a private room where we can talk openly about what’s been happening with your mom."),
                ("assistant", "We appreciate that. We’ve seen the tests and we’re worried. We just want someone to be honest with us."),
                ("user", "Before I explain the results, can you share what you each understand about her condition and what you’re most concerned about right now?"),
                ("assistant", "We know things have been getting worse, but we’re not sure how serious it really is or what to expect next."),
                ("user", "Thank you for telling me that. Would it be alright if I go over what the team thinks is happening, in clear terms, and then pause to hear your reactions?"),
                ("assistant", "Yes, please. We need to hear the truth, even if it’s hard, but we also want to know how this fits with what she wanted."),
                ("user", "Based on the tests and how she’s been doing, we believe your mom’s illness is in an advanced stage and that time may be shorter than we had hoped."),
                ("assistant", "That’s really hard to hear, even though part of us suspected it. It feels like we’re losing her faster than we were ready for."),
                ("user", "I’m so sorry this is the news I have to share. It’s clear how much you all care about her, and this kind of grief can feel overwhelming."),
                ("assistant", "We just don’t want her to suffer or feel like her wishes are being ignored at the end."),
                ("user", "That’s incredibly important, and it aligns with what she told us about valuing comfort and being surrounded by family. Would it be okay if we talked about a plan that focuses on keeping her comfortable and honoring those wishes?"),
                ("assistant", "Yes, that’s what she would want. We need to know what that plan actually looks like for us day to day."),
                ("user", "We can work with the palliative care team to manage her symptoms at home or in a hospice setting, make sure you have support, and schedule regular check-ins so you’re not carrying this alone."),
                ("assistant", "Hearing there’s a plan that respects her values helps, even though this still hurts a lot."),
                ("user", "Your love and advocacy for her are clear. For now, let’s agree on the next two steps—meeting the palliative team and deciding where she would feel most at peace—and we’ll keep revisiting the plan together."),
                ("assistant", "Okay. As long as we keep talking like this and she’s comfortable, we can face what’s ahead as a family."),
            ],
            close_after=False,
        )

        await create_demo_session(
            trainee,
            "Breaking Bad News to Family",
            [
                ("user", "Thank you for sitting down with me today. I wanted to make sure we had a quiet space to talk about what’s been going on with your dad."),
                ("assistant", "We’ve noticed he’s been getting weaker and in and out of the hospital. We’re scared of what you’re going to say."),
                ("user", "Before I say anything more, can you tell me what you understand about his illness so far and what worries you most right now?"),
                ("assistant", "We know his heart is failing, but we don’t know how much time he really has or what to expect at the end."),
                ("user", "Thank you for being so open. Would it be okay if I share, as clearly and gently as I can, what the team thinks is happening and then we pause to check in with you?"),
                ("assistant", "Yes, we’d rather hear the truth than be left guessing, even if it’s painful."),
                ("user", "Given how his heart is working and how he’s been declining, we believe he is in the last phase of his illness, and that time may be limited, likely in the range of weeks to a few short months."),
                ("assistant", "That’s really hard to hear, even though we wondered. It suddenly feels very real hearing you say that out loud."),
                ("user", "I can see how much you care about him and how heavy this is. Feeling shocked, sad, or even numb right now is completely understandable."),
                ("assistant", "We just want to make sure he’s comfortable and that we’re doing what he would have wanted."),
                ("user", "That’s such an important priority. From what you’ve shared, he valued being at home with family and not being in and out of the hospital—does that sound right to you?"),
                ("assistant", "Yes, that’s exactly what he said. He didn’t want a lot of machines at the end."),
                ("user", "In that case, I’d suggest we focus on a plan that prioritizes comfort at home with support from a palliative care team, regular visits, and medications adjusted to keep him as comfortable as possible."),
                ("assistant", "Having that kind of plan makes this feel a little less chaotic, even though it’s still heartbreaking."),
                ("user", "We can keep talking and adjusting the plan as things change. For today, how about we start with arranging a home visit from the palliative team and setting up a follow-up meeting with me to check how you’re coping?"),
                ("assistant", "That sounds like a good place to start. Knowing we’re not alone in this helps us face what’s coming."),
            ],
            close_after=False,
        )

        await create_demo_session(
            admin,
            "Responding to Patient Distress",
            [
                ("user", "I’ve blocked this time so we won’t be interrupted, and I’m going to sit here with you to understand what this treatment recommendation has been like for you."),
                ("assistant", "Honestly, I’m angry. It feels like this surgery is being pushed on me and no one really cares what it does to my life."),
                ("user", "It sounds like you’re feeling both angry and overlooked, and worried that this plan might take away your independence."),
                ("assistant", "Exactly. I’m 34, I work full time, and I’m scared of ending up dependent on other people."),
                ("user", "Before I add any more information, could you tell me in your own words what you’ve understood about why surgery was recommended and what you’re expecting it to involve?"),
                ("assistant", "All I heard was 'major surgery' and a list of complications. It sounded like months of being laid up and totally out of control."),
                ("user", "Thank you for being so clear. Would it be alright if I explain, step by step, what we’re actually recommending and then we check together whether it fits what matters most to you?"),
                ("assistant", "Yes, but please don’t drown me in medical jargon. I just need to know what this really means for me."),
                ("user", "We’re recommending a minimally invasive, keyhole procedure that typically has a shorter recovery time, with a plan to get you moving again quickly so you can get back to your routines."),
                ("assistant", "Hearing that it’s smaller than I imagined helps, but I’m still scared of being helpless and stuck in bed."),
                ("user", "That fear makes complete sense, especially for someone who values being active and independent as much as you do."),
                ("assistant", "I just don’t want to look back and feel like I signed away my quality of life without understanding my options."),
                ("user", "How about we make a plan where you get a detailed pre-op visit to go over risks and benefits, early physiotherapy to support your recovery, and a follow-up appointment with me soon after surgery to adjust the plan if it’s not working for you?"),
                ("assistant", "Having those steps laid out makes this feel more like a partnership than an order."),
                ("user", "That’s exactly what I’m aiming for. We’ll keep checking in so the plan stays aligned with what’s most important to you."),
                ("assistant", "If we can do it that way, with honest conversations and support, I think I can seriously consider moving forward."),
            ],
            close_after=False,
        )

        await create_demo_session(
            admin,
            "Delivering a Difficult Diagnosis",
            [
                ("user", "Thanks for coming in. Let's sit down and go over your biopsy results."),
                ("assistant", "I've been really nervous. I just keep thinking, what if it's cancer?"),
                ("user", "The biopsy shows that you do have an early-stage breast cancer. I know that's a lot to take in."),
                ("assistant", "So it is cancer. That's a lot to hear all at once."),
                ("user", "It's an invasive ductal carcinoma in an early stage, which means we caught it before it spread widely."),
                ("assistant", "I don't really know what that term means, just that it sounds serious."),
                ("user", "It is a type of breast cancer that we usually treat with surgery and sometimes medication afterward."),
                ("assistant", "Okay... I guess I just want to know what happens to me now."),
                ("user", "We'll refer you to the surgical and oncology teams. They'll organize the specific operations and treatments and contact you with appointments."),
                ("assistant", "Do I need to change anything right now or tell my family something specific?"),
                ("user", "For now, keep your usual routine as much as you can and wait for the hospital letters and calls about next steps."),
                ("assistant", "Alright. I don't fully understand everything, but I guess I'll wait to hear from them."),
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
