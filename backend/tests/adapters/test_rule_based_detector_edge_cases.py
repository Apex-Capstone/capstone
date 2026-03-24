"""Edge-case tests for the rule-based NLU detectors (EO, responses, elicitations, SPIKES stages)."""

import pytest

from adapters.nlu.span_detector import SpanDetector
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

    async def test_implicit_eo_weak_fragments_do_not_trigger(self):
        nlu = SimpleRuleNLU()
        weak_fragments = [
            "I guess.",
            "A bit.",
            "Thinking about.",
        ]
        for text in weak_fragments:
            spans = await nlu.detect_eo_spans(text)
            assert len(spans) == 0, f"Did not expect implicit EO span in: {text}"

    async def test_implicit_eo_contextual_phrases_still_detect(self):
        nlu = SimpleRuleNLU()
        contextual = [
            "I'm not sure what this means.",
            "I don't know what to do.",
        ]
        for text in contextual:
            spans = await nlu.detect_eo_spans(text)
            assert len(spans) > 0, f"Expected implicit EO span in: {text}"

    async def test_implicit_appreciation_broad_single_words_do_not_trigger(self):
        nlu = SimpleRuleNLU()
        broad_words = [
            "It matters.",
            "This is significant.",
            "That seems relevant.",
            "This counts.",
            "Worth it.",
        ]
        for text in broad_words:
            spans = await nlu.detect_eo_spans(text)
            assert len(spans) == 0, f"Did not expect implicit appreciation EO in: {text}"

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

    async def test_contextual_distress_eo_scary(self):
        nlu = SimpleRuleNLU()
        spans = await nlu.detect_eo_spans("That sounds really scary.")
        assert any(s.get("dimension") == "Feeling" for s in spans)

    async def test_contextual_distress_eo_long_wait(self):
        nlu = SimpleRuleNLU()
        spans = await nlu.detect_eo_spans("A week feels like such a long time to wait.")
        assert any(s.get("dimension") == "Feeling" for s in spans)

    async def test_contextual_distress_eo_hard_to_wait_sit(self):
        nlu = SimpleRuleNLU()
        spans = await nlu.detect_eo_spans("It's still so hard to just sit and wait.")
        assert any(s.get("dimension") == "Feeling" for s in spans)

    async def test_contextual_distress_eo_keep_worrying(self):
        nlu = SimpleRuleNLU()
        spans = await nlu.detect_eo_spans("I just keep worrying.")
        assert any(s.get("dimension") == "Feeling" for s in spans)

    async def test_contextual_distress_eo_feeling_of_dread(self):
        nlu = SimpleRuleNLU()
        spans = await nlu.detect_eo_spans("I can't shake this feeling of dread.")
        assert any(
            s.get("dimension") == "Feeling" and "dread" in s.get("text", "").lower() for s in spans
        )

    async def test_contextual_distress_eo_feeling_over_judgment_precedence(self):
        nlu = SimpleRuleNLU()
        text = "What if the news is bad? I can't shake this feeling of dread."
        spans = await nlu.detect_eo_spans(text)
        assert any(
            s.get("dimension") == "Feeling" and "dread" in s.get("text", "").lower() for s in spans
        )
        assert not (
            len(spans) == 1 and all(s.get("dimension") == "Judgment" for s in spans)
        )

    async def test_dread_sentence_prefers_phrase_over_bad_judgment(self):
        nlu = SimpleRuleNLU()
        text = "I can't shake this feeling of dread. What if the news is bad?"
        spans = await nlu.detect_eo_spans(text)
        feeling = [s for s in spans if s.get("dimension") == "Feeling"]
        assert feeling, "Expected a Feeling span for dread"
        assert any(
            "feeling of dread" in s.get("text", "").lower() or "dread" in s.get("text", "").lower()
            for s in feeling
        )
        assert not any(s.get("text", "").strip().lower() == "bad" for s in feeling)


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

    async def test_response_pattern_strong_empathy_detected(self):
        nlu = SimpleRuleNLU()
        text = "I can see how overwhelming this feels."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("i can see how overwhelming this feels" in s.get("text", "").lower() for s in spans)

    async def test_response_pattern_validation_detected(self):
        nlu = SimpleRuleNLU()
        text = "That must be really difficult."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("that must be really difficult" in s.get("text", "").lower() for s in spans)

    async def test_response_pattern_multiclause_captures_first_clause(self):
        nlu = SimpleRuleNLU()
        text = "I can see this is hard, and we will support you."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("i can see this is hard" == s.get("text", "").lower().strip() for s in spans)

    async def test_response_pattern_weak_generic_still_detected(self):
        nlu = SimpleRuleNLU()
        text = "I understand."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("i understand" in s.get("text", "").lower() for s in spans)

    async def test_response_pattern_non_empathic_plan_not_detected(self):
        nlu = SimpleRuleNLU()
        text = "We will begin treatment tomorrow."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) == 0

    async def test_response_keyword_understand_why_expands_full_clause(self):
        nlu = SimpleRuleNLU()
        text = "I understand why you're worried."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any(s.get("text", "").lower().strip() == "i understand why you're worried." for s in spans)

    async def test_response_keyword_understand_how_expands_across_comma_payload(self):
        nlu = SimpleRuleNLU()
        text = "I understand how overwhelming this feels, especially with so much uncertainty."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any(
            s.get("text", "").lower().strip()
            == "i understand how overwhelming this feels, especially with so much uncertainty."
            for s in spans
        )

    async def test_response_pattern_apology_with_burden_detected(self):
        nlu = SimpleRuleNLU()
        text = "I'm sorry this feels so overwhelming."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("i'm sorry this feels so overwhelming" in s.get("text", "").lower() for s in spans)

    async def test_response_pattern_i_know_with_difficulty_detected(self):
        nlu = SimpleRuleNLU()
        text = "I know that waiting can be difficult."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any(s.get("text", "").lower().strip() == "i know that waiting can be difficult." for s in spans)

    async def test_response_pattern_i_can_see_not_truncated(self):
        nlu = SimpleRuleNLU()
        text = "I can see how helpless this feels, and it's really hard to be in this kind of waiting period."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any(
            s.get("text", "").lower().strip().startswith("i can see how helpless this feels")
            and s.get("text", "").lower().strip() != "i can see how"
            for s in spans
        )

    async def test_response_pattern_can_be_hardship_detected(self):
        nlu = SimpleRuleNLU()
        text = "This can be overwhelming."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("this can be overwhelming" in s.get("text", "").lower() for s in spans)

    async def test_response_pattern_factual_plan_not_detected(self):
        nlu = SimpleRuleNLU()
        text = "We should repeat the test next week."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) == 0

    async def test_response_pattern_apology_multiclause_first_clause_only(self):
        nlu = SimpleRuleNLU()
        text = "I'm sorry this feels so overwhelming. Usually results take about a week."
        spans = await nlu.detect_response_spans(text)
        assert len(spans) > 0
        assert any("i'm sorry this feels so overwhelming." == s.get("text", "").lower().strip() for s in spans)


