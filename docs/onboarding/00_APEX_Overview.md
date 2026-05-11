# APEX Overview

**Audience:** New researchers onboarding to the **implemented** APEX backend and API.

This document reflects the codebase under `backend/src` as of the repository state you are reading. For interface details, see `interfaces/` and `plugins/`.

---

## What APEX Is

**APEX** (AI Patient Experience Simulator) is a clinical communication training system delivered as a **FastAPI** backend (`app.py`) and a separate frontend. Trainees hold text-based (and optional audio) dialogues with a simulated patient; after the session is closed, the backend produces structured **feedback** and stores **research-oriented** fields.

---

## Problem It Addresses

- Repeated, low-risk practice for difficult conversations using **case** scripts and a **session** transcript.
- Automated **feedback** derived from persisted turns, NLU spans, and SPIKES-related stage progression.
- **Admin-only** anonymized exports for analysis (`ResearchService`, `/v1/research/...`).

---

## Who It Is For

| Role | Implementation |
|------|----------------|
| **Trainee** | Authenticated user: create/list sessions, submit turns, close session, read feedback (`sessions_controller`, `analytics_controller`). |
| **Admin** | Admin-only routes: case CRUD, all-session views, plugin registry visibility, research export (`admin_controller`, `research_controller`). |

Role checks use `core/deps.py` (`get_current_user`, `require_admin`).

---

## Implemented Core Features

- **Sessions** linked to **cases**, with reuse of an active session per (user, case) unless `force_new` (`SessionService.create_session`).
- **Turn loop** via `DialogueService.process_user_turn`: NLU on clinician text → SPIKES stage update → user turn persisted → **PatientModel** plugin generates patient text → NLU on patient text → assistant turn persisted.
- **Optional audio** turn path: Whisper ASR + tone analysis, then same dialogue pipeline (`submit_audio_turn`).
- **Optional assistant TTS** when `enable_tts` and adapters are configured.
- **Session close** → `ScoringService.generate_feedback` → persisted **Feedback**; **MetricsPlugin** results stored on `sessions.metrics_json`.
- **Research exports**: anonymized session id (`anon_` + hash), JSON and CSV endpoints under `/v1/research/`.
- **Plugin system**: `PatientModel`, `Evaluator`, `MetricsPlugin` protocols; registration at startup via `plugins/load_plugins.py`.

---

## Layered Architecture (As in Code)

```text
FastAPI routers (controllers/*)  →  services/*  →  repositories/*  →  PostgreSQL (SQLAlchemy entities under domain/entities/)
                    ↓
        DialogueService + ScoringService + SessionService + CaseService + ResearchService + …
                    ↓
        adapters/llm, adapters/nlu, adapters/asr, adapters/tts, adapters/storage
                    ↓
        plugins/* (PatientModel, Evaluator, MetricsPlugin) + PluginRegistry
```

OpenAPI is mounted at **`/v1/docs`** (see `app.py`).

---

## Key Domain Concepts

| Concept | Implementation |
|---------|----------------|
| **Case** | `domain/entities/case.py`: script, objectives, optional `evaluator_plugin`, `patient_model_plugin`, `metrics_plugins` (JSON text). |
| **Session** | `domain/entities/session.py`: `state` (`active`, `paused`, `completed`, `abandoned`), `current_spikes_stage`, frozen plugin fields, `metrics_json`. |
| **Turn** | User and assistant rows with `text`, `metrics_json`, `spans_json`, `spikes_stage`. |
| **Feedback** | `domain/entities/feedback.py` / `FeedbackResponse`: scores, JSON metric fields, `evaluator_meta` (includes `session_plugins` when written by `ScoringService._persist_feedback_from_rule_state`). |
| **Dialogue** | `DialogueService` + `NLUPipeline` (`services/nlu_pipeline.py`) + `SimpleRuleNLU` (`adapters/nlu/simple_rule_nlu.py`) + `StageTracker` (`services/stage_tracker.py`). |
| **Scoring** | `ScoringService`: rule-based core, `generate_feedback_hybrid`, `generate_feedback_hybrid_v2`; invoked through **Evaluator** plugins or directly from `generate_feedback`. |
| **Plugins** | Protocols in `interfaces/`; loaded by `load_plugins()` on startup; resolved from session row + `PluginRegistry` / `_load_class_from_path`. |

---

## SPIKES Stages in the Running System

During each user turn, `StageTracker` (`services/stage_tracker.py`) detects and persists stages (monotonic progression):

`setting` → `perception` → `invitation` → `knowledge` → `emotion` → `strategy`

(`DialogueService` defines a different list for legacy helpers; **live turn processing uses `StageTracker`**.)

---

## One-Sentence Summary

APEX persists structured turns and SPIKES stages, generates patient replies through a **PatientModel** plugin, and on **session close** runs a frozen **Evaluator** plugin plus **MetricsPlugin** list through **`ScoringService.generate_feedback`**, with admin-only anonymized export of the resulting data.

---

*Pipeline detail — `01_System_Pipeline.md`*
