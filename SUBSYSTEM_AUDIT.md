# APEX (AI Patient Experience Simulator) — Structured Subsystem Audit

**Document:** Technical Status Report by Subsystem  
**Project:** APEX (AI Patient Experience Simulator) (Capstone)  
**Context:** Healthcare-training platform; no PHI/PII stored; admin role-restricted; research read-only; WebSocket must not bypass auth; HTTPS required (FR-9).

---

## Reference: SRS Functional Requirements (FR-1 to FR-20)

| FR ID | Requirement |
|-------|-------------|
| FR-1 | Authentication & role handling (trainee/admin) |
| FR-2 | Case selection — SPIKES-focused cases with demographics |
| FR-3 | Chat interface — text chat with patient emotion indicators |
| FR-4 | Session management — real-time timer, SPIKES stage tracking |
| FR-5 | Voice input — ASR integration (placeholder or live) |
| FR-6 | Feedback dashboard — SPIKES coverage, enhanced metrics |
| FR-7 | Admin dashboard — user management, analytics |
| FR-8 | Research API view — read-only, anonymized analytics |
| FR-9 | HTTPS required |
| FR-10 | End session — button redirects to feedback |
| FR-11 | (Session persistence / data retention) |
| FR-12 | Enhanced metrics — empathy scores, open-question ratio, dialogue examples |
| FR-13 | User overview — admin views trainee performance |
| FR-14 | Session logs — admin accesses session transcripts |
| FR-15 | Fairness metrics — bias probe, demographic parity (research) |
| FR-16 | PIPEDA / no PHI — compliance |
| FR-17 | Admin role restriction |
| FR-18 | Research API read-only |
| FR-19 | WebSocket does not bypass authentication |
| FR-20 | (Security & audit controls) |

*Note: No formal SRS document was found in the repository; the above is inferred from README, frontend README, API docs, and codebase.*

---

## 1. Auth Subsystem

### 1.1 Current Implementation Status

**What is implemented?**
- Backend: JWT access tokens (HS256), password hashing (pbkdf2_sha256), login (`POST /v1/auth/login`), register (`POST /v1/auth/register`), refresh (`POST /v1/auth/refresh`), and `GET /v1/auth/me`. Role scopes: `trainee` and `admin`. Dependencies `get_current_user`, `require_role`, `require_admin`, `require_trainee` used across protected routes.
- Frontend: Zustand auth store with persist to `localStorage`; login calls backend; Axios interceptor attaches `Authorization: Bearer <token>`; `ProtectedRoute` enforces `isAuthenticated` and optional `allowedRoles` (admin/trainee).

**What works end-to-end?**
- Login with email/password → JWT returned → stored in localStorage → subsequent API calls include token. Protected routes redirect unauthenticated users to `/login`. Admin-only routes (e.g. `/admin`) redirect non-admin to `/dashboard`.

**What is shallow / placeholder / mock?**
- Login response returns only `access_token` (no refresh_token in response despite `/auth/refresh` existing). Frontend does not use refresh flow; token expiry can strand the user without re-login. Instructor role is mentioned in root README but not in backend `RoleScopes` (only trainee/admin).

**What does not match SRS?**
- FR-9: No HTTPS enforcement in app or config (no redirect-to-HTTPS, no `require_https` flag in settings). Development defaults to HTTP.
- Three-role model (Trainee, Instructor, Admin) in README is not implemented; only trainee and admin exist.

### 1.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-1 | Partially implemented | Login, roles, and protected routes work; instructor role and refresh flow are missing. |
| FR-9 | Not implemented | No HTTPS enforcement in code or configuration. |
| FR-17 | Fully implemented | Admin-only routes use `require_admin`; trainee cannot access admin/research write. |

### 1.3 Architectural Gaps

