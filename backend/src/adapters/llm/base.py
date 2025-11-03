"""Base LLM adapter protocol."""

from typing import Protocol


class LLMAdapter(Protocol):
    """Protocol for LLM adapters."""
    
    async def generate_response(
        self,
        prompt: str,
        context: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: The prompt/question to send to the LLM
            context: Additional context for the conversation
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        ...
    
    async def generate_patient_response(
        self,
        case_script: str,
        conversation_history: list[dict[str, str]],
        current_spikes_stage: str,
    ) -> str:
        """Generate a patient response based on case and conversation.
        
        Args:
            case_script: The case scenario script
            conversation_history: List of previous turns
            current_spikes_stage: Current SPIKES protocol stage
            
        Returns:
            Patient's response
        """
        ...
    
    async def analyze_turn(
        self,
        user_text: str,
        conversation_history: list[dict[str, str]],
    ) -> dict[str, any]:
        """Analyze a user's turn for metrics.
        
        Args:
            user_text: The user's message
            conversation_history: Previous conversation
            
        Returns:
            Dictionary with metrics (empathy, question_type, etc.)
        """
        ...

