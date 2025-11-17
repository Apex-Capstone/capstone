"""Simple rule-based NLU adapter implementation with AFCE-aligned span detection."""

import re
import json
from typing import Any

from config.logging import get_logger
from adapters.nlu.span_detector import SpanDetector

logger = get_logger(__name__)


class SimpleRuleNLU:
    """Simple rule-based NLU adapter with AFCE-aligned span detection."""
    
    def __init__(self):
        """Initialize span detector."""
        self.span_detector = SpanDetector()
    
    # Legacy empathy keywords (kept for backward compatibility)
    EMPATHY_KEYWORDS = [
        "understand", "feel", "difficult", "sorry", "imagine",
        "support", "here for you", "concern", "worry", "comfort",
    ]
    
    # Tone keywords
    CALM_KEYWORDS = [
        "calm", "relaxed", "peaceful", "steady", "composed",
    ]
    
    AGITATED_KEYWORDS = [
        "upset", "frustrated", "angry", "anxious", "worried",
        "stressed", "overwhelmed", "panicked",
    ]
    
    CLEAR_KEYWORDS = [
        "clear", "understand", "comprehend", "grasp",
    ]
    
    UNCLEAR_KEYWORDS = [
        "confused", "unclear", "don't understand", "not sure",
        "vague", "ambiguous",
    ]
    
    # Open question starters
    OPEN_QUESTION_WORDS = [
        "how", "what", "why", "tell me", "describe", "explain",
        "can you tell", "could you share", "help me understand",
    ]
    
    # Closed question words
    CLOSED_QUESTION_WORDS = [
        "is", "are", "do", "does", "did", "have", "has",
        "can", "could", "would", "will", "shall",
    ]
    
    async def analyze_intent(
        self,
        text: str,
        context: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Analyze intent using simple rules."""
        text_lower = text.lower()
        
        is_question = "?" in text or any(
            text_lower.startswith(word) 
            for word in self.OPEN_QUESTION_WORDS + self.CLOSED_QUESTION_WORDS
        )
        
        has_empathy = any(keyword in text_lower for keyword in self.EMPATHY_KEYWORDS)
        
        return {
            "is_question": is_question,
            "has_empathy_keywords": has_empathy,
            "confidence": 0.7,
        }
    
    async def detect_empathy_cues(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Detect empathy cues using keyword matching."""
        text_lower = text.lower()
        
        found_keywords = [
            keyword for keyword in self.EMPATHY_KEYWORDS
            if keyword in text_lower
        ]
        
        # Simple scoring: 0-10 based on number of keywords
        empathy_score = min(10, len(found_keywords) * 2.5)
        
        return {
            "empathy_score": empathy_score,
            "found_keywords": found_keywords,
            "has_empathy": len(found_keywords) > 0,
        }
    
    async def classify_question_type(
        self,
        text: str,
    ) -> str:
        """Classify question type using simple rules."""
        text_lower = text.lower().strip()
        
        # Not a question if no question mark and doesn't start with question word
        if "?" not in text:
            starts_with_question = any(
                text_lower.startswith(word)
                for word in self.OPEN_QUESTION_WORDS + self.CLOSED_QUESTION_WORDS
            )
            if not starts_with_question:
                return "statement"
        
        # Check for open-ended questions
        if any(text_lower.startswith(word) for word in self.OPEN_QUESTION_WORDS):
            return "open"
        
        # Check for closed questions
        if any(text_lower.startswith(word) for word in self.CLOSED_QUESTION_WORDS):
            return "closed"
        
        # Default to closed if has question mark but unclear
        return "closed" if "?" in text else "statement"
    
    async def detect_empathy_opportunity(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Detect empathy opportunities in text (legacy method for backward compatibility)."""
        # Use span detection for AFCE-aligned detection
        spans = await self.detect_eo_spans(text)
        
        # Determine EO type from spans for backward compatibility
        if not spans:
            return {
                "empathy_opportunity_type": None,
                "empathy_opportunity": False,
                "missed_opportunity": False,
            }
        
        # Check if any spans are explicit
        has_explicit = any(s.get("explicit_or_implicit") == "explicit" for s in spans)
        eo_type = "explicit" if has_explicit else "implicit"
        
        return {
            "empathy_opportunity_type": eo_type,
            "empathy_opportunity": True,
            "missed_opportunity": False,  # Will be set by dialogue service based on context
        }
    
    async def detect_eo_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect empathy opportunity spans with AFCE dimensions."""
        return self.span_detector.detect_eo_spans(text)
    
    async def detect_elicitation_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect elicitation spans with AFCE dimensions."""
        return self.span_detector.detect_elicitation_spans(text)
    
    async def classify_empathy_response_type(
        self,
        text: str,
    ) -> str:
        """Classify type of empathy response (legacy method for backward compatibility)."""
        # Use span detection for AFCE-aligned detection
        spans = await self.detect_response_spans(text)
        
        if not spans:
            return "other"
        
        # Return the first response type found (prioritized by span detector)
        return spans[0].get("type", "other")
    
    async def detect_response_spans(
        self,
        text: str,
    ) -> list[dict[str, Any]]:
        """Detect empathic response spans (AFCE taxonomy)."""
        return self.span_detector.detect_response_spans(text)
    
    async def analyze_tone(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Analyze tone of communication."""
        text_lower = text.lower()
        
        # Check for calm indicators
        calm_indicators = sum(1 for keyword in self.CALM_KEYWORDS if keyword in text_lower)
        agitated_indicators = sum(1 for keyword in self.AGITATED_KEYWORDS if keyword in text_lower)
        
        # Determine calm/agitated
        if agitated_indicators > calm_indicators:
            calm = False
        elif calm_indicators > 0:
            calm = True
        else:
            # Default to calm if no strong indicators
            calm = agitated_indicators == 0
        
        # Check for clear indicators
        clear_indicators = sum(1 for keyword in self.CLEAR_KEYWORDS if keyword in text_lower)
        unclear_indicators = sum(1 for keyword in self.UNCLEAR_KEYWORDS if keyword in text_lower)
        
        # Determine clear/unclear
        if unclear_indicators > clear_indicators:
            clear = False
        elif clear_indicators > 0:
            clear = True
        else:
            # Default to clear if no strong indicators
            clear = unclear_indicators == 0
        
        return {
            "calm": calm,
            "clear": clear,
        }

