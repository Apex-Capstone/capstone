## APEX Architecture Decision Log

This document records major architectural decisions made during the development of **APEX (AI Patient Experience Simulator)**.

The goal of this log is to document **why key design choices were made**, what alternatives were considered, and how each decision supports the **System Requirements Specification (SRS)** and project research foundations.

Recording decisions improves traceability, supports future maintenance, and strengthens architectural defensibility for the capstone evaluation.

---

# ADR-001

## Dialogue System Architecture

### Status

Accepted

### Context

APEX is a clinical communication training system that simulates patient conversations and evaluates learner empathy and communication behavior.

The system must support:

* structured dialogue flow based on the **SPIKES protocol**
* empathy analysis based on the **Appraisal Framework for Clinical Empathy (AFCE)**
* automated feedback scoring
* structured transcript storage for research export

The architecture must therefore support both:

1. realistic patient dialogue generation
2. interpretable analysis of clinician communication behavior

A key design question was how to structure the dialogue engine.

---

### Options Considered

#### Option 1: Pure LLM Dialogue System

```
User message
→ LLM
→ Patient response
→ LLM-generated feedback
```

Advantages

* simple architecture
* minimal implementation complexity
* fast prototyping

Disadvantages

* dialogue state hidden inside prompts
* no explicit SPIKES stage tracking
* unreliable extraction of empathy signals
* difficult to validate scoring logic
* weak research reproducibility

This design would make it difficult to generate structured metrics such as:

* Empathic Opportunity detection
* EO-response linking
* SPIKES stage coverage

It would also reduce transparency of scoring decisions.

---

#### Option 2: Fully Symbolic Dialogue System

```
User message
→ NLU
→ Deterministic dialogue policy
→ Rule-based patient response
```

Advantages

* fully interpretable
* deterministic behavior
* easy scoring integration

Disadvantages

* extremely rigid conversations
* unrealistic patient responses
* difficult to scale across cases
* poor conversational naturalness

This approach would undermine the realism needed for training.

---

#### Option 3: Hybrid Dialogue Architecture

```
User message
→ Rule-based NLU
→ Dialogue Service
→ LLM patient generation
→ Turn persistence
→ Post-session scoring
```

Advantages

* realistic patient responses via LLM
* explicit dialogue state tracking
* structured empathy detection
* explainable scoring
* modular architecture

Disadvantages

* increased implementation complexity
* additional orchestration layer required

---

### Decision

APEX adopts a **hybrid dialogue architecture** combining rule based NLU with LLM based patient response generation.

Structure

```
User message
→ NLU analysis
→ Dialogue state update
→ LLM patient response generation
→ Turn persistence
→ Session scoring
```

The LLM is responsible only for generating patient dialogue.
Dialogue control, state tracking, and scoring remain within the backend system.

---

### Rationale

This design aligns best with the goals of the system.

1. **Educational transparency**

Empathy detection and SPIKES stage tracking remain system controlled rather than hidden inside prompts.

2. **Explainable feedback**

Structured signals such as Empathic Opportunities and elicitation attempts can be explicitly detected and linked.

3. **Research export**

Structured annotations can be exported for research analysis.

4. **Extensibility**

LLM providers can be replaced through adapter interfaces without affecting the dialogue pipeline.

5. **Architectural defensibility**

Separating generation from evaluation ensures scoring logic can be validated independently.

---

### Consequences

Positive

* realistic patient simulation
* interpretable communication scoring
* modular architecture
* supports future research analysis

Negative

* additional orchestration complexity
* rule based NLU may require improvement over time

---

### Future Improvements

Potential future upgrades include

* machine learning based NLU
* dialogue act classification layer
* patient emotional state modeling
* reinforcement learning dialogue policies

These improvements can be introduced without replacing the overall architecture.

---

# ADR-002

## Rule Based NLU for Initial System

### Status

Accepted

### Context

The system requires extraction of clinically meaningful communication signals such as

* empathic responses
* elicitation attempts
* question type
* tone markers

These signals support scoring and feedback generation.

---

### Decision

The initial version of APEX uses a **rule based NLU subsystem** consisting of

```
SimpleRuleNLU
SpanDetector
```

These modules detect patterns using keyword rules and lightweight heuristics.

---

### Rationale

Rule based detection is suitable for the initial system because

* annotated training datasets for clinical empathy are limited
* rules are easy to debug and validate
* scoring logic becomes transparent
* development complexity remains manageable for a capstone project

---

### Consequences

Positive

* interpretable detection logic
* predictable scoring behavior
* easier debugging

Negative

* limited robustness to paraphrases
* weaker contextual reasoning
* limited multilingual support

---

### Future Improvements

Potential upgrades include

* transformer based span detection
* contextual emotion recognition
* supervised empathy classification

---

# ADR-003

## Adapter Based LLM Integration

### Status

Accepted

### Context

The system must support different LLM providers and potentially switch providers in the future.

---

### Decision

APEX integrates LLM services through an **adapter layer**.

Example adapters

```
OpenAIAdapter
GeminiAdapter
```

The dialogue service communicates only with the adapter interface.

---

### Rationale

This approach

* prevents vendor lock in
* isolates API specific logic
* simplifies provider switching
* improves testability

---

### Consequences

Positive

* modular design
* provider flexibility
* cleaner code separation

Negative

* additional abstraction layer

---

# ADR-004

## Post Session Feedback Scoring

### Status

Accepted

### Context

Feedback evaluation may involve complex analysis including

* EO detection
* EO response linking
* SPIKES stage coverage
* communication behavior metrics

Real time scoring could increase latency and complicate dialogue processing.

---

### Decision

Scoring is executed **only after the session closes**.

```
Session closed
→ ScoringService
→ Feedback generation
→ Feedback persistence
```

---

### Rationale

This approach

* reduces latency during conversation
* simplifies system design
* ensures one consolidated feedback record per session

---

### Consequences

Positive

* predictable scoring workflow
* simpler session logic
* easier debugging

Negative

* feedback not available during conversation

Future versions may support partial real time feedback.

---

# ADR-005

## Closed Session Immutability

### Status

Accepted

### Context

Research exports and evaluation metrics require reproducible session records.

---

### Decision

Once a session is closed, the conversation and scoring outputs are treated as immutable.

---

### Rationale

This ensures

* reproducible research analysis
* auditability of scoring results
* stable export artifacts

---

### Consequences

Positive

* reliable research datasets
* traceable session history

Negative

* sessions cannot be edited after completion

---

# Summary

The architectural decisions recorded here establish APEX as a **hybrid dialogue system combining structured analysis with LLM generated simulation**.

This design balances

* conversational realism
* explainable scoring
* research traceability
* modular extensibility

These decisions form the foundation for subsequent implementation and validation of the system.