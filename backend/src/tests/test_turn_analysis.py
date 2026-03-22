"""Unit tests for turn-level analysis metric consistency."""

import pytest

from services.turn_analysis import analyze_user_input


class _StubPipeline:
    """Simple stub returning a provided analysis payload."""

    def __init__(self, analysis):
        self.analysis = analysis

    async def analyze(self, text: str):
        return self.analysis


@pytest.mark.asyncio
async def test_empathy_response_uses_response_spans_not_broad_cues():
    """Broad empathy cues alone should not mark an empathy response."""
    pipeline = _StubPipeline(
        {
            "empathy": {
                "empathy_score": 2.5,
                "found_keywords": ["sorry"],
                "has_empathy": True,
            },
            "question_type": "statement",
            "tone": {"calm": True, "clear": True},
            "response_spans": [],
            "elicitation_spans": [],
            "empathy_response_type": "other",
        }
    )

    metrics, spans = await analyze_user_input(pipeline, "I'm sorry this feels stressful.")

    assert metrics["empathy_response"] is False
    assert metrics["empathy_cue_detected"] is True
    assert metrics["empathy_cue_score"] == 2.5
    assert spans == []


@pytest.mark.asyncio
async def test_empathy_response_true_when_response_spans_detected():
    """Detected response spans should drive empathy_response=True."""
    pipeline = _StubPipeline(
        {
            "empathy": {
                "empathy_score": 0.0,
                "found_keywords": [],
                "has_empathy": False,
            },
            "question_type": "statement",
            "tone": {"calm": True, "clear": True},
            "response_spans": [
                {
                    "type": "understanding",
                    "start_char": 0,
                    "end_char": 6,
                    "text": "I hear",
                    "confidence": 0.8,
                    "provenance": "rule",
                }
            ],
            "elicitation_spans": [],
            "empathy_response_type": "understanding",
        }
    )

    metrics, spans = await analyze_user_input(pipeline, "I hear you.")

    assert metrics["empathy_response"] is True
    assert metrics["empathy_response_type"] == "understanding"
    assert len(spans) == 1
    assert spans[0]["span_type"] == "response"
