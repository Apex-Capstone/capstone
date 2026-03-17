# APEX Repository Structure

## Overview

This document describes the repository organization for the APEX system.

The repository follows a layered architecture separating:

- API controllers
- dialogue orchestration
- NLU modules
- LLM adapters
- persistence
- scoring and feedback
- frontend interface

This structure ensures the system remains modular and extensible.

---

# High-Level Repository Layout

```

repo/
│
├─ backend/
│
│  ├─ controllers/
│  │
│  │  session_controller.py
│  │  research_controller.py
│  │
│  ├─ services/
│  │
│  │  dialogue_service.py
│  │  scoring_service.py
│  │  session_service.py
│  │
│  ├─ dialogue/
│  │
│  │  dialogue_state.py
│  │  stage_tracker.py
│  │
│  ├─ nlu/
│  │
│  │  simple_rule_nlu.py
│  │  span_detector.py
│  │
│  ├─ adapters/
│  │
│  │  llm_adapter.py
│  │  openai_adapter.py
│  │  gemini_adapter.py
│  │
│  ├─ repositories/
│  │
│  │  session_repository.py
│  │  turn_repository.py
│  │  feedback_repository.py
│  │
│  ├─ models/
│  │
│  │  session.py
│  │  turn.py
│  │  feedback.py
│  │
│  └─ main.py
│
├─ frontend/
│
├─ docs/
│
│  ├─ architecture/
│  ├─ research/
│  ├─ implementation/
│  └─ design-decisions/
│
└─ README.md

```

---

# Key Architectural Layers

## Controllers

Controllers expose the REST API used by the frontend.

Example endpoints:

```

POST /sessions
POST /sessions/{id}/turn
POST /sessions/{id}/close
GET /sessions/{id}/feedback

```

Controllers should remain thin and delegate logic to services.

---

## Services

Services contain the main application logic.

Key services include:

- DialogueService
- ScoringService
- SessionService

These services coordinate the lower-level modules.

---

## Dialogue Layer

The dialogue layer manages conversation state and stage progression.

Components:

- DialogueState
- SPIKES stage tracker

These objects track structured dialogue information during a session.

---

## NLU Layer

The NLU layer extracts communication signals from dialogue turns.

Modules include:

- rule-based feature detection
- empathy span detection
- elicitation detection

These outputs feed both dialogue state updates and the scoring engine.

---

## Adapter Layer

The adapter layer abstracts LLM providers.

Adapters implement a shared interface:

```

generate_patient_response(context)

```

This allows the system to support multiple providers.

---

## Repository Layer

Repositories manage persistence.

They handle database reads and writes for:

- sessions
- conversation turns
- feedback reports

This layer isolates database logic from services.

---

## Models

Models define the data structures stored in the system.

Examples:

- Session
- Turn
- Feedback

These correspond to database tables or ORM objects.

---

# Versioning Strategy

The repository currently contains a partial implementation.

Existing implementations may be labeled as **v1** components.

Future improvements may introduce:

- v2 NLU pipeline
- improved scoring engine
- advanced dialogue state tracking

Maintaining versioned components allows safe iteration without breaking existing functionality.

---

# Development Philosophy

The system is designed with the following principles:

• modular architecture  
• explainable AI feedback  
• separation of LLM generation and scoring  
• reproducible dialogue state tracking  

This design ensures the platform remains suitable for both educational deployment and research experimentation.
