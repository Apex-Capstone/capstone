"""Scoring service for empathy, communication, and SPIKES metrics."""

import json
import os
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from config.settings import get_settings
from core.errors import NotFoundError
from core.plugin_manager import _load_class_from_path
from domain.entities.feedback import Feedback
from domain.models.sessions import FeedbackResponse, SuggestedResponse, TimelineEvent
from plugins.registry import PluginRegistry
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository


def _truncate_meta_str(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    if len(value) <= max_len:
        return value
    return value[: max_len - 1] + "…"


def _compact_llm_output_for_evaluator_meta(llm_out: Any) -> dict[str, Any]:
    """Persist a structured LLM summary without storing an unbounded raw dump."""
    d = llm_out.model_dump(mode="json")
    truncated = False
    max_mo, max_ann = 40, 60
    str_cap = 500

    mos_raw = list(d.get("missed_opportunities") or [])
    if len(mos_raw) > max_mo:
        mos_raw = mos_raw[:max_mo]
        truncated = True
    new_mos: list[dict[str, Any]] = []
    for m in mos_raw:
        if not isinstance(m, dict):
            continue
        mm = dict(m)
        for k in (
            "patient_emotional_cue",
            "clinician_response_summary",
            "why_missed_or_weak",
            "suggested_response",
        ):
            if isinstance(mm.get(k), str):
                t = _truncate_meta_str(mm[k], str_cap)
                if t != mm[k]:
                    truncated = True
                mm[k] = t
        new_mos.append(mm)
    d["missed_opportunities"] = new_mos

    ann_raw = list(d.get("spikes_annotations") or [])
    if len(ann_raw) > max_ann:
        ann_raw = ann_raw[:max_ann]
        truncated = True
    new_ann: list[dict[str, Any]] = []
    for a in ann_raw:
        if not isinstance(a, dict):
            continue
        aa = dict(a)
        if isinstance(aa.get("evidence_snippet"), str):
            t = _truncate_meta_str(aa["evidence_snippet"], str_cap)
            if t != aa["evidence_snippet"]:
                truncated = True
            aa["evidence_snippet"] = t
        new_ann.append(aa)
    d["spikes_annotations"] = new_ann

    strengths = list(d.get("strengths") or [])
    if len(strengths) > 25:
        d["strengths"] = strengths[:25]
        truncated = True
    areas = list(d.get("areas_for_improvement") or [])
    if len(areas) > 25:
        d["areas_for_improvement"] = areas[:25]
        truncated = True

    max_eo_bullets, max_stage_map = 40, 60
    if "empathic_opportunities" in d:
        eo_bullets = list(d.get("empathic_opportunities") or [])
        if len(eo_bullets) > max_eo_bullets:
            eo_bullets = eo_bullets[:max_eo_bullets]
            truncated = True
        new_eo: list[str] = []
        for s in eo_bullets:
            if isinstance(s, str):
                t = _truncate_meta_str(s, str_cap)
                if t != s:
                    truncated = True
                new_eo.append(t or "")
            else:
                new_eo.append(str(s))
        d["empathic_opportunities"] = new_eo

    if "stage_turn_mapping" in d:
        stm_raw = list(d.get("stage_turn_mapping") or [])
        if len(stm_raw) > max_stage_map:
            stm_raw = stm_raw[:max_stage_map]
            truncated = True
        new_stm: list[dict[str, Any]] = []
        for row in stm_raw:
            if not isinstance(row, dict):
                continue
            new_stm.append(dict(row))
        d["stage_turn_mapping"] = new_stm

    for text_key in (
        "empathy_review_reasoning",
        "spikes_sequencing_notes",
        "clarity_observation",
        "organization_observation",
        "professionalism_observation",
        "question_quality_observation",
        "notes",
    ):
        if text_key in d and isinstance(d.get(text_key), str):
            t = _truncate_meta_str(d[text_key], str_cap)
            if t != d[text_key]:
                truncated = True
            d[text_key] = t

    if truncated:
        d["_meta_truncated"] = True
    return d


@dataclass
class _RuleFeedbackState:
    """Rule-only computation snapshot before persistence (no LLM)."""

    session_id: int
    session: Any
    turns: list
    eo_spans: list[dict[str, Any]]
    elicitation_spans: list[dict[str, Any]]
    response_spans: list[dict[str, Any]]
    eo_counts_by_dimension: dict[str, Any]
    elicitation_counts_by_type: dict[str, Any]
    response_counts_by_type: dict[str, Any]
    spikes_coverage: dict[str, Any] | None
    spikes_timestamps: dict[str, Any] | None
    spikes_strategies: dict[str, Any] | None
    question_breakdown: dict[str, Any]
    eo_to_response_links: Any
    missed_opportunities: Any
    linkage_stats: Any
    eo_to_elicitation_links: Any
    missed_opportunities_by_dimension: Any
    latency_ms_avg: float
    empathy_score: float
    communication_score: float
    spikes_score: float
    overall_score: float
    rule_scores_for_textual_feedback: tuple[float, float, float]
    strengths: str | None
    improvements: str | None
    timeline_events: list[TimelineEvent]
    suggested_responses: list[SuggestedResponse]


class ScoringService:
    """Service for calculating performance scores and feedback."""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_repo = SessionRepository(db)
        self.turn_repo = TurnRepository(db)
        self.feedback_repo = FeedbackRepository(db)
    
    def _parse_metrics_json(self, metrics_json: str) -> dict[str, Any] | None:
        """Parse metrics_json, handling both proper JSON and string representations."""
        if not metrics_json:
            return None
        
        try:
            # Try parsing as proper JSON first (new format)
            return json.loads(metrics_json)
        except json.JSONDecodeError:
            try:
                # Fallback: handle string representation (old format)
                return json.loads(metrics_json.replace("'", '"'))
            except:
                return None
    
    def _deserialize_json_field(self, value: str | None) -> dict | list | None:
        """Deserialize JSON string to dict/list, or return None."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        # If already dict/list, return as-is (shouldn't happen, but safe)
        return value if isinstance(value, (dict, list)) else None

    def _clamp_score(self, score: float) -> float:
        """Round to 2 decimals and clamp score to [0, 100]."""
        score = round(float(score), 2)
        return max(0.0, min(100.0, score))

    def _merge_rule_and_llm_component_scores(
        self,
        rule_empathy: float,
        rule_communication: float,
        rule_spikes: float,
        llm_empathy: float,
        llm_communication: float,
        llm_spikes: float,
    ) -> tuple[float, float, float, float]:
        """Blend rule vs LLM component scores and recompute overall from merged components."""
        e = 0.7 * rule_empathy + 0.3 * llm_empathy
        c = 0.7 * rule_communication + 0.3 * llm_communication
        s = 0.7 * rule_spikes + 0.3 * llm_spikes
        o = 0.5 * e + 0.2 * c + 0.3 * s
        return (
            self._clamp_score(e),
            self._clamp_score(c),
            self._clamp_score(s),
            self._clamp_score(o),
        )

    # Subscores use this when a component has no usable signal (missing metrics/spans),
    # so the aggregate is not pulled toward 0 by absence of data.
    _COMMUNICATION_MISSING_SUBSCORE = 50.0

    # SPIKES strategy buckets from `_identify_spikes_strategies` that indicate signposting /
    # structure. We intentionally omit "empathize" here: those phrases overlap strongly with
    # empathy response detection and would double-count themes already reflected in empathy_score.
    _COMMUNICATION_STRUCTURE_STRATEGIES = frozenset(
        {"summarize", "acknowledge", "explore", "validate", "clarify"}
    )

    # Among classified (open+closed) questions, treat ~65% open as "enough" for full credit on
    # the open-question term (empathy-oriented dialogue favors exploration over symmetry).
    _QUESTION_OPEN_RATIO_TARGET = 0.65

    def _compute_communication_score(
        self,
        turns: list,
        question_breakdown: dict[str, Any],
        spikes_strategies: dict[str, list[dict[str, Any]]],
        all_spans: list[dict[str, Any]],
    ) -> float:
        """Deterministic communication quality score (0-100, pre-clamp).

        Combines only rule/NLU signals we already persist: tone clarity/calmness,
        question mix + AFCE elicitation spans, and SPIKES-adjacent signposting keywords.

        Final formula (interpretable weights on 0-100 subscores):
            communication_score =
              0.40 * clarity_subscore +
              0.35 * question_quality_subscore +
              0.25 * structure_subscore

        This deliberately does **not** reuse spikes_completion_score, SPIKES stage coverage
        fractions, or the legacy (SPIKES coverage + open-question ratio) blend.

        Subscore definitions:
        - clarity_subscore: primarily ``tone.clear`` per clinician turn; ``tone.calm`` is a
          smaller positive factor (85% / 15%). Turns without parseable ``tone`` are excluded
          from the average; if none qualify, clarity_subscore = neutral (50).
        - question_quality_subscore: rewards a **high** share of open questions (vs 50/50
          symmetry) plus AFCE elicitation span density. Uses smoothed open ratio for small
          question counts and a target threshold so closed questions are not implicitly ideal.
        - structure_subscore: diversity of non-empathize signposting strategies from
          ``_identify_spikes_strategies`` (summarize/clarify/explore/…); if none detected,
          neutral (50).
        """
        clinician_turns = max(1, sum(1 for t in turns if t.role == "user"))

        clarity_subscore = self._communication_clarity_subscore(turns)
        question_quality_subscore = self._communication_question_quality_subscore(
            question_breakdown, clinician_turns, all_spans
        )
        structure_subscore = self._communication_structure_subscore(spikes_strategies)

        return (
            0.40 * clarity_subscore
            + 0.35 * question_quality_subscore
            + 0.25 * structure_subscore
        )

    def _communication_clarity_subscore(self, turns: list) -> float:
        """Tone clarity (primary) and calmness (secondary) over clinician turns with tone data."""
        clear_vals: list[float] = []
        calm_vals: list[float] = []
        for turn in turns:
            if turn.role != "user" or not turn.metrics_json:
                continue
            metrics = self._parse_metrics_json(turn.metrics_json)
            if not metrics:
                continue
            tone = metrics.get("tone")
            if not isinstance(tone, dict):
                continue
            # Require explicit booleans so we do not treat missing keys as False.
            if "clear" not in tone or "calm" not in tone:
                continue
            if tone.get("clear") is True:
                clear_vals.append(1.0)
            elif tone.get("clear") is False:
                clear_vals.append(0.0)
            if tone.get("calm") is True:
                calm_vals.append(1.0)
            elif tone.get("calm") is False:
                calm_vals.append(0.0)

        if not clear_vals:
            return self._COMMUNICATION_MISSING_SUBSCORE

        clear_frac = sum(clear_vals) / len(clear_vals)
        calm_frac = sum(calm_vals) / len(calm_vals) if calm_vals else clear_frac
        return 100.0 * (0.85 * clear_frac + 0.15 * calm_frac)

    def _communication_question_quality_subscore(
        self,
        question_breakdown: dict[str, Any],
        clinician_turns: int,
        all_spans: list[dict[str, Any]],
    ) -> float:
        """Open-question emphasis + elicitation span density (AFCE), capped and normalized.

        Open share uses Beta-style smoothing (open+0.5)/(total+1) so very small question
        counts are not all-or-nothing. The open term is min(1, r_smooth / target); target
        is ``_QUESTION_OPEN_RATIO_TARGET`` (~0.65), i.e. rewards higher open ratio without
        requiring 100% open and without treating 50/50 as ideal.
        """
        open_count = int(question_breakdown.get("open") or 0)
        closed_count = int(question_breakdown.get("closed") or 0)
        total_classified = open_count + closed_count

        elicitation_count = sum(
            1 for s in all_spans if s.get("span_type") == "elicitation"
        )
        density = elicitation_count / float(clinician_turns)
        # Cap typical density (~0.25 elicitation spans per clinician turn) at full credit.
        elicitation_part = min(1.0, density / 0.25)

        if total_classified > 0:
            # Smoothed fraction open in (0,1); stabilizes 1–2 question sessions.
            ratio_open_smooth = (open_count + 0.5) / float(total_classified + 1.0)
            open_part = min(
                1.0,
                ratio_open_smooth / self._QUESTION_OPEN_RATIO_TARGET,
            )
            return 100.0 * (0.55 * open_part + 0.45 * elicitation_part)

        if elicitation_count > 0:
            return 100.0 * elicitation_part

        return self._COMMUNICATION_MISSING_SUBSCORE

    def _communication_structure_subscore(
        self,
        spikes_strategies: dict[str, list[dict[str, Any]]],
    ) -> float:
        """Signposting / structure from SPIKES-stage keyword buckets (not stage completion)."""
        seen: set[str] = set()
        for _stage, events in (spikes_strategies or {}).items():
            for ev in events or []:
                name = ev.get("strategy")
                if isinstance(name, str) and name in self._COMMUNICATION_STRUCTURE_STRATEGIES:
                    seen.add(name)
        if not seen:
            return self._COMMUNICATION_MISSING_SUBSCORE
        return 100.0 * (len(seen) / len(self._COMMUNICATION_STRUCTURE_STRATEGIES))

    async def _compute_rule_feedback_state(self, session_id: int) -> _RuleFeedbackState:
        """Compute rule-only metrics, scores, textual feedback, and timeline (no LLM, no env checks)."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session {session_id} not found")

        turns = self.turn_repo.get_by_session(session_id)

        all_spans = self._extract_spans_from_turns(turns)

        eo_counts_by_dimension = self._calculate_eo_counts_by_dimension(all_spans)
        elicitation_counts_by_type = self._calculate_elicitation_counts_by_type(all_spans)
        response_counts_by_type = self._calculate_response_counts_by_type(all_spans)

        spikes_coverage = self._analyze_spikes_coverage(turns)
        spikes_timestamps = self._calculate_spikes_timestamps(turns)
        spikes_strategies = self._identify_spikes_strategies(turns)

        question_breakdown = self._calculate_question_breakdown(turns)

        eo_spans, elicitation_spans, response_spans = self._collect_span_lists(all_spans)
        eo_to_response_links, missed_opportunities, linkage_stats, _eo_id_to_span = self._compute_eo_linking(
            eo_spans, response_spans, elicitation_spans, turns
        )
        eo_to_elicitation_links = self._compute_eo_to_elicitation_links(
            eo_spans, elicitation_spans, turns
        )
        missed_opportunities_by_dimension = self._compute_missed_opportunities_by_dimension(
            missed_opportunities, eo_spans
        )

        latency_ms_avg = self._calculate_latency_ms_avg(turns)

        total_eos = linkage_stats.get("total_eos", 0) if linkage_stats else 0
        addressed_count = linkage_stats.get("addressed_count", 0) if linkage_stats else 0
        empathy_response_count = sum(response_counts_by_type.values()) if response_counts_by_type else 0
        total_clinician_turns = sum(1 for t in turns if t.role == "user")
        eo_coverage = (addressed_count / total_eos) if total_eos > 0 else 0.0
        empathy_frequency = (empathy_response_count / total_clinician_turns) if total_clinician_turns > 0 else 0.0
        empathy_score = (0.7 * eo_coverage + 0.3 * empathy_frequency) * 100.0

        spikes_score = self._calculate_spikes_completion(session, turns, all_spans)

        communication_score = self._compute_communication_score(
            turns, question_breakdown, spikes_strategies, all_spans
        )

        empathy_score = self._clamp_score(empathy_score)
        communication_score = self._clamp_score(communication_score)
        spikes_score = self._clamp_score(spikes_score)
        overall_score = self._clamp_score(
            round(
                0.5 * empathy_score + 0.2 * communication_score + 0.3 * spikes_score,
                2,
            )
        )

        rule_scores_for_textual_feedback = (
            empathy_score,
            communication_score,
            spikes_score,
        )

        strengths, improvements = self._generate_textual_feedback(
            rule_scores_for_textual_feedback[0],
            rule_scores_for_textual_feedback[1],
            rule_scores_for_textual_feedback[2],
            eo_spans,
        )

        timeline_events = self._build_timeline_events(
            eo_spans, missed_opportunities, response_spans, turns
        )
        suggested_responses = self._build_suggested_responses(missed_opportunities, turns)

        return _RuleFeedbackState(
            session_id=session_id,
            session=session,
            turns=turns,
            eo_spans=eo_spans,
            elicitation_spans=elicitation_spans,
            response_spans=response_spans,
            eo_counts_by_dimension=eo_counts_by_dimension,
            elicitation_counts_by_type=elicitation_counts_by_type,
            response_counts_by_type=response_counts_by_type,
            spikes_coverage=spikes_coverage,
            spikes_timestamps=spikes_timestamps,
            spikes_strategies=spikes_strategies,
            question_breakdown=question_breakdown,
            eo_to_response_links=eo_to_response_links,
            missed_opportunities=missed_opportunities,
            linkage_stats=linkage_stats,
            eo_to_elicitation_links=eo_to_elicitation_links,
            missed_opportunities_by_dimension=missed_opportunities_by_dimension,
            latency_ms_avg=latency_ms_avg,
            empathy_score=empathy_score,
            communication_score=communication_score,
            spikes_score=spikes_score,
            overall_score=overall_score,
            rule_scores_for_textual_feedback=rule_scores_for_textual_feedback,
            strengths=strengths,
            improvements=improvements,
            timeline_events=timeline_events,
            suggested_responses=suggested_responses,
        )

    async def _hybrid_llm_merge_scores(
        self,
        state: _RuleFeedbackState,
        session_id: int,
    ) -> tuple[float, float, float, float, dict[str, Any] | None]:
        """LLM transcript review + 70/30 merge. LLM imports only run inside this method."""
        rule_snapshot = {
            "empathy_score": float(state.empathy_score),
            "communication_score": float(state.communication_score),
            "spikes_completion_score": float(state.spikes_score),
            "overall_score": float(state.overall_score),
        }
        real_llm_enabled = os.getenv("LLM_REVIEWER_REAL_CALLS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not real_llm_enabled:
            return (
                state.empathy_score,
                state.communication_score,
                state.spikes_score,
                state.overall_score,
                None,
            )

        from schemas.llm_reviewer import LLMReviewerInput, TranscriptTurnLite
        from services.llm_reviewer_service import LLMReviewerService
        from adapters.llm.openai_adapter import OpenAIAdapter

        try:
            transcript_context: list[Any] = []
            for t in state.turns:
                speaker = "clinician" if t.role == "user" else "patient"
                transcript_context.append(
                    TranscriptTurnLite(
                        turn_number=t.turn_number,
                        speaker=speaker,
                        text=t.text or "",
                    )
                )

            payload = LLMReviewerInput(
                session_id=session_id,
                case_id=getattr(state.session, "case_id", None),
                transcript_context=transcript_context,
                reviewer_version="v1",
            )

            reviewer = LLMReviewerService(OpenAIAdapter())
            llm_output = await reviewer.review(payload)

            if llm_output is None:
                return (
                    state.empathy_score,
                    state.communication_score,
                    state.spikes_score,
                    state.overall_score,
                    {
                        "phase": "hybrid_llm_v1",
                        "status": "failed",
                        "error": "llm_reviewer_returned_none",
                        "rule_scores": rule_snapshot,
                        "llm_scores": None,
                        "merged_scores": None,
                    },
                )

            llm_snapshot = {
                "empathy_score": float(llm_output.empathy_score),
                "communication_score": float(llm_output.communication_score),
                "spikes_completion_score": float(llm_output.spikes_completion_score),
                "overall_score": float(llm_output.overall_score),
            }
            me, mc, ms, mo = self._merge_rule_and_llm_component_scores(
                rule_snapshot["empathy_score"],
                rule_snapshot["communication_score"],
                rule_snapshot["spikes_completion_score"],
                llm_snapshot["empathy_score"],
                llm_snapshot["communication_score"],
                llm_snapshot["spikes_completion_score"],
            )
            merged_snapshot = {
                "empathy_score": me,
                "communication_score": mc,
                "spikes_completion_score": ms,
                "overall_score": mo,
            }
            evaluator_meta = {
                "phase": "hybrid_llm_v1",
                "status": "success",
                "merge_policy": {
                    "components": "0.7 * rule + 0.3 * llm",
                    "overall": "0.5 * merged_empathy + 0.2 * merged_communication + 0.3 * merged_spikes",
                },
                "rule_scores": rule_snapshot,
                "llm_scores": llm_snapshot,
                "merged_scores": merged_snapshot,
                "llm_output": _compact_llm_output_for_evaluator_meta(llm_output),
            }
            return (me, mc, ms, mo, evaluator_meta)
        except Exception as e:
            return (
                state.empathy_score,
                state.communication_score,
                state.spikes_score,
                state.overall_score,
                {
                    "phase": "hybrid_llm_v1",
                    "status": "failed",
                    "error": str(e)[:500],
                    "rule_scores": rule_snapshot,
                    "llm_scores": None,
                    "merged_scores": None,
                },
            )

    async def _hybrid_v2_llm_merge_scores(
        self,
        state: _RuleFeedbackState,
        session_id: int,
    ) -> tuple[float, float, float, float, dict[str, Any] | None]:
        """Three-call LLM transcript review + same 70/30 component merge as v1."""
        rule_snapshot = {
            "empathy_score": float(state.empathy_score),
            "communication_score": float(state.communication_score),
            "spikes_completion_score": float(state.spikes_score),
            "overall_score": float(state.overall_score),
        }
        real_llm_enabled = os.getenv("LLM_REVIEWER_REAL_CALLS", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not real_llm_enabled:
            return (
                state.empathy_score,
                state.communication_score,
                state.spikes_score,
                state.overall_score,
                None,
            )

        from schemas.llm_reviewer import LLMReviewerInput, TranscriptTurnLite
        from services.hybrid_v2_llm_service import (
            HybridV2LLMOrchestrator,
            build_compiled_review_and_llm_scores,
            overall_v2_status,
        )
        from adapters.llm.openai_adapter import OpenAIAdapter

        try:
            transcript_context: list[Any] = []
            for t in state.turns:
                speaker = "clinician" if t.role == "user" else "patient"
                transcript_context.append(
                    TranscriptTurnLite(
                        turn_number=t.turn_number,
                        speaker=speaker,
                        text=t.text or "",
                    )
                )

            payload = LLMReviewerInput(
                session_id=session_id,
                case_id=getattr(state.session, "case_id", None),
                transcript_context=transcript_context,
                reviewer_version="v2",
            )

            orchestrator = HybridV2LLMOrchestrator(OpenAIAdapter())
            outcome = await orchestrator.run(payload)
            agg_status = overall_v2_status(outcome.prompt_status)

            adapter_calls = orchestrator.adapter_call_count

            if agg_status == "failed":
                return (
                    state.empathy_score,
                    state.communication_score,
                    state.spikes_score,
                    state.overall_score,
                    {
                        "phase": "hybrid_llm_v2",
                        "status": "failed",
                        "prompt_status": outcome.prompt_status,
                        "error": "all_llm_prompts_failed",
                        "rule_scores": rule_snapshot,
                        "llm_scores": None,
                        "merged_scores": None,
                        "llm_adapter_calls": adapter_calls,
                    },
                )

            r_e = rule_snapshot["empathy_score"]
            r_c = rule_snapshot["communication_score"]
            r_s = rule_snapshot["spikes_completion_score"]
            eff_llm_e = float(outcome.empathy.empathy_score) if outcome.empathy else r_e
            eff_llm_c = (
                float(outcome.communication.communication_score) if outcome.communication else r_c
            )
            eff_llm_s = (
                float(outcome.spikes.spikes_completion_score) if outcome.spikes else r_s
            )

            me, mc, ms, mo = self._merge_rule_and_llm_component_scores(
                r_e,
                r_c,
                r_s,
                eff_llm_e,
                eff_llm_c,
                eff_llm_s,
            )
            merged_snapshot = {
                "empathy_score": me,
                "communication_score": mc,
                "spikes_completion_score": ms,
                "overall_score": mo,
            }

            compiled, llm_scores = build_compiled_review_and_llm_scores(
                rule_snapshot,
                outcome.empathy,
                outcome.spikes,
                outcome.communication,
            )

            evaluator_meta: dict[str, Any] = {
                "phase": "hybrid_llm_v2",
                "status": agg_status,
                "prompt_status": outcome.prompt_status,
                "merge_policy": {
                    "components": "0.7 * rule + 0.3 * llm",
                    "overall": "0.5 * merged_empathy + 0.2 * merged_communication + 0.3 * merged_spikes",
                    "llm_component_fallback": "failed prompt uses rule score as LLM slot before merge",
                },
                "rule_scores": rule_snapshot,
                "llm_scores": llm_scores,
                "merged_scores": merged_snapshot,
                "llm_output": _compact_llm_output_for_evaluator_meta(compiled),
                "llm_adapter_calls": adapter_calls,
            }
            return (me, mc, ms, mo, evaluator_meta)
        except Exception as e:
            return (
                state.empathy_score,
                state.communication_score,
                state.spikes_score,
                state.overall_score,
                {
                    "phase": "hybrid_llm_v2",
                    "status": "failed",
                    "prompt_status": {"empathy": "failed", "spikes": "failed", "communication": "failed"},
                    "error": str(e)[:500],
                    "rule_scores": rule_snapshot,
                    "llm_scores": None,
                    "merged_scores": None,
                },
            )

    async def _persist_feedback_from_rule_state(
        self,
        state: _RuleFeedbackState,
        *,
        empathy_score: float,
        communication_score: float,
        spikes_score: float,
        overall_score: float,
        evaluator_meta: dict[str, Any] | None,
    ) -> FeedbackResponse:
        """Persist feedback row and return FeedbackResponse (shared by baseline and hybrid)."""
        session_id = state.session_id
        bias_probe_info = None

        existing_feedback = self.feedback_repo.get_by_session(session_id)
        if existing_feedback:
            feedback = existing_feedback
        else:
            feedback = Feedback(session_id=session_id)

        feedback.empathy_score = empathy_score
        feedback.communication_score = communication_score
        feedback.clinical_reasoning_score = None
        feedback.professionalism_score = None
        feedback.spikes_completion_score = spikes_score
        feedback.overall_score = overall_score

        feedback.eo_counts_by_dimension = (
            json.dumps(state.eo_counts_by_dimension) if state.eo_counts_by_dimension is not None else None
        )
        feedback.elicitation_counts_by_type = (
            json.dumps(state.elicitation_counts_by_type) if state.elicitation_counts_by_type is not None else None
        )
        feedback.response_counts_by_type = (
            json.dumps(state.response_counts_by_type) if state.response_counts_by_type is not None else None
        )

        feedback.linkage_stats = json.dumps(state.linkage_stats) if state.linkage_stats is not None else None
        feedback.missed_opportunities_by_dimension = (
            json.dumps(state.missed_opportunities_by_dimension)
            if state.missed_opportunities_by_dimension is not None
            else None
        )
        feedback.eo_to_elicitation_links = (
            json.dumps(state.eo_to_elicitation_links) if state.eo_to_elicitation_links is not None else None
        )
        feedback.eo_to_response_links = (
            json.dumps(state.eo_to_response_links) if state.eo_to_response_links is not None else None
        )
        feedback.missed_opportunities = (
            json.dumps(state.missed_opportunities) if state.missed_opportunities is not None else None
        )

        feedback.spikes_coverage = json.dumps(state.spikes_coverage) if state.spikes_coverage is not None else None
        feedback.spikes_timestamps = json.dumps(state.spikes_timestamps) if state.spikes_timestamps is not None else None
        feedback.spikes_strategies = json.dumps(state.spikes_strategies) if state.spikes_strategies is not None else None

        feedback.question_breakdown = json.dumps(state.question_breakdown) if state.question_breakdown is not None else None

        feedback.bias_probe_info = json.dumps(bias_probe_info) if bias_probe_info is not None else None
        feedback.evaluator_meta = json.dumps(evaluator_meta) if evaluator_meta is not None else None
        feedback.latency_ms_avg = state.latency_ms_avg

        feedback.strengths = state.strengths if state.strengths and state.strengths.strip() else None
        feedback.areas_for_improvement = (
            state.improvements if state.improvements and state.improvements.strip() else None
        )
        feedback.detailed_feedback = f"Overall Score: {overall_score:.1f}/100" if overall_score >= 0 else None

        if existing_feedback:
            saved_feedback = self.feedback_repo.update(feedback)
        else:
            saved_feedback = self.feedback_repo.create(feedback)

        saved_feedback.eo_counts_by_dimension = self._deserialize_json_field(saved_feedback.eo_counts_by_dimension)
        saved_feedback.elicitation_counts_by_type = self._deserialize_json_field(saved_feedback.elicitation_counts_by_type)
        saved_feedback.response_counts_by_type = self._deserialize_json_field(saved_feedback.response_counts_by_type)
        saved_feedback.linkage_stats = self._deserialize_json_field(saved_feedback.linkage_stats)
        saved_feedback.missed_opportunities_by_dimension = self._deserialize_json_field(
            saved_feedback.missed_opportunities_by_dimension
        )
        saved_feedback.eo_to_elicitation_links = self._deserialize_json_field(saved_feedback.eo_to_elicitation_links)
        saved_feedback.eo_to_response_links = self._deserialize_json_field(saved_feedback.eo_to_response_links)
        saved_feedback.missed_opportunities = self._deserialize_json_field(saved_feedback.missed_opportunities)
        saved_feedback.spikes_coverage = self._deserialize_json_field(saved_feedback.spikes_coverage)
        saved_feedback.spikes_timestamps = self._deserialize_json_field(saved_feedback.spikes_timestamps)
        saved_feedback.spikes_strategies = self._deserialize_json_field(saved_feedback.spikes_strategies)
        saved_feedback.question_breakdown = self._deserialize_json_field(saved_feedback.question_breakdown)
        saved_feedback.bias_probe_info = self._deserialize_json_field(saved_feedback.bias_probe_info)
        saved_feedback.evaluator_meta = self._deserialize_json_field(saved_feedback.evaluator_meta)

        saved_feedback.eo_spans = state.eo_spans
        saved_feedback.elicitation_spans = state.elicitation_spans
        saved_feedback.response_spans = state.response_spans

        saved_feedback.relations = None

        response = FeedbackResponse.model_validate(saved_feedback)

        try:
            self.db.expunge(saved_feedback)
        except Exception:
            pass

        return response.model_copy(
            update={
                "timeline_events": state.timeline_events or None,
                "suggested_responses": state.suggested_responses or None,
            }
        )

    async def generate_feedback_rule_only(self, session_id: int) -> FeedbackResponse:
        """100% rule-based feedback (baseline evaluator path). No LLM."""
        state = await self._compute_rule_feedback_state(session_id)
        return await self._persist_feedback_from_rule_state(
            state,
            empathy_score=state.empathy_score,
            communication_score=state.communication_score,
            spikes_score=state.spikes_score,
            overall_score=state.overall_score,
            evaluator_meta={"phase": "baseline_rule_v1"},
        )

    async def generate_feedback_hybrid(self, session_id: int) -> FeedbackResponse:
        """Rule-based core then optional LLM merge + 70/30 (hybrid evaluator path)."""
        state = await self._compute_rule_feedback_state(session_id)
        e, c, s, o, meta = await self._hybrid_llm_merge_scores(state, session_id)
        return await self._persist_feedback_from_rule_state(
            state,
            empathy_score=e,
            communication_score=c,
            spikes_score=s,
            overall_score=o,
            evaluator_meta=meta,
        )

    async def generate_feedback_hybrid_v2(self, session_id: int) -> FeedbackResponse:
        """Rule-based core + three-call LLM merge (hybrid v2)."""
        state = await self._compute_rule_feedback_state(session_id)
        e, c, s, o, meta = await self._hybrid_v2_llm_merge_scores(state, session_id)
        return await self._persist_feedback_from_rule_state(
            state,
            empathy_score=e,
            communication_score=c,
            spikes_score=s,
            overall_score=o,
            evaluator_meta=meta,
        )

    async def generate_feedback(self, session_id: int) -> FeedbackResponse:
        """Generate comprehensive feedback for a session via the Evaluator plugin.

        The evaluator is resolved primarily from the session's frozen metadata.
        For backward compatibility with existing sessions, this falls back to
        the globally configured settings.evaluator_plugin when the session does
        not yet carry evaluator fields.
        """
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise NotFoundError(f"Session {session_id} not found")

        # Prefer the evaluator frozen on the session; fall back to settings.
        plugin_key: str | None = getattr(session, "evaluator_plugin", None)
        if not plugin_key:
            settings = get_settings()
            plugin_key = getattr(settings, "evaluator_plugin", None)

        if not plugin_key:
            raise RuntimeError("No evaluator plugin configured for scoring.")

        try:
            plugin_cls = PluginRegistry.get_evaluator(plugin_key)
        except ValueError:
            # Backward compatibility: if the evaluator was not registered
            # in the PluginRegistry, load and register it on demand.
            plugin_cls = _load_class_from_path(plugin_key)
            PluginRegistry.register_evaluator(plugin_key, plugin_cls)

        evaluator = plugin_cls()
        return await evaluator.evaluate(self.db, session_id)
    
    # AFCE span-based metric calculation methods
    
    def _extract_spans_from_turns(self, turns: list) -> list[dict[str, Any]]:
        """Extract all spans from turns' spans_json."""
        all_spans = []
        for turn in turns:
            if turn.spans_json:
                spans = self._deserialize_json_field(turn.spans_json)
                if spans and isinstance(spans, list):
                    # Add turn_id and turn_number to each span for reference
                    for span in spans:
                        span["turn_id"] = turn.id
                        span["turn_number"] = turn.turn_number
                    all_spans.extend(spans)
        return all_spans
    
    def _calculate_eo_counts_by_dimension(self, all_spans: list) -> dict[str, Any]:
        """Calculate EO counts by AFCE dimension and explicit/implicit."""
        counts = {
            "Feeling": {"explicit": 0, "implicit": 0},
            "Judgment": {"explicit": 0, "implicit": 0},
            "Appreciation": {"explicit": 0, "implicit": 0},
        }
        
        for span in all_spans:
            if span.get("span_type") == "eo":
                dimension = span.get("dimension")
                explicit_implicit = span.get("explicit_or_implicit")
                if dimension in counts and explicit_implicit in ["explicit", "implicit"]:
                    counts[dimension][explicit_implicit] += 1
        
        return counts
    
    def _calculate_elicitation_counts_by_type(self, all_spans: list) -> dict[str, Any]:
        """Calculate elicitation counts by type (direct/indirect) and dimension."""
        counts = {
            "direct": {"Feeling": 0, "Judgment": 0, "Appreciation": 0},
            "indirect": {"Feeling": 0, "Judgment": 0, "Appreciation": 0},
        }
        
        for span in all_spans:
            if span.get("span_type") == "elicitation":
                elicitation_type = span.get("type")
                dimension = span.get("dimension")
                if elicitation_type in counts and dimension in counts[elicitation_type]:
                    counts[elicitation_type][dimension] += 1
        
        return counts
    
    def _calculate_response_counts_by_type(self, all_spans: list) -> dict[str, int]:
        """Calculate response counts by AFCE type (understanding/sharing/acceptance)."""
        counts = {
            "understanding": 0,
            "sharing": 0,
            "acceptance": 0,
        }
        
        for span in all_spans:
            if span.get("span_type") == "response":
                response_type = span.get("type")
                if response_type in counts:
                    counts[response_type] += 1
        
        return counts
    
    def _link_eos_to_responses(
        self,
        eo_spans: list[dict],
        response_spans: list[dict],
        turns: list,
    ) -> dict[int, list[dict]]:
        """Link EOs to responses in the immediate next clinician turn only.

        A response span can address an EO only when it appears in the first
        clinician turn after the EO turn. Later clinician turns are invalid and
        cannot retroactively resolve that EO.
        
        Returns:
            dict mapping EO turn_number to list of linked response spans
        """
        # Create a map of turn_number -> turn for quick lookup
        turn_map = {turn.turn_number: turn for turn in turns}
        
        # Group response spans by turn_number
        responses_by_turn = {}
        for response_span in response_spans:
            turn_num = response_span.get("turn_number")
            if turn_num is not None:
                if turn_num not in responses_by_turn:
                    responses_by_turn[turn_num] = []
                responses_by_turn[turn_num].append(response_span)
        
        # For each EO, find responses only in the next clinician turn
        eo_to_responses = {}
        
        for eo_span in eo_spans:
            eo_turn_num = eo_span.get("turn_number")
            if eo_turn_num is None:
                continue
            
            # Find the EO's turn
            eo_turn = turn_map.get(eo_turn_num)
            if not eo_turn:
                continue
            
            # Only link if EO is from a patient turn (assistant role)
            if eo_turn.role != "assistant":
                continue
            
            linked_responses = []
            for response_span in response_spans:
                response_turn_num = response_span.get("turn_number")
                if response_turn_num is None:
                    continue
                if self._is_temporally_valid_response_link(
                    eo_turn_number=eo_turn_num,
                    response_turn_number=response_turn_num,
                    turn_map=turn_map,
                ):
                    linked_responses.append(response_span)

            eo_to_responses[eo_turn_num] = linked_responses
        
        return eo_to_responses

    def _is_temporally_valid_response_link(
        self,
        eo_turn_number: int,
        response_turn_number: int,
        turn_map: dict[int, Any],
    ) -> bool:
        """Return True only when response is in EO's next clinician turn."""
        if response_turn_number <= eo_turn_number:
            return False

        next_clinician_turn = self._get_next_clinician_turn_number(
            eo_turn_number=eo_turn_number,
            turn_map=turn_map,
        )
        if next_clinician_turn is None:
            return False

        return response_turn_number == next_clinician_turn

    def _get_next_clinician_turn_number(
        self,
        eo_turn_number: int,
        turn_map: dict[int, Any],
    ) -> int | None:
        """Find the next user/clinician turn after a given EO turn."""
        max_turn = max(turn_map.keys(), default=0)
        for turn_number in range(eo_turn_number + 1, max_turn + 1):
            turn = turn_map.get(turn_number)
            if turn and turn.role == "user":
                return turn_number
        return None
    
    def _compute_eo_linking(
        self,
        eo_spans: list,
        response_spans: list,
        elicitation_spans: list,
        turns: list,
    ) -> tuple[list, list, dict, dict]:
        """Compute EO→response links, missed opportunities, and linkage stats.
        
        Returns:
            Tuple of (eo_to_response_links, missed_opportunities, linkage_stats, eo_id_to_span)
        """
        # Link EOs to responses
        eo_to_responses_map = self._link_eos_to_responses(eo_spans, response_spans, turns)
        
        # Build eo_to_response_links list
        eo_to_response_links = []
        missed_opportunities = []
        addressed_count = 0
        missed_count = 0
        
        # Create span ID mapping (use turn_number + index as ID)
        span_id_map = {}
        next_id = 1
        eo_id_to_span: dict[str, dict[str, Any]] = {}
        
        # Assign IDs to EOs
        eo_id_map = {}
        for eo in eo_spans:
            eo_id = f"eo_{next_id}"
            eo_id_map[id(eo)] = eo_id
            span_id_map[eo_id] = eo
            eo_id_to_span[eo_id] = eo
            next_id += 1
        
        # Assign IDs to responses (use index-based matching since objects may differ)
        response_id_map = {}
        response_match_key_map = {}  # Map from (turn_number, start_char, end_char, text) to ID
        for i, resp in enumerate(response_spans):
            resp_id = f"resp_{next_id}"
            response_id_map[i] = resp_id
            span_id_map[resp_id] = resp
            # Create a match key for linking
            match_key = (
                resp.get("turn_number"),
                resp.get("start_char"),
                resp.get("end_char"),
                resp.get("text", "")[:50],  # First 50 chars for matching
            )
            response_match_key_map[match_key] = resp_id
            next_id += 1
        
        # Create links
        for eo in eo_spans:
            eo_turn_num = eo.get("turn_number")
            eo_id = eo_id_map.get(id(eo))
            
            if eo_turn_num is None or eo_id is None:
                continue
            
            linked_responses = eo_to_responses_map.get(eo_turn_num, [])
            
            if linked_responses:
                addressed_count += 1
                # Create links for each linked response
                for resp in linked_responses:
                    # Match response by turn_number, start_char, end_char, and text
                    match_key = (
                        resp.get("turn_number"),
                        resp.get("start_char"),
                        resp.get("end_char"),
                        resp.get("text", "")[:50],
                    )
                    resp_id = response_match_key_map.get(match_key)
                    if resp_id:
                        eo_to_response_links.append({
                            "source_span_id": eo_id,
                            "target_span_id": resp_id,
                            "relation_type": "responds_to",
                            "confidence": 0.9,
                        })
            else:
                missed_count += 1
                missed_opportunities.append({
                    "span_id": eo_id,
                    "turn_number": eo_turn_num,
                    "dimension": eo.get("dimension"),
                    "explicit_or_implicit": eo.get("explicit_or_implicit"),
                    "text": eo.get("text", "")[:100],  # Truncate
                })
        
        total_eos = len(eo_spans)
        linkage_stats = {
            "total_eos": total_eos,
            "addressed_count": addressed_count,
            "missed_count": missed_count,
            "addressed_rate": addressed_count / total_eos if total_eos > 0 else 0.0,
            "missed_rate": missed_count / total_eos if total_eos > 0 else 0.0,
        }
        
        # Convert list to dict keyed by EO ID for easier lookup
        eo_to_response_links_dict = {}
        for link in eo_to_response_links:
            source_id = link["source_span_id"]
            if source_id not in eo_to_response_links_dict:
                eo_to_response_links_dict[source_id] = []
            eo_to_response_links_dict[source_id].append(link)
        
        return eo_to_response_links_dict, missed_opportunities, linkage_stats, eo_id_to_span
    
    def _compute_eo_to_elicitation_links(
        self,
        eo_spans: list,
        elicitation_spans: list,
        turns: list,
    ) -> list:
        """Compute EO→elicitation links.
        
        Returns:
            List of links with source_span_id, target_span_id, relation_type
        """
        links = []
        
        # Create span ID mapping
        eo_id_map = {}
        next_id = 1
        
        for eo in eo_spans:
            eo_id = f"eo_{next_id}"
            eo_id_map[id(eo)] = eo_id
            next_id += 1
        
        elicitation_id_map = {}
        for el in elicitation_spans:
            el_id = f"elic_{next_id}"
            elicitation_id_map[id(el)] = el_id
            next_id += 1
        
        # Create a map of turn_number -> elicitation spans
        elicitations_by_turn = {}
        for el in elicitation_spans:
            turn_num = el.get("turn_number")
            if turn_num is not None:
                if turn_num not in elicitations_by_turn:
                    elicitations_by_turn[turn_num] = []
                elicitations_by_turn[turn_num].append(el)
        
        # For each EO, find elicitations in the same or previous clinician turns
        turn_map = {turn.turn_number: turn for turn in turns}
        
        for eo in eo_spans:
            eo_turn_num = eo.get("turn_number")
            eo_id = eo_id_map.get(id(eo))
            eo_dimension = eo.get("dimension")
            
            if eo_turn_num is None or eo_id is None:
                continue
            
            # Find the EO's turn
            eo_turn = turn_map.get(eo_turn_num)
            if not eo_turn or eo_turn.role != "assistant":  # Patient turn
                continue
            
            # Look back at previous clinician turns (up to 2 turns back)
            # to find elicitations that may have prompted this EO
            turns_checked = 0
            current_turn_num = eo_turn_num - 1
            
            while turns_checked < 2 and current_turn_num > 0:
                if current_turn_num in turn_map:
                    candidate_turn = turn_map[current_turn_num]
                    if candidate_turn.role == "user":  # Clinician turn
                        turns_checked += 1
                        # Check if there are elicitations in this turn matching the EO dimension
                        if current_turn_num in elicitations_by_turn:
                            for el in elicitations_by_turn[current_turn_num]:
                                el_dimension = el.get("dimension")
                                el_id = elicitation_id_map.get(id(el))
                                # Match if dimensions match or if elicitation is general
                                if el_id and (el_dimension == eo_dimension or el_dimension == "Feeling"):
                                    links.append({
                                        "source_span_id": eo_id,
                                        "target_span_id": el_id,
                                        "relation_type": "elicits",
                                        "confidence": 0.85,
                                    })
                
                current_turn_num -= 1
        
        # Convert list to dict keyed by EO ID for easier lookup
        eo_to_elicitation_links_dict = {}
        for link in links:
            source_id = link["source_span_id"]
            if source_id not in eo_to_elicitation_links_dict:
                eo_to_elicitation_links_dict[source_id] = []
            eo_to_elicitation_links_dict[source_id].append(link)
        
        return eo_to_elicitation_links_dict
    
    def _compute_missed_opportunities_by_dimension(
        self,
        missed_opportunities: list,
        eo_spans: list,
    ) -> dict:
        """Compute missed opportunities counts by dimension.
        
        Returns:
            Dict with counts per dimension
        """
        counts = {
            "Feeling": 0,
            "Judgment": 0,
            "Appreciation": 0,
        }
        
        for missed in missed_opportunities:
            dimension = missed.get("dimension")
            if dimension in counts:
                counts[dimension] += 1
        
        return counts
    
    def _collect_span_lists(
        self,
        all_spans: list,
    ) -> tuple[list, list, list]:
        """Collect spans into separate lists by type for turn-level analysis."""
        eo_spans = []
        elicitation_spans = []
        response_spans = []
        
        for span in all_spans:
            span_type = span.get("span_type")
            if span_type == "eo":
                eo_spans.append(span)
            elif span_type == "elicitation":
                elicitation_spans.append(span)
            elif span_type == "response":
                response_spans.append(span)
        
        return eo_spans, elicitation_spans, response_spans
    
    def _calculate_spikes_completion(
        self, 
        session, 
        turns: list,
        all_spans: list,
    ) -> float:
        """Calculate SPIKES protocol completion score as simple coverage.
        
        Returns a 0–100 score based on how many of the six canonical SPIKES
        stages were covered at least once in the conversation.
        """
        # Map various labels to the canonical six SPIKES stages
        stage_map = {
            "s": "setting",
            "setting": "setting",
            "p": "perception",
            "perception": "perception",
            "i": "invitation",
            "invitation": "invitation",
            "k": "knowledge",
            "knowledge": "knowledge",
            "e": "empathy",
            "emotion": "empathy",
            "empathy": "empathy",
            "s2": "strategy",
            "strategy": "strategy",
            "summary": "strategy",
        }

        covered: set[str] = set()
        for turn in turns:
            if not turn.spikes_stage:
                continue
            raw = str(turn.spikes_stage).strip().lower()
            canonical = stage_map.get(raw)
            if canonical:
                covered.add(canonical)

        # Canonical six stages
        canonical_stages = ["setting", "perception", "invitation", "knowledge", "empathy", "strategy"]
        total_stages = len(canonical_stages)

        covered_count = len(covered & set(canonical_stages))
        coverage_fraction = covered_count / total_stages if total_stages > 0 else 0.0

        spikes_completion_score = coverage_fraction * 100.0
        spikes_completion_score = max(0.0, min(100.0, spikes_completion_score))
        return round(spikes_completion_score, 2)
    
    def _calculate_question_breakdown(self, turns: list) -> dict[str, Any]:
        """Calculate question breakdown: open, closed, and eliciting questions."""
        open_count = 0
        closed_count = 0
        eliciting_count = 0
        
        for turn in turns:
            if turn.role == "user" and turn.metrics_json:
                metrics = self._parse_metrics_json(turn.metrics_json)
                if metrics:
                    q_type = metrics.get("question_type")
                    if q_type == "open":
                        open_count += 1
                    elif q_type == "closed":
                        closed_count += 1
                    
                    # Check if question is eliciting (asks for emotion/feeling)
                    text_lower = turn.text.lower()
                    eliciting_keywords = ["feel", "feeling", "emotion", "emotions", "how do you", "what do you feel"]
                    if any(keyword in text_lower for keyword in eliciting_keywords):
                        eliciting_count += 1
        
        total = open_count + closed_count
        return {
            "open": open_count,
            "closed": closed_count,
            "eliciting": eliciting_count,
            "ratio_open": open_count / total if total > 0 else 0,
        }
    
    def _analyze_spikes_coverage(self, turns: list) -> dict[str, Any]:
        """Analyze coverage of SPIKES stages."""
        covered_stages = set()
        for turn in turns:
            if turn.spikes_stage:
                covered_stages.add(turn.spikes_stage)
        
        all_stages = ["S", "P", "I", "K", "E", "S2"]
        covered_list = sorted(list(covered_stages))
        percent = len(covered_stages) / len(all_stages) if all_stages else 0.0
        
        return {
            "covered": covered_list,
            "percent": percent,
        }
    
    def _generate_textual_feedback(
        self,
        empathy_score: float,
        communication_score: float,
        spikes_completion_score: float,
        eo_spans: list | None = None,
    ) -> tuple[str, str]:
        """Generate strengths and improvement areas (scores are 0-100)."""
        strengths = []
        improvements = []

        if eo_spans is None:
            eo_spans = []

        if empathy_score > 70:
            strengths.append("Excellent use of empathetic language")
        if communication_score > 70:
            strengths.append("Clear communication with balanced questioning and structured delivery")
        if spikes_completion_score > 70:
            strengths.append("Strong coverage of SPIKES stages across the conversation")

        if empathy_score < 50:
            improvements.append("Work on responding to empathy opportunities when they arise")
        elif not eo_spans and empathy_score < 70:
            improvements.append("Consider recognizing and naming patient emotions more explicitly")
        if communication_score < 50:
            improvements.append(
                "Aim for clearer explanations, a better mix of open and closed questions, and more explicit signposting"
            )
        if spikes_completion_score < 50:
            improvements.append(
                "Progress through more SPIKES stages (setting through strategy) in order"
            )

        return "\n".join(strengths), "\n".join(improvements)

    def _build_timeline_events(
        self,
        eo_spans: list,
        missed_opportunities: list,
        response_spans: list,
        turns: list,
    ) -> list[TimelineEvent]:
        """Build timeline events from EOs, responses, missed opportunities, and SPIKES stages."""
        events: list[TimelineEvent] = []
        seen: set[tuple[int, str]] = set()

        def add_event(turn_number: int, event_type: Literal["eo", "response", "missed", "spikes"], label: str) -> None:
            key = (turn_number, event_type)
            if key not in seen:
                seen.add(key)
                events.append(TimelineEvent(turn_number=turn_number, type=event_type, label=label))

        for eo in eo_spans or []:
            tn = eo.get("turn_number")
            if tn is not None:
                add_event(tn, "eo", "Empathy Opportunity")

        for resp in response_spans or []:
            tn = resp.get("turn_number")
            if tn is not None:
                add_event(tn, "response", "Empathy Response")

        for missed in missed_opportunities or []:
            tn = missed.get("turn_number")
            if tn is not None:
                add_event(tn, "missed", "Missed Opportunity")

        for turn in turns:
            if turn.spikes_stage:
                stage = str(turn.spikes_stage).strip()
                label_map = {
                    "setting": "SPIKES Setting",
                    "s": "SPIKES Setting",
                    "perception": "SPIKES Perception",
                    "p": "SPIKES Perception",
                    "invitation": "SPIKES Invitation",
                    "i": "SPIKES Invitation",
                    "knowledge": "SPIKES Knowledge",
                    "k": "SPIKES Knowledge",
                    "emotion": "SPIKES Emotion",
                    "empathy": "SPIKES Emotion",
                    "e": "SPIKES Emotion",
                    "strategy": "SPIKES Strategy",
                    "summary": "SPIKES Strategy",
                    "s2": "SPIKES Strategy",
                }
                label = label_map.get(stage.lower(), f"SPIKES {stage}")
                add_event(turn.turn_number, "spikes", label)

        events.sort(key=lambda e: (e.turn_number, e.type))
        return events

    def _build_suggested_responses(
        self,
        missed_opportunities: list,
        turns: list,
    ) -> list[SuggestedResponse]:
        """Build suggested empathetic responses for missed opportunities."""
        template = "I can see this is really difficult. Thank you for sharing that with me."
        suggestions: list[SuggestedResponse] = []
        turn_map = {t.turn_number: t for t in turns}

        for missed in missed_opportunities or []:
            tn = missed.get("turn_number")
            patient_text = missed.get("text", "")[:200] or "patient expressed emotion"
            if tn is not None:
                turn = turn_map.get(tn)
                if turn and turn.text:
                    patient_text = turn.text[:200]
                suggestions.append(
                    SuggestedResponse(
                        turn_number=tn,
                        patient_text=patient_text,
                        suggestion=template,
                    )
                )
        return suggestions
    
    # SPIKES metrics
    def _calculate_spikes_timestamps(self, turns: list) -> dict[str, Any]:
        """Track when each SPIKES stage started and ended."""
        timestamps = {}
        stage_starts = {}
        
        for turn in turns:
            if turn.spikes_stage:
                stage = turn.spikes_stage
                if stage not in stage_starts:
                    stage_starts[stage] = turn.timestamp
                    timestamps[stage] = {
                        "start_ts": str(turn.timestamp),
                        "end_ts": str(turn.timestamp),
                    }
                else:
                    timestamps[stage]["end_ts"] = str(turn.timestamp)
        
        return timestamps
    
    def _identify_spikes_strategies(self, turns: list) -> dict[str, list[dict[str, Any]]]:
        """Map strategies used per SPIKES stage."""
        strategies = {}
        
        strategy_keywords = {
            "summarize": [
                "summary", "summarize", "recap", "to summarize",
                "let me summarize", "in summary", "to recap"
            ],
            "acknowledge": [
                "understand", "acknowledge", "recognize", "i see",
                "i hear you", "i get it", "i understand"
            ],
            "explore": [
                "explore", "tell me more", "can you", "would you like to",
                "how do you feel", "what are your thoughts", "help me understand"
            ],
            "validate": [
                "valid", "makes sense", "understandable", "that's normal",
                "that's understandable", "i can see why"
            ],
            "empathize": [
                "i'm sorry", "that must be", "i can imagine", "that sounds",
                "i understand how", "that must feel"
            ],
            "clarify": [
                "clarify", "let me clarify", "to be clear", "just to make sure",
                "can you clarify", "help me understand"
            ],
        }
        
        for turn in turns:
            if turn.spikes_stage and turn.role == "user":  # User (doctor) uses strategies
                stage = turn.spikes_stage
                if stage not in strategies:
                    strategies[stage] = []
                
                text_lower = turn.text.lower()
                # Check for multiple strategies (don't break after first match)
                matched_strategies = []
                for strategy, keywords in strategy_keywords.items():
                    if any(keyword in text_lower for keyword in keywords):
                        matched_strategies.append(strategy)
                
                # Add all matched strategies
                for strategy in matched_strategies:
                    strategies[stage].append({
                        "strategy": strategy,
                        "turn": turn.turn_number,
                    })
        
        return strategies
    
    # Performance metrics
    def _calculate_latency_ms_avg(self, turns: list) -> float:
        """Calculate average response latency in milliseconds."""
        latencies = []
        
        for turn in turns:
            if turn.role == "assistant" and turn.metrics_json:
                metrics = self._parse_metrics_json(turn.metrics_json)
                if metrics:
                    latency = metrics.get("latency_ms")
                    if latency:
                        latencies.append(float(latency))
        
        return sum(latencies) / len(latencies) if latencies else 0.0

