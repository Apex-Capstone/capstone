"""Base NLU (Natural Language Understanding) adapter protocol with AFCE taxonomy."""

from typing import Any, Protocol


# AFCE dimension types
AFCE_DIMENSION_FEELING = "Feeling"
AFCE_DIMENSION_JUDGMENT = "Judgment"
AFCE_DIMENSION_APPRECIATION = "Appreciation"

# Explicit/implicit variants
AFCE_EXPLICIT = "explicit"
AFCE_IMPLICIT = "implicit"

# Elicitation types
ELICITATION_DIRECT = "direct"
ELICITATION_INDIRECT = "indirect"

# Response types (AFCE taxonomy)
RESPONSE_UNDERSTANDING = "understanding"
RESPONSE_SHARING = "sharing"
RESPONSE_ACCEPTANCE = "acceptance"

# Provenance types
PROVENANCE_RULE = "rule"
PROVENANCE_ML = "ml"
PROVENANCE_LLM = "llm"

# Relation types (for future use)
RELATION_ELICITS = "elicits"
RELATION_RESPONDS_TO = "responds_to"
RELATION_MISSED = "missed"


class NLUAdapter(Protocol):
    """Protocol for NLU adapters with AFCE-aligned span detection."""
    
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
        """Detect empathy cues in text (legacy method for backward compatibility).
        
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
    
    async def detect_empathy_opportunity(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Detect empathy opportunities in text (legacy method for backward compatibility).
        
        Args:
            text: Text to analyze (patient response)
            
        Returns:
            Dictionary with empathy_opportunity_type ('implicit', 'explicit', or None),
            empathy_opportunity (bool), and missed_opportunity (bool)
        """
        ...
    
    async def classify_empathy_response_type(
        self,
        text: str,
    ) -> str:
        """Classify type of empathy response (legacy method for backward compatibility).
        
        Args:
            text: User (doctor) text to analyze
            
        Returns:
            'understanding', 'interpretation', 'acceptance', 'validation', or 'other'
        """
        ...
    
    async def analyze_tone(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Analyze tone of communication.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with calm (bool), clear (bool), and other tone indicators
        """
        ...
    
    # AFCE-aligned span detection methods
    
    async def detect_eo_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect empathy opportunity spans with AFCE dimensions.
        
        Args:
            text: Text to analyze (patient/assistant response)
            
        Returns:
            List of EO spans, each with:
            - dimension: 'Feeling', 'Judgment', or 'Appreciation'
            - explicit_or_implicit: 'explicit' or 'implicit'
            - start_char: int (character offset start)
            - end_char: int (character offset end)
            - text: str (extracted text substring)
            - confidence: float (0.0-1.0)
            - provenance: 'rule', 'ml', or 'llm'
        """
        ...
    
    async def detect_elicitation_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect elicitation spans with AFCE dimensions.
        
        Args:
            text: Text to analyze (clinician turn)
            
        Returns:
            List of elicitation spans, each with:
            - type: 'direct' or 'indirect'
            - dimension: 'Feeling', 'Judgment', or 'Appreciation'
            - start_char: int (character offset start)
            - end_char: int (character offset end)
            - text: str (extracted text substring)
            - confidence: float (0.0-1.0)
            - provenance: 'rule', 'ml', or 'llm'
        """
        ...
    
    async def detect_response_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect empathic response spans (AFCE taxonomy).
        
        Args:
            text: Text to analyze (clinician turn)
            
        Returns:
            List of response spans, each with:
            - type: 'understanding', 'sharing', or 'acceptance'
            - start_char: int (character offset start)
            - end_char: int (character offset end)
            - text: str (extracted text substring)
            - confidence: float (0.0-1.0)
            - provenance: 'rule', 'ml', or 'llm'
        """
        ...

