"""SPIKES coverage merge policy tests for baseline and hybrid evaluator paths."""

import pytest

from services.scoring_service import (
    _calculate_spikes_completion_from_coverage,
    _compute_spikes_coverage_merge,
)


def test_merge_policy_canonical_order_alias_normalization_and_deduping() -> None:
    rule_cov = {"covered": ["S", "k", "E", "setting"], "percent": 0.0}
    meta = {
        "status": "completed",
        "llm_output": {
            "spikes_annotations": [
                {"stage": "perception", "confidence": 0.9},
                {"stage": "P", "confidence": 0.9},
                {"stage": "summary", "confidence": 0.9},
            ]
        },
    }
    merged = _compute_spikes_coverage_merge(rule_cov, meta)
    assert merged["covered"] == ["setting", "perception", "knowledge", "emotion", "strategy"]


def test_merge_policy_normalizes_empathy_alias_to_emotion() -> None:
    rule_cov = {"covered": ["empathy"], "percent": 0.0}
    merged = _compute_spikes_coverage_merge(rule_cov, None)
    assert merged["covered"] == ["emotion"]


def test_merge_policy_confidence_threshold_and_missing_confidence_behavior() -> None:
    rule_cov = {"covered": ["setting"], "percent": 1 / 6}
    meta = {
        "status": "completed",
        "llm_output": {
            "spikes_annotations": [
                {"stage": "invitation", "confidence": 0.59},
                {"stage": "knowledge", "confidence": 0.6},
                {"stage": "emotion", "confidence": None},
            ]
        },
    }
    merged = _compute_spikes_coverage_merge(rule_cov, meta)
    assert merged["covered"] == ["setting", "knowledge", "emotion"]


def test_merge_policy_fallback_when_gating_fails() -> None:
    rule_cov = {"covered": ["setting", "perception"], "percent": 2 / 6}
    # missing evaluator_meta
    merged = _compute_spikes_coverage_merge(rule_cov, None)
    assert merged["covered"] == ["setting", "perception"]

    # non-completed status
    merged2 = _compute_spikes_coverage_merge(
        rule_cov, {"status": "failed", "llm_output": {"spikes_annotations": [{"stage": "knowledge"}]}}
    )
    assert merged2["covered"] == ["setting", "perception"]

    # missing llm_output
    merged3 = _compute_spikes_coverage_merge(
        rule_cov, {"status": "completed"}
    )
    assert merged3["covered"] == ["setting", "perception"]

    # empty spikes_annotations
    merged4 = _compute_spikes_coverage_merge(
        rule_cov, {"status": "completed", "llm_output": {"spikes_annotations": []}}
    )
    assert merged4["covered"] == ["setting", "perception"]


def test_hybrid_persists_only_stage_turn_mapping_four_distinct_stages() -> None:
    """Hybrid: persisted coverage is mapping only — rule `E` and annotations do not add stages."""
    rule_cov = {"covered": ["E"], "percent": 1 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [{"stage": "setting", "confidence": 0.9}],
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 3, "stage": "perception"},
                {"turn_number": 5, "stage": "knowledge"},
                {"turn_number": 7, "stage": "summary"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5, 6, 7}),
    )
    assert merged["covered"] == ["setting", "perception", "knowledge", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((4 / 6) * 100.0, 2))


def test_hybrid_excludes_llm_inference_when_only_four_turn_attributed() -> None:
    """LLM annotations imply 6/6; only mapping ∪ per-turn rule stages yield 4 — no extra inference."""
    rule_cov = {"covered": ["S", "P", "K", "S2"], "percent": 4 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [
                {"stage": "setting", "confidence": 0.9},
                {"stage": "perception", "confidence": 0.9},
                {"stage": "invitation", "confidence": 0.9},
                {"stage": "knowledge", "confidence": 0.9},
                {"stage": "emotion", "confidence": 0.9},
                {"stage": "strategy", "confidence": 0.9},
            ],
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 3, "stage": "perception"},
                {"turn_number": 5, "stage": "knowledge"},
                {"turn_number": 7, "stage": "summary"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5, 6, 7}),
    )
    assert merged["covered"] == ["setting", "perception", "knowledge", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((4 / 6) * 100.0, 2))


def test_hybrid_empty_mapping_ignores_rule_and_annotations() -> None:
    """Hybrid with no mapping rows: persisted coverage is empty even if rule/annotations have stages."""
    rule_cov = {"covered": ["E", "S2"], "percent": 0.0}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [{"stage": "setting", "confidence": 0.9}],
            "stage_turn_mapping": [],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3}),
    )
    assert merged["covered"] == []
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(0.0)


def test_hybrid_ignores_llm_mapping_rows_for_nonexistent_turn_numbers() -> None:
    """LLM mapping must reference a real session turn_number to count toward hybrid coverage."""
    rule_cov = {"covered": [], "percent": 0.0}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [{"stage": "setting", "confidence": 0.9}],
            "stage_turn_mapping": [
                {"turn_number": 999, "stage": "emotion"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5}),
    )
    assert merged["covered"] == []
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(0.0)


def test_hybrid_v2_persists_only_stage_turn_mapping_four_stages() -> None:
    """Hybrid v2: same mapping-only persistence as v1."""
    rule_cov = {"covered": ["E"], "percent": 1 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_v2_evaluator:ApexHybridV2Evaluator",
        },
        "llm_output": {
            "spikes_annotations": [{"stage": "setting", "confidence": 0.9}],
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 3, "stage": "perception"},
                {"turn_number": 5, "stage": "knowledge"},
                {"turn_number": 7, "stage": "summary"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5, 6, 7}),
    )
    assert merged["covered"] == ["setting", "perception", "knowledge", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((4 / 6) * 100.0, 2))


def test_hybrid_v2_keeps_full_coverage_when_all_stages_are_mapped() -> None:
    rule_cov = {"covered": ["setting"], "percent": 1 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_v2_evaluator:ApexHybridV2Evaluator",
        },
        "llm_output": {
            "spikes_annotations": [{"stage": "setting", "confidence": 0.9}],
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 2, "stage": "perception"},
                {"turn_number": 3, "stage": "invitation"},
                {"turn_number": 4, "stage": "knowledge"},
                {"turn_number": 5, "stage": "emotion"},
                {"turn_number": 6, "stage": "strategy"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5, 6}),
    )
    assert merged["covered"] == ["setting", "perception", "invitation", "knowledge", "emotion", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(100.0)


def test_hybrid_annotations_six_of_six_do_not_override_mapping_four() -> None:
    """Annotations list all six stages; persisted hybrid SPIKES still follows mapping only (4/6)."""
    rule_cov = {"covered": ["S", "P", "I", "K", "E", "S2"], "percent": 1.0}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [
                {"stage": "setting", "confidence": 0.9},
                {"stage": "perception", "confidence": 0.9},
                {"stage": "invitation", "confidence": 0.9},
                {"stage": "knowledge", "confidence": 0.9},
                {"stage": "emotion", "confidence": 0.9},
                {"stage": "strategy", "confidence": 0.9},
            ],
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 3, "stage": "perception"},
                {"turn_number": 5, "stage": "knowledge"},
                {"turn_number": 7, "stage": "summary"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3, 4, 5, 6, 7}),
    )
    assert merged["covered"] == ["setting", "perception", "knowledge", "strategy"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((4 / 6) * 100.0, 2))


def test_hybrid_rule_coverage_extra_stages_not_persisted() -> None:
    """Rule path lists extra stages; hybrid DB row still only reflects mapping."""
    rule_cov = {"covered": ["invitation", "emotion"], "percent": 2 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator",
        },
        "llm_output": {
            "stage_turn_mapping": [
                {"turn_number": 1, "stage": "setting"},
                {"turn_number": 2, "stage": "perception"},
            ],
        },
    }
    merged = _compute_spikes_coverage_merge(
        rule_cov,
        meta,
        valid_session_turn_numbers=frozenset({1, 2, 3}),
    )
    assert merged["covered"] == ["setting", "perception"]
    assert _calculate_spikes_completion_from_coverage(merged) == pytest.approx(round((2 / 6) * 100.0, 2))


def test_baseline_merge_behavior_unchanged_without_hybrid_evaluator_context() -> None:
    rule_cov = {"covered": ["setting"], "percent": 1 / 6}
    meta = {
        "status": "completed",
        "session_plugins": {
            "evaluator_plugin": "plugins.evaluators.apex_baseline_evaluator:ApexBaselineEvaluator",
        },
        "llm_output": {
            "spikes_annotations": [
                {"stage": "knowledge", "confidence": 0.95},
            ],
            "stage_turn_mapping": [],
        },
    }
    merged = _compute_spikes_coverage_merge(rule_cov, meta)
    assert merged["covered"] == ["setting", "knowledge"]
