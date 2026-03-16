from __future__ import annotations

from typing import Any

from adapters.llm import LLMAdapter, OpenAIAdapter, GeminiAdapter
from config.settings import get_settings
from services.patient_prompt_builder import PatientPromptBuilder


class DefaultLLMPatientModel:
    """
    Default PatientModel implementation that wraps the existing LLM adapter
    behavior used by DialogueService for patient response generation.
    """

    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        if llm_adapter is None:
            settings = get_settings()
            provider = (settings.default_llm_provider or "openai").lower()
            if provider == "gemini":
                self._llm_adapter = GeminiAdapter()
            else:
                # Default to OpenAI if provider is unknown or "openai"
                self._llm_adapter = OpenAIAdapter()
        else:
            self._llm_adapter = llm_adapter
        self._prompt_builder = PatientPromptBuilder()

    async def generate_response(self, state: Any, clinician_input: str) -> str:
        """
        Generate a simulated patient response using the same logic as DialogueService.

        The `state` object is expected to expose:
        - `case`: current case object
        - `session`: current session object with `current_spikes_stage`
        - `conversation_history`: list of prior turns, in the same shape
          used by DialogueService._get_conversation_history.
        """
        case = getattr(state, "case", None)
        session = getattr(state, "session", None)
        conversation_history = getattr(state, "conversation_history", [])

        if case is None or session is None:
            raise ValueError("state must provide 'case' and 'session' for DefaultLLMPatientModel")

        # Build patient prompt from case metadata and current SPIKES stage
        patient_context = self._prompt_builder.build_prompt(
            case=case,
            stage=getattr(session, "current_spikes_stage", None),
        )

        # Delegate to the existing LLM adapter patient generation method
        response = await self._llm_adapter.generate_patient_response(
            case_script=patient_context,
            conversation_history=conversation_history,
            current_spikes_stage=getattr(session, "current_spikes_stage", None) or "setting",
        )

        return response

