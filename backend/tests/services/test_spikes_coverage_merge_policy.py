"""SPIKES coverage merge policy tests for phase 1 display canonicalization."""

from services.scoring_service import _compute_spikes_coverage_merge


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
