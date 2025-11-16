<!-- 98e54224-5dab-45b7-a183-f3cab35e1d89 5488c7e8-6b3f-411e-83b0-1d57e82425a1 -->
# AFCE-SPIKES NLU Alignment Implementation

Transform the NLU system from simple keyword matching to comprehensive AFCE-aligned span-based detection.

**This plan is split into two parts:**

- **Part 1 (Phases 1-2)**: Foundation with rule-based AFCE detection and span extraction
- **Part 2 (Phases 3-5, deferred)**: ML sentiment, LLM fallback, hybrid routing, relation linking, and content-based SPIKES detection

---

## PART 1: Foundation (Phases 1-2)

### Phase 1: AFCE Taxonomy and Data Models

#### 1.1 Update NLU Protocol (`backend/src/adapters/nlu/base.py`)

- Add AFCE dimension types: `Feeling`, `Judgment`, `Appreciation`
- Add explicit/implicit variants: `explicit`, `implicit`
- Add elicitation types: `direct`, `indirect` with dimension mapping
- Update response types: restrict to `Understanding`, `Sharing`, `Acceptance` (remove `Interpretation`, `Validation`)
- Add provenance types: `rule`, `ml`, `llm` (for future phases)
- Add span structure: `start_char`, `end_char`, `text`, `dimension`, `explicit_or_implicit`, `confidence` (0-1), `provenance`
- Add relation types: `elicits`, `responds_to`, `missed` (for future phases)
- Add methods returning spans:
- `detect_eo_spans(text)` → List[EOSpan]
- `detect_elicitation_spans(text)` → List[ElicitationSpan]
- `detect_response_spans(text)` → List[ResponseSpan]
- Note: `classify_spikes_stage()` will be added in Part 2

#### 1.2 Create Span Models (`backend/src/domain/entities/spans.py`)

- `EmpathyOpportunitySpan`: dimension (Feeling/Judgment/Appreciation), explicit_or_implicit, start_char, end_char, text, confidence, provenance
- `ElicitationSpan`: type (direct/indirect), dimension, start_char, end_char, text, confidence, provenance
- `ResponseSpan`: type (understanding/sharing/acceptance), start_char, end_char, text, confidence, provenance
- `SPIKESStageSpan`: stage, start_char, end_char, text, confidence, provenance (for future use)
- `Relation`: source_span_id, target_span_id, relation_type (elicits/responds_to/missed), confidence (for future use)

#### 1.3 Update Turn Entity (`backend/src/domain/entities/turn.py`)

- Add `spans_json` column (Text/JSON): store all detected spans with offsets
- Add `relations_json` column (Text/JSON): store span-relation links (nullable, will be populated in Part 2)
- Keep `metrics_json` for backward compatibility (populate from spans during transition)
- Keep `spikes_stage` (continue using turn-count-based staging for now; content-based detection in Part 2)

#### 1.4 Update Feedback Entity (`backend/src/domain/entities/feedback.py`)

- Remove/stop computing: `communication_score`, `interruptions`, `reflections_interpretations`, `prohibited_behaviors`, `deescalation_strategies`
- Add AFCE-structured metrics: `eo_counts_by_dimension`, `elicitation_counts_by_type`, `response_counts_by_type`
- Add relation metrics placeholders (will be computed in Part 2): `eo_to_elicitation_links`, `eo_to_response_links`, `missed_opportunities_by_dimension`
- Keep existing SPIKES coverage (will update to exclude "Setting" stage in Part 2)
- Keep: `tone_summary` (metadata, separate from AFCE), `bias_probe_info`, `evaluator_meta`, `latency_ms_avg`

#### 1.5 Create Database Migration (`backend/src/db/migrations/versions/add_afce_spans.py`)

- Add `spans_json` column to `turns` table (Text, nullable)
- Add `relations_json` column to `turns` table (Text, nullable)
- Update feedback table structure:
- Remove deprecated metric columns OR leave nullable and stop computing them
- Add AFCE-structured metric columns (JSON/Text)
- Migrate existing data: populate spans_json from metrics_json where possible

#### 1.6 Update Feedback Models (`backend/src/domain/models/sessions.py`)

- Update `FeedbackResponse` to include AFCE-structured data:
- `eo_spans`: list of EO spans with dimensions (for turn-level analysis)
- `elicitation_spans`: list of elicitation spans with types
- `response_spans`: list of response spans with types
- Add session-level metrics:
- `eo_counts_by_dimension`: count by dimension (Feeling/Judgment/Appreciation) and explicit/implicit
- `elicitation_counts_by_type`: count by type (direct/indirect) and dimension
- `response_counts_by_type`: count by type (understanding/sharing/acceptance)
- Add placeholders for Part 2:
- `relations`: list of span relations (will be populated in Part 2)
- `linkage_stats`: EO-to-elicitation, EO-to-response rates (will be computed in Part 2)
- `missed_opportunities_by_dimension`: missed EOs by dimension (will be computed in Part 2)
- Keep: `tone_summary`, `question_breakdown`, `spikes_coverage`, `bias_probe_info`, `evaluator_meta`, `latency_ms_avg`

