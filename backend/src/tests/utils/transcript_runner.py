"""Utilities for running seeded transcript fixtures through the scoring service."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from db.base import Base
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from domain.entities.case import Case
from domain.entities.session import Session as SessionEntity
from domain.entities.turn import Turn
from domain.entities.user import User
from services.nlu_pipeline import NLUPipeline
from services.scoring_service import ScoringService
from services.stage_tracker import StageTracker


def _simplify_span(span: dict, default_span_type: Optional[str] = None) -> dict:
    """Project a raw span dict into a small, debug-friendly structure."""
    return {
        "span_type": span.get("span_type", default_span_type),
        "text": span.get("text"),
        "dimension": span.get("dimension"),
        "explicit_or_implicit": span.get("explicit_or_implicit"),
        "type": span.get("type"),
        "confidence": span.get("confidence"),
    }


def create_all_for_test_engine(engine) -> None:
    """Create all tables on the given engine with SQLite schema compatibility.

    For SQLite, temporarily strip schema qualifiers from tables so that
    declarations like `core.users` work. For other dialects, use metadata
    as-is. This is test/eval-only and does not touch the production engine.
    """
    if engine.dialect.name == "sqlite":
        for table in Base.metadata.tables.values():
            table.schema = None
    Base.metadata.create_all(engine)


def format_turn_debug_entry(entry: Dict[str, Any]) -> str:
    """Format a single turn_debug entry into readable text."""
    lines: List[str] = []
    tn = entry.get("turn_number")
    role = entry.get("role")
    text = entry.get("text", "")
    lines.append(f"TURN {tn} ({role})")
    lines.append(f"Text: {text}")
    lines.append("")

    seeded_stage = entry.get("seeded_spikes_stage")
    preview_stage = entry.get("preview_stage")
    if seeded_stage is not None or preview_stage is not None:
        lines.append(f"Seeded Stage: {seeded_stage}")
        lines.append(f"Preview Stage: {preview_stage}")
        lines.append("")

    def _format_spans(label: str, spans: Optional[List[dict]]) -> None:
        lines.append(f"{label}:")
        if not spans:
            lines.append("  (none)")
            return
        for s in spans:
            text_val = s.get("text")
            dim = s.get("dimension")
            expl = s.get("explicit_or_implicit")
            stype = s.get("type") or s.get("span_type")
            parts = [repr(text_val)]
            if dim:
                parts.append(dim)
            if expl:
                parts.append(expl)
            if stype:
                parts.append(stype)
            lines.append("  - " + " (".join([parts[0]]) + (f" → {', '.join(parts[1:])})" if len(parts) > 1 else ")"))

    # Seeded spans grouped heuristically by type
    seeded_spans = entry.get("seeded_spans_json") or []
    seeded_eo = [s for s in seeded_spans if (s.get("span_type") == "eo" or s.get("dimension"))]
    seeded_resp = [s for s in seeded_spans if s.get("span_type") == "response" or s.get("type") in {"understanding", "sharing", "acceptance"}]
    seeded_el = [s for s in seeded_spans if s.get("span_type") == "elicitation" or s.get("type") in {"direct", "indirect"}]

    if seeded_spans:
        lines.append("Seeded spans:")
        _format_spans("  EO", seeded_eo)
        _format_spans("  Responses", seeded_resp)
        _format_spans("  Elicitations", seeded_el)
        lines.append("")

    preview_spans = entry.get("preview_spans") or {}
    lines.append("Preview spans:")
    _format_spans("  EO", preview_spans.get("eo_spans"))
    _format_spans("  Responses", preview_spans.get("response_spans"))
    _format_spans("  Elicitations", preview_spans.get("elicitation_spans"))

    return "\n".join(lines)


def build_scoring_debug(feedback: Any) -> Dict[str, Any]:
    """Extract a compact, debug-friendly view of scoring-side empathy/linkage details."""
    return {
        "missed_opportunities": feedback.missed_opportunities,
        "eo_to_response_links": feedback.eo_to_response_links,
        "eo_to_elicitation_links": feedback.eo_to_elicitation_links,
        "linkage_stats": feedback.linkage_stats,
        "timeline_events": feedback.timeline_events,
        "eo_spans": feedback.eo_spans,
        "response_spans": feedback.response_spans,
        "elicitation_spans": feedback.elicitation_spans,
    }


def format_scoring_debug(scoring_debug: Dict[str, Any]) -> str:
    """Format scoring_debug into a readable summary for debugging.

    Best-effort and defensive against missing or oddly-shaped fields.
    """
    lines: List[str] = []

    def _safe_len(val: Any) -> int:
        try:
            return len(val) if val is not None else 0
        except Exception:
            return 0

    # Missed opportunities
    missed = scoring_debug.get("missed_opportunities") or []
    lines.append("Missed opportunities:")
    if not missed:
        lines.append("  (none)")
    else:
        for mo in missed:
            try:
                tn = mo.get("turn_number")
                text = mo.get("text") or mo.get("patient_text")
                dim = mo.get("dimension")
                parts = [f"turn={tn}"]
                if dim:
                    parts.append(f"dimension={dim}")
                if text:
                    parts.append(f"text={repr(text)}")
                lines.append("  - " + ", ".join(parts))
            except Exception:
                lines.append(f"  - {repr(mo)}")

    # EO→response links
    links_resp = scoring_debug.get("eo_to_response_links") or {}
    lines.append("")
    lines.append("EO→response links:")
    if not links_resp:
        lines.append("  (none)")
    else:
        try:
            for eo_key, resp_list in links_resp.items():
                lines.append(f"  EO {eo_key}: { _safe_len(resp_list) } linked responses")
        except Exception:
            lines.append(f"  {repr(links_resp)}")

    # EO→elicitation links
    links_el = scoring_debug.get("eo_to_elicitation_links") or {}
    lines.append("")
    lines.append("EO→elicitation links:")
    if not links_el:
        lines.append("  (none)")
    else:
        try:
            for eo_key, el_list in links_el.items():
                lines.append(f"  EO {eo_key}: { _safe_len(el_list) } linked elicitations")
        except Exception:
            lines.append(f"  {repr(links_el)}")

    # Linkage stats
    stats = scoring_debug.get("linkage_stats") or {}
    lines.append("")
    lines.append("Linkage stats:")
    if not stats:
        lines.append("  (none)")
    else:
        try:
            for k, v in stats.items():
                lines.append(f"  {k}: {v}")
        except Exception:
            lines.append(f"  {repr(stats)}")

    # Timeline events (compact)
    events = scoring_debug.get("timeline_events") or []
    lines.append("")
    lines.append("Timeline events (first 20):")
    if not events:
        lines.append("  (none)")
    else:
        try:
            for ev in events[:20]:
                tn = ev.get("turn_number")
                etype = ev.get("type")
                label = ev.get("label")
                lines.append(f"  - turn={tn}, type={etype}, label={label}")
            if len(events) > 20:
                lines.append(f"  ... ({len(events) - 20} more)")
        except Exception:
            lines.append(f"  {repr(events)}")

    # Span summaries
    def _summarize_spans(label: str, spans: Any) -> None:
        lines.append("")
        lines.append(f"{label}:")
        if not spans:
            lines.append("  (none)")
            return
        try:
            for s in spans[:10]:
                text_val = s.get("text") if isinstance(s, dict) else None
                dim = s.get("dimension") if isinstance(s, dict) else None
                stype = s.get("type") or s.get("span_type") if isinstance(s, dict) else None
                parts = []
                if text_val:
                    parts.append(repr(text_val))
                if dim:
                    parts.append(dim)
                if stype:
                    parts.append(stype)
                if parts:
                    lines.append("  - " + " | ".join(parts))
                else:
                    lines.append(f"  - {repr(s)}")
            if _safe_len(spans) > 10:
                lines.append(f"  ... ({_safe_len(spans) - 10} more)")
        except Exception:
            lines.append(f"  {repr(spans)}")

    _summarize_spans("EO spans", scoring_debug.get("eo_spans"))
    _summarize_spans("Response spans", scoring_debug.get("response_spans"))
    _summarize_spans("Elicitation spans", scoring_debug.get("elicitation_spans"))

    return "\n".join(lines)


async def run_fixture_seeded_transcript_through_scoring(
    db: Session,
    user: User,
    case: Case,
    transcript_fixture: Dict[str, Any],
    include_pipeline_preview: bool = False,
) -> Dict[str, Any]:
    """Persist a fixture-seeded transcript and run it through ScoringService.

    Returns a dict with feedback, session_id, and per-turn debug info.
    """

    # Create a real Session row for this transcript
    session = SessionEntity(
        user_id=user.id,
        case_id=case.id,
        state="completed",
        current_spikes_stage=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Persist Turn rows directly from the fixture transcript
    for turn_data in transcript_fixture.get("transcript", []):
        role = turn_data["role"]
        turn_number = turn_data["turn_number"]
        text = turn_data["text"]

        metrics = turn_data.get("metrics_json")
        spans = turn_data.get("spans_json")
        expected_spikes = turn_data.get("expected_spikes")

        turn = Turn(
            session_id=session.id,
            user_id=user.id if role == "user" else None,
            turn_number=turn_number,
            role=role,
            text=text,
            audio_url=None,
            metrics_json=json.dumps(metrics) if metrics is not None else None,
            spans_json=json.dumps(spans) if spans is not None else None,
            relations_json=None,
            spikes_stage=expected_spikes,
        )
        db.add(turn)

    db.commit()

    # Run scoring on the seeded data
    scoring_service = ScoringService(db)
    feedback = await scoring_service.generate_feedback(session.id)

    # Build debug info
    fixture_turns = {t["turn_number"]: t for t in transcript_fixture.get("transcript", [])}
    persisted_turns: List[Turn] = (
        db.query(Turn)
        .filter(Turn.session_id == session.id)
        .order_by(Turn.turn_number)
        .all()
    )

    nlu = None
    pipeline = None
    stage_tracker = None
    if include_pipeline_preview:
        nlu = SimpleRuleNLU()
        pipeline = NLUPipeline(
            span_detector=nlu,
            empathy_detector=nlu,
            question_classifier=nlu,
            tone_analyzer=nlu,
        )
        stage_tracker = StageTracker()

    turn_debug: List[Dict[str, Any]] = []

    for t in persisted_turns:
        seeded = fixture_turns.get(t.turn_number, {})
        seeded_metrics = seeded.get("metrics_json")
        seeded_spans = seeded.get("spans_json")
        seeded_stage = seeded.get("expected_spikes")

        persisted_metrics = json.loads(t.metrics_json) if t.metrics_json else None
        persisted_spans_raw = json.loads(t.spans_json) if t.spans_json else None

        debug_entry: Dict[str, Any] = {
            "turn_number": t.turn_number,
            "role": t.role,
            "text": t.text,
            "seeded_metrics_json": seeded_metrics,
            "seeded_spans_json": seeded_spans,
            "seeded_spikes_stage": seeded_stage,
            "persisted_metrics_json": persisted_metrics,
            "persisted_spans_json": persisted_spans_raw,
            "persisted_spikes_stage": t.spikes_stage,
            "preview_question_type": None,
            "preview_spans": {
                "eo_spans": [],
                "response_spans": [],
                "elicitation_spans": [],
            },
            "preview_stage": None,
        }

        if include_pipeline_preview and pipeline is not None and stage_tracker is not None:
            try:
                analysis = await pipeline.analyze(t.text)
                debug_entry["preview_question_type"] = analysis.get("question_type")

                eo_spans = [
                    _simplify_span(s, default_span_type="eo")
                    for s in analysis.get("emotion_spans") or []
                ]
                resp_spans = [
                    _simplify_span(s, default_span_type="response")
                    for s in analysis.get("response_spans") or []
                ]
                elic_spans = [
                    _simplify_span(s, default_span_type="elicitation")
                    for s in analysis.get("elicitation_spans") or []
                ]

                debug_entry["preview_spans"] = {
                    "eo_spans": eo_spans,
                    "response_spans": resp_spans,
                    "elicitation_spans": elic_spans,
                }

                preview_stage = stage_tracker.detect_stage(t.text, session=None)
                debug_entry["preview_stage"] = preview_stage
            except Exception:
                # Preview is best-effort and must not affect scoring
                pass

        turn_debug.append(debug_entry)

    scoring_debug = build_scoring_debug(feedback)

    return {
        "feedback": feedback,
        "session_id": session.id,
        "turn_debug": turn_debug,
        "scoring_debug": scoring_debug,
    }