@pytest.mark.asyncio
class TestElicitationEdgeCases:
    async def test_elicitation_positive_cases(self):
        nlu = SimpleRuleNLU()
        positives = [
            "How are you feeling about all of this?",
            "What worries you most right now?",
            "What do you make of this?",
            "How do you see this situation?",
            "What matters most to you as we plan next steps?",
            "What does this mean for your day-to-day life?",
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
            "Can you tell me what?",
        ]
        for text in negatives:
            spans = await nlu.detect_elicitation_spans(text)
            assert len(spans) == 0, f"Did not expect elicitation span in: {text}"

    async def test_elicitation_dimension_mapping_examples(self):
        nlu = SimpleRuleNLU()

        feeling_spans = await nlu.detect_elicitation_spans("How has this been for you emotionally?")
        assert any(s.get("dimension") == "Feeling" for s in feeling_spans)

        judgment_spans = await nlu.detect_elicitation_spans("What do you make of this?")
        assert any(s.get("dimension") == "Judgment" for s in judgment_spans)

        appreciation_spans = await nlu.detect_elicitation_spans(
            "What does this mean for your day-to-day life?"
        )
        assert any(s.get("dimension") == "Appreciation" for s in appreciation_spans)


class TestSpanDetectorSpikesStage:
    def setup_method(self):
        self.detector = SpanDetector()

    def test_spikes_stage_naming_alignment(self):
        stage = self.detector.detect_spikes_stage(
            "From here, the next step is to focus on comfort and make a plan together."
        )
        assert stage in {
            "setting",
            "perception",
            "invitation",
            "knowledge",
            "emotion",
            "strategy_and_summary",
        }
        assert stage not in {"empathy", "summary"}

    def test_spikes_detection_examples(self):
        assert (
            self.detector.detect_spikes_stage("Thank you for coming in. Is this a good place for us to talk?")
            == "setting"
        )
        assert (
            self.detector.detect_spikes_stage("Can you tell me what you've been told so far?")
            == "perception"
        )
        assert (
            self.detector.detect_spikes_stage("Would you like me to go over the results in detail?")
            == "invitation"
        )
        assert (
            self.detector.detect_spikes_stage("The scan shows that the cancer has grown.")
            == "knowledge"
        )
        assert (
            self.detector.detect_spikes_stage("I'm sorry this feels so overwhelming.", has_responses=True)
            == "emotion"
        )
        assert (
            self.detector.detect_spikes_stage(
                "From here, the next step is to focus on comfort and make a plan together."
            )
            == "strategy_and_summary"
        )

    def test_spikes_mixed_function_dominance(self):
        # Primarily knowledge disclosure with brief empathy preface -> knowledge.
        assert (
            self.detector.detect_spikes_stage(
                "I'm sorry this is hard. The scan shows the illness has progressed.",
                has_responses=True,
            )
            == "knowledge"
        )

        # Primarily emotional validation with minor information -> emotion.
        assert (
            self.detector.detect_spikes_stage(
                "I'm sorry this feels overwhelming. We should talk soon.",
                has_responses=True,
            )
            == "emotion"
        )

        # Planning/summary with one empathy phrase -> strategy_and_summary.
        assert (
            self.detector.detect_spikes_stage(
                "I know this is hard, and from here our plan is to focus on comfort and next steps.",
                has_responses=True,
            )
            == "strategy_and_summary"
        )

        # Invitation intent should win over lightweight knowledge wording.
        assert (
            self.detector.detect_spikes_stage(
                "Would you like me to go over the results in detail now?"
            )
            == "invitation"
        )

    def test_spikes_mixed_turn_dominance_rebalance(self):
        """Knowledge / strategy win over emotion when disclosure or planning dominates the turn."""
        hr = True
        assert (
            self.detector.detect_spikes_stage(
                "I understand why you're worried. There are a few different things this could be, and we will need more tests.",
                has_responses=hr,
            )
            == "knowledge"
        )
        assert (
            self.detector.detect_spikes_stage(
                "The timing can depend on the specific tests, but usually results come back within a few days to about a week.",
                has_responses=hr,
            )
            == "knowledge"
        )
        assert (
            self.detector.detect_spikes_stage(
                "I can see how helpless this feels. For now, there isn't anything specific you need to do medically until we have the results.",
                has_responses=hr,
            )
            == "strategy_and_summary"
        )
        assert (
            self.detector.detect_spikes_stage(
                "If anything changes with their condition, it's important to let us know, but otherwise the focus is on waiting for more information.",
                has_responses=hr,
            )
            == "strategy_and_summary"
        )
        assert (
            self.detector.detect_spikes_stage(
                "I'm sorry this feels so overwhelming. I know the waiting is hard.",
                has_responses=hr,
            )
            == "emotion"
        )
        # Regression: early SPIKES stages unchanged.
        assert self.detector.detect_spikes_stage(
            "Thank you for coming in. Is this a good place for us to talk?"
        ) == "setting"
        assert self.detector.detect_spikes_stage(
            "Can you tell me what you've been told so far?"
        ) == "perception"
        assert self.detector.detect_spikes_stage(
            "Would you like me to go over the results in detail?"
        ) == "invitation"


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