### Phase 2: Rule-Based AFCE Detection with Spans

#### 2.1 Expand Rule-Based NLU (`backend/src/adapters/nlu/simple_rule_nlu.py`)

- Expand EO keywords by AFCE dimension:
- **Feeling/Explicit**: scared, afraid, worried, anxious, terrified, sad, upset, devastated, depressed, hopeless, angry, furious, frustrated, mad, annoyed, confused, overwhelmed, shocked, stunned, pain, hurting, ache, suffering, don't know what to do, can't handle, too much
- **Feeling/Implicit**: i guess, maybe, sort of, kind of, not sure, wondering, thinking about, concerned, a bit, somewhat, difficult, hard, challenging, tough
- **Judgment/Explicit**: wrong, bad, unfair, unjust, terrible, awful, horrible, shouldn't have, should have, fault, blame
- **Judgment/Implicit**: difficult, challenging, tough, problematic, concerning, questionable
- **Appreciation/Explicit**: important, meaningful, valuable, significant, matters, precious, cherished, meaningful to me
- **Appreciation/Implicit**: matters, significant, relevant, counts, worth it
- Add elicitation keywords with dimension mapping:
- **Direct/Feeling**: "how do you feel", "what emotions", "tell me about your feelings", "what are you feeling"
- **Indirect/Feeling**: "it sounds like you're feeling", "you seem", "it seems like you feel"
- **Direct/Judgment**: "what do you think about", "how do you see this", "what's your opinion"
- **Indirect/Judgment**: "it seems like you think", "you're saying", "it sounds like you believe", "if i understand correctly"
- **Direct/Appreciation**: "what matters to you", "what's important", "what do you value"
- **Indirect/Appreciation**: "it sounds like this is important", "it seems like this matters", "you're saying this is meaningful"
- Update response keywords (AFCE taxonomy):
- **Understanding**: "i understand", "i see", "i get it", "i hear you", "that makes sense", "i can see why", "i follow you"
- **Sharing**: "i feel the same", "i understand how", "that resonates", "i can relate", "i've felt that way", "that's how i feel too"
- **Acceptance**: "that's valid", "that's understandable", "that makes sense", "that's reasonable", "anyone would feel", "that's normal"
- Move "interpretation" patterns to indirect elicitations (e.g., "it sounds like", "you're saying")
- Remove validation keywords from responses (move to understanding/acceptance if needed)

#### 2.2 Implement Span Detection (`backend/src/adapters/nlu/span_detector.py`)

- `detect_eo_spans(text)`: returns List[EmpathyOpportunitySpan] with character offsets, dimension, explicit_or_implicit, confidence (0.7-0.9 based on keyword strength), provenance='rule'
- `detect_elicitation_spans(text)`: returns List[ElicitationSpan] with type (direct/indirect), dimension, offsets, confidence (0.7-0.9), provenance='rule'
- `detect_response_spans(text)`: returns List[ResponseSpan] with type (understanding/sharing/acceptance), offsets, confidence (0.7-0.9), provenance='rule'
- Use regex + keyword matching for offset detection: `re.search()` with case-insensitive matching
- Handle overlapping spans: prioritize by confidence, merge if same type
- Extract exact text substring for each span using offsets
- Return spans sorted by start_char position

#### 2.3 Update SimpleRuleNLU Methods

- Update `detect_empathy_opportunity()` to call `span_detector.detect_eo_spans()` and return span list with dimension and explicit/implicit
- Update `classify_empathy_response_type()` to call `span_detector.detect_response_spans()` and return span list with type (understanding/sharing/acceptance)
- Add `detect_elicitation_spans()` method that calls `span_detector.detect_elicitation_spans()`
- All methods return spans with confidence (0.7-0.9) and provenance='rule'
- Maintain backward compatibility: also populate old-style metrics for `metrics_json` during transition

#### 2.4 Integrate Spans into Dialogue Service (`backend/src/services/dialogue_service.py`)

- Update `_analyze_user_input()`:
- Call `nlu_adapter.detect_elicitation_spans()` for elicitation detection
- Call `nlu_adapter.detect_response_spans()` for response detection
- Combine spans into spans_json format
- Store spans in `turn.spans_json` as JSON list
- Populate `metrics_json` from spans for backward compatibility
- Update `_analyze_assistant_response()`:
- Call `nlu_adapter.detect_eo_spans()` for EO detection
- Store EO spans in `turn.spans_json` as JSON list
- Populate `metrics_json` from spans for backward compatibility
- Keep existing `_update_spikes_stage()` (turn-count-based for now; will be replaced in Part 2)
- Note: Relation linking will be added in Part 2

#### 2.5 Update Scoring Service (`backend/src/services/scoring_service.py`)

