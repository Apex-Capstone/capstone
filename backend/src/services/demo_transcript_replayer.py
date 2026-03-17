from __future__ import annotations

import json
from typing import Sequence, Tuple

from sqlalchemy.orm import Session

from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from core.errors import NotFoundError
from domain.entities.turn import Turn
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from services.nlu_pipeline import NLUPipeline
from services.stage_tracker import StageTracker
from services.turn_analysis import analyze_user_input, analyze_assistant_response


Transcript = Sequence[Tuple[str, str]]


async def replay_transcript_into_session(
    db: Session,
    session_id: int,
    user_id: int,
    transcript: Transcript,
) -> None:
    """Replay a deterministic transcript into an existing session.

    Creates Turns with metrics_json, spans_json, and spikes_stage populated
    using the rule-based NLU pipeline and StageTracker. No LLM calls are made.
    """
    session_repo = SessionRepository(db)
    turn_repo = TurnRepository(db)

    session = session_repo.get_by_id(session_id)
    if not session:
        raise NotFoundError(f"Session {session_id} not found")

    # Deterministic NLU-only pipeline (no LLM)
    nlu = SimpleRuleNLU()
    pipeline = NLUPipeline(
        span_detector=nlu,
        empathy_detector=nlu,
        question_classifier=nlu,
        tone_analyzer=nlu,
    )
    stage_tracker = StageTracker(session_repo)

    next_turn_number = turn_repo.get_next_turn_number(session_id)
    turn_number = next_turn_number if next_turn_number is not None else 1
    previous_user_turn: Turn | None = None

    for role, text in transcript:
        if role == "user":
            user_metrics, user_spans = await analyze_user_input(pipeline, text)

            stage = stage_tracker.detect_stage(text, session)
            stage_tracker.update_session_stage(session, stage)

            user_turn = Turn(
                session_id=session_id,
                user_id=user_id,
                turn_number=turn_number,
                role="user",
                text=text,
                audio_url=None,
                metrics_json=json.dumps(user_metrics),
                spans_json=json.dumps(user_spans) if user_spans else None,
                spikes_stage=stage,
            )
            turn_repo.create(user_turn)
            previous_user_turn = user_turn
            turn_number += 1
        else:
            # Assistant (patient) turn. Skip if we don't yet have a clinician turn.
            if previous_user_turn is None:
                continue

            assistant_metrics, assistant_spans = await analyze_assistant_response(
                nlu,
                text,
                previous_user_turn,
                latency_ms=0.0,
            )

            assistant_turn = Turn(
                session_id=session_id,
                user_id=None,
                turn_number=turn_number,
                role="assistant",
                text=text,
                audio_url=None,
                metrics_json=json.dumps(assistant_metrics),
                spans_json=json.dumps(assistant_spans) if assistant_spans else None,
                spikes_stage=session.current_spikes_stage,
            )
            turn_repo.create(assistant_turn)
            turn_number += 1

