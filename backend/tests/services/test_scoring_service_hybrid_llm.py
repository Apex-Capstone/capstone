"""Hybrid merge: 70/30 component blend and overall from merged components."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schemas.llm_reviewer import (
    HybridV2CompiledLLMReview,
    LLMMissedOpportunityItem,
    LLMReviewerOutput,
    LLMSpikesAnnotationItem,
)
from services.scoring_service import (
    ScoringService,
    _calculate_spikes_completion_from_coverage,
    _compact_llm_output_for_evaluator_meta,
    _compute_spikes_coverage_merge,
    _ensure_stage_turn_mapping,
)
from tests.utils.transcript_runner import create_all_for_test_engine


@pytest.fixture
def scoring_service() -> ScoringService:
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    testing_session_local = sessionmaker(bind=engine)
    db = testing_session_local()
    try:
        yield ScoringService(db)
    finally:
        db.close()


def test_merge_rule_and_llm_component_scores(scoring_service: ScoringService) -> None:
    e, c, s, o = scoring_service._merge_rule_and_llm_component_scores(
        70.0,
        80.0,
        90.0,
        50.0,
        50.0,
        50.0,
    )
    assert e == pytest.approx(0.7 * 70.0 + 0.3 * 50.0)
    assert c == pytest.approx(0.7 * 80.0 + 0.3 * 50.0)
    assert s == pytest.approx(0.7 * 90.0 + 0.3 * 50.0)
    # Displayed overall is always recomputed from merged components (not blended from LLM overall_score).
    assert o == pytest.approx(0.5 * e + 0.2 * c + 0.3 * s)


def test_compact_llm_output_for_evaluator_meta_caps_list_length() -> None:
    mos = [
        LLMMissedOpportunityItem(
            turn_number=i,
            patient_emotional_cue="cue",
            why_missed_or_weak="why",
        )
        for i in range(1, 50)
    ]
    out = LLMReviewerOutput(
        empathy_score=50.0,
        communication_score=50.0,
        spikes_completion_score=50.0,
        overall_score=50.0,
        missed_opportunities=mos,
        spikes_annotations=[],
        strengths=["ok"],
        areas_for_improvement=["ok"],
    )
    d = _compact_llm_output_for_evaluator_meta(out)
    assert len(d["missed_opportunities"]) == 40
    assert d.get("_meta_truncated") is True


def test_ensure_stage_turn_mapping_keeps_valid_nonempty_as_is() -> None:
    d = {
        "spikes_annotations": [{"turn_number": 9, "stage": "knowledge", "evidence_snippet": "x", "confidence": 0.9}],
        "stage_turn_mapping": [{"turn_number": 1, "stage": "setting"}],
    }
    out = _ensure_stage_turn_mapping(d)
    assert out["stage_turn_mapping"] == [{"turn_number": 1, "stage": "setting"}]


def test_ensure_stage_turn_mapping_rebuilds_when_duplicate_turn_numbers() -> None:
    d = {
        "spikes_annotations": [
            {"turn_number": 1, "stage": "setting", "evidence_snippet": "a", "confidence": 0.9},
        ],
        "stage_turn_mapping": [
            {"turn_number": 1, "stage": "setting"},
            {"turn_number": 1, "stage": "knowledge"},
        ],
    }
    out = _ensure_stage_turn_mapping(d)
    assert out["stage_turn_mapping"] == [{"turn_number": 1, "stage": "setting"}]


def test_ensure_stage_turn_mapping_rebuilds_when_stage_invalid() -> None:
    d = {
        "spikes_annotations": [
            {"turn_number": 2, "stage": "perception", "evidence_snippet": "x", "confidence": 0.8},
        ],
        "stage_turn_mapping": [{"turn_number": 1, "stage": "not_a_real_stage"}],
    }
    out = _ensure_stage_turn_mapping(d)
    assert out["stage_turn_mapping"] == [{"turn_number": 2, "stage": "perception"}]


def test_ensure_stage_turn_mapping_rebuilds_when_turn_number_not_int() -> None:
    d = {
        "spikes_annotations": [
            {"turn_number": 1, "stage": "emotion", "evidence_snippet": "x"},
        ],
        "stage_turn_mapping": [{"turn_number": 1.0, "stage": "emotion"}],
    }
    out = _ensure_stage_turn_mapping(d)
    assert out["stage_turn_mapping"] == [{"turn_number": 1, "stage": "emotion"}]


def test_ensure_stage_turn_mapping_derives_from_annotations_confidence_then_first() -> None:
    d = {
        "spikes_annotations": [
            {"turn_number": 1, "stage": "P", "evidence_snippet": "a", "confidence": 0.5},
            {"turn_number": 1, "stage": "knowledge", "evidence_snippet": "b", "confidence": 0.9},
            {"turn_number": 2, "stage": "S2", "evidence_snippet": "c"},
        ]
    }
    out = _ensure_stage_turn_mapping(d)
    assert out["stage_turn_mapping"] == [
        {"turn_number": 1, "stage": "knowledge"},
        {"turn_number": 2, "stage": "strategy"},
    ]
    turn_numbers = [r["turn_number"] for r in out["stage_turn_mapping"]]
    assert len(turn_numbers) == len(set(turn_numbers))


def test_ensure_stage_turn_mapping_empty_annotations() -> None:
    out = _ensure_stage_turn_mapping({"spikes_annotations": []})
    assert out["stage_turn_mapping"] == []


def test_compact_then_ensure_v1_has_stage_turn_mapping() -> None:
    lo = LLMReviewerOutput(
        empathy_score=50.0,
        communication_score=50.0,
        spikes_completion_score=50.0,
        overall_score=50.0,
        missed_opportunities=[],
        spikes_annotations=[
            LLMSpikesAnnotationItem(
                turn_number=1, stage="setting", evidence_snippet="hi", confidence=0.8
            ),
            LLMSpikesAnnotationItem(
                turn_number=3, stage="emotion", evidence_snippet="ok", confidence=None
            ),
        ],
        strengths=[],
        areas_for_improvement=[],
    )
    compacted = _compact_llm_output_for_evaluator_meta(lo)
    normalized = _ensure_stage_turn_mapping(compacted)
    assert "stage_turn_mapping" in normalized
    assert normalized["stage_turn_mapping"] == [
        {"turn_number": 1, "stage": "setting"},
        {"turn_number": 3, "stage": "emotion"},
    ]


def test_compact_hybrid_v2_compiled_includes_v2_fields() -> None:
    compiled = HybridV2CompiledLLMReview(
        empathy_score=1.0,
        communication_score=2.0,
        spikes_completion_score=3.0,
        overall_score=2.2,
        empathic_opportunities=["a"],
        stage_turn_mapping=[{"turn_number": 1, "stage": "setting"}],
        llm_score_source={"empathy": "llm", "communication": "llm", "spikes": "llm"},
    )
    d = _compact_llm_output_for_evaluator_meta(compiled)
    assert d["reviewer_version"] == "v2"
    assert d["empathic_opportunities"] == ["a"]
    assert d["stage_turn_mapping"] == [{"turn_number": 1, "stage": "setting"}]


def test_spikes_coverage_merge_union_and_confidence_gate() -> None:
    rule_cov = {"covered": ["setting", "strategy"], "percent": 2 / 6}
    evaluator_meta = {
        "status": "completed",
        "llm_output": {
            "spikes_annotations": [
                {"stage": "perception", "confidence": 0.95},
                {"stage": "invitation", "confidence": 0.3},
                {"stage": "knowledge"},  # missing confidence should be allowed
            ]
        },
    }
    merged = _compute_spikes_coverage_merge(rule_cov, evaluator_meta)
    assert merged["covered"] == ["setting", "perception", "knowledge", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((4 / 6) * 100.0, 2))


def test_spikes_coverage_merge_gating_fallbacks_to_rule_only() -> None:
    rule_cov = {"covered": ["setting"], "percent": 1 / 6}
    for meta in (
        None,
        {"status": "failed", "llm_output": {"spikes_annotations": [{"stage": "knowledge"}]}},
        {"status": "completed"},
        {"status": "completed", "llm_output": {}},
        {"status": "completed", "llm_output": {"spikes_annotations": []}},
    ):
        merged = _compute_spikes_coverage_merge(rule_cov, meta)
        assert merged["covered"] == ["setting"]