- Update `generate_feedback()` to use span-based metrics:
- Extract spans from `turn.spans_json` for all turns in session
- `eo_counts_by_dimension`: count by dimension (Feeling/Judgment/Appreciation) and explicit/implicit from EO spans
- `elicitation_counts_by_type`: count by type (direct/indirect) and dimension from elicitation spans
- `response_counts_by_type`: count by type (understanding/sharing/acceptance) from response spans
- Remove/stop computing deprecated metrics:
- `communication_score`, `interruptions`, `reflections_interpretations`, `prohibited_behaviors`, `deescalation_strategies`
- Keep existing SPIKES metrics (will be updated in Part 2):
- Continue using `turn.spikes_stage` for SPIKES coverage (turn-count-based)
- Keep tone_summary as metadata (separate from AFCE scoring)
- Calculate composite `empathy_score` from AFCE metrics (weighted by dimension and explicit/implicit)
- Note: `linkage_stats` and `missed_opportunities` will be computed in Part 2 when relation linking is implemented

---

## PART 2: Advanced Features (Phases 3-5, Deferred)

*These phases will be implemented after Part 1 is complete.*

### Phase 3: ML Sentiment Integration

- Add ML dependencies (vaderSentiment, textblob, nltk)
- Create ML sentiment adapter for implicit Feeling EO detection
- Add settings configuration for ML thresholds
- Integrate ML sentiment as fallback when rule confidence < 0.7

### Phase 4: LLM Fallback and Hybrid Routing

- Create LLM classifier for AFCE taxonomy (EO dimensions, elicitation types, response types)
- Update LLM adapter with AFCE classification methods
- Create hybrid NLU router (rules → ML → LLM)
- Add budget-aware routing with LLM call limits
- Integrate hybrid routing into dialogue service

### Phase 5: Span-Relation Linking and Content-Based SPIKES Detection

- Implement relation linker for cross-turn span linking
- Implement content-based SPIKES stage detection
- Update dialogue service for relation linking and content-based SPIKES staging
- Update scoring service with relation-based metrics (linkage_stats, missed_opportunities)
- Compute SPIKES coverage excluding "Setting" stage

---

## Implementation Details (Part 1)

### Key Files to Create (Part 1)

1. `backend/src/domain/entities/spans.py` - Span models
2. `backend/src/adapters/nlu/span_detector.py` - Span detection logic

### Key Files to Modify (Part 1)

1. `backend/src/adapters/nlu/base.py` - Update protocol with span methods
2. `backend/src/adapters/nlu/simple_rule_nlu.py` - Expand keywords, add span detection methods
3. `backend/src/services/dialogue_service.py` - Integrate span detection and storage
4. `backend/src/services/scoring_service.py` - Use span-based metrics, remove deprecated metrics
5. `backend/src/domain/entities/turn.py` - Add spans_json, relations_json columns
6. `backend/src/domain/entities/feedback.py` - Update feedback structure
7. `backend/src/domain/models/sessions.py` - Update response models
8. `backend/src/db/migrations/versions/add_afce_spans.py` - Database migration

### Key Files to Create (Part 2 - Future)

3. `backend/src/adapters/nlu/hybrid_nlu.py` - Hybrid routing
4. `backend/src/adapters/ml/sentiment_adapter.py` - ML sentiment (VADER/TextBlob)
5. `backend/src/adapters/llm/afce_classifier.py` - LLM classifiers
6. `backend/src/services/relation_linker.py` - Span linking
7. `backend/src/adapters/nlu/spikes_classifier.py` - SPIKES detection

### Key Decisions (Part 1)

- Use rule-based detection only (provenance='rule')
- Store spans with character offsets for explainability and future UI highlighting
- Separate tone analysis from AFCE constructs (metadata only)
- Continue using turn-count-based SPIKES staging (content-based in Part 2)
- Remove deprecated metrics: communication_score, interruptions, reflections_interpretations, prohibited_behaviors, deescalation_strategies
- Keep `metrics_json` populated from spans for backward compatibility during transition

### Key Decisions (Part 2 - Future)

- Use `vaderSentiment` and `textblob` for ML sentiment (lightweight, no GPU needed)
- Implement hybrid routing: rules (conf≥0.8) → ML (conf<0.8, implicit Feeling only) → LLM (conf<0.8 or conflicts)
- Allow multi-stage SPIKES turns (primary in spikes_stage, secondary in spans_json)
- Compute SPIKES coverage excluding Setting stage (Perception → Strategy/Summary)
- Cap LLM calls at 5 per session (configurable)
- Context window N=2 clinician turns for span linking (configurable)

### Performance Considerations

- Use lightweight rule-based detection (no ML/LLM overhead in Part 1)
- Limit text length for span detection (max 2000 chars per turn)
- Use async/await for all I/O operations
- Optimize regex patterns for span detection
- Monitor latency and optimize hot paths (span detection should be fast)

### Testing Notes

- Unit tests for span detection accuracy
- Integration tests for span storage and retrieval
- Test backward compatibility with existing metrics_json
- Test AFCE taxonomy alignment (keywords match dimensions correctly)