# APEX Project Status (Implementation-Based)

This document describes **what the repository actually does today**, not a product roadmap. Details come from `backend/src` and `docs/vnv_alignment.md` (the latter is only a short strategy note; formal SRS/V&V PDFs in `docs/` are outside this audit).

---

## Maturity

- **Backend:** FastAPI app with migrations, role-based admin/trainee routes, plugins, research export service.
- **Scoring:** Rule-based pipeline with optional LLM merge (**`generate_feedback_hybrid`**, **`generate_feedback_hybrid_v2`**) implemented in **`ScoringService`**; selectable via **Evaluator** plugin.
- **NLU:** **`SimpleRuleNLU`** + **`NLUPipeline`** / **`turn_analysis`** — heuristic, English keyword-driven behavior.

---

## Stable Behaviors (Observable in Code)

- **Session lifecycle:** `SessionService.create_session` (reuse active session unless `force_new`); `close_session` sets **`completed`** + timestamps + **`duration_seconds`**.
- **Turn persistence:** User and assistant **`Turn`** rows with **`spans_json`**, **`metrics_json`**, **`spikes_stage`**.
- **SPIKES in dialogue:** **`StageTracker`** stages **`setting` … `strategy`** persisted on **`sessions.current_spikes_stage`**.
- **Scoring entrypoint:** **`POST /v1/sessions/{session_id}:close`** → **`generate_feedback`** → evaluator + metrics plugins.
- **Plugin registration:** Deterministic **`PLUGIN_MODULES`** import list + **`PluginRegistry`**.
- **Research:** Admin-only **`/v1/research/*`** with **deterministic anon session ids** (`ResearchService.generate_anon_session_id`).

---

## Implemented Features (Non-Exhaustive)

- Text and **audio** turns (Whisper + **`AudioToneAdapter`**).
- Optional **assistant TTS** + storage (**`dialogue_service._create_assistant_audio`**).
- **WebSocket** dialogue: **`/v1/ws/sessions/{session_id}`** with JWT query param.
- **Trainee analytics:** **`GET /v1/analytics/my-sessions`** (`TraineeAnalyticsService`).
- **Admin:** session lists, case management, **`/admin/plugin-registry`**, **`/admin/plugins`** — see **`admin_controller.py`**.
- **Feedback entity** with rich JSON fields and **`evaluator_meta`** (includes **`session_plugins`** when set in **`_persist_feedback_from_rule_state`**).

---

## Extensible (By Design)

| Area | Mechanism |
|------|-----------|
| Patient replies | New **`PatientModel`** + `PLUGIN_MODULES` + settings/case |
| Scoring methodology | New **`Evaluator`** delegating to new or existing **`ScoringService`** methods |
| Research metrics | New **`MetricsPlugin`** + session `metrics_plugins` list |
| LLM vendor (patient) | **`DefaultLLMPatientModel`** branches on **`default_llm_provider`** (`openai` vs `gemini`) |

---

## Known Limitations (From Current Implementation)

- **NLU / SPIKES detection** are keyword-heuristic (**`StageTracker`**, **`SimpleRuleNLU`**); no learned discourse parser in-repo.
- **Patient LLM path** in `sessions_controller` / `ws_controller` constructs **`DialogueService(..., OpenAIAdapter(), ...)`** while **`DefaultLLMPatientModel`** ignores that injected adapter and instantiates its own LLM from **settings** — can confuse readers of the HTTP layer.
- **Metrics plugins** only run in **`generate_feedback`**, not inside **`generate_feedback_hybrid`** / **`_hybrid_v2`** alone.
- **Session states** `paused` / `abandoned` exist on the entity but listing filters in **`list_user_sessions`** use **`active`** / **`completed`** only.
- **`ApexMetrics`** depends on **`ScoringService` private methods** — tight coupling for example metrics plugin.
- **Research anon id** reverse lookup scans batches of sessions (**`resolve_anon_to_session_id`**) — acceptable for small DBs; may need indexing strategy for very large deployments (not implemented).

---

## “Research-Ready” (What Is Actually True)

- Structured **turn** + **feedback** storage suitable for CSV/JSON export.
- Admin-only export endpoints with **no raw `session_id`** in research JSON (anon ids).
- **Frozen plugin ids** on **`sessions`** for configuration traceability.
- **Evaluator meta** can carry compact LLM outputs and **`session_plugins`** for provenance on hybrid paths.

---

## Out of Scope for This Spec

- Frontend feature list, hosting, IRB, or clinical validation claims.
- Future features **not** present in code (e.g. automatic scoring without `:close`, plugin filesystem auto-discovery, multimodal emotion models) — not documented here.

---

*Overview — `00_APEX_Overview.md`*
