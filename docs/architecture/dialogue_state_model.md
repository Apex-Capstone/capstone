# APEX Dialogue State Model

## 1. Overview

The Dialogue State Model defines the structured variables the system maintains during a training session. These variables allow APEX to behave as a structured clinical training simulator rather than a stateless chatbot.

The dialogue state is maintained and updated by the **DialogueService** for every conversational turn. It captures the evolving context of the interaction, including protocol stage progression, patient emotional state, and detected learner behaviors.

The dialogue state supports four major system goals:

* structured dialogue progression using the SPIKES protocol
* empathy detection aligned with the Appraisal Framework for Clinical Empathy (AFCE)
* explainable feedback generation
* reproducible research export

Without an explicit dialogue state model, conversation behavior would be hidden inside prompts and difficult to validate.

---

# 2. Dialogue State Architecture

Each training session maintains a **DialogueState object** that represents the current conversational context.

```text
DialogueState
│
├─ session_state
├─ spikes_stage
├─ turn_history
├─ patient_state
├─ clinician_behavior_state
├─ empathy_event_state
└─ conversation_metadata
```

The DialogueState object is stored in memory during the session and persisted indirectly through the session and turn records in the database.

---

# 3. DialogueState Object Structure

## 3.1 Top Level State Object

Example representation:

```json
{
  "session_id": "session_abc123",
  "session_state": "active",
  "spikes_stage": "perception",
  "turn_count": 6,
  "patient_state": {},
  "clinician_behavior_state": {},
  "empathy_event_state": {},
  "conversation_metadata": {}
}
```

---

# 4. Session State Variables

## session_state

Tracks lifecycle status of the session.

Possible values

```
active
completed
```

Active sessions allow dialogue turns to be processed.
Completed sessions trigger scoring and become immutable research artifacts.

---

## turn_count

Tracks the number of conversational turns that have occurred in the session.

Used for:

* latency analysis
* pacing metrics
* research export

---

# 5. SPIKES Dialogue Stage Tracking

The SPIKES protocol structures difficult clinical conversations into six stages.

APEX explicitly tracks the current stage so that dialogue generation and feedback scoring remain aligned with the educational framework.

## Possible values

```
setting
perception
invitation
knowledge
empathy
strategy_summary
```

The stage is updated after each clinician turn using rule based cues detected by the NLU layer.

Example:

```json
"spikes_stage": "knowledge"
```

---

# 6. Patient State Model

The patient state represents the simulated patient's internal emotional and informational condition.

This state helps the system produce more realistic patient responses and supports future adaptive behavior.

Example structure:

```json
"patient_state": {
  "emotion": "anxious",
  "understanding_level": "partial",
  "cooperation_level": "neutral",
  "primary_concern": "treatment_failure"
}
```

---

## Patient Emotion

Represents the current emotional state of the patient.

Possible values

```
neutral
anxious
confused
distressed
angry
resigned
```

Emotion may evolve based on clinician communication quality.

Example rule

If empathy is detected, patient emotion may shift toward calm or cooperative.

---

## Patient Understanding Level

Tracks how well the patient understands their condition.

Possible values

```
none
partial
clear
```

This variable allows the patient simulator to ask clarification questions or express confusion.

---

## Cooperation Level

Represents how willing the patient is to engage with the clinician.

Possible values

```
cooperative
neutral
resistant
```

Poor communication or ignored empathic opportunities may reduce cooperation.

---

# 7. Clinician Behavior State

The clinician behavior state tracks observable communication patterns used for feedback evaluation.

Example structure

```json
"clinician_behavior_state": {
  "open_questions": 3,
  "closed_questions": 2,
  "empathic_responses": 1,
  "elicitation_attempts": 2,
  "support_statements": 1
}
```

These counts are updated by the NLU system for each turn.

---

## Open Question Count

Counts open ended questions asked by the clinician.

Example

"How are you feeling about this diagnosis?"

---

## Closed Question Count

Counts yes or no style questions.

Example

"Are you in pain?"

---

## Empathic Response Count

Counts responses acknowledging patient emotion.

Example

"I can see this is really overwhelming."

---

## Elicitation Attempts

Tracks attempts to explore patient emotion or concerns.

Example

"What worries you most about this?"

---

# 8. Empathy Event State

This component tracks **Empathic Opportunities (EOs)** and clinician responses to those opportunities.

The structure follows the AFCE framework.

Example

```json
"empathy_event_state": {
  "detected_EOs": 3,
  "responded_EOs": 2,
  "elicited_EOs": 1,
  "missed_EOs": 1
}
```

---

## Empathic Opportunity Detection

An EO occurs when the patient expresses emotional, evaluative, or experiential content.

Example

"I am scared about what this means."

---

## EO Response

Occurs when the clinician acknowledges the emotional content.

Example

"I can understand why that feels frightening."

---

## EO Elicitation

Occurs when the clinician invites deeper exploration.

Example

"Can you tell me more about what worries you?"

---

## Missed Opportunity

Occurs when the clinician ignores the emotional cue and changes topic.

Example

Patient

"I am really worried."

Clinician

"Let's talk about your medication."

---

# 9. Conversation Metadata

Metadata tracks contextual information about the conversation.

Example

```json
"conversation_metadata": {
  "case_id": "case_02",
  "start_time": "2026-03-10T15:02:11",
  "last_turn_time": "2026-03-10T15:07:32",
  "duration_seconds": 321
}
```

---

# 10. Dialogue State Update Process

For every clinician message, the DialogueService performs the following steps.

```
1. Receive clinician message
2. Run NLU analysis
3. Detect communication features
4. Update clinician behavior state
5. Update empathy event state
6. Update SPIKES stage if needed
7. Update patient emotional state
8. Store updated state
9. Generate patient response
```

This ensures the dialogue state remains synchronized with conversation behavior.

---

# 11. Why Explicit Dialogue State Matters

Explicit dialogue state enables several key capabilities.

## Educational transparency

Feedback is derived from structured interaction events rather than hidden model reasoning.

## Consistent dialogue behavior

Patient responses remain grounded in protocol context rather than random generation.

## Research reproducibility

Interaction traces can be exported and analyzed across sessions.

## Future extensibility

Additional variables such as trust level, uncertainty, or empathy intensity can be added without redesigning the system.

---

# 12. Relationship to System Components

The DialogueState object interacts with several system components.

| Component       | Role                                            |
| --------------- | ----------------------------------------------- |
| DialogueService | Maintains and updates dialogue state            |
| SimpleRuleNLU   | Detects communication features                  |
| StageTracker    | Updates SPIKES stage                            |
| LLM Adapter     | Generates patient responses using current state |
| ScoringService  | Evaluates conversation using stored state       |

---

# 13. Future Extensions

Future versions of the system may extend the dialogue state with additional variables.

Possible extensions

* patient trust level
* unresolved emotional concerns
* clinician communication style profile
* uncertainty indicators
* adaptive patient personality traits

These additions would support more advanced simulation behavior.

---

# 14. Summary

The Dialogue State Model provides the structured context required for APEX to function as a clinical training simulator rather than a generic conversational agent.

By explicitly tracking protocol stage, empathy events, patient emotion, and clinician communication patterns, the system can generate realistic dialogue while producing explainable educational feedback and structured research data.