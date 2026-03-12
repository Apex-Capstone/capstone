# APEX Dialogue Turn Processing Specification

## 1. Overview

This document specifies how APEX processes a single conversational turn during an active training session.

The goal of this processing pipeline is to ensure that every learner message is handled in a structured, reproducible, and educationally meaningful way. The turn pipeline combines:

* rule based NLU
* dialogue state updates
* SPIKES stage tracking
* LLM based patient response generation
* persistence of structured annotations
* post-session evaluability

This design supports the hybrid architecture adopted by APEX, where the backend controls state and analysis while the LLM is used primarily for patient response generation.

---

# 2. Turn Processing Goals

The turn processing pipeline must achieve the following goals:

## 2.1 Maintain structured dialogue flow

The system must interpret the learner turn in the context of the existing session and update the conversation state appropriately.

## 2.2 Extract educationally relevant communication signals

The system must identify features needed for feedback and evaluation, such as empathy cues, elicitation attempts, and question type.

## 2.3 Preserve explainability

Each turn must be stored with the annotations and metadata required for later scoring and research export.

## 2.4 Generate realistic patient responses

The LLM must receive enough structured context to produce a coherent and case-grounded patient response.

---

# 3. High-Level Turn Pipeline

The high-level sequence for processing one learner turn is:

```text id="abrjqt"
Learner message
→ Session lookup
→ NLU analysis
→ Dialogue state update
→ Clinician turn persistence
→ LLM patient generation
→ Patient turn analysis
→ Patient turn persistence
→ Return structured response
```

---

# 4. Inputs to Turn Processing

Each turn processing request requires the following inputs:

## 4.1 Required Inputs

* `session_id`
* learner text
* authenticated user identity

## 4.2 Session Context Inputs

The system loads the following state from storage:

* case ID
* current session state
* current SPIKES stage
* prior turns
* prior dialogue annotations
* case metadata and patient persona

---

# 5. Outputs of Turn Processing

The turn processing pipeline returns:

* patient response text
* updated SPIKES stage
* assistant turn metadata
* persisted turn records
* optional audio output path if speech mode is enabled

Example response shape:

```json id="e6h0pp"
{
  "patient_reply": "I don't know how to deal with this.",
  "spikes_stage": "empathy",
  "turn_id": "turn_102",
  "session_id": "session_abc123"
}
```

---

# 6. Detailed Turn Processing Steps

## Step 1: Validate Session Access

The controller verifies that:

* the session exists
* the requesting user has access
* the session is still active

If the session is closed, no further turns may be processed.

Example failure conditions:

* invalid session ID
* unauthorized access
* completed session

---

## Step 2: Load Session and Case Context

The backend loads:

* session object
* case object
* current SPIKES stage
* existing turn history

This context is required to interpret the learner message as part of an evolving dialogue rather than as an isolated statement.

Example retrieved context:

```json id="71o7zq"
{
  "session_state": "active",
  "spikes_stage": "knowledge",
  "case_id": "case_02",
  "turn_count": 7
}
```

---

## Step 3: Run NLU Analysis on Learner Turn

The learner message is passed through the NLU subsystem.

The current NLU pipeline includes:

* empathy cue detection
* question type classification
* tone analysis
* elicitation span detection
* empathic response span detection
* SPIKES cue detection

Example learner message:

> I can see this is overwhelming. Can you tell me what worries you most right now?

Example extracted features:

```json id="h4rn1d"
{
  "question_type": "open",
  "tone": "supportive",
  "empathy_detected": true,
  "elicitation_detected": true,
  "response_detected": true
}
```

---

## Step 4: Generate Structured Span Annotations

The SpanDetector identifies structured AFCE related spans.

Supported span categories include:

* `eo`
* `elicitation`
* `response`

Example output:

```json id="5u4wsx"
[
  {
    "span_type": "response",
    "dimension": "feeling",
    "text": "I can see this is overwhelming",
    "start_char": 0,
    "end_char": 31,
    "confidence": 0.88
  },
  {
    "span_type": "elicitation",
    "dimension": "feeling",
    "text": "what worries you most right now",
    "start_char": 47,
    "end_char": 79,
    "confidence": 0.91
  }
]
```

These spans are stored for later scoring.

---

## Step 5: Update Dialogue State

The DialogueService updates the session’s internal dialogue state using the extracted NLU signals.

State updates include:

* clinician behavior counts
* empathy event counts
* SPIKES stage update
* patient interaction context

Example updates:

```json id="ckf3ol"
{
  "open_questions": 4,
  "elicitation_attempts": 2,
  "empathic_responses": 3,
  "spikes_stage": "empathy"
}
```

This step ensures the next patient response is grounded in structured context.

---

## Step 6: Determine SPIKES Stage

The system evaluates whether the learner message implies a transition in SPIKES stage.

Possible stages:

```text id="1lrlni"
setting
perception
invitation
knowledge
empathy
strategy_summary
```

The stage may remain unchanged or progress depending on the current stage and detected cues.

Example rules:

* greetings and orientation suggest `setting`
* asking what the patient understands suggests `perception`
* asking permission to explain suggests `invitation`
* diagnostic disclosure suggests `knowledge`
* validating emotion suggests `empathy`
* discussing next steps suggests `strategy_summary`

---

## Step 7: Persist Clinician Turn

The clinician turn is written to storage with:

* text
* role
* timestamp
* spikes stage
* metrics JSON
* spans JSON

Example persisted turn:

```json id="o3o4rl"
{
  "role": "user",
  "text": "Can you tell me what worries you most right now?",
  "spikes_stage": "empathy",
  "metrics_json": {
    "question_type": "open",
    "tone": "supportive"
  },
  "spans_json": [...]
}
```

This ensures the scoring engine can reconstruct the interaction later.

---

## Step 8: Build LLM Prompt Context

The backend prepares the context for patient generation.

This includes:

* patient persona and case background
* prior conversation history
* current SPIKES stage
* current patient state
* relevant recent learner behavior

Example prompt inputs:

```json id="q3ugip"
{
  "patient_background": "54 year old patient awaiting scan results",
  "spikes_stage": "empathy",
  "conversation_history": [...],
  "patient_emotion": "anxious"
}
```

The backend controls the prompt inputs so that the LLM remains guided by system state.

---

## Step 9: Generate Patient Response

The selected LLM adapter generates the next patient utterance.

Current adapters may include:

* OpenAIAdapter
* GeminiAdapter

The response should be:

* role consistent
* grounded in the case
* consistent with prior dialogue
* aligned with current emotional context

Example generated response:

> I'm scared that this means my treatment is not working.

---

## Step 10: Analyze Patient Response for Empathy Opportunities

After generating the patient turn, the backend runs a second NLU pass on the patient utterance.

The goal is to detect:

* empathy opportunities
* AFCE emotional dimensions
* explicit vs implicit cues

Example output:

```json id="w5nshu"
{
  "eo_detected": true,
  "dimension": "feeling",
  "explicit_or_implicit": "explicit",
  "text": "I'm scared"
}
```

This analysis is essential because future feedback depends on patient emotional cues.

---

## Step 11: Persist Patient Turn

The patient turn is stored with:

* generated text
* timestamp
* session ID
* stage
* EO related metrics
* EO spans

Example:

```json id="y1qo8e"
{
  "role": "assistant",
  "text": "I'm scared that this means my treatment is not working.",
  "spikes_stage": "empathy",
  "metrics_json": {
    "eo_detected": true
  },
  "spans_json": [...]
}
```

---

## Step 12: Return Response to Frontend

The backend returns the structured assistant turn to the frontend.

The frontend displays:

* patient reply
* updated stage
* session progress information

If audio mode is enabled, the backend may also return a TTS output path.

---

# 7. Turn Processing Pseudocode

The following pseudocode shows the intended system behavior.

```python
def process_turn(session_id: str, learner_text: str) -> TurnResponse:
    session = load_session(session_id)
    assert session.state == "active"

    case = load_case(session.case_id)
    history = load_turn_history(session_id)

    learner_metrics = nlu.analyze_user_input(learner_text)
    learner_spans = span_detector.detect_clinician_spans(learner_text)

    update_dialogue_state(session, learner_metrics, learner_spans)

    current_stage = detect_spikes_stage(
        learner_text,
        session.current_spikes_stage,
        learner_spans
    )

    clinician_turn = save_turn(
        role="user",
        text=learner_text,
        stage=current_stage,
        metrics=learner_metrics,
        spans=learner_spans
    )

    llm_context = build_llm_context(
        case=case,
        history=history,
        stage=current_stage,
        state=session.dialogue_state
    )

    patient_text = llm_adapter.generate_patient_response(llm_context)

    patient_metrics = nlu.analyze_patient_output(patient_text)
    patient_spans = span_detector.detect_patient_spans(patient_text)

    assistant_turn = save_turn(
        role="assistant",
        text=patient_text,
        stage=current_stage,
        metrics=patient_metrics,
        spans=patient_spans
    )

    return build_turn_response(assistant_turn, current_stage)
```

---

# 8. Relationship to Dialogue State Model

The turn processing pipeline directly updates the DialogueState object.

This relationship is shown below.

```text id="y0kc6r"
Learner message
→ NLU
→ DialogueState update
→ LLM prompt context
→ Patient response
→ New EO detection
→ DialogueState update
```

The DialogueState model therefore acts as the structured memory of the conversation.

---

# 9. Relationship to Feedback Scoring

Turn processing is designed so that post-session feedback can be computed reliably.

Stored turn artifacts support:

* EO detection
* EO-response linking
* EO-elicitation linking
* question ratio calculation
* SPIKES stage coverage
* missed opportunity detection

If the turn processing pipeline fails to store structured spans and metrics, the feedback engine cannot perform valid scoring.

---

# 10. Error Handling and Undesired Behaviors

The turn pipeline must guard against several failure conditions.

## 10.1 Session Errors

* closed session still accepting turns
* unauthorized access
* missing session record

## 10.2 NLU Errors

* malformed span output
* incorrect confidence values
* false positives from keyword heuristics

## 10.3 LLM Errors

* empty output
* unsafe response content
* excessively long response
* response inconsistent with case

## 10.4 Persistence Errors

* clinician turn saved but assistant turn fails
* partial write during turn processing
* stage not synchronized with stored turn

These risks should be tested in V&V.

---

# 11. Design Rationale

The turn processing pipeline is designed as a backend controlled workflow rather than a direct prompt-response chain.

Reasons:

## Explainability

The system can show why a score was assigned.

## Modularity

NLU, LLM generation, and scoring remain separate components.

## Reliability

Turn storage and state tracking are system controlled.

## Research usefulness

Each turn can be exported with structured metadata.

This design is more defensible than using a single LLM prompt for the full interaction.

---

# 12. Future Extensions

Future versions of turn processing may add:

* dialogue act classification
* patient emotional trajectory updates
* live safety filtering
* real time micro-feedback
* multimodal ASR and TTS integration
* adaptive response modulation based on learner quality

These can be added without replacing the existing hybrid structure.

---

# 13. Summary

The APEX turn processing pipeline is the operational core of the dialogue system.

Each learner message is:

* interpreted through rule based NLU
* mapped into structured spans and metrics
* used to update dialogue state
* passed into the LLM through controlled context
* stored for later scoring and export

This architecture supports realistic patient simulation while preserving the structured signals required for educational feedback, validation, and research analysis.