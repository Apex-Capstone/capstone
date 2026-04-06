# APEX Plugin Developer Guide

This guide explains how to extend APEX by writing and registering your own **PatientModel**, **Evaluator**, and **MetricsPlugin** implementations.

---

## 1. Introduction

APEX allows researchers and developers to extend the system by implementing plugins. **Defaults** come from **settings** (e.g. environment variables); **cases** can override plugins for new sessions. At **session creation**, resolved plugin ids are **frozen on the session row** so dialogue and scoring use that configuration for reproducibility. You can swap the patient model, evaluator, or metrics without modifying core application code beyond registration and config.

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

**Integration:** When **`ScoringService.generate_feedback`** runs (e.g. on session close), after the **evaluator** finishes the backend runs each plugin listed in the session’s frozen **`metrics_plugins`**, calls **`compute(db, session_id)`**, and stores a single JSON object on **`sessions.metrics_json`**: keys are plugin ids, values are each **`compute`** return dict. Use that column (or the API field **`metrics_json`**) for research export and analytics. Metrics plugins are **not** run if code calls only the internal hybrid/rule helpers without going through **`generate_feedback`**.

---

## 5. Plugin Registration

1. **Code registration (import time)**  
   Each plugin module calls **`PluginRegistry.register_*`** when imported. **`plugins/load_plugins.py`** lists **`PLUGIN_MODULES`** so startup imports run registration. Add your module there.

2. **Configuration (which plugin runs)**  
   Resolution order is typically **case override → settings default** at **session creation**; the **session row** stores the frozen ids.

- **Patient model:** `patient_model_plugin` in settings and/or on the **case**. **Dialogue** loads the class using **`session.patient_model_plugin`** (fallback: **`settings.patient_model_plugin`**).
- **Evaluator:** `evaluator_plugin` on case/settings → frozen **`session.evaluator_plugin`** for **scoring**.
- **Metrics (list):** `metrics_plugins` on case/settings → frozen **`session.metrics_plugins`** (JSON array text) for **scoring**.

**Example plugin path:**

```text
plugins.patient_models.default_llm_patient:DefaultLLMPatientModel
```

Format is always `module.path:ClassName`. The module must be importable (e.g. under `backend/src` or on `PYTHONPATH`), and the class must implement the corresponding interface.

---

## 6. Testing Plugins

- **Location:** Add tests under `backend/tests/plugins/` and, for integration coverage, `backend/tests/services/` (e.g. dialogue and scoring plugin tests).
- **Patient model:** **`DialogueService`** resolves from the **session** and **`PluginRegistry`** (not `get_patient_model()`). Prefer registering a dummy class on **`PluginRegistry`** and setting **`session.patient_model_plugin`** (or patching **`_instantiate_patient_model`** in `dialogue_service`) instead of mocking deprecated globals.
- **Evaluator / metrics:** **`ScoringService.generate_feedback`** uses the session’s frozen evaluator and metrics list; **`PluginRegistry`** + tests that clear registry between runs (see existing scoring plugin tests) match production.
- **`lru_cache`:** Clear **`get_patient_model`**, **`get_evaluator`**, **`get_metrics_plugins`** in **`core/plugin_manager`** only when tests still exercise those **settings-based** entry points directly.
- **Interfaces:** Prefer testing against **`generate_response`**, **`evaluate`**, and **`compute`** so refactors preserve behavior.

---

## 7. Best Practices

- **Keep plugins stateless where possible:** Rely on `state`, `db`, and `session_id` for input. Avoid global mutable state so that plugins are safe under concurrency and caching.
- **Reuse services where possible:** Use existing repositories and services (e.g. `ScoringService`, session/turn repos) inside your plugin to stay consistent with the rest of the system and avoid duplicating logic.
- **Avoid modifying core services:** Extend behavior via new plugins or new classes that implement the interfaces; do not change `DialogueService` or `ScoringService` internals to suit a single plugin.
- **Validate configuration early:** Use the same `module.path:ClassName` format as the defaults. Invalid paths cause errors at startup or first use, which is intentional so misconfiguration is caught quickly.
