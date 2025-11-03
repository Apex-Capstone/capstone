"""Tests for dialogue functionality."""

import pytest

from adapters.nlu.simple_rule_nlu import SimpleRuleNLU


@pytest.mark.asyncio
async def test_classify_open_question():
    """Test classifying open-ended questions."""
    nlu = SimpleRuleNLU()
    
    result = await nlu.classify_question_type("How are you feeling today?")
    assert result == "open"
    
    result = await nlu.classify_question_type("What concerns do you have?")
    assert result == "open"


@pytest.mark.asyncio
async def test_classify_closed_question():
    """Test classifying closed questions."""
    nlu = SimpleRuleNLU()
    
    result = await nlu.classify_question_type("Are you in pain?")
    assert result == "closed"
    
    result = await nlu.classify_question_type("Do you have any questions?")
    assert result == "closed"


@pytest.mark.asyncio
async def test_detect_empathy_cues():
    """Test detecting empathy in text."""
    nlu = SimpleRuleNLU()
    
    # High empathy
    result = await nlu.detect_empathy_cues(
        "I understand this must be very difficult for you. I'm here to support you."
    )
    assert result["has_empathy"] is True
    assert result["empathy_score"] > 5
    
    # Low empathy
    result = await nlu.detect_empathy_cues("The test results are negative.")
    assert result["empathy_score"] < 5


@pytest.mark.asyncio
async def test_analyze_intent():
    """Test intent analysis."""
    nlu = SimpleRuleNLU()
    
    result = await nlu.analyze_intent("I understand how you feel. Do you have any concerns?")
    assert result["is_question"] is True
    assert result["has_empathy_keywords"] is True