- **Separation of concerns:** Auth logic is coherent (core/security, core/deps, auth_service, auth_controller). Minor: refresh endpoint decodes token but does not validate refresh_token type (single token type used for both access and refresh).
- **Missing APIs:** Logout is client-only (token discarded in store); no server-side revocation or blocklist.
- **Missing validation:** Password strength not validated on register; email format validated via Pydantic `EmailStr`.
- **Missing security controls:** No rate limiting on login/register; no account lockout; `SECRET_KEY` must be set via env (no in-code default in settings, but .env example exists).
- **Appendix A:** Not found in repo; cannot verify diagram alignment.

### 1.4 Non-Functional Gaps

- **Security:** No HTTPS enforcement; no refresh token rotation; token in localStorage (XSS exposure).
- **Logging:** Auth service does not log failed/successful logins for audit.
- **Compliance:** PIPEDA-relevant access logging (who accessed what) not present at auth layer.
- **Testing:** `test_auth.py` covers register, duplicate register, login success, invalid password; no tests for refresh, expired token, or role denial.

### 1.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | Enforce HTTPS in production (reverse proxy or app-level redirect) and document in deployment. |
| P0 | Align frontend feedback URL: use `GET /v1/sessions/{sessionId}/feedback` (see Feedback subsystem). |
| P1 | Add login/register rate limiting and optional account lockout. |
| P1 | Either implement refresh token in login response + frontend refresh flow, or document that users must re-login after token expiry. |
| P2 | Add audit logging for login success/failure and role-based access denials. |
| P2 | Decide on instructor role: add to RoleScopes and routes or remove from README. |

### 1.6 Owner Recommendation

- **Owner:** Backend-focused developer with security awareness.
- **Heavy:** Backend (FastAPI, JWT, deps); light frontend (store/interceptor already in place). QA for negative cases (expired token, 403).

---

## 2. Sessions Subsystem

### 2.1 Current Implementation Status

**What is implemented?**
- Backend: Create session (`POST /v1/sessions`), get session (`GET /v1/sessions/{id}`), list user sessions (`GET /v1/sessions`), submit text turn (`POST /v1/sessions/{id}/turns`), submit audio turn (`POST /v1/sessions/{id}/audio`), close session (`POST /v1/sessions/{id}:close`), get feedback (`GET /v1/sessions/{id}/feedback`). Session reuse for same user/case when `force_new` is false. Ownership enforced via `verify_session_access` (trainee: own session only; admin: any).
- Frontend: Case detail page creates or resumes session via `createSession` / `getSession`; timer; message list; submit turn and close session; redirect to feedback on close.

**What works end-to-end?**
- Trainee opens case → session created or resumed → turns submitted via REST → patient reply and SPIKES stage returned → close session → feedback generated and returned. List sessions and resume by `sessionId` query param work.

**What is shallow / placeholder / mock?**
- Session list total count uses `len(total_turns)` in one place (sessions_controller `get_session_turns`) — likely intended as total turns; session list total is correct in `list_user_sessions`. No major placeholders.

**What does not match SRS?**
- FR-4: Session timer and SPIKES stage are implemented; no explicit SRS mismatch.

### 2.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-4 | Fully implemented | Session lifecycle, timer (frontend), SPIKES stage on session and turns. |
| FR-10 | Fully implemented | Close session endpoint and frontend "End Session" redirect to feedback. |
| FR-11 | Fully implemented | Sessions and turns persisted; list and resume supported. |

### 2.3 Architectural Gaps

- **Separation of concerns:** Controllers delegate to SessionService, DialogueService, ScoringService; session ownership in deps. Good.
- **Missing APIs:** None critical; pagination for turns exists.
- **Missing validation:** Session ID and case_id validated by existence in DB; input text length not bounded.
- **Security:** Session access correctly restricted; no bypass.

### 2.4 Non-Functional Gaps

- **Performance:** No caching; each turn triggers LLM + NLU. Acceptable for demo.
- **Logging:** Session create/close could be audited for compliance.
- **Testing:** test_sessions.py covers create and reuse; no integration test for full flow with turns and close.

### 2.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | Fix frontend feedback URL to `GET /v1/sessions/{sessionId}/feedback` (see Feedback). |
| P1 | Add optional request validation (e.g. max length for turn text). |
| P2 | Add audit log events for session create and close (user_id, session_id, case_id). |

### 2.6 Owner Recommendation

- **Owner:** Full-stack; sessions span frontend (CaseDetail, session list) and backend (session + dialogue).
- **Heavy:** Backend; frontend already wired. QA for resume flow and close → feedback.

---

## 3. Feedback Subsystem

### 3.1 Current Implementation Status

**What is implemented?**
- Backend: Feedback generated on close via `ScoringService.generate_feedback`; stored in `feedback` table; returned by `GET /v1/sessions/{session_id}/feedback`. Metrics include AFCE-style EO/elicitation/response counts, SPIKES coverage/timestamps/strategies, question breakdown, linkage/missed opportunities, textual strengths/improvements.
- Frontend: Feedback page at `/feedback/:sessionId`; calls `fetchFeedback(sessionId)` which currently requests **`GET /v1/feedback/${sessionId}`**. Backend does **not** expose `/v1/feedback/:id`; it exposes **`GET /v1/sessions/{session_id}/feedback`**. So the frontend hits a non-existent endpoint and falls back to **mock data** in the catch block.

**What works end-to-end?**
- Close session → backend generates and returns feedback in the close response. If the frontend used the correct endpoint for the feedback page, GET feedback would work. Currently the Feedback page shows mock data after close because of the wrong URL.

**What is shallow / placeholder / mock?**
- Frontend feedback type and mock fallback: `Feedback` type (e.g. `overallScore`, `strengths[]`) does not match backend `FeedbackResponse` (e.g. `overall_score`, `strengths` string). Fairness/bias fields in backend are placeholder (`bias_probe_info`, `evaluator_meta` = None). Research fairness metrics (FR-15) not computed.

**What does not match SRS?**
- FR-6, FR-12: Backend delivers SPIKES and enhanced metrics; frontend does not receive them in production path because it calls the wrong endpoint and then uses a different shape (mock).

### 3.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-6 | Partially implemented | Backend has full feedback and SPIKES metrics; frontend uses wrong URL and mock type. |
| FR-12 | Partially implemented | Backend has empathy score, question breakdown, etc.; frontend not wired to real API for feedback page. |

### 3.3 Architectural Gaps

- **API contract mismatch:** Frontend expects `/v1/feedback/:sessionId` and a different response shape; backend provides `/v1/sessions/:sessionId/feedback` and `FeedbackResponse`. This is a critical integration gap.
- **Missing validation:** Feedback only exists for closed sessions; backend returns 404 when feedback not found (correct).

### 3.4 Non-Functional Gaps

- **Logging:** Feedback generation could be logged for audit.
- **Testing:** No dedicated test for GET feedback endpoint in sessions_controller; scoring covered indirectly.

### 3.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | Change frontend `fetchFeedback` to call `GET /v1/sessions/${sessionId}/feedback` and remove mock fallback for that path. |
| P0 | Align frontend `Feedback` type with backend `FeedbackResponse` (snake_case, optional fields, spikes_coverage, question_breakdown, etc.) and update Feedback.tsx to use real fields. |
| P1 | Add integration test: close session → GET session feedback → assert scores and structure. |
| P2 | (Optional) Implement or document fairness/bias placeholders (FR-15) for research. |

### 3.6 Owner Recommendation

- **Owner:** Full-stack; one person should own the feedback API contract and both FE/BE types.
- **Heavy:** Frontend (type and page) and backend (already implemented); QA to verify real data end-to-end.

---

## 4. Research Subsystem

### 4.1 Current Implementation Status

**What is implemented?**
- Backend: All research endpoints are GET-only and protected by `require_admin`. Endpoints: list anonymized sessions (`GET /v1/research/sessions`), get session by anon id (`GET /v1/research/sessions/{anon_session_id}`), JSON export (`GET /v1/research/export`), CSV exports (`/export.csv`, `/export/metrics.csv`, `/export/transcripts.csv`, `/export/session/{anon_session_id}.csv`). ResearchService uses deterministic `anon_` IDs (salt in settings), redacts PII in text (email, phone, names), and does not expose raw user_id or session_id in responses.
- Frontend: Research page fetches sessions via `fetchResearchSessions` (correct URL); downloads metrics/transcripts CSV with Bearer token; maps backend sessions to `ResearchData` with placeholder demographics and fairness metrics (backend does not provide them).

**What works end-to-end?**
- Admin logs in → Research page loads anonymized sessions from API → export buttons download CSV/JSON. No write operations; read-only.

**What is shallow / placeholder / mock?**
- Demographics and fairness metrics: backend does not store or compute demographics per session or bias/fairness metrics; frontend uses placeholders ("—", 0). FR-15 (fairness metrics) not implemented.

**What does not match SRS?**
- FR-15: Fairness metrics (bias probe consistency, demographic parity) are not implemented; frontend shows placeholders.

### 4.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-8 | Fully implemented | Read-only research API; anonymized data; admin-only. |
| FR-15 | Not implemented | No bias/fairness computation or demographics in backend. |
| FR-16 | Partially implemented | Anonymization and no PHI in research export; no formal PIPEDA checklist or doc. |
| FR-18 | Fully implemented | Research routes are GET-only; no POST/PUT/DELETE. |

### 4.3 Architectural Gaps

- **Separation of concerns:** Research service and controller are clearly separated; anonymization in one place.
- **Missing APIs:** None for read-only mandate. Optional: filter params (date range, case_id) on list/export not fully exposed in all endpoints.
- **Missing validation:** Anon session ID format validated by lookup; CSV/JSON streaming is correct.
- **Security:** Admin-only and read-only; no bypass.

### 4.4 Non-Functional Gaps

- **Compliance:** PIPEDA: anonymization and no PHI in export are in place; document data flows and retention for compliance review.
- **Logging:** Export actions are logged (admin_user_id, timestamp); good for audit.

### 4.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | None blocking for MVP; research is usable for demo. |
| P1 | Document that fairness metrics (FR-15) are placeholder and out of scope for demo, or implement minimal stub (e.g. single aggregate number). |
| P2 | Add optional filters (e.g. date range) to research list/export if required by stakeholders. |

### 4.6 Owner Recommendation

- **Owner:** Backend-lead with frontend alignment on response shape.
- **Heavy:** Backend (anonymization, export); frontend is thin (list + download). QA for export correctness and no PII leakage.

---

## 5. Cases Subsystem

### 5.1 Current Implementation Status

**What is implemented?**
- Backend: List cases (`GET /v1/cases`) with optional difficulty/category; get case (`GET /v1/cases/{id}`); create/update/delete cases (admin only). Case entity has title, description, script, objectives, difficulty_level, category, patient_background, expected_spikes_flow. Seed script creates SPIKES-focused cases.
- Frontend: Dashboard lists cases via API; CaseDetail loads case by id; case data used for session and chat context.

**What works end-to-end?**
- Trainee sees case list → selects case → case detail and session load. Admin can create/update/delete cases via API (no dedicated admin UI for CRUD in the files reviewed; Admin.tsx has tabs for Users, Sessions, Analytics).

**What is shallow / placeholder / mock?**
- Frontend previously had mock data (client_old.ts); current client and pages use real API. Demographics (FR-2) may be in case description/script rather than structured fields; no separate demographics object in CaseResponse.

**What does not match SRS?**
- FR-2: "SPIKES-focused virtual patient cases with demographics" — cases are SPIKES-focused; demographics are narrative in script/patient_background, not a dedicated structured field. Acceptable if SRS allows narrative demographics.

### 5.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-2 | Fully implemented | Cases are SPIKES-focused; demographics in script/patient_background. |

### 5.3 Architectural Gaps

