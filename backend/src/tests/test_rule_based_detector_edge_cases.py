"""Edge-case tests for the rule-based NLU detectors (EO, responses, elicitations, SPIKES stages)."""

import pytest

from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from services.stage_tracker import StageTracker


@pytest.mark.asyncio
class TestEOEdgeCases:
    async def test_eo_positive_cases(self):
        nlu = SimpleRuleNLU()
        positives = [
            "My symptoms have been getting worse.",
            "It's been affecting my sleep.",
            "I barely sleep anymore.",
            "I feel alone in this.",
            "It scares me a lot.",
            "My dad had heart problems.",
            "I feel overwhelmed.",
            "I'm afraid something serious is happening.",
        ]
        for text in positives:
            spans = await nlu.detect_eo_spans(text)
            assert len(spans) > 0, f"Expected EO span in: {text}"

    async def test_eo_negative_cases(self):
        nlu = SimpleRuleNLU()
        negatives = [
            "Any chest pain?",
            "Family history is common.",
            "That sounds difficult.",
            "Is there anything important you haven't shared yet?",
            "Let's talk about next steps.",
        ]
        for text in negatives:
            spans = await nlu.detect_eo_spans(text)
            assert len(spans) == 0, f"Did not expect EO span in: {text}"

    async def test_eo_long_phrase_preference(self):
        nlu = SimpleRuleNLU()
        text = "Sometimes, and it scares me a lot."
        spans = await nlu.detect_eo_spans(text)
        assert any("it scares me a lot" in s.get("text", "").lower() for s in spans)

        text2 = "My symptoms have been getting worse."
        spans2 = await nlu.detect_eo_spans(text2)
        assert any(
            phrase in s.get("text", "").lower()
            for s in spans2
            for phrase in [
                "my symptoms have been getting worse",
                "symptoms have been getting worse",
            ]
        )

        text3 = "I feel like something is really wrong."
        spans3 = await nlu.detect_eo_spans(text3)
        assert any("something is really wrong" in s.get("text", "").lower() for s in spans3)


@pytest.mark.asyncio
class TestResponseEdgeCases:
    async def test_response_positive_cases(self):
        nlu = SimpleRuleNLU()
        positives = [
            "Thank you for telling me that.",
            "Thank you for sharing that.",
            "I hear that.",
            "I hear you.",
            "That makes sense.",
            "It makes sense that you'd feel afraid.",
            "I'll support you through every step.",
            "We'll support you through this.",
            "We'll go through this together.",
        ]
        for text in positives:
            spans = await nlu.detect_response_spans(text)
            assert len(spans) > 0, f"Expected response span in: {text}"

    async def test_response_negative_cases(self):
        nlu = SimpleRuleNLU()
        negatives = [
            "Okay.",
            "Noted.",
            "Let's move on.",
            "We'll review the bloodwork.",
        ]
        for text in negatives:
            spans = await nlu.detect_response_spans(text)
            assert len(spans) == 0, f"Did not expect response span in: {text}"


@pytest.mark.asyncio
class TestElicitationEdgeCases:
    async def test_elicitation_positive_cases(self):
        nlu = SimpleRuleNLU()
        positives = [
            "Is there anything else you're hoping to understand today?",
            "Can you tell me if there's anything important you haven't shared yet?",
            "Can you tell me what symptoms have been getting worse?",
            "Do you have any other questions?",
            "Would you like me to explain more?",
            "Can you tell me what part feels the hardest?",
            "Can you tell me what has been getting worse?",
        ]
        for text in positives:
            spans = await nlu.detect_elicitation_spans(text)
            assert len(spans) > 0, f"Expected elicitation span in: {text}"

    async def test_elicitation_negative_cases(self):
        nlu = SimpleRuleNLU()
        negatives = [
            "I understand how frightening that can be.",
            "Here's our plan.",
            "We'll support you.",
        ]
        for text in negatives:
            spans = await nlu.detect_elicitation_spans(text)
            assert len(spans) == 0, f"Did not expect elicitation span in: {text}"


class TestStageTrackerEdgeCases:
    def setup_method(self):
        self.tracker = StageTracker()

    def test_setting_stage(self):
        assert self.tracker.detect_stage("Is this still a good time to talk?", None) == "setting"
        assert self.tracker.detect_stage("Would you prefer a quieter room?", None) == "setting"

    def test_perception_stage(self):
        assert self.tracker.detect_stage("Can you tell me what symptoms have been getting worse?", None) == "perception"
        assert self.tracker.detect_stage("What have you been thinking about this?", None) == "perception"

    def test_emotion_stage(self):
        assert self.tracker.detect_stage("I hear you.", None) == "emotion"
        assert self.tracker.detect_stage("That sounds difficult.", None) == "emotion"
        assert self.tracker.detect_stage("It makes sense that you'd feel afraid.", None) == "emotion"

    def test_knowledge_stage(self):
        assert self.tracker.detect_stage("Let me walk through what we know so far.", None) == "knowledge"
        assert self.tracker.detect_stage(
            "I'll explain what tests can help us understand what's going on.", None
        ) == "knowledge"

    def test_invitation_stage(self):
        assert self.tracker.detect_stage(
            "Is there anything else you're hoping to understand today?", None
        ) == "invitation"
        assert self.tracker.detect_stage("Do you have any other questions?", None) == "invitation"

    def test_strategy_stage(self):
        assert (
            self.tracker.detect_stage(
                "Here's our plan: we'll check your heart and review next steps together.", None
            )
            == "strategy"
        )
        assert self.tracker.detect_stage("I'll support you through every step.", None) == "strategy"

    def test_ambiguity_precedence(self):
        # Perception vs emotion: should stay perception
        assert self.tracker.detect_stage(
            "Can you tell me what symptoms have been getting worse?", None
        ) == "perception"

        # Invitation vs strategy: should be invitation
        assert self.tracker.detect_stage(
            "Can you tell me if there's anything important you haven't shared yet?", None
        ) == "invitation"

        # Strategy vs emotion: should be strategy
        assert self.tracker.detect_stage("I'll support you through every step.", None) == "strategy"

        # Emotion + invitation: invitation should win over emotion
        assert self.tracker.detect_stage(
            "Thank you for telling me that. Is there anything else you're hoping to understand today?",
            None,
        ) == "invitation"

        # Knowledge + strategy: strategy should win
        assert self.tracker.detect_stage(
            "Let me walk through what we know so far, and then we'll discuss next steps.", None
        ) == "strategy"

