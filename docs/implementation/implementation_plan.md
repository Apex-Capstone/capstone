# APEX Implementation Plan

## 1. Overview

This document defines the implementation roadmap for the APEX system based on the finalized architecture.

The implementation plan converts the architectural specifications into concrete development tasks. It identifies the components that must be built or refined, the order of implementation, and how each subsystem connects to the architecture.

The development process follows three guiding principles:

* architectural traceability
* modular implementation
* incremental validation

The system will be implemented according to the following subsystem order:

```text
Dialogue State Model
→ NLU Modules
→ Dialogue Service
→ LLM Adapter
→ Turn Processing Pipeline
→ Scoring Engine
→ API Integration
→ Frontend Integration
→ Research Export
```

Each stage produces a working subsystem that can be tested independently.

---

# 2. Backend Architecture Overview

The backend codebase will follow a layered structure.

```text
backend/
│
├─ controllers/
│
├─ services/
│   ├─ dialogue_service.py
│   ├─ scoring_service.py
│   ├─ session_service.py
│   └─ case_service.py
│
├─ nlu/
│   ├─ simple_rule_nlu.py
│   └─ span_detector.py
│
├─ dialogue/
│   ├─ dialogue_state.py
│   └─ stage_tracker.py
│
├─ adapters/
│   ├─ llm_adapter.py
│   ├─ openai_adapter.py
│   └─ gemini_adapter.py
│
├─ repositories/
│   ├─ session_repository.py
│   ├─ turn_repository.py
│   ├─ case_repository.py
│   └─ feedback_repository.py
│
└─ models/
    ├─ session.py
    ├─ turn.py
    └─ feedback.py
```

This structure matches the architecture defined in the system design document.

---

# 3. Implementation Phases

## Phase 1: Dialogue State Implementation

The first step is implementing the DialogueState object described in the architecture.

File:

```text
backend/dialogue/dialogue_state.py
```

Responsibilities:

* track SPIKES stage
* track clinician behavior counts
* track empathy events
* track patient state

Example structure:

```python
class DialogueState:
    def __init__(self):
        self.spikes_stage = "setting"

        self.clinician_behavior = {
            "open_questions": 0,
            "closed_questions": 0,
            "empathic_responses": 0,
            "elicitation_attempts": 0
        }

        self.empathy_events = {
            "detected_eo": 0,
            "responded_eo": 0,
            "elicited_eo": 0,
            "missed_eo": 0
        }

        self.patient_state = {
            "emotion": "neutral",
            "cooperation_level": "neutral"
        }
```

This state object will be updated during every turn.

---

# 4. Phase 2: NLU Modules

The next step is implementing the NLU components.

Directory:

```
backend/nlu/
```

Modules:

```
simple_rule_nlu.py
span_detector.py
```

Responsibilities:

### simple_rule_nlu

Detects high level features:

* open vs closed question
* tone classification
* empathy keywords
* elicitation patterns

Example:

```python
def detect_open_question(text: str) -> bool:
    patterns = [
        "how",
        "what",
        "tell me",
        "can you describe"
    ]
```

---

### span_detector

Extracts AFCE spans.

Supported span types:

* empathy response
* elicitation
* empathic opportunity

Example span output:

```python
{
    "span_type": "response",
    "dimension": "feeling",
    "text": "I can see this is difficult",
    "confidence": 0.87
}
```

These spans will later support scoring.

---

# 5. Phase 3: SPIKES Stage Tracker

File:

```
backend/dialogue/stage_tracker.py
```

This module determines stage transitions.

Possible stages:

```
setting
perception
invitation
knowledge
empathy
strategy_summary
```

Example rule:

```python
if detect_empathy_phrase(text):
    stage = "empathy"
```

The stage tracker must consider:

* previous stage
* detected cues
* conversation context

---

# 6. Phase 4: Dialogue Service

File:

```
backend/services/dialogue_service.py
```

This service orchestrates the turn pipeline.

Responsibilities:

* run NLU
* update dialogue state
* determine SPIKES stage
* store clinician turn
* call LLM adapter
* store patient turn
* return structured response

Core method:

```python
process_turn(session_id, learner_text)
```

---

# 7. Phase 5: LLM Adapter Layer

Directory:

```
backend/adapters/
```

Files:

```
llm_adapter.py
openai_adapter.py
gemini_adapter.py
```

The adapter interface standardizes generation.

Example interface:

```python
class LLMAdapter:

    def generate_patient_response(self, context):
        raise NotImplementedError
```

Adapters implement this interface for each provider.

---

# 8. Phase 6: Turn Persistence

The repository layer stores conversation turns.

File:

```
backend/repositories/turn_repository.py
```

Stored attributes:

* role
* text
* timestamp
* spikes stage
* metrics json
* spans json

Example schema:

```python
Turn(
    session_id,
    role,
    text,
    stage,
    metrics_json,
    spans_json
)
```

---

# 9. Phase 7: Scoring Engine

File:

```
backend/services/scoring_service.py
```

Scoring runs when a session closes.

Responsibilities:

* EO detection
* EO response linking
* EO elicitation linking
* missed opportunity detection
* SPIKES coverage scoring
* communication behavior metrics

Example output:

```python
Feedback(
    empathy_score=82,
    spikes_score=90,
    communication_score=85
)
```

---

# 10. Phase 8: API Integration

Controllers expose the services to the frontend.

Directory:

```
backend/controllers/
```

Key endpoints:

```
POST /sessions
POST /sessions/{id}/turn
POST /sessions/{id}/close
GET /sessions/{id}/feedback
```

---

# 11. Phase 9: Research Export

Research endpoints expose anonymized session data.

Supported exports:

* session CSV
* transcript CSV
* metrics CSV

Files:

```
backend/controllers/research_controller.py
```

---

# 12. Phase 10: Frontend Integration

Frontend will consume the backend endpoints.

Main UI features:

* session creation
* chat interface
* session completion
* feedback visualization
* research dashboard

---

# 13. Development Workflow

The development workflow will follow a structured branch strategy.

Example workflow:

```text
main
↑
staging
↑
feature/dialogue-state
feature/nlu
feature/dialogue-service
feature/scoring
```

Each feature branch should implement one subsystem.

---

# 14. Validation Strategy

Each subsystem should be validated independently.

Testing categories:

## Unit Tests

* NLU detection
* stage tracker logic
* scoring calculations

## Integration Tests

* full turn pipeline
* session lifecycle

## End-to-End Tests

* simulated training session
* scoring generation
* research export

---

# 15. Implementation Milestones

Target sequence:

```
Week 1
Dialogue state + NLU modules

Week 2
Dialogue service + LLM adapter

Week 3
Turn persistence + scoring engine

Week 4
API integration + frontend + research export
```

This sequence ensures the dialogue system works before expanding additional features.

---

# 16. Summary

The APEX implementation plan transforms the architectural design into a structured development roadmap.

The system will be implemented incrementally starting from the dialogue state and NLU layers, followed by dialogue orchestration, LLM integration, scoring, and frontend interaction.

This approach ensures that each subsystem can be validated independently while maintaining architectural alignment with the system design.