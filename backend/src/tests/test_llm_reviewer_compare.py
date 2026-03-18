from schemas.llm_reviewer import ReviewedEventAssessment
from services.llm_reviewer_compare import (
    compare_rule_and_llm_event,
    build_llm_reviewer_audit_summary,
)


def _llm_event(
    *,
    target_id: str = "t1",
    missed_opportunity: bool = True,
    acknowledged_emotion: bool = False,
    validated_feeling: bool = False,
) -> ReviewedEventAssessment:
    return ReviewedEventAssessment(
        target_id=target_id,
        acknowledged_emotion=acknowledged_emotion,
        validated_feeling=validated_feeling,
        missed_opportunity=missed_opportunity,
        empathy_quality_score_0_to_4=2,
        disposition="confirm",
        confidence=0.8,
        rationale="Test rationale",
        suggested_response="Test suggestion",
    )


def test_compare_rule_and_llm_event_agreement():
    rule_link = {
        "target_id": "t1",
        "rule_missed_opportunity": True,
        "rule_addressed": False,
    }
    llm_event = _llm_event(
        target_id="t1",
        missed_opportunity=True,
        acknowledged_emotion=False,
    )

    result = compare_rule_and_llm_event(rule_link=rule_link, llm_event=llm_event)

    assert result["target_id"] == "t1"
    assert result["rule_verdict"]["rule_missed_opportunity"] is True
    assert result["rule_verdict"]["rule_addressed"] is False

    assert result["llm_verdict"]["missed_opportunity"] is True
    assert result["llm_verdict"]["acknowledged_emotion"] is False

    agreement = result["agreement"]
    assert agreement["missed_opportunity_agree"] is True
    assert agreement["addressed_vs_acknowledged_agree"] is True
    assert agreement["overall_agree"] is True


def test_compare_rule_and_llm_event_disagreement():
    rule_link = {
        "target_id": "t2",
        "rule_missed_opportunity": True,
        "rule_addressed": False,
    }
    llm_event = _llm_event(
        target_id="t2",
        missed_opportunity=False,
        acknowledged_emotion=True,
    )

    result = compare_rule_and_llm_event(rule_link=rule_link, llm_event=llm_event)

    agreement = result["agreement"]
    assert agreement["missed_opportunity_agree"] is False
    assert agreement["addressed_vs_acknowledged_agree"] is False
    assert agreement["overall_agree"] is False


def test_build_llm_reviewer_audit_summary_counts_and_rate():
    events = []

    # Two agreements
    events.append(
        {
            "agreement": {
                "overall_agree": True,
            }
        }
    )
    events.append(
        {
            "agreement": {
                "overall_agree": True,
            }
        }
    )

    # One disagreement
    events.append(
        {
            "agreement": {
                "overall_agree": False,
            }
        }
    )

    summary = build_llm_reviewer_audit_summary(reviewed_events=events)

    assert summary["total_reviewed_events"] == 3
    assert summary["total_disagreements"] == 1
    assert summary["disagreement_rate"] == 0.333


def test_build_llm_reviewer_audit_summary_empty():
    summary = build_llm_reviewer_audit_summary(reviewed_events=[])
    assert summary["total_reviewed_events"] == 0
    assert summary["total_disagreements"] == 0
    assert summary["disagreement_rate"] == 0.0

