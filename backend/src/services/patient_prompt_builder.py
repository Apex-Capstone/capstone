from typing import Any


class PatientPromptBuilder:
    """Build structured prompts to condition the LLM patient behavior."""

    def build_prompt(self, case: Any, stage: str) -> str:
        """Construct a patient-facing system prompt using case metadata and SPIKES stage."""
        # Fallback-safe metadata extraction
        diagnosis = getattr(case, "diagnosis", None) or getattr(case, "title", None) or "serious medical condition"
        emotion = getattr(case, "emotional_state", None) or "concerned"
        knowledge_level = getattr(case, "knowledge_level", None) or "low"

        stage_label = stage or "setting"

        return (
            "You are a patient speaking with a doctor.\n\n"
            "Patient profile:\n"
            f"- Diagnosis: {diagnosis}\n"
            f"- Emotional state: {emotion}\n"
            f"- Medical knowledge: {knowledge_level}\n\n"
            f"You are currently in the SPIKES stage: {stage_label}.\n\n"
            "Respond naturally as a patient. Express uncertainty, questions, or emotions "
            "when appropriate, and keep your responses realistic and concise."
        )