- **Separation of concerns:** CaseService and CaseRepository; controller thin. Good.
- **Missing APIs:** None for MVP. Optional: PATCH/DELETE used; list filters exist.
- **Missing validation:** Case create/update validated by Pydantic; no duplicate title check.
- **Security:** Create/update/delete require admin; list/get require authenticated user.

### 5.4 Non-Functional Gaps

- **Testing:** test_cases_api_smoke and test_cases exist; coverage reasonable.
- **Maintainability:** Clear domain model and repo.

### 5.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P1 | Confirm with SRS whether structured demographics (age, gender) are required on case; if yes, add optional fields and seed. |
| P2 | Optional: Admin UI for case CRUD if demo requires it. |

### 5.6 Owner Recommendation

- **Owner:** Backend (cases are backend-driven); frontend consumes. QA for list/get and admin create/update/delete.

---

## 6. Dialogue Subsystem

### 6.1 Current Implementation Status

**What is implemented?**
- Backend: DialogueService processes each user turn: loads session and case; gets next turn number; runs NLU (empathy, question type, elicitation/response/EO spans, SPIKES stage detection); creates user turn; calls LLM for patient response; analyzes assistant response (EO/spans); creates assistant turn; updates session SPIKES stage. Uses OpenAIAdapter and SimpleRuleNLU; SPIKES state machine with fallback turn-based progression.
- Frontend: CaseDetail sends user message via `submitTurn` (REST); displays patient reply and current SPIKES stage.

**What works end-to-end?**
- User sends message → backend runs NLU + LLM → patient reply and updated SPIKES stage returned → UI updates. Dialogue and scoring share the same turn/span model.

**What is shallow / placeholder / mock?**
- NLU is rule/keyword-based (SimpleRuleNLU); not a full ML model. LLM is live (OpenAI). Span detection and SPIKES stage logic are implemented but heuristic.

**What does not match SRS?**
- FR-3: Chat interface with "patient emotion indicators" — backend does not return a separate emotion label per message; frontend could derive from context or add later. Not a strict SRS violation if "indicators" are optional.

### 6.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-3 | Partially implemented | Text chat works; explicit patient emotion indicators not returned. |

### 6.3 Architectural Gaps

- **Separation of concerns:** DialogueService orchestrates LLM and NLU; controllers only call service. Good.
- **Missing APIs:** None; dialogue is invoked via session turn endpoints.
- **Missing validation:** Turn text length not bounded; could allow very long input.
- **Security:** Dialogue only within authenticated session; session ownership enforced.

### 6.4 Non-Functional Gaps

- **Performance:** Each turn is synchronous (LLM + NLU); latency depends on provider. No streaming in REST path.
- **Logging:** Errors logged; no structured audit of prompts or responses for compliance (acceptable if no PHI in logs).
- **Testing:** test_dialogue.py and test_conversation_fixture exist; coverage for dialogue flow.

### 6.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P1 | Optional: Return simple emotion/valence per assistant message if FR-3 requires it. |
| P2 | Add max length validation for turn text (e.g. 2000 chars). |

### 6.6 Owner Recommendation

- **Owner:** ML/backend (NLU + LLM integration); frontend only displays. QA for conversation flow and SPIKES progression.

---

## 7. WebSocket Subsystem

### 7.1 Current Implementation Status

**What is implemented?**
- Backend: Single WebSocket endpoint `GET /v1/ws/sessions/{session_id}`. On connect: accepts connection, creates DB session, instantiates DialogueService, sends welcome message, then loop: receive JSON text → extract `content` → TurnCreate → process_user_turn → send assistant message (or error). No authentication or authorization: any client can connect to any session_id and send/receive messages.

**What works end-to-end?**
- If a client connects to the WebSocket with a session_id, it can send messages and receive patient replies without providing a JWT or user identity. Session data (turns) are written to the DB under that session_id; ownership is not checked.

**What is shallow / placeholder / mock?**
- WebSocket handler uses `metadata` in the outgoing message dict while `WebSocketMessage` model has field `meta`; Pydantic may drop `metadata` (extra), so client receives `meta: null`. Minor bug.

