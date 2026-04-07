"""Seeded evaluator validation: difficult diagnosis transcripts × baseline / hybrid v1 / v2.

These tests exercise the **real** evaluator stack, including **live OpenAI API calls** for hybrid
evaluators (v1 transcript reviewer + v2 three-call orchestrator). No LLM mocking.

**Before running:** configure API credentials and model settings the app uses for OpenAI
(typically ``OPENAI_API_KEY`` and ``OPENAI_MODEL_ID`` in ``.env`` or the environment). The
backend ``Settings`` loader must resolve ``database_url``, ``supabase_jwt_secret``, ``openai_api_key``,
``gemini_api_key``, and other required fields—same as running the API locally.

Runs are **slower** than mocked tests and **nondeterministic**: assertions are intentionally soft
(structure and presence checks); rich ``print`` output is the primary inspection surface.

Run with live console output::

    cd backend && poetry run pytest -s tests/services/test_seeded_evaluator_validation.py
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from domain.entities.case import Case
from domain.entities.user import User
from domain.models.sessions import FeedbackResponse
from plugins.evaluators.apex_baseline_evaluator import ApexBaselineEvaluator
from plugins.evaluators.apex_hybrid_evaluator import ApexHybridEvaluator
from plugins.evaluators.apex_hybrid_v2_evaluator import ApexHybridV2Evaluator
from tests.fixtures.generated_validation_cases import (
    ALL_DIFFICULT_DIAGNOSIS_FIXTURES,
    TEST_DIFFICULT_DIAGNOSIS_DECENT,
    TEST_DIFFICULT_DIAGNOSIS_MIXED,
    TEST_DIFFICULT_DIAGNOSIS_STRONG,
    TEST_DIFFICULT_DIAGNOSIS_WEAK,
)
from tests.utils.transcript_runner import (
    create_all_for_test_engine,
    run_fixture_seeded_transcript_through_scoring,
)

BASELINE = ApexBaselineEvaluator.name
HYBRID_V1 = ApexHybridEvaluator.name
HYBRID_V2 = ApexHybridV2Evaluator.name


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    create_all_for_test_engine(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    user = User(
        email="difficult_diagnosis_validation@example.com",
        role="trainee",
        full_name="Difficult Diagnosis Validation",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_case(test_db):
    """Patient case: Delivering a Difficult Diagnosis."""
    case = Case(
        title="Delivering a Difficult Diagnosis",
        description=(
            "A 52-year-old patient discusses recent test results. Findings are concerning "
            "for a likely cancer diagnosis pending confirmation. The patient is anxious and uncertain."
        ),
        script=(
            "Trainee practices delivering difficult news with empathy and SPIKES structure "
            "in an outpatient setting."
        ),
        difficulty_level="advanced",
        category="oncology",
        patient_background=(
            "52-year-old with recent abnormal imaging/labs; awaiting confirmation. "
            "Patient is anxious about the possibility of cancer."
        ),
        expected_spikes_flow=None,
    )
    test_db.add(case)
    test_db.commit()
    test_db.refresh(case)
    return case


def _feedback_snapshot(fb: FeedbackResponse) -> dict[str, Any]:
    meta = fb.evaluator_meta if isinstance(fb.evaluator_meta, dict) else {}
    llm_out = meta.get("llm_output") if isinstance(meta.get("llm_output"), dict) else {}
    mo = llm_out.get("missed_opportunities")
    return {
        "empathy_score": fb.empathy_score,
        "communication_score": fb.communication_score,
        "spikes_completion_score": fb.spikes_completion_score,
        "overall_score": fb.overall_score,
        "evaluator_phase": meta.get("phase"),
        "evaluator_status": meta.get("status"),
        "rule_scores": meta.get("rule_scores"),
        "llm_scores": meta.get("llm_scores"),
        "merged_scores": meta.get("merged_scores"),
        "llm_output_present": bool(llm_out),
        "missed_opportunities": mo,
        "stage_turn_mapping": llm_out.get("stage_turn_mapping"),
        "spikes_annotations": llm_out.get("spikes_annotations"),
        "spikes_sequencing_notes": llm_out.get("spikes_sequencing_notes"),
        "prompt_status": meta.get("prompt_status"),
        "llm_adapter_calls": meta.get("llm_adapter_calls"),
    }


def _assert_core_scores(fb: FeedbackResponse, ctx: str) -> None:
    assert fb.empathy_score is not None, ctx
    assert fb.communication_score is not None, ctx
    assert fb.spikes_completion_score is not None, ctx
    assert fb.overall_score is not None, ctx
    for name, val in (
        ("empathy", fb.empathy_score),
        ("communication", fb.communication_score),
        ("spikes", fb.spikes_completion_score),
        ("overall", fb.overall_score),
    ):
        assert 0.0 <= float(val) <= 100.0, f"{ctx} {name}={val} out of range"


def _warn_v1_suspicious_scores(meta: dict[str, Any]) -> None:
    ls = meta.get("llm_scores")
    if not isinstance(ls, dict):
        return
    nums = [ls.get(k) for k in ("empathy_score", "communication_score", "spikes_completion_score")]
    if all(isinstance(x, (int, float)) and float(x) == 50.0 for x in nums):
        print(
            "    WARNING: v1 llm_scores are all 50.0 — may indicate fallback-like behavior; "
            "inspect rule_scores and evaluator_meta.error if status is failed."
        )


def _warn_v2_adapter_calls(meta: dict[str, Any]) -> None:
    n = meta.get("llm_adapter_calls")
    st = meta.get("status")
    if st == "completed" and (n is None or n == 0):
        print(
            "    WARNING: v2 completed but llm_adapter_calls is missing or zero — "
            "unexpected for a successful three-call orchestration."
        )


def _print_hybrid_failure(meta: dict[str, Any]) -> None:
    if meta.get("status") == "failed":
        err = meta.get("error")
        print(f"    WARNING hybrid status=failed: error={err!r}")


def _print_real_llm_hybrid_block(label: str, tier: str, meta: dict[str, Any]) -> None:
    """Rich print for v1 or v2 (REAL LLM paths)."""
    print(f"  --- {label} {tier} (real LLM) ---")
    print(f"    phase: {meta.get('phase')!r}")
    print(f"    status: {meta.get('status')!r}")
    _print_hybrid_failure(meta)
    if meta.get("llm_scores") is not None:
        print(f"    llm_scores: {meta.get('llm_scores')}")
    if meta.get("merged_scores") is not None:
        print(f"    merged_scores: {meta.get('merged_scores')}")
    if meta.get("prompt_status") is not None:
        print(f"    prompt_status: {meta.get('prompt_status')}")
    if meta.get("llm_adapter_calls") is not None:
        print(f"    llm_adapter_calls: {meta.get('llm_adapter_calls')}")
    lo = meta.get("llm_output")
    if isinstance(lo, dict):
        mo = lo.get("missed_opportunities")
        if mo is not None:
            print(f"    missed_opportunities count: {len(mo) if isinstance(mo, list) else 'n/a'}")
        if lo.get("stage_turn_mapping"):
            print(f"    stage_turn_mapping: {lo.get('stage_turn_mapping')}")
        if lo.get("spikes_annotations"):
            ann = lo.get("spikes_annotations") or []
            print(f"    spikes_annotations count: {len(ann)}")


@pytest.mark.asyncio
async def test_seeded_difficult_diagnosis_print_and_structure(
    test_db, test_user, test_case,
) -> None:
    """Run all variants × evaluators; print snapshots; assert structural sanity only."""
    print("\n" + "=" * 72)
    print("REAL LLM MODE: ENABLED (no mocks — hybrid evaluators call OpenAI via OpenAIAdapter)")
    print("=" * 72 + "\n")

    for fx in ALL_DIFFICULT_DIAGNOSIS_FIXTURES:
        label = fx.get("label", fx.get("name"))
        print("\n" + "=" * 72)
        print(f"FIXTURE: {label}")
        print("=" * 72)

        baseline_result = await run_fixture_seeded_transcript_through_scoring(
            test_db, test_user, test_case, fx, evaluator_plugin=BASELINE
        )
        v1_result = await run_fixture_seeded_transcript_through_scoring(
            test_db, test_user, test_case, fx, evaluator_plugin=HYBRID_V1
        )
        v2_result = await run_fixture_seeded_transcript_through_scoring(
            test_db, test_user, test_case, fx, evaluator_plugin=HYBRID_V2
        )

        fb_b = baseline_result["feedback"]
        fb_1 = v1_result["feedback"]
        fb_2 = v2_result["feedback"]

        for name, fb in (("baseline", fb_b), ("hybrid_v1", fb_1), ("hybrid_v2", fb_2)):
            assert isinstance(fb, FeedbackResponse), name
            _assert_core_scores(fb, f"{label}/{name}")

        sb, s1, s2 = _feedback_snapshot(fb_b), _feedback_snapshot(fb_1), _feedback_snapshot(fb_2)

        print("  BASELINE (rule-only, final scores)")
        print(
            f"    scores: emp={sb['empathy_score']:.2f} comm={sb['communication_score']:.2f} "
            f"spikes={sb['spikes_completion_score']:.2f} overall={sb['overall_score']:.2f}"
        )
        print(f"    meta phase={sb['evaluator_phase']!r} status={sb['evaluator_status']!r}")

        meta1 = fb_1.evaluator_meta if isinstance(fb_1.evaluator_meta, dict) else {}
        meta2 = fb_2.evaluator_meta if isinstance(fb_2.evaluator_meta, dict) else {}

        _print_real_llm_hybrid_block(label, "HYBRID V1", meta1)
        _warn_v1_suspicious_scores(meta1)

        _print_real_llm_hybrid_block(label, "HYBRID V2", meta2)
        _warn_v2_adapter_calls(meta2)

        # Baseline meta
        assert sb["evaluator_phase"] == "baseline_rule_v1", label
        assert sb["evaluator_status"] is None

        assert isinstance(meta1, dict) and meta1.get("phase") == "hybrid_llm_v1", label
        assert isinstance(meta2, dict) and meta2.get("phase") == "hybrid_llm_v2", label

        st1, st2 = meta1.get("status"), meta2.get("status")
        assert st1 in ("completed", "failed"), f"{label} v1 status={st1!r}"
        assert st2 in ("completed", "failed"), f"{label} v2 status={st2!r}"

        if meta1.get("llm_output") is not None:
            assert isinstance(meta1["llm_output"], dict), label
        if meta2.get("llm_output") is not None:
            assert isinstance(meta2["llm_output"], dict), label

        # Informational: mixed / strong missed-opportunity notes (do not assert counts)
        lo2 = meta2.get("llm_output") if isinstance(meta2.get("llm_output"), dict) else {}
        if fx is TEST_DIFFICULT_DIAGNOSIS_MIXED:
            mo_mix = lo2.get("missed_opportunities")
            print(f"  [MIXED v2] missed_opportunities (informational): {mo_mix!r}")

        if fx is TEST_DIFFICULT_DIAGNOSIS_STRONG:
            mo_s = lo2.get("missed_opportunities")
            print(f"  [STRONG v2] missed_opportunities (informational): {mo_s!r}")

        if fx is TEST_DIFFICULT_DIAGNOSIS_DECENT:
            print("  [DECENT v2] SPIKES inspection (informational):")
            print(f"    stage_turn_mapping: {lo2.get('stage_turn_mapping')}")
            print(f"    spikes_annotations: {lo2.get('spikes_annotations')}")
            print(f"    spikes_sequencing_notes: {lo2.get('spikes_sequencing_notes')}")


@pytest.mark.asyncio
async def test_seeded_difficult_diagnosis_directional_ordering(test_db, test_user, test_case) -> None:
    """Print score ordering observations (non-failing; real LLM outputs are not guaranteed to rank)."""

    async def _collect(plugin: str) -> dict[str, FeedbackResponse]:
        out: dict[str, FeedbackResponse] = {}
        for fx in ALL_DIFFICULT_DIAGNOSIS_FIXTURES:
            label = fx["label"]
            res = await run_fixture_seeded_transcript_through_scoring(
                test_db, test_user, test_case, fx, evaluator_plugin=plugin
            )
            out[label] = res["feedback"]
        return out

    print("\n" + "=" * 72)
    print("DIRECTIONAL OBSERVATIONS (informational only — not asserted)")
    print("REAL LLM MODE: ENABLED")
    print("=" * 72)

    for plugin_name, plugin_key in (
        ("baseline", BASELINE),
        ("hybrid_v1", HYBRID_V1),
        ("hybrid_v2", HYBRID_V2),
    ):
        scores = await _collect(plugin_key)
        strong = scores[TEST_DIFFICULT_DIAGNOSIS_STRONG["label"]]
        weak = scores[TEST_DIFFICULT_DIAGNOSIS_WEAK["label"]]
        decent = scores[TEST_DIFFICULT_DIAGNOSIS_DECENT["label"]]
        mixed = scores[TEST_DIFFICULT_DIAGNOSIS_MIXED["label"]]

        print(f"\n  [{plugin_name}] overall scores: "
              f"strong={strong.overall_score:.2f} decent={decent.overall_score:.2f} "
              f"mixed={mixed.overall_score:.2f} weak={weak.overall_score:.2f}")
        print(
            f"  [{plugin_name}] empathy: "
            f"strong={strong.empathy_score:.2f} decent={decent.empathy_score:.2f} "
            f"mixed={mixed.empathy_score:.2f} weak={weak.empathy_score:.2f}"
        )
        print(
            f"  [{plugin_name}] spikes_completion: "
            f"strong={strong.spikes_completion_score:.2f} decent={decent.spikes_completion_score:.2f} "
            f"mixed={mixed.spikes_completion_score:.2f} weak={weak.spikes_completion_score:.2f}"
        )


@pytest.mark.asyncio
async def test_evaluator_meta_presence_and_score_sources(test_db, test_user, test_case) -> None:
    """Structural checks on evaluator_meta; hybrid branches tolerate failed LLM steps."""
    for fx in ALL_DIFFICULT_DIAGNOSIS_FIXTURES:
        label = fx["label"]
        for plugin_key, phase_expected, is_hybrid in (
            (BASELINE, "baseline_rule_v1", False),
            (HYBRID_V1, "hybrid_llm_v1", True),
            (HYBRID_V2, "hybrid_llm_v2", True),
        ):
            res = await run_fixture_seeded_transcript_through_scoring(
                test_db, test_user, test_case, fx, evaluator_plugin=plugin_key
            )
            fb = res["feedback"]
            meta = fb.evaluator_meta
            assert meta is not None, f"{label} {plugin_key}"
            assert isinstance(meta, dict), f"{label} {plugin_key}"
            assert meta.get("phase") == phase_expected, f"{label} {plugin_key}"

            if not is_hybrid:
                continue

            status = meta.get("status")
            assert status in ("completed", "failed"), f"{label} {plugin_key} {status}"

            lo = meta.get("llm_output")
            if lo is not None:
                assert isinstance(lo, dict), f"{label} {plugin_key}"

            if phase_expected == "hybrid_llm_v1" and status == "completed":
                assert meta.get("rule_scores") is not None
                assert isinstance(meta["rule_scores"], dict)
                assert meta.get("merged_scores") is not None
                assert isinstance(meta["merged_scores"], dict)

            if phase_expected == "hybrid_llm_v2":
                assert "prompt_status" in meta
                assert isinstance(meta["prompt_status"], dict)
                if status == "completed":
                    assert meta.get("merged_scores") is not None
                    assert isinstance(meta["merged_scores"], dict)
