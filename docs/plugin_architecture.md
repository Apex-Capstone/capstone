# APEX Plugin Architecture

## 1. Overview

APEX (AI Patient Experience Simulator) uses a **modular plugin architecture** to support research experimentation in clinical dialogue simulation. The core system remains stable while plugins allow extension without modifying core code.

### Core vs. Plugins

- **Core system**: Dialogue flow, session management, HTTP/WebSocket APIs, and contracts are fixed. This keeps the application predictable and maintainable.
- **Plugins**: Swappable components that implement well-defined **Protocols** under `interfaces/`. Researchers change behavior by implementing classes and wiring them through **settings**, **`plugins/load_plugins.py`**, and the **`PluginRegistry`**.

### Three Plugin Types

| Plugin Type       | Purpose |
|-------------------|--------|
| **PatientModel**  | Generates simulated patient responses during a dialogue turn. |
| **Evaluator**     | Evaluates a completed session and produces structured feedback (scores, strengths, areas for improvement). |
| **MetricsPlugin** | Defines additional research-oriented metrics (`compute`). Frozen **`metrics_plugins`** on the session records **which** plugins apply; after scoring, **`compute`** runs for each and results are stored on **`sessions.metrics_json`** (JSON object: plugin id → result dict). |

---

## 2. System Architecture (as implemented)

### Registration and loading

1. **Explicit module imports**  
   On startup, `plugins/load_plugins.py` imports a fixed list **`PLUGIN_MODULES`**. Each plugin module runs **register** calls on import (e.g. `PluginRegistry.register_evaluator(...)`) so classes are available by **registry key** (the plugin class’s `name`, typically `module.path:ClassName`).

2. **PluginRegistry** (`plugins/registry.py`)  
   In-memory maps: **evaluators**, **patient_models**, **metrics_plugins**. Session and case creation **resolve** plugins by these keys. Unknown keys for **case** overrides are rejected with `400`; **settings** fallbacks may use **dynamic import** (see below).

3. **Dynamic import by path** (`core/plugin_manager.py`)  
   `_load_class_from_path("module.path:ClassName")` imports the module and returns the class. **`get_patient_model`**, **`get_evaluator`**, and **`get_metrics_plugins`** use **settings** and **`lru_cache`** for process-wide singletons where those entry points are still used (e.g. legacy callers).  
   **Dialogue** resolves the **patient model** from the **session’s frozen `patient_model_plugin`** (then **`settings.patient_model_plugin`**) via **`PluginRegistry.get_patient_model`**, with the same **dynamic import + register** fallback as evaluators.  
   **Scoring** resolves the **evaluator** from the **session’s frozen `evaluator_plugin`** (then settings) via **`PluginRegistry.get_evaluator`**, with **fallback**: if the key is not registered, **`_load_class_from_path`** loads the class and registers it—supporting older sessions or paths not pre-registered.

4. **No automatic discovery**  
   The app does **not** scan the filesystem for plugins. New files must be **imported** from `PLUGIN_MODULES` (or pulled in by an already-imported module) so registration runs.

### High-level flow

```
HTTP controller
        ↓
DialogueService  →  PatientModel (session.patient_model_plugin → registry / dynamic load)
        ↓
Turns persisted
        ↓
Session close  →  ScoringService.generate_feedback
                        →  Evaluator.evaluate(db, session_id)
                        →  for each frozen metrics plugin: MetricsPlugin.compute(db, session_id)
                        →  persist aggregated results → sessions.metrics_json
        ↓
Feedback persisted / returned
```

**Metrics plugins** run only on code paths that call **`generate_feedback`** (e.g. session close). **`metrics_plugins`** on the session is the frozen **list of plugin ids**; **`metrics_json`** holds the **outputs** after scoring.

### Key components

- **DialogueService**  
  Orchestrates turns and resolves the **PatientModel** from **`session.patient_model_plugin`** (fallback: **`settings.patient_model_plugin`**): **`PluginRegistry.get_patient_model`**, then **`_load_class_from_path`** if missing. Invalid plugin → **`RuntimeError`** with a clear message.

