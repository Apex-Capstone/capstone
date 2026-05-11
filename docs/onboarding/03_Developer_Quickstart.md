# APEX Developer Quickstart (Repository-Accurate)

**Root:** `backend/` — application package under **`backend/src`** (import path `src` on `PYTHONPATH`).

---

## Run the API Locally

1. `cd backend && poetry install`
2. `cp .env.example .env` — fill **`database_url`**, **`supabase_jwt_secret`**, **`openai_api_key`**, **`gemini_api_key`**, etc. (`config/settings.py` lists fields).
3. `poetry run alembic upgrade head`
4. Set `PYTHONPATH` to **`backend/src`** (PowerShell: `$env:PYTHONPATH = "$PWD\src"` from `backend/`).
5. `poetry run uvicorn src.app:app --reload --host 0.0.0.0 --port 8000`

- Health: **`GET /health`**
- OpenAPI: **`http://localhost:8000/v1/docs`**
- Media (local storage): **`/media`** mount (`app.py`)

---

## Plugin Code Locations

| Item | Path |
|------|------|
| Load list | `src/plugins/load_plugins.py` — **`PLUGIN_MODULES`** |
| Registry | `src/plugins/registry.py` — **`PluginRegistry`** |
| Dynamic import / cached getters | `src/core/plugin_manager.py` — **`_load_class_from_path`**, **`get_patient_model`**, **`get_evaluator`**, **`get_metrics_plugins`** |
| Startup hook | `src/core/events.py` — **`load_plugins()`** |

---

## Add a Plugin (Minimal Steps)

1. Create a module under `src/plugins/...` with a class implementing the matching **`Protocol`** in `src/interfaces/`.
2. Set **`name: str = "full.module.path:ClassName"`** (must match how you reference it in settings/case/session).
3. On module import, call **`PluginRegistry.register_patient_model(name, Cls)`**, **`register_evaluator`**, or **`register_metrics_plugin`**.
4. Append the **module path** (dotted, no class) to **`PLUGIN_MODULES`** in `load_plugins.py`.
5. Optionally set defaults in **`.env`** / settings: **`patient_model_plugin`**, **`evaluator_plugin`**, **`metrics_plugins`** (list).

**Reference implementations:** `default_llm_patient.py`, `apex_hybrid_evaluator.py`, `apex_metrics.py`.

---

## Configure Which Plugin Runs

| Layer | Mechanism |
|-------|-----------|
| Defaults | `Settings` in `config/settings.py` — e.g. default evaluator `plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator` |
| Case | DB columns on **`cases`**: `evaluator_plugin`, `patient_model_plugin`, `metrics_plugins` (JSON array text) |
| Single session | `POST /v1/sessions` body: **`evaluator_plugin`** only (optional override); patient/metrics come from case/settings |

Resolved values are **frozen** on **`sessions`** columns when the row is created (`SessionService.create_session`).

---

## Tests

- `backend/tests/plugins/` — registry and plugin behavior
- Clear **`lru_cache`** on `plugin_manager.get_*` if tests change **`settings`**

---

## Scoring and Metrics (Important)

- Trainee flow triggers **`ScoringService.generate_feedback`** via **`POST /v1/sessions/{id}:close`** (`sessions_controller.close_session_and_get_feedback`).
- **`generate_feedback`** calls **`evaluator.evaluate`**, then **`_run_and_store_metrics_plugins`**.
- Evaluator plugins call **`generate_feedback_rule_only`**, **`generate_feedback_hybrid`**, or **`generate_feedback_hybrid_v2`** — those methods **do not** run metrics plugins.

---

## Useful API Examples (prefix `/v1`)

| Action | Method | Path |
|--------|--------|------|
| Create session | POST | `/sessions` |
| Text turn | POST | `/sessions/{id}/turns` |
| Close + feedback | POST | `/sessions/{id}:close` |
| Get feedback | GET | `/sessions/{id}/feedback` |
| Admin plugin list | GET | `/admin/plugin-registry` |
| Research JSON | GET | `/research/export` |

---

## Frontend

Separate app under **`frontend/`** (`npm install`, `npm run dev`). Not required to verify backend plugin behavior.

---

*Status and limits — `04_Project_Status_and_Roadmap.md`*
