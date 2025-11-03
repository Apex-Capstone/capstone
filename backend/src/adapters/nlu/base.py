"""Base NLU (Natural Language Understanding) adapter protocol."""

from typing import Any, Protocol


class NLUAdapter(Protocol):
    """Protocol for NLU adapters."""
    
    async def analyze_intent(
        self,
        text: str,
        context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Analyze intent of user input.
        
        Args:
            text: User input text
            context: Additional context
            
        Returns:
            Dictionary with intent analysis results
        """
        ...
    
    async def detect_empathy_cues(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Detect empathy cues in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with empathy analysis
        """
        ...
    
    async def classify_question_type(
        self,
        text: str,
    ) -> str:
        """Classify question as open-ended or closed.
        
        Args:
            text: Question text
            
        Returns:
            'open', 'closed', or 'statement'
        """
        ...

