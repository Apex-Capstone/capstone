"""Span detection for AFCE-aligned empathy opportunities, elicitations, and responses."""

import re
from typing import List, Dict, Any, Tuple

from adapters.nlu.base import (
    AFCE_DIMENSION_FEELING,
    AFCE_DIMENSION_JUDGMENT,
    AFCE_DIMENSION_APPRECIATION,
    AFCE_EXPLICIT,
    AFCE_IMPLICIT,
    ELICITATION_DIRECT,
    ELICITATION_INDIRECT,
    RESPONSE_UNDERSTANDING,
    RESPONSE_SHARING,
    RESPONSE_ACCEPTANCE,
    PROVENANCE_RULE,
)


class SpanDetector:
    """Detects spans with character offsets for AFCE constructs."""
    
    # AFCE EO keywords by dimension and explicit/implicit
    EO_KEYWORDS = {
        (AFCE_DIMENSION_FEELING, AFCE_EXPLICIT): [
            "scared", "afraid", "worried", "anxious", "terrified",
            "sad", "upset", "devastated", "depressed", "hopeless",
            "angry", "furious", "frustrated", "mad", "annoyed",
            "confused", "overwhelmed", "shocked", "stunned",
            "pain", "hurting", "ache", "suffering",
            "don't know what to do", "can't handle", "too much",
        ],
        (AFCE_DIMENSION_FEELING, AFCE_IMPLICIT): [
            "i guess", "maybe", "sort of", "kind of",
            "not sure", "wondering", "thinking about",
            "concerned", "a bit", "somewhat",
            "difficult", "hard", "challenging", "tough",
            "not being able to", "being sick", "take care of",  # Implicit concerns about ability/health
            "picturing being",  # Implicit fears/concerns
        ],
        (AFCE_DIMENSION_JUDGMENT, AFCE_EXPLICIT): [
            "wrong", "bad", "unfair", "unjust", "terrible", "awful", "horrible",
            "shouldn't have", "should have", "fault", "blame",
        ],
        (AFCE_DIMENSION_JUDGMENT, AFCE_IMPLICIT): [
            "difficult", "challenging", "tough", "problematic", "concerning", "questionable",
        ],
        (AFCE_DIMENSION_APPRECIATION, AFCE_EXPLICIT): [
            "important", "meaningful", "valuable", "significant", "matters",
            "precious", "cherished", "meaningful to me",
        ],
        (AFCE_DIMENSION_APPRECIATION, AFCE_IMPLICIT): [
            "matters", "significant", "relevant", "counts", "worth it",
            "what this really means for", "for my life", "day to day",  # Implicit Appreciation of impact
            "what this means", "means for my",  # Life impact concerns
        ],
    }
    
    # Elicitation keywords by type and dimension
    ELICITATION_KEYWORDS = {
        (ELICITATION_DIRECT, AFCE_DIMENSION_FEELING): [
            "how do you feel", "what emotions", "tell me about your feelings",
            "what are you feeling", "how are you feeling",
            "how you've been feeling", "how you're feeling",
            "how you're coping", "what specifically worries you",
            "can you tell me more about", "tell me more about",
            "can you tell me what", "tell me what",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_FEELING): [
            "it sounds like you're feeling", "you seem", "it seems like you feel",
            "you appear to be feeling",
        ],
        (ELICITATION_DIRECT, AFCE_DIMENSION_JUDGMENT): [
            "what do you think about", "how do you see this", "what's your opinion",
            "what are your thoughts", "how do you view",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_JUDGMENT): [
            "it seems like you think", "you're saying", "it sounds like you believe",
            "if i understand correctly", "you appear to think",
        ],
        (ELICITATION_DIRECT, AFCE_DIMENSION_APPRECIATION): [
            "what matters to you", "what's important", "what do you value",
            "what's meaningful to you", "what's significant",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_APPRECIATION): [
            "it sounds like this is important", "it seems like this matters",
            "you're saying this is meaningful", "it appears this is valuable",
        ],
    }
    
    # Response keywords (AFCE taxonomy)
    RESPONSE_KEYWORDS = {
        RESPONSE_UNDERSTANDING: [
            "i understand",
            "i see",
            "i get it",
            "i hear you",
            "that makes sense",
            "i can see why",
            "i follow you",
            "it makes sense",
            "it sounds like",
            "i understand how",
            "i understand how important",
            "sounds like",
            # Additional common empathic framings
            "i can see this is difficult",
            "i can see this is hard",
            "i can see this is a lot",
            "i can see this is a lot to take in",
            "i know this is hard",
            "i know this is difficult",
            "i understand this is hard",
            "i understand this must be difficult",
        ],
        RESPONSE_SHARING: [
            "i feel the same",
            "i understand how",
            "that resonates",
            "i can relate",
            "i've felt that way",
            "that's how i feel too",
        ],
        RESPONSE_ACCEPTANCE: [
            "that's valid",
            "that's understandable",
            "that makes sense",
            "that's reasonable",
            "anyone would feel",
            "that's normal",
            "it makes sense that",
            "makes sense that you'd",
            # Strong normalizing / validating language
            "this must be overwhelming",
            "this must be hard",
        ],
    }
    
    def detect_eo_spans(self, text: str) -> List[Dict[str, Any]]:
        """Detect empathy opportunity spans with AFCE dimensions.
        
        Args:
            text: Text to analyze (patient/assistant response)
            
        Returns:
            List of EO spans with dimension, explicit_or_implicit, offsets, confidence, provenance
        """
        spans = []
        text_lower = text.lower()
        
        # Check each dimension and explicit/implicit combination
        for (dimension, explicit_implicit), keywords in self.EO_KEYWORDS.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                keyword_words = keyword.split()
                
                # For multi-word keywords, use substring search (more flexible)
                # For single-word keywords, use word boundary matching (more precise)
                if len(keyword_words) > 1:
                    # Multi-word: find all substring matches
                    start_idx = 0
                    while True:
                        idx = text_lower.find(keyword_lower, start_idx)
                        if idx == -1:
                            break
                        
                        start_char = idx
                        end_char = idx + len(keyword)
                        span_text = text[start_char:end_char]
                        
                        # Confidence based on keyword strength
                        confidence = 0.85 if explicit_implicit == AFCE_EXPLICIT else 0.72
                        
                        span = {
                            "dimension": dimension,
                            "explicit_or_implicit": explicit_implicit,
                            "start_char": start_char,
                            "end_char": end_char,
                            "text": span_text,
                            "confidence": confidence,
                            "provenance": PROVENANCE_RULE,
                        }
                        spans.append(span)
                        
                        start_idx = idx + 1
                else:
                    # Single-word: use word boundary matching
                    pattern = re.escape(keyword)
                    matches = list(re.finditer(rf'\b{pattern}\b', text_lower, re.IGNORECASE))
                    
                    for match in matches:
                        start_char = match.start()
                        end_char = match.end()
                        span_text = text[start_char:end_char]
                        
                        # Confidence based on keyword strength
                        confidence = 0.85 if explicit_implicit == AFCE_EXPLICIT else 0.72
                        
                        span = {
                            "dimension": dimension,
                            "explicit_or_implicit": explicit_implicit,
                            "start_char": start_char,
                            "end_char": end_char,
                            "text": span_text,
                            "confidence": confidence,
                            "provenance": PROVENANCE_RULE,
                        }
                        spans.append(span)
        
        # Remove overlapping spans (keep higher confidence)
        spans = self._remove_overlapping_spans(spans)
        
        # Sort by start_char
        spans.sort(key=lambda s: s["start_char"])
        
        return spans
    
    def detect_elicitation_spans(self, text: str) -> List[Dict[str, Any]]:
        """Detect elicitation spans with AFCE dimensions.
        
        Args:
            text: Text to analyze (clinician turn)
            
        Returns:
            List of elicitation spans with type (direct/indirect), dimension, offsets, confidence, provenance
        """
        spans = []
        text_lower = text.lower()
        
        # Check each elicitation type and dimension combination
        for (elicitation_type, dimension), keywords in self.ELICITATION_KEYWORDS.items():
            for keyword in keywords:
                # Case-insensitive search
                pattern = re.escape(keyword)
                matches = list(re.finditer(rf'\b{pattern}\b', text_lower, re.IGNORECASE))
                
                for match in matches:
                    start_char = match.start()
                    end_char = match.end()
                    span_text = text[start_char:end_char]
                    
                    # Confidence: direct elicitations get 0.85, indirect get 0.8
                    confidence = 0.85 if elicitation_type == ELICITATION_DIRECT else 0.8
                    
                    # Handle multi-word keywords
                    if len(keyword.split()) > 1:
                        keyword_lower = keyword.lower()
                        idx = text_lower.find(keyword_lower, start_char)
                        if idx != -1:
                            start_char = idx
                            end_char = idx + len(keyword)
                            span_text = text[start_char:end_char]
                    
                    span = {
                        "type": elicitation_type,
                        "dimension": dimension,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": span_text,
                        "confidence": confidence,
                        "provenance": PROVENANCE_RULE,
                    }
                    spans.append(span)
        
        # Remove overlapping spans
        spans = self._remove_overlapping_spans(spans)
        
        # Sort by start_char
        spans.sort(key=lambda s: s["start_char"])
        
        return spans
    
    def detect_response_spans(self, text: str) -> List[Dict[str, Any]]:
        """Detect empathic response spans (AFCE taxonomy).
        
        Args:
            text: Text to analyze (clinician turn)
            
        Returns:
            List of response spans with type (understanding/sharing/acceptance), offsets, confidence, provenance
        """
        spans = []
        text_lower = text.lower()
        
        # Check each response type
        for response_type, keywords in self.RESPONSE_KEYWORDS.items():
            for keyword in keywords:
                # Case-insensitive search
                pattern = re.escape(keyword)
                matches = list(re.finditer(rf'\b{pattern}\b', text_lower, re.IGNORECASE))
                
                for match in matches:
                    start_char = match.start()
                    end_char = match.end()
                    span_text = text[start_char:end_char]
                    
                    # Confidence: understanding gets 0.8, sharing gets 0.85, acceptance gets 0.82
                    confidence_map = {
                        RESPONSE_UNDERSTANDING: 0.8,
                        RESPONSE_SHARING: 0.85,
                        RESPONSE_ACCEPTANCE: 0.82,
                    }
                    confidence = confidence_map.get(response_type, 0.8)
                    
                    # Handle multi-word keywords
                    if len(keyword.split()) > 1:
                        keyword_lower = keyword.lower()
                        idx = text_lower.find(keyword_lower, start_char)
                        if idx != -1:
                            start_char = idx
                            end_char = idx + len(keyword)
                            span_text = text[start_char:end_char]
                    
                    span = {
                        "type": response_type,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": span_text,
                        "confidence": confidence,
                        "provenance": PROVENANCE_RULE,
                    }
                    spans.append(span)
        
        # Remove overlapping spans (prioritize by type: sharing > acceptance > understanding)
        spans = self._remove_overlapping_spans(spans, priority_key="type", priority_order=[
            RESPONSE_SHARING, RESPONSE_ACCEPTANCE, RESPONSE_UNDERSTANDING
        ])
        
        # Sort by start_char
        spans.sort(key=lambda s: s["start_char"])
        
        return spans
    
    def _remove_overlapping_spans(
        self,
        spans: List[Dict[str, Any]],
        priority_key: str = "confidence",
        priority_order: List[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Remove overlapping spans, keeping higher priority ones.
        
        Args:
            spans: List of span dictionaries
            priority_key: Key to use for prioritization (default: "confidence")
            priority_order: Optional ordered list for priority values (e.g., for response types)
            
        Returns:
            List of non-overlapping spans
        """
        if not spans:
            return []
        
        # Sort by start_char, then by priority
        def sort_key(span: Dict[str, Any]) -> Tuple[int, float, float]:
            priority_val = span.get(priority_key)
            if priority_order and priority_val in priority_order:
                priority_rank = priority_order.index(priority_val)
            elif isinstance(priority_val, (int, float)):
                priority_rank = -priority_val  # Higher confidence = lower rank number (better)
            else:
                priority_rank = 999
            
            return (span["start_char"], priority_rank, -span.get("confidence", 0))
        
        sorted_spans = sorted(spans, key=sort_key)
        non_overlapping = []
        
        for span in sorted_spans:
            overlaps = False
            for existing in non_overlapping:
                # Check if spans overlap
                if not (span["end_char"] <= existing["start_char"] or span["start_char"] >= existing["end_char"]):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(span)
        
        return non_overlapping
    
    def detect_spikes_stage(self, text: str, has_elicitations: bool = False, has_responses: bool = False) -> str | None:
        """Detect SPIKES stage from turn content.
        
        Args:
            text: Text to analyze (clinician turn)
            has_elicitations: Whether this turn contains elicitations
            has_responses: Whether this turn contains empathic responses
            
        Returns:
            SPIKES stage name or None if unclear
        """
        text_lower = text.lower()
        
        # Setting: Opening statements, greetings, comfort checks
        setting_keywords = [
            "hi", "hello", "thank you for coming", "welcome",
            "before we dive in", "can i help you feel more comfortable",
            "is there anything i can do", "let's get started",
        ]
        if any(keyword in text_lower for keyword in setting_keywords):
            return "setting"
        
        # Perception: Questions about understanding/perception
        perception_keywords = [
            "what do you understand", "what you understand",
            "how do you see", "what are your thoughts about",
            "tell me what you know", "what do you think is happening",
            "how you're feeling about it", "how you've been feeling",
        ]
        if any(keyword in text_lower for keyword in perception_keywords) or has_elicitations:
            # Check if it's specifically asking about perception
            if "understand" in text_lower or "perception" in text_lower or "know" in text_lower:
                return "perception"
        
        # Invitation: Asking permission/preference to share information
        invitation_keywords = [
            "would you like me to", "would you like", "would you prefer",
            "shall i", "should i", "do you want me to",
            "when would be a good time", "when would you like to",
        ]
        if any(keyword in text_lower for keyword in invitation_keywords):
            return "invitation"
        
        # Knowledge: Delivering information about diagnosis, test results, treatment
        knowledge_keywords = [
            "the scan shows", "the test results", "the diagnosis",
            "we have several treatment options", "treatment options",
            "prognosis", "the results indicate", "based on the",
            "let me explain", "here's what we know",
        ]
        if any(keyword in text_lower for keyword in knowledge_keywords):
            return "knowledge"
        
        # Empathy: Empathic responses (can be detected by response spans)
        empathy_keywords = [
            "i hear you", "i understand how", "that must be",
            "it makes sense", "anyone would feel", "i can imagine",
            "that sounds", "it sounds like you're",
        ]
        if has_responses or any(keyword in text_lower for keyword in empathy_keywords):
            # Check if it's primarily an empathic response vs strategy
            if "plan" not in text_lower and "let's make" not in text_lower:
                return "empathy"
        
        # Strategy/Summary: Planning, summarizing, next steps
        strategy_keywords = [
            "let's make a plan", "let's plan", "make a plan together",
            "here's what we'll do", "next steps", "moving forward",
            "let's work together", "we can manage", "strategy",
            "to summarize", "in summary",
        ]
        if any(keyword in text_lower for keyword in strategy_keywords):
            return "summary"
        
        # If turn has empathic responses but no strategy keywords, it's empathy
        if has_responses:
            return "empathy"
        
        # If turn has elicitations asking about feelings/perception, it's perception
        if has_elicitations and "feel" in text_lower:
            return "perception"
        
        return None