**What does not match SRS?**
- FR-19: "WebSocket must not bypass auth." Currently the WebSocket **does bypass auth**: no token or user check; anyone can use any session_id. This is a **critical security gap**.

### 7.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-19 | Not implemented | No authentication or session-ownership check on WebSocket connection. |

### 7.3 Architectural Gaps

- **Security:** WebSocket accepts unauthenticated connections; no verification that the connected user owns the session. Violates SRS and allows data injection/access to other users’ sessions.
- **Missing APIs:** N/A; single endpoint.
- **Missing validation:** Session existence is implicit (dialogue_service will 404 if session missing); no upfront auth.

### 7.4 Non-Functional Gaps

- **Security:** Critical: unauthenticated and unauthorized WebSocket access.
- **Logging:** Connection and errors logged; no audit of who connected to which session.

### 7.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | Require authentication on WebSocket: accept token in query param or first message, validate JWT, resolve user, then verify session ownership (session.user_id == current_user.id or admin). Reject connection with 403 if invalid/unauthorized. |
| P0 | Document WebSocket auth in API docs and frontend (if frontend uses WS). |
| P1 | Fix WebSocketMessage: send `meta` not `metadata` in JSON. |
| P2 | Add integration test: connect with valid token and owned session → send message → receive reply; connect without token or with wrong session → reject. |

### 7.6 Owner Recommendation

- **Owner:** Backend (security-critical). Frontend may or may not use WebSocket (CaseDetail uses REST for turns); confirm and document.
- **Heavy:** Backend security; QA for auth and ownership tests.

---

## 8. Audio Subsystem

### 8.1 Current Implementation Status

**What is implemented?**
- Backend: `POST /v1/sessions/{session_id}/audio` accepts multipart `audio_file`; WhisperAdapter transcribes (OpenAI Whisper API); S3StorageAdapter uploads file and returns URL; transcribed text is then processed as a normal turn (DialogueService). TTS adapter exists (generic_tts_adapter) but is not used in the session flow (no patient audio reply in API response).
- Frontend: CaseDetail has microphone button and can call `submitAudioTurn`; backend supports wav/ogg/mp3.

**What works end-to-end?**
- User uploads audio → backend transcribes with Whisper → stores in S3 → processes as turn → returns text reply and optional audio_url (user’s recording URL). Patient (assistant) reply is text-only; no TTS playback.

**What is shallow / placeholder / mock?**
- TTS: Not integrated into session response; API_ENDPOINTS mentioned `audio_url` for patient reply but that is for the user’s uploaded file, not synthesized speech. So "voice output" is placeholder.
- ASR: Live Whisper; S3 required (env vars); failure if S3/Whisper not configured.

**What does not match SRS?**
- FR-5: Voice input is implemented (ASR); voice output (TTS) is not in the session flow. SRS says "Voice Input Placeholder" in frontend README — so input is beyond placeholder; output is missing.

### 8.2 SRS Mapping

| FR | Status | Justification |
|----|--------|---------------|
| FR-5 | Partially implemented | Voice input (ASR) works; TTS for patient reply not in use. |

### 8.3 Architectural Gaps

- **Separation of concerns:** ASR and storage in adapters; controller orchestrates. Good.
- **Missing APIs:** No separate "synthesize patient reply" endpoint; TTS could be added to turn response.
- **Missing validation:** File type/size limits not enforced (could allow very large uploads).
- **Security:** Same as sessions (auth and session ownership); audio stored in S3 with path including session_id.

### 8.4 Non-Functional Gaps

- **Performance:** Whisper and S3 add latency; acceptable for demo.
- **Security:** Audio files in S3 should not be publicly readable; presigned URLs or private bucket with auth.
- **Compliance:** Audio may be considered sensitive; ensure no PHI in filenames and retention policy.

### 8.5 What Must Be Done Before Final Demo

