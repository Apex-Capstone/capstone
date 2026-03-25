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
    # NOTE: These are phrase-level where possible to reduce noisy single-word matches.
    EO_KEYWORDS = {
        (AFCE_DIMENSION_FEELING, AFCE_EXPLICIT): [
            # Core emotion/fear words
            "scared", "afraid", "worried", "anxious", "terrified",
            "sad", "upset", "devastated", "depressed", "hopeless",
            "angry", "furious", "frustrated", "mad", "annoyed",
            "confused", "overwhelmed", "shocked", "stunned",
            # Burden / impact phrases
            "it scares me", "it scares me a lot",
            "feel alone", "i feel alone",
            "i barely sleep anymore", "barely sleep anymore",
            "i hardly sleep", "hardly sleep",
            "affecting my sleep", "been affecting my sleep",
            "fatigue", "pressure in my chest",
            # Progression / seriousness
            "getting worse", "been getting worse",
            "symptoms have been getting worse",
            "my symptoms seem to be getting worse",
            "something is really wrong",
            "something serious is happening",
        ],
        (AFCE_DIMENSION_FEELING, AFCE_IMPLICIT): [
            # Contextual implicit burden/uncertainty (avoid hedge-only fragments).
            "i'm not sure what this means",
            "i am not sure what this means",
            "i don't know what to do",
            "i dont know what to do",
            "i don't know how to handle this",
            "i dont know how to handle this",
            "i keep thinking about what happens next",
            "i'm finding it difficult to",
            "i am finding it difficult to",
            "this has been really hard",
            "i'm worried about how this will affect",
            "i am worried about how this will affect",
            "this is hard to process",
            "this is difficult to process",
        ],
        (AFCE_DIMENSION_JUDGMENT, AFCE_EXPLICIT): [
            "wrong", "bad", "unfair", "unjust", "terrible", "awful", "horrible",
            "shouldn't have", "should have", "fault", "blame",
        ],
        (AFCE_DIMENSION_JUDGMENT, AFCE_IMPLICIT): [
            # Avoid generic single-word triggers like "difficult"/"tough" which are
            # highly context-dependent and often appear in clinician turns.
            "problematic", "concerning", "questionable",
        ],
        (AFCE_DIMENSION_APPRECIATION, AFCE_EXPLICIT): [
            # Avoid generic 'important' on clinician side; focus on patient appraisal phrases.
            "important to me", "meaningful to me", "matters to me",
            "precious", "cherished",
        ],
        (AFCE_DIMENSION_APPRECIATION, AFCE_IMPLICIT): [
            # Contextual appreciation/priority language only (avoid broad single tokens).
            "what this means for my life",
            "means for my day-to-day life",
            "means for my day to day life",
            "what matters most to me",
            "worth it for me",
            "important for my family",
            # Family-history context as concern/appraisal (patient-specific)
            "my dad had heart problems", "my dad had heart issues",
        ],
    }
    
    # Elicitation keywords by type and dimension
    ELICITATION_KEYWORDS = {
        (ELICITATION_DIRECT, AFCE_DIMENSION_FEELING): [
            "how do you feel", "what emotions", "tell me about your feelings",
            "what are you feeling", "how are you feeling",
            "how you've been feeling", "how you're feeling",
            "how you're coping", "what specifically worries you",
            "what worries you most", "how has this been for you",
            "what feels hardest right now", "tell me more about how this feels",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_FEELING): [
            "it sounds like you're feeling", "you seem", "it seems like you feel",
            "you appear to be feeling",
        ],
        (ELICITATION_DIRECT, AFCE_DIMENSION_JUDGMENT): [
            "what do you think about", "how do you see this", "what's your opinion",
            "what are your thoughts about what's happening", "how do you view",
            "what do you make of this", "how are you making sense of this",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_JUDGMENT): [
            "it seems like you think", "you're saying", "it sounds like you believe",
            "if i understand correctly", "you appear to think",
        ],
        (ELICITATION_DIRECT, AFCE_DIMENSION_APPRECIATION): [
            "what matters to you", "what's important", "what do you value",
            "what's meaningful to you", "what's significant",
            "what matters most",
            "what feels most important right now",
            "what does this mean for your day-to-day life",
            "what are you hoping we keep in mind",
        ],
        (ELICITATION_INDIRECT, AFCE_DIMENSION_APPRECIATION): [
            "it sounds like this is important", "it seems like this matters",
            "you're saying this is meaningful", "it appears this is valuable",
            "it sounds like maintaining your routine matters",
            "it seems like your priorities are shifting",
        ],
    }
    
    # Response keywords (AFCE taxonomy):
    # - keep direct/high-precision phrases here
    # - keep broader linguistic patterns in _detect_pattern_response_spans
    RESPONSE_KEYWORDS = {
        RESPONSE_UNDERSTANDING: [
            "i understand",
            "i see",
            "i get it",
            "i hear you",
            "i can see why",
            "i follow you",
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
            # Thanking / acknowledging sharings
            "thank you for telling me",
            "thank you for sharing",
            "thank you for sharing that",
            # Hearing / validating
            "i hear that",
            "i hear you",
            # Supportive commitments
            "i'll support you",
            "i will support you",
            "we'll support you",
            "we will support you",
            "we'll go through this together",
            "we will go through this together",
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

    # Minimal pattern cues for response-span detection without large phrase lists.
    PERCEPTION_ANCHORS = [
        "i can see",
        "it seems like",
        "i hear that",
    ]
    VALIDATION_ANCHORS = [
        "that must be",
        "that sounds",
        "that's a lot to take in",
        "that makes sense",
        "it makes sense",
    ]
    APOLOGY_ANCHORS = [
        "i'm sorry",
        "i am sorry",
    ]
    KNOW_ANCHORS = [
        "i know",
    ]
    RESPONSE_PIVOT_PATTERNS = [
        r",\s*(?:and\s+)?but\b",
        r",\s*however\b",
        r",\s*(?:and\s+)?right now\b",
        r",\s*for now\b",
        r",\s*what i can say is\b",
        r",\s*the next step is\b",
        r",\s*(?:and\s+)?we(?:'ll| will)\b",
        r"\bhowever\b",
        r"\bbut\b",
        r"\bfor now\b",
        r"\bright now\b",
        r"\bwhat i can say is\b",
        r"\bthe next step is\b",
        r"\bwe(?:'ll| will)\b",
    ]
    EMOTIONAL_CONTEXT_WORDS = [
        "stressful",
        "overwhelming",
        "difficult",
        "scary",
        "serious",
        "hard",
        "upsetting",
        "helpless",
        "unsettling",
        "afraid",
        "happening",
    ]

    # Phrase-level distress cues for patient/family turns. More specific patterns first;
    # matched against lowercased text (offsets match ASCII-only case changes).
    _CONTEXTUAL_DISTRESS_PATTERN_SPECS: List[Tuple[str, str]] = [
        (
            r"\bcan['\u2019]?t shake (?:this )?feeling of dread\b",
            AFCE_EXPLICIT,
        ),
        (r"\bfeeling of dread\b", AFCE_EXPLICIT),
        (r"\bfeels like such a long time to wait\b", AFCE_EXPLICIT),
        (r"\b(?:long time to wait|such a long time to wait)\b", AFCE_EXPLICIT),
        (r"\bit(?:'|\u2019)?s (?:still )?so hard to (?:just )?(?:sit and )?wait\b", AFCE_EXPLICIT),
        (r"\b(?:hard|difficult) to wait\b", AFCE_EXPLICIT),
        (r"\b(?:that |it )?sounds (?:really )?scary\b", AFCE_EXPLICIT),
        (r"\bfeels? (?:really )?scary\b", AFCE_EXPLICIT),
        (r"\b(?:this|that|it) (?:is|was) (?:really )?scary\b", AFCE_EXPLICIT),
        (r"\b(?:i |we )(?:just )?keep worrying\b", AFCE_EXPLICIT),
        (r"\bkeep worrying\b", AFCE_EXPLICIT),
        (r"\bdread\b", AFCE_EXPLICIT),
        (r"\b(?:feeling |feel )?(?:completely |totally |so )?helpless\b", AFCE_EXPLICIT),
        (r"\bi(?:'|\u2019)?m (?:just )?(?:so |really )?worried\b", AFCE_EXPLICIT),
        (r"\bworrying\b", AFCE_EXPLICIT),
    ]

    _EO_DIMENSION_PRIORITY = [
        AFCE_DIMENSION_FEELING,
        AFCE_DIMENSION_APPRECIATION,
        AFCE_DIMENSION_JUDGMENT,
    ]

    def _detect_contextual_distress_eos(self, text: str) -> List[Dict[str, Any]]:
        """High-precision phrase-level Feeling EOs for fear, dread, worry, and waiting burden."""
        if not text or not text.strip():
            return []
        text_lower = text.lower()
        spans: List[Dict[str, Any]] = []
        for pattern, explicit_implicit in self._CONTEXTUAL_DISTRESS_PATTERN_SPECS:
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                start_char = match.start()
                end_char = match.end()
                span_text = text[start_char:end_char]
                spans.append(
                    {
                        "dimension": AFCE_DIMENSION_FEELING,
                        "explicit_or_implicit": explicit_implicit,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": span_text,
                        "confidence": 0.88,
                        "provenance": PROVENANCE_RULE,
                    }
                )
        return self._remove_overlapping_spans(spans)

    def detect_eo_spans(self, text: str) -> List[Dict[str, Any]]:
        """Detect empathy opportunity spans with AFCE dimensions.
        
        Args:
            text: Text to analyze (patient/assistant response)
            
        Returns:
            List of EO spans with dimension, explicit_or_implicit, offsets, confidence, provenance
        """
        spans: List[Dict[str, Any]] = []
        text_lower = text.lower()

        spans.extend(self._detect_contextual_distress_eos(text))

        # Check each dimension and explicit/implicit combination
        for (dimension, explicit_implicit), keywords in self.EO_KEYWORDS.items():
            # Prefer longer, multiword keywords first so that phrases like
            # "my symptoms have been getting worse" are matched before shorter
            # substrings like "worse".
            for keyword in sorted(keywords, key=len, reverse=True):
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
        
        # Remove overlapping spans: Feeling > Appreciation > Judgment; then confidence/length.
        spans = self._remove_overlapping_spans(
            spans,
            priority_key="dimension",
            priority_order=self._EO_DIMENSION_PRIORITY,
        )
        
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

                    start_char, end_char = self._expand_to_empathic_clause(text, start_char)
                    span_text = text[start_char:end_char].strip()
                    
                    span = {
                        "type": response_type,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": span_text,
                        "confidence": confidence,
                        "provenance": PROVENANCE_RULE,
                    }
                    spans.append(span)
        
        # Add pattern-based response spans (anchor + emotional context / validation cues).
        pattern_spans = self._detect_pattern_response_spans(text)
        spans.extend(pattern_spans)

        # Remove overlapping spans (prioritize by type: sharing > acceptance > understanding)
        spans = self._remove_overlapping_spans(spans, priority_key="type", priority_order=[
            RESPONSE_SHARING, RESPONSE_ACCEPTANCE, RESPONSE_UNDERSTANDING
        ])
        
        # Sort by start_char
        spans.sort(key=lambda s: s["start_char"])
        
        return spans

    def _detect_pattern_response_spans(self, text: str) -> List[Dict[str, Any]]:
        """Detect empathy responses from lightweight structural patterns."""
        spans: List[Dict[str, Any]] = []
        text_lower = text.lower()

        for sentence_start, sentence_end in self._iter_sentence_spans(text):
            sentence_text = text[sentence_start:sentence_end]
            sentence_lower = sentence_text.lower()
            if not sentence_lower.strip():
                continue

            # Rule 1: perception anchor + emotional context => understanding response.
            has_emotional_context = any(
                re.search(rf"\b{re.escape(word)}\b", sentence_lower)
                for word in self.EMOTIONAL_CONTEXT_WORDS
            )
            if has_emotional_context:
                for anchor in self.PERCEPTION_ANCHORS:
                    anchor_idx = sentence_lower.find(anchor)
                    if anchor_idx == -1:
                        continue
                    start_char = sentence_start + anchor_idx
                    _, end_char = self._expand_to_empathic_clause(text, start_char)
                    end_char = min(end_char, sentence_end)
                    spans.append(
                        {
                            "type": RESPONSE_UNDERSTANDING,
                            "start_char": start_char,
                            "end_char": end_char,
                            "text": text[start_char:end_char].strip(),
                            "confidence": 0.84,
                            "provenance": PROVENANCE_RULE,
                        }
                    )

            # Rule 2: validation clause cues => acceptance response.
            for anchor in self.VALIDATION_ANCHORS:
                anchor_idx = sentence_lower.find(anchor)
                if anchor_idx == -1:
                    continue
                start_char = sentence_start + anchor_idx
                _, end_char = self._expand_to_empathic_clause(text, start_char)
                end_char = min(end_char, sentence_end)
                spans.append(
                    {
                        "type": RESPONSE_ACCEPTANCE,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": text[start_char:end_char].strip(),
                        "confidence": 0.84,
                        "provenance": PROVENANCE_RULE,
                    }
                )

            # Rule 3: apology + emotional context => understanding response.
            if has_emotional_context:
                for anchor in self.APOLOGY_ANCHORS:
                    anchor_idx = sentence_lower.find(anchor)
                    if anchor_idx == -1:
                        continue
                    start_char = sentence_start + anchor_idx
                    _, end_char = self._expand_to_empathic_clause(text, start_char)
                    end_char = min(end_char, sentence_end)
                    spans.append(
                        {
                            "type": RESPONSE_UNDERSTANDING,
                            "start_char": start_char,
                            "end_char": end_char,
                            "text": text[start_char:end_char].strip(),
                            "confidence": 0.85,
                            "provenance": PROVENANCE_RULE,
                        }
                    )

            # Rule 4: "I know" + emotional burden => understanding response.
            if has_emotional_context:
                for anchor in self.KNOW_ANCHORS:
                    anchor_idx = sentence_lower.find(anchor)
                    if anchor_idx == -1:
                        continue
                    start_char = sentence_start + anchor_idx
                    _, end_char = self._expand_to_empathic_clause(text, start_char)
                    end_char = min(end_char, sentence_end)
                    spans.append(
                        {
                            "type": RESPONSE_UNDERSTANDING,
                            "start_char": start_char,
                            "end_char": end_char,
                            "text": text[start_char:end_char].strip(),
                            "confidence": 0.84,
                            "provenance": PROVENANCE_RULE,
                        }
                    )

            # Rule 5: "<situation> can be hard/scary/..." framing => understanding response.
            can_be_match = re.search(
                r"\b(?:this|that|it|waiting|results|uncertainty|news|situation)\b[^.!?;,:]{0,40}\bcan be\b[^.!?;,:]{0,40}\b(?:difficult|hard|scary|overwhelming|stressful|upsetting)\b",
                sentence_lower,
            )
            if can_be_match:
                start_char = sentence_start + can_be_match.start()
                _, end_char = self._expand_to_empathic_clause(text, start_char)
                end_char = min(end_char, sentence_end)
                spans.append(
                    {
                        "type": RESPONSE_UNDERSTANDING,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": text[start_char:end_char].strip(),
                        "confidence": 0.83,
                        "provenance": PROVENANCE_RULE,
                    }
                )

        return spans

    def _iter_sentence_spans(self, text: str) -> List[Tuple[int, int]]:
        """Return sentence ranges (start, end) preserving original offsets."""
        spans: List[Tuple[int, int]] = []
        for match in re.finditer(r"[^.!?]+[.!?]?", text):
            start = match.start()
            end = match.end()
            if text[start:end].strip():
                spans.append((start, end))
        return spans

    def _expand_to_empathic_clause(self, text: str, start_idx: int) -> Tuple[int, int]:
        """Expand from an empathy anchor to the end of its empathic clause."""
        if start_idx < 0 or start_idx >= len(text):
            return start_idx, start_idx

        remainder = text[start_idx:]
        sentence_match = re.search(r"[.!?]", remainder)
        sentence_end = start_idx + sentence_match.start() + 1 if sentence_match else len(text)

        segment = text[start_idx:sentence_end]
        segment_lower = segment.lower()

        semicolon_idx = segment.find(";")
        hard_end = start_idx + semicolon_idx if semicolon_idx != -1 else sentence_end

        pivot_offsets: List[int] = []
        for pattern in self.RESPONSE_PIVOT_PATTERNS:
            match = re.search(pattern, segment_lower)
            if match and match.start() > 0:
                pivot_offsets.append(match.start())

        if pivot_offsets:
            return start_idx, min(start_idx + min(pivot_offsets), hard_end)
        return start_idx, hard_end
    
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
        
        # Sort by start_char, then by priority, then by confidence and length.
        # For EO spans (default priority_key="confidence"), this ensures that when
        # multiple overlapping spans share similar confidence, longer phrases like
        # "it scares me a lot" win over shorter substrings like "scared".
        def sort_key(span: Dict[str, Any]) -> Tuple[int, float, float, int]:
            priority_val = span.get(priority_key)
            if priority_order and priority_val in priority_order:
                priority_rank = priority_order.index(priority_val)
            elif isinstance(priority_val, (int, float)):
                priority_rank = -priority_val  # Higher confidence = lower rank number (better)
            else:
                priority_rank = 999
            length = span.get("end_char", 0) - span.get("start_char", 0)
            return (
                span["start_char"],
                priority_rank,
                -span.get("confidence", 0.0),
                -length,
            )
        
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
        """Detect a single best SPIKES stage from clinician turn content."""
        if not text or not text.strip():
            return None

        stage_names = [
            "setting",
            "perception",
            "invitation",
            "knowledge",
            "emotion",
            "strategy_and_summary",
        ]
        stage_max_scores = {stage: 0 for stage in stage_names}
        stage_total_scores = {stage: 0 for stage in stage_names}

        clauses = self._iter_clause_spans(text)
        for clause_start, clause_end in clauses:
            clause_text = text[clause_start:clause_end].strip()
            if not clause_text:
                continue

            clause_scores = {
                "setting": self._score_setting_clause(clause_text),
                "perception": self._score_perception_clause(clause_text, has_elicitations),
                "invitation": self._score_invitation_clause(clause_text),
                "knowledge": self._score_knowledge_clause(clause_text),
                "emotion": self._score_emotion_clause(clause_text, has_responses),
                "strategy_and_summary": self._score_strategy_and_summary_clause(clause_text),
            }
            for stage, score in clause_scores.items():
                stage_max_scores[stage] = max(stage_max_scores[stage], score)
                stage_total_scores[stage] += score

        # Primarily validation / support with at most incidental knowledge or planning cues.
        if (
            stage_max_scores["emotion"] >= 3
            and stage_max_scores["knowledge"] <= 1
            and stage_max_scores["strategy_and_summary"] <= 1
        ):
            return "emotion"

        priority = {
            "setting": 0,
            "perception": 1,
            "invitation": 2,
            "knowledge": 3,
            "emotion": 4,
            "strategy_and_summary": 5,
        }
        candidates = []
        for stage in stage_names:
            if stage_max_scores[stage] <= 0:
                continue
            candidates.append((stage_max_scores[stage], stage_total_scores[stage], -priority[stage], stage))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        winner = candidates[0][3]

        # When informative or planning clauses outweigh affective wording, do not let emotion win.
        if winner == "emotion":
            mk = stage_max_scores["knowledge"]
            ms = stage_max_scores["strategy_and_summary"]
            me = stage_max_scores["emotion"]
            tk = stage_total_scores["knowledge"]
            ts = stage_total_scores["strategy_and_summary"]
            te = stage_total_scores["emotion"]
            # Strong knowledge clause, or clearly higher clause-level knowledge weight.
            if not (ms >= 3 and ts > tk) and (
                (mk >= 3 and tk >= te) or (mk >= 2 and tk > te)
            ):
                return "knowledge"
            # Strong planning / next-step clause; allow tied totals (tie-break wrongly favored emotion).
            if ms >= 3 and ts >= te and (ms >= me or ts > te):
                return "strategy_and_summary"

        return winner

    def _contains_any_phrase(self, text_lower: str, phrases: List[str]) -> bool:
        return any(phrase in text_lower for phrase in phrases)

    def _iter_clause_spans(self, text: str) -> List[Tuple[int, int]]:
        """Return clause spans from sentence chunks using light punctuation boundaries."""
        clause_spans: List[Tuple[int, int]] = []
        for sentence_start, sentence_end in self._iter_sentence_spans(text):
            sentence = text[sentence_start:sentence_end]
            boundaries = [0]
            for match in re.finditer(r", and |[,;]", sentence, re.IGNORECASE):
                boundaries.append(match.end())
            boundaries.append(len(sentence))
            for i in range(len(boundaries) - 1):
                start = sentence_start + boundaries[i]
                end = sentence_start + boundaries[i + 1]
                if text[start:end].strip():
                    clause_spans.append((start, end))
        return clause_spans

    def _score_setting_clause(self, clause_text: str) -> int:
        text_lower = clause_text.lower().strip()
        score = 0
        setting_phrases = [
            "is this a good time",
            "is this a good place",
            "before we begin",
            "before we start",
            "would you like anyone else here",
            "who would you like here",
            "are you comfortable",
            "thank you for coming in",
            "thank you for coming today",
        ]
        if self._contains_any_phrase(text_lower, setting_phrases):
            score += 2
        if re.search(r"^(hi|hello|good (morning|afternoon|evening))\b", text_lower):
            score += 1
        return min(score, 3)

    def _score_perception_clause(self, clause_text: str, has_elicitations: bool) -> int:
        text_lower = clause_text.lower()
        score = 0
        perception_phrases = [
            "what have you been told",
            "what's your understanding",
            "what is your understanding",
            "what have you noticed",
            "what do you think is happening",
            "what are you expecting",
            "what's your sense of this",
            "tell me what you know so far",
            "what have the doctors explained",
            "how are you making sense of this",
        ]
        if self._contains_any_phrase(text_lower, perception_phrases):
            score += 2
        if "?" in text_lower and re.search(r"\b(understanding|understand|sense|expect|think|know|noticed|told)\b", text_lower):
            score += 1
        if has_elicitations and re.search(r"\b(understand|sense|think|know|expect)\b", text_lower):
            score += 1
        return min(score, 3)

    def _score_invitation_clause(self, clause_text: str) -> int:
        text_lower = clause_text.lower()
        score = 0
        invitation_phrases = [
            "would you like me to explain",
            "do you want me to go over",
            "would it help if i explained",
            "how much detail would you like",
            "shall i go through",
            "are you okay if i explain",
            "would you prefer i give the details now",
            "would you like me to go over the results",
        ]
        if self._contains_any_phrase(text_lower, invitation_phrases):
            score += 2
        if "?" in text_lower and re.search(r"\b(would you like|do you want|shall i|are you okay if|would you prefer)\b", text_lower):
            score += 1
        return min(score, 3)

    def _score_knowledge_clause(self, clause_text: str) -> int:
        text_lower = clause_text.lower()
        score = 0
        strong_disclosure_phrases = [
            "the scan shows",
            "the results show",
            "the biopsy shows",
            "the biopsy confirms",
            "this means",
            "this tells us",
            "what this suggests is",
            "what this means is",
            "this is consistent with",
            "the diagnosis is",
            "the prognosis is",
            "it is cancer",
            "the illness has progressed",
            "treatment options are limited",
            "we are concerned that",
            "i'm concerned that",
            "i am concerned that",
            "i wish i had better news",
            "what we're seeing is",
            "what we are seeing is",
            # Uncertainty, testing, and timing (disclosure / explanation, not affect alone).
            "there are a few different things this could be",
            "there are a few things this could be",
            "we'll need more tests",
            "we will need more tests",
            "we need more tests",
            "the timing can depend on the specific tests",
            "results come back within",
            "within a few days",
            "about a week",
            "right now, we don't have the final answers",
            "right now, we do not have the final answers",
            "we don't have the final answers",
            "we do not have the final answers",
            "i don't want to give false reassurance",
            "i do not want to give false reassurance",
            "we need more information before we know",
            "more information before we know",
            "this suggests",
            "this could mean",
        ]
        matched_phrases = [p for p in sorted(strong_disclosure_phrases, key=len, reverse=True) if p in text_lower]
        # Drop shorter hits wholly contained in a longer matched phrase (substring inflation).
        pruned: List[str] = []
        for p in matched_phrases:
            if any(p != q and p in q for q in matched_phrases):
                continue
            pruned.append(p)
        if pruned:
            score += min(len(pruned) + 1, 3)
        if re.search(
            r"\b(results?|tests?|scan|biopsy|diagnosis|prognosis|treatment|cancer|progressed|illness|disease)\b",
            text_lower,
        ):
            score += 1
        if re.search(
            r"\b(shows|indicates|confirms|means|suggests|could be|could mean)\b", text_lower
        ):
            score += 1
        return min(score, 3)

    def _score_emotion_clause(self, clause_text: str, has_responses: bool) -> int:
        text_lower = clause_text.lower()
        score = 0
        emotion_phrases = [
            "i'm sorry",
            "i am sorry",
            "i know this is hard",
            "i know this is difficult",
            "i can see this feels overwhelming",
            "i can see how helpless this feels",
            "that must be difficult",
            "that sounds overwhelming",
            "i hear that",
            "i hear you",
        ]
        if self._contains_any_phrase(text_lower, emotion_phrases):
            score += 2
            # Aligns empathic response spans with explicit affect phrasing; weak tie-break only.
            if has_responses:
                score += 1
        elif not has_responses and re.search(
            r"\b(sorry|hard|difficult|overwhelming|scary|afraid|helpless|upsetting|worried)\b", text_lower
        ):
            # Light affect words without a full empathic phrase (only when not inflated by turn-global response flag).
            score += 1
        return min(score, 3)

    def _score_strategy_and_summary_clause(self, clause_text: str) -> int:
        text_lower = clause_text.lower()
        score = 0
        strategy_phrases = [
            "next steps",
            "from here",
            "what we can do now",
            "our plan",
            "our plan for now",
            "we can focus on",
            "moving forward",
            "to summarize",
            "in summary",
            "what matters most now",
            "given what's important to you",
            "we'll make sure",
            "we will make sure",
            "the plan going forward",
            "the best next step",
            "the next step is",
            "what i recommend now",
            "the focus now will be",
            "the focus is on",
            "otherwise the focus is",
            "our goal from here",
            "we will go through the results together",
            "we'll go through the results together",
            "go through the results together",
            "there isn't anything specific you need to do medically until we have the results",
            "there is not anything specific you need to do medically until we have the results",
            "anything specific you need to do medically until we have the results",
            "if anything changes",
            "important to let us know",
            "let us know",
            "waiting for more information",
        ]
        if self._contains_any_phrase(text_lower, strategy_phrases):
            score += 2
        if re.search(
            r"\b(for now|plan|next step|moving forward|summarize|summary|recommend|goal|focus)\b", text_lower
        ):
            score += 1
        # Defer monitoring / watchful waiting until data arrives (often split from "for now," by comma).
        if re.search(r"\buntil we (have|get) the results\b", text_lower):
            score += 1
        return min(score, 3)

