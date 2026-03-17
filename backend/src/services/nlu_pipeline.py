from typing import Any


class NLUPipeline:
    """Unified entry point for NLU analysis.

    This pipeline consolidates span detection, empathy detection,
    question classification, and tone analysis into a single
    `analyze(text)` call.
    """

    def __init__(
        self,
        span_detector,
        empathy_detector,
        question_classifier,
        tone_analyzer,
    ):
        self.span_detector = span_detector
        self.empathy_detector = empathy_detector
        self.question_classifier = question_classifier
        self.tone_analyzer = tone_analyzer

    async def analyze(self, text: str) -> dict[str, Any]:
        """Run all NLU analyses for the given text.

        Returns a structured analysis object that can be used by
        dialogue orchestration and feedback components.
        """
        # Span detection (AFCE-aligned)
        elicitation_spans = await self.span_detector.detect_elicitation_spans(text)
        response_spans = await self.span_detector.detect_response_spans(text)
        emotion_spans = await self.span_detector.detect_eo_spans(text)

        # Empathy and empathy opportunity signals
        empathy = await self.empathy_detector.detect_empathy_cues(text)
        empathy_response_type = await self.empathy_detector.classify_empathy_response_type(text)
        eo_analysis = await self.empathy_detector.detect_empathy_opportunity(text)

        # Question classification
        question_type = await self.question_classifier.classify_question_type(text)

        # Tone analysis
        tone = await self.tone_analyzer.analyze_tone(text)

        return {
            # Core surface used by new architecture
            "emotion_spans": emotion_spans,
            "empathy_opportunity": eo_analysis.get("empathy_opportunity", False),
            "question_type": question_type,
            "tone": {
                "calm": tone.get("calm", False),
                "clear": tone.get("clear", False),
            },
            # Extended fields for backward compatibility / richer feedback
            "elicitation_spans": elicitation_spans,
            "response_spans": response_spans,
            "empathy": empathy,
            "empathy_response_type": empathy_response_type,
            "empathy_opportunity_type": eo_analysis.get("empathy_opportunity_type"),
            "eo_analysis": eo_analysis,
        }