| Priority | Task |
|----------|------|
| P0 | Enforce file type (e.g. wav, ogg, mp3) and max size (e.g. 10 MB) on upload. |
| P1 | Document that TTS is out of scope for demo or add optional TTS to assistant turn (audio_url for synthesized reply). |
| P2 | Ensure S3 bucket is not public; use presigned URLs for playback if needed. |

### 8.6 Owner Recommendation

- **Owner:** Backend (ASR/S3); optional ML for TTS. Frontend only sends file and displays text. QA for upload and transcription accuracy.

---

## Summary Table

| Subsystem | MVP Status | Production Ready? | Risk Level | Priority |
|-----------|------------|-------------------|------------|----------|
| Auth | Partial | No | Medium | P0 (HTTPS, refresh/docs) |
| Sessions | Yes | Near | Low | P0 (fix feedback URL only) |
| Feedback | Partial | No | High | P0 (wrong URL + type mismatch) |
| Research | Yes | Near | Low | P1 (FR-15 placeholder doc) |
| Cases | Yes | Yes | Low | P2 |
| Dialogue | Yes | Near | Low | P1/P2 |
| WebSocket | No | No | **Critical** | P0 (auth required) |
| Audio | Partial | No | Medium | P0 (validation); P1 (TTS doc) |

---

## Top 5 Immediate Risks

1. **WebSocket has no authentication (FR-19).** Any client can connect to any `session_id` and read/write dialogue. **Mitigation:** Add token-based auth and session-ownership check before processing messages; reject unauthenticated/unauthorized connections.
2. **Feedback page uses wrong API and mock data.** Frontend calls `GET /v1/feedback/:id` (nonexistent) and falls back to mock; real feedback is at `GET /v1/sessions/:id/feedback`. **Mitigation:** Point `fetchFeedback` to sessions endpoint and align response type; remove mock fallback for that path.
3. **HTTPS not enforced (FR-9).** Production could run over HTTP. **Mitigation:** Enforce HTTPS at reverse proxy or app level and document in deployment guide.
4. **Audio upload has no file size/type validation.** Risk of DoS or abuse. **Mitigation:** Enforce allowed MIME types and max size (e.g. 10 MB).
5. **Token expiry and refresh not used.** Users may be logged out without clear messaging; refresh endpoint exists but is not used by frontend. **Mitigation:** Either implement refresh flow and return refresh_token on login, or document re-login and surface expiry in UI.

---

## 2-Week Stabilization Plan

**Week 1 — P0 security and integration**

- **Day 1–2:** WebSocket auth: require JWT (query or first message), validate and resolve user, verify session ownership; reject 401/403. Add test. Fix WebSocketMessage `meta` vs `metadata`.
- **Day 2–3:** Feedback integration: change frontend to `GET /v1/sessions/${sessionId}/feedback`; define TypeScript type from backend `FeedbackResponse`; update Feedback.tsx to use real fields; remove mock fallback for this endpoint.
- **Day 3–4:** HTTPS: add production checklist (e.g. Nginx/OpenShift TLS, redirect HTTP→HTTPS); add `require_https` or env note in settings if applicable.
- **Day 4–5:** Audio: validate content type (audio/wav, audio/ogg, audio/mpeg) and max size (e.g. 10 MB); return 400 for invalid uploads. Document TTS as out of scope or stub.

**Week 2 — Hardening and demo readiness**

- **Day 6–7:** Auth: add rate limiting on login/register (e.g. 5/min per IP); document refresh vs re-login; optional audit log for login success/failure.
- **Day 7–8:** Sessions: add integration test (create → turns → close → GET feedback). Research: document FR-15 fairness as placeholder.
- **Day 8–9:** Logging: ensure session create/close and research export are logged with user/session identifiers (no PHI). Quick pass on error messages for 403/404.
- **Day 9–10:** Demo run: full flow (login → case → chat → close → feedback) and research export; fix any regressions; update README with known limitations (instructor role, TTS, fairness metrics).

---

*End of Subsystem Audit.*