- **ScoringService**  
  **`generate_feedback`**: loads the **Evaluator** from **`PluginRegistry`** (and dynamic fallback) using the **session’s `evaluator_plugin`**, calls **`evaluate`**, then runs each frozen **metrics** plugin’s **`compute`** and writes **`sessions.metrics_json`**. Persisted **feedback** **`evaluator_meta`** includes **`session_plugins`** (evaluator, patient model, and metrics plugin ids frozen on the session) for reproducibility alongside hybrid/rule metadata.

- **`plugin_manager`**  
  Path parsing, **`importlib`** loading, and cached getters for **settings-based** defaults—not the only path used for evaluators at scoring time.

---

## 3. Plugin Interfaces

All interfaces live under `interfaces/` as typing **`Protocol`** definitions.

### `interfaces.patient_model.PatientModel`

| Method | Signature | Purpose |
|--------|------------|--------|
| `generate_response` | `async def generate_response(self, state: Any, clinician_input: str) -> str` | Next patient utterance. |

### `interfaces.evaluator.Evaluator`

| Method | Signature | Purpose |
|--------|------------|--------|
| `evaluate` | `async def evaluate(self, db, session_id: int) -> FeedbackResponse` | Full session feedback. |

### `interfaces.metrics.MetricsPlugin`

| Method | Signature | Purpose |
|--------|------------|--------|
| `compute` | `def compute(self, db, session_id: int) -> dict[str, Any]` | Extra metrics for research/analytics; invoked after the evaluator on **`generate_feedback`** when **`metrics_plugins`** is set on the session. |

---

## 4. Plugin manager (`core/plugin_manager.py`)

- **Dynamic loading**: `"module.path:ClassName"` → import module, `getattr` class.
- **Caching**: `get_patient_model()`, `get_evaluator()`, `get_metrics_plugins()` use **`lru_cache`** (process lifetime).
- **Errors**: Malformed path → `ValueError`; missing module/class → `ImportError`; missing setting → `RuntimeError` where applicable.

---

## 5. Default plugins

| Plugin | Registry key (typical) | Role |
|--------|------------------------|------|
| **DefaultLLMPatientModel** | `plugins.patient_models.default_llm_patient:DefaultLLMPatientModel` | LLM + prompt builder for patient replies. |
| **ApexHybridEvaluator** | `plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator` | Hybrid feedback via `ScoringService`. |
| **ApexMetrics** | `plugins.metrics.apex_metrics:ApexMetrics` | Example `compute()` using scoring helpers. |

Replace by adding modules, registering, listing in **`PLUGIN_MODULES`**, and updating **settings** / **case** / **session** configuration as needed.

---

## 6. Configuration

| Field | Where | Description |
|-------|--------|-------------|
| `patient_model_plugin` | Settings / case / **session (frozen)** | Registry key or `module:Class` path for the patient model. **Dialogue** uses the **session** value at runtime. |
| `evaluator_plugin` | Settings / case / **session (frozen)** | Registry key or path for the evaluator. **Scoring** uses the **session** value. |
| `metrics_plugins` | Settings / case / **session (frozen)** | JSON array of metrics plugin ids. Defines **which** plugins run; outputs go to **`metrics_json`**. |
| `metrics_json` | **Session row only** | Written after **`generate_feedback`**: JSON object **`{ "<plugin_id>": <compute() dict>, ... }`**. Nullable until scoring runs. |

Session creation **freezes** resolved plugin ids (and versions where defined) on the session row for research traceability.

---

## 7. Testing

- **`backend/tests/plugins/`** — manager, registry, default plugins.
- **Service tests** — session create, evaluator selection, **dialogue patient-model resolution** (`test_dialogue_service_plugin.py`), **metrics execution** (`test_scoring_service_plugins.py`), hybrid **`session_plugins`** on feedback.
- Clear **`lru_cache`** on plugin getters when tests swap settings.

---

## 8. Design philosophy

- **Experimentation**: Swap implementations via config and registry keys without forking core controllers.
- **Honest boundaries**: Registry + explicit imports for discoverability; dynamic load as **fallback** and for path-based settings.
- **Reproducibility**: Persist chosen plugin ids (and versions where defined) on **sessions** (and optional **case** overrides). Runtime behavior matches frozen session fields for dialogue and scoring; **feedback** carries **`session_plugins`** inside **`evaluator_meta`** for audit trails.
