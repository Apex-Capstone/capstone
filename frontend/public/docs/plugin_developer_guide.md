# APEX Plugin Developer Guide

This guide explains how to extend APEX by writing and registering your own **PatientModel**, **Evaluator**, and **MetricsPlugin** implementations.

---

## 1. Introduction

APEX allows researchers and developers to extend the system by implementing plugins. Plugins are configured via settings (e.g. environment variables) and loaded at runtime. You can swap the default patient model, evaluator, or metrics without modifying core application code.

---

## 2. Creating a PatientModel Plugin

Implement the `PatientModel` protocol: an async method `generate_response(state, clinician_input)` that returns the simulated patient response as a string.

**Example:**

```python
from typing import Any


class MyPatientModel:
    async def generate_response(self, state: Any, clinician_input: str) -> str:
        # Use state.case, state.session, state.conversation_history as needed.
        # Return the next patient utterance.
        return "I'm not sure how to feel about that."
```

**Expected behavior:**

- `state` is provided by the dialogue service and typically has `case`, `session`, and `conversation_history`.
- Your method should return a single string: the next patient turn. Keep responses appropriate for the clinical context and, if relevant, the current SPIKES stage.

---

## 3. Creating an Evaluator Plugin

Implement the `Evaluator` protocol: an async method `evaluate(db, session_id)` that returns a `FeedbackResponse`.

**Example:**

```python
from sqlalchemy.orm import Session
from domain.models.sessions import FeedbackResponse


class MyEvaluator:
    async def evaluate(self, db: Session, session_id: int) -> FeedbackResponse:
        # Load session/turns from db, compute scores and text feedback.
        return FeedbackResponse(
            empathy_score=75.0,
            overall_score=80.0,
            strengths="Clear structure.",
            areas_for_improvement="More empathy phrases.",
            suggested_responses=[],
            timeline_events=[],
        )
```

**Expected return type:** `FeedbackResponse` (or a compatible type) with at least empathy score, overall score, and optional strengths/areas for improvement, suggested responses, and timeline events as defined in the domain model.

---

## 4. Creating a Metrics Plugin

Implement the `MetricsPlugin` protocol: a synchronous method `compute(db, session_id)` that returns a dictionary of metrics.

**Example:**

```python
from typing import Any
from sqlalchemy.orm import Session


class MyMetricsPlugin:
    def compute(self, db: Session, session_id: int) -> dict[str, Any]:
        # Compute custom metrics from session/turns.
        return {
            "custom_metric_a": 42,
            "custom_metric_b": "value",
        }
```

**Integration:** The scoring/feedback pipeline calls all configured metrics plugins and merges or stores their results. These metrics can be used for research export and analytics.

---

## 5. Plugin Registration

Plugins are registered by **configuration**, not by code registration. Set the following in your environment or settings:

- **Patient model:** `patient_model_plugin=module.path:ClassName`
- **Evaluator:** `evaluator_plugin=module.path:ClassName`
- **Metrics (list):** `metrics_plugins=module.path:ClassA module.path:ClassB` (or the equivalent list in your config)

**Example plugin path:**

```text
plugins.patient_models.default_llm_patient:DefaultLLMPatientModel
```

Format is always `module.path:ClassName`. The module must be importable (e.g. under `backend/src` or on `PYTHONPATH`), and the class must implement the corresponding interface.

---

## 6. Testing Plugins

- **Location:** Add tests under `backend/tests/plugins/`.
- **Patterns:** Reuse the patterns from existing plugin tests: mock or override `get_patient_model`, `get_evaluator`, or `get_metrics_plugins` where needed, and clear `lru_cache` on the plugin manager in tests that change configuration so the new plugin is loaded.
- **Interfaces:** Prefer testing against the public interface (e.g. `generate_response`, `evaluate`, `compute`) so that refactors preserve behavior.

---

## 7. Best Practices

- **Keep plugins stateless where possible:** Rely on `state`, `db`, and `session_id` for input. Avoid global mutable state so that plugins are safe under concurrency and caching.
- **Reuse services where possible:** Use existing repositories and services (e.g. `ScoringService`, session/turn repos) inside your plugin to stay consistent with the rest of the system and avoid duplicating logic.
- **Avoid modifying core services:** Extend behavior via new plugins or new classes that implement the interfaces; do not change `DialogueService` or `ScoringService` internals to suit a single plugin.
- **Validate configuration early:** Use the same `module.path:ClassName` format as the defaults. Invalid paths cause errors at startup or first use, which is intentional so misconfiguration is caught quickly.
