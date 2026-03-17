# APEX Plugin Architecture

## 1. Overview

APEX (AI Patient Experience Simulator) uses a **modular plugin architecture** to support research experimentation in clinical dialogue simulation. The core system remains stable while plugins allow extension without modifying core code.

### Core vs. Plugins

- **Core system**: Dialogue flow, session management, WebSocket handling, and API contracts are fixed. This keeps the application predictable and maintainable.
- **Plugins**: Optional, swappable components that implement well-defined interfaces. Researchers and developers can add or replace behavior by implementing plugins and configuring them in settings.

### Three Plugin Types

| Plugin Type       | Purpose |
|-------------------|--------|
| **PatientModel**  | Generates simulated patient responses during a dialogue turn. |
| **Evaluator**     | Evaluates a completed session and produces structured feedback (scores, strengths, areas for improvement). |
| **MetricsPlugin** | Computes additional research-oriented metrics for a session (e.g., SPIKES coverage, response counts). |

---

## 2. System Architecture

### Component Flow

```
Controller (HTTP/WebSocket)
        ↓
DialogueService
        ↓
PatientModel plugin  →  generate_response(state, clinician_input)
        ↓
Simulated patient response
        ↓
ScoringService (on session end)
        ↓
Evaluator plugin  →  evaluate(db, session_id)
        ↓
Metrics plugins  →  compute(db, session_id)
        ↓
Feedback + research metrics
```

### Key Components

- **DialogueService**  
  Orchestrates each dialogue turn: loads dialogue state, calls the configured **PatientModel** plugin to generate the patient reply, persists turns, and updates SPIKES stage. It does not implement patient logic itself; that is delegated to the plugin.

- **DialogueState**  
  A value object (or similar) passed into the PatientModel. It typically exposes `case`, `session`, and `conversation_history` so the plugin can build context-aware responses.

- **ScoringService**  
  Invoked when a session is completed. It uses the configured **Evaluator** plugin to produce feedback and the configured **MetricsPlugin** instances to compute extra metrics. Results are stored and returned to the client.

- **plugin_manager**  
  Lives in `core/plugin_manager.py`. It loads plugin classes from configured paths (e.g. `module.path:ClassName`), instantiates them, and caches instances. The rest of the system calls `get_patient_model()`, `get_evaluator()`, and `get_metrics_plugins()` instead of importing concrete implementations.

---

## 3. Plugin Interfaces

All interfaces are defined under `interfaces/` and use typing `Protocol` for structural subtyping.

### `interfaces.patient_model.PatientModel`

| Method | Signature | Purpose |
|--------|------------|--------|
| `generate_response` | `async def generate_response(self, state: Any, clinician_input: str) -> str` | Generate a simulated patient response for the given dialogue state and clinician input. |

The `state` object is expected to expose at least `case`, `session`, and `conversation_history` for the default implementation; custom plugins may use a subset or extensions.

---

### `interfaces.evaluator.Evaluator`

| Method | Signature | Purpose |
|--------|------------|--------|
| `evaluate` | `async def evaluate(self, db, session_id: int) -> FeedbackResponse` | Evaluate a completed session and return structured feedback (scores, strengths, areas for improvement). |

`FeedbackResponse` is the same domain model used by the API for session feedback.

---

### `interfaces.metrics.MetricsPlugin`

| Method | Signature | Purpose |
|--------|------------|--------|
| `compute` | `def compute(self, db, session_id: int) -> dict[str, Any]` | Compute additional research metrics for a completed session. Return a dictionary of metric names to values. |

Metrics are merged or stored as needed by the scoring/feedback pipeline and can be exposed for research export.

---

## 4. Plugin Manager

**Module:** `core/plugin_manager.py`

### Responsibilities

- **Dynamic loading**: Plugin classes are loaded from strings in the form `module.path:ClassName` (e.g. `plugins.patient_models.default_llm_patient:DefaultLLMPatientModel`). The manager imports the module and resolves the class by name.
- **Caching**: `get_patient_model()`, `get_evaluator()`, and `get_metrics_plugins()` are wrapped with `lru_cache()`, so each plugin type is instantiated once per process and reused.
- **Lifecycle**: Plugins are created at first use. There is no explicit shutdown; cache is process-scoped. For tests, caches can be cleared so that new settings or mocks take effect.

### Path Format

- **Single plugin (patient model, evaluator):** one string `"module.path:ClassName"`.
- **Multiple plugins (metrics):** a list of such strings. Each is loaded and instantiated; the result is a tuple of `MetricsPlugin` instances.

### Error Handling

- Malformed paths (no `:`) raise `ValueError`.
- Missing module or class raises `ImportError` with a clear message. Missing configuration (e.g. no `patient_model_plugin` in settings) raises `RuntimeError`.

---

## 5. Default Plugins

The system ships with default implementations that wrap existing logic:

| Plugin | Class | Description |
|--------|--------|-------------|
| **DefaultLLMPatientModel** | `plugins.patient_models.default_llm_patient:DefaultLLMPatientModel` | Uses the same LLM adapter and prompt builder as the original DialogueService to generate patient responses. |
| **ApexHybridEvaluator** | `plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator` | Delegates to `ScoringService._generate_feedback_impl()` to produce feedback. |
| **ApexMetrics** | `plugins.metrics.apex_metrics:ApexMetrics` | Uses ScoringService helpers to compute SPIKES coverage, EO counts, and response counts for research. |

These can be replaced by other implementations via configuration without changing core code.

---

## 6. Configuration

Plugin selection is done via application settings (e.g. environment or `.env`).

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `patient_model_plugin` | string | Single plugin path for the patient model. |
| `evaluator_plugin` | string | Single plugin path for the evaluator. |
| `metrics_plugins` | list of strings | Zero or more plugin paths for metrics. |

### Example

```env
# Optional; these are the defaults if not set
patient_model_plugin=plugins.patient_models.default_llm_patient:DefaultLLMPatientModel
evaluator_plugin=plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator
metrics_plugins=plugins.metrics.apex_metrics:ApexMetrics
```

In code (e.g. Pydantic settings), `metrics_plugins` is a list:

```python
metrics_plugins: list[str] = ["plugins.metrics.apex_metrics:ApexMetrics"]
```

---

## 7. Testing Strategy

- **Location**: Plugin-related tests live under `backend/tests/plugins/`.
- **Scope**: Tests cover the plugin manager (path parsing, loading, caching), each default plugin (PatientModel, Evaluator, MetricsPlugin), and the interfaces (e.g. that implementations satisfy the protocols).
- **Rationale**: Testing interfaces and manager ensures that new or swapped plugins integrate correctly and that configuration and lifecycle behave as expected.

---

## 8. Design Philosophy

- **Research experimentation**: Different patient models, evaluators, or metrics can be tried by changing configuration, without forking the codebase.
- **Extensibility**: New plugins can be added in new modules and wired in via settings; the core stays unchanged.
- **Modular evaluation**: Feedback and research metrics are separated into Evaluator and MetricsPlugin, so evaluation logic and extra metrics can evolve independently.
