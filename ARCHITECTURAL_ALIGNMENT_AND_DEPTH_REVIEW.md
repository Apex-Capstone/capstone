# ARCHITECTURAL ALIGNMENT & DEPTH REVIEW — APEX (AI Patient Experience Simulator)

**Document type:** Architectural and depth review for PM decision-making  
**Purpose:** Enable the Project Manager to gather subsystem owners, decide what must be deepened, what must be redesigned, and delegate work accordingly.  
**Focus:** Architecture, depth, and SRS/V&V alignment.  
**Scope:** This document is not a sprint plan, timeline, or lightweight status report. It is a formal technical assessment suitable for review by a research supervisor.

---

## PART 1 — Dialogue Architecture Validation

### 1.1 What the SRS and Documentation Claim

- **Root README (System Architecture):** States that the backend provides a *"Dialogue pipeline (NLU → DM → NLG)"*.
- **Backend README:** Lists adapters for *"nlu/"* (Natural language understanding) and describes *"Dialogue pipeline (NLU → DM → NLG)"*; states *"NLU: Rule-based NLU for empathy detection and question classification."*
- **Implicit V&V expectation:** A classical pipeline implies that NLU output informs a Dialogue Manager (DM), which produces dialogue acts or state updates, and NLG produces surface form—either from acts or from a modular generator.

### 1.2 Actual Implementation

- **NLU:** Implemented as `SimpleRuleNLU` and `SpanDetector`: keyword/rule-based detection of empathy cues, question type (open/closed), tone, AFCE-aligned spans (elicitation, response, empathy-opportunity), and SPIKES stage from clinician text. This runs on the **user (clinician) turn** before persistence and again on the **assistant (patient) turn** after generation.
- **Dialogue Manager (DM):** **There is no Dialogue Manager.** No component consumes NLU output to produce dialogue acts, state vectors, or intent/act structures. Session state is limited to `current_spikes_stage` (a string). Stage updates are driven by the same rule-based SPIKES detector and a turn-count fallback; no act-based state machine exists.
- **NLG:** Patient replies are produced by a single LLM call (`OpenAIAdapter.generate_patient_response`). Inputs to the LLM are: (1) a concatenated text *case_script* (patient background, scenario, instruction to roleplay), (2) raw *conversation_history* (list of `role`/`content`), and (3) *current_spikes_stage* (string). **No NLU-derived structures (spans, dialogue acts, intents) are passed to the LLM.** The LLM generates free-form text end-to-end; there is no separate NLG module (e.g. templates, act-to-surface, or conditioned generation from acts).
- **Data flow:** User text → NLU (metrics/spans/stage) → user turn stored with metrics → **LLM(case_script, history, stage)** → assistant text → NLU on assistant text (EO/spans for scoring only) → assistant turn stored. NLU output is used for **analytics and feedback only**; it does **not** influence the content or form of the next utterance.

### 1.3 Direct Answers

| Question | Answer |
|----------|--------|
| Do we have a true NLU → DM → NLG loop? | **No.** There is no DM. The loop is NLU (analytics) + monolithic LLM (generation). |
| Is NLU influencing generation? | **No.** The generator receives only raw dialogue history and the current SPIKES stage string. No spans, acts, or intents are passed to the LLM. |
| Is DM producing dialogue acts? | **N/A.** There is no DM. No dialogue acts are produced or consumed. |
| Is NLG modular or is the LLM end-to-end? | **End-to-end.** The LLM is the sole NLG. There is no modular NLG (e.g. act-to-surface or template layer). |

**Conclusion:** The system implements a **hybrid LLM pipeline**, not a classical NLU→DM→NLG architecture. The documented "Dialogue pipeline (NLU → DM → NLG)" is **architecturally inaccurate**. In practice: (1) NLU runs in parallel for scoring and stage tagging; (2) generation is a single black-box LLM call conditioned on text context and stage label; (3) no dialogue acts or NLU-derived control structures exist between understanding and generation. For a healthcare-training system, this matters: the architecture cannot be described as a transparent, auditable pipeline where each phase (understanding, decision, formulation) is separately verifiable.

### 1.4 What Would Need to Change for a True Modular Loop

- **Introduce a Dialogue Manager:** A component that receives NLU output (e.g. intents, dialogue acts, SPIKES-relevant labels) and session/case state, and produces a **dialogue act** or **response specification** (e.g. *express_emotion*, *request_clarification*, *acknowledge_concern*) for the patient at this turn. The DM would own SPIKES progression and scenario logic.
- **Make NLU feed the DM:** NLU output (and optionally span-level signals) must be passed into the DM as the primary input for deciding the next patient move, not only for post-hoc scoring.
- **Make NLG act-driven (or act-conditioned):** Either (a) a modular NLG that maps dialogue acts to surface form (templates, rules, or a small generator), or (b) an LLM explicitly conditioned on the **dialogue act(s)** produced by the DM, with clear separation between "what to say" (act) and "how to say it" (NLG). Today the LLM receives no act; it infers behaviour from prose instructions and history alone.
- **Define dialogue act taxonomy:** Establish a formal taxonomy of patient dialogue acts (and optionally clinician acts) aligned with SPIKES and the training objectives, and use it as the interface between DM and NLG.

---

## PART 2 — Feedback Depth Review

### 2.1 Current Feedback Metrics (Implementation)

- **Empathy:** AFCE-aligned span counts (EO by dimension and explicit/implicit; elicitation by type/dimension; response by understanding/sharing/acceptance); EO–response linking and missed opportunities; composite empathy score from coverage, dimension matching, and timing.
- **SPIKES:** Coverage (stages present), sequence correctness (order of stages), empathy-during-E component; completion score; timestamps and strategy keywords per stage.
- **Questioning:** Open/closed/eliciting counts and ratio.
- **Textual feedback:** Short strengths and improvement bullets from simple rules (e.g. empathy score threshold, open-question ratio, SPIKES score).
- **Placeholders:** Bias/fairness and evaluator metadata are null; no rubric-based item scores; no qualitative explanation depth.

All span detection and scoring are **rule/keyword-based** (SpanDetector, SimpleRuleNLU). No learned model for empathy or communication quality; no human-rubric alignment.

### 2.2 Comparison to Research Literature

- **SPIKES communication training:** Literature emphasizes structured phases, learner self-assessment, and often expert or peer rating against phase-specific behaviours. Typical evaluations use checklists or rubrics (e.g. did the learner set the scene, assess perception, invite information, etc.) with explicit criteria. **Current system:** SPIKES is approximated by keyword presence and turn order; there is no item-level rubric (e.g. "Did the trainee check understanding before giving knowledge?") or phase-specific behavioural criteria.
- **Empathy scoring:** Established instruments (e.g. CARE, NEPCS, KCEPS) use item-level rubrics with defined scales and, where used quantitatively, validated aggregation. **Current system:** Empathy is derived from keyword spans and EO–response linkage; there is no rubric itemisation, no calibration to human ratings, and no published validation of the scoring formula.
- **Medical communication assessment:** OSCE-style assessments typically use structured rubrics (e.g. 1–5 per item), qualitative comments, and sometimes global ratings. **Current system:** No multi-item rubric; no qualitative depth (e.g. explaining *why* a response was strong or weak with reference to the transcript); no dialogue-act-level evaluation (e.g. "This turn was a deflection rather than an acknowledgment").

### 2.3 What Is Superficial

- **Keyword/span counts as scores:** Raw counts and ratios (e.g. open-question ratio, EO coverage) are not equivalent to validated communication or empathy scales. Without rubric alignment and validation, they remain heuristic indicators.
- **Textual feedback:** Rule-based bullets (e.g. "Consider using more empathetic phrases") are generic; they are not grounded in specific turn-level evidence or dialogue acts.
- **SPIKES "coverage" and "sequence":** Based on keyword and turn order; they do not assess whether the trainee actually performed the intended *behaviours* (e.g. explicit perception check, clear invitation) as would be required in a rubric.
- **No qualitative explanation:** No narrative that ties scores to specific utterances or moments in the dialogue (e.g. "At turn 5 the patient expressed fear; your response was acknowledging; a stronger option would be…").

### 2.4 What Is Missing (Architectural)

- **Structured rubric scoring:** A feedback architecture that produces **item-level scores** (e.g. per SPIKES phase or per CARE-like dimension) from explicit criteria, not only aggregate counts.
- **Dialogue-act-based evaluation:** Representation of clinician (and optionally patient) turns as dialogue acts, and evaluation of appropriateness and quality at the act level (e.g. acknowledgment vs. deflection, open vs. closed elicitation).
- **Qualitative explanation depth:** A component that generates or selects **evidence-grounded** explanations: which turns or spans support the score, what was missed, and what would constitute an improvement, with reference to the transcript.
- **Calibration and validation:** A pipeline for aligning automated scores with human rubric scores (e.g. expert ratings) and reporting agreement or validation metrics. Without this, feedback is not academically defensible as an assessment tool.
- **Provenance and interpretability:** Clear provenance for each score component (which spans, which rules, which rubric item) so that feedback can be audited and explained.

### 2.5 Architectural Upgrades Required for Academically Defensible Feedback

1. **Introduce a rubric model:** Define a formal rubric (e.g. SPIKES phase behaviours + empathy/communication items) with discrete items and scale levels. Feedback must produce **per-item scores** (or explicit "not observed") in addition to any aggregate.
2. **Dialogue-act layer:** Add a layer that maps turns (or spans) to dialogue acts. Feedback logic should reason over **acts** (e.g. "elicitation open-feeling", "response acknowledgment") for both scoring and explanation.
3. **Evidence-grounded explanation:** Design an architecture for **qualitative feedback** that references specific turns/spans/acts and explains strengths and improvements with transcript evidence. This may involve templates, retrieval, or NLG conditioned on acts and scores.
4. **Validation and calibration:** Define an architecture for **human–system agreement**: collection of human rubric ratings, comparison to system scores, and reporting of reliability/validity (e.g. correlation, agreement). This is a design requirement, not only an operational step.
5. **Provenance and auditability:** Store and expose **provenance** for every score component (rules, spans, rubric item, model version) so that feedback can be reproduced and critiqued.

No implementation steps are specified here; these are **architectural requirements** that the system design must satisfy for academic defensibility.

---

## PART 3 — Cases Depth Review

### 3.1 Current Case Structure (Implementation)

- **Data model:** Case entity has `title`, `description`, `script` (large text), `objectives`, `difficulty_level`, `category`, `patient_background`, `expected_spikes_flow` (text). There are **no structured fields** for demographics (e.g. age, gender, ethnicity) or emotional state. Demographics and emotional cues appear only **inside the script prose** (e.g. "52-year-old woman", "34-year-old man").
- **Script content:** Scripts are freeform text with sections such as [Persona], [ClinicalContext], [SPIKES], [BehaviorRules]. SPIKES and behaviour are described in natural language for the LLM; they are not machine-parseable state machines or stage–response tables.
- **Expected SPIKES flow:** Stored as a comma-separated string (e.g. "setting, perception, invitation, knowledge, emotions, strategy"). It is not a structured model (e.g. graph, allowed transitions, or stage-specific expectations).
- **Variability:** No stochastic or branching model. The same case and script always yield LLM behaviour that is emergent from the prompt; there is no explicit variability (e.g. multiple persona variants, randomised presentation order, or conditional branches).

### 3.2 Assessment Against Depth Criteria

| Criterion | Present? | Notes |
|-----------|----------|--------|
| Structured demographics | **No** | Age, gender, etc. exist only in narrative script text. No structured fields or queryable attributes. |
| Emotional state progression | **No** | Emotional state is described in prose (e.g. "You may well up"); there is no explicit state variable or progression model (e.g. anxiety level by stage). |
| SPIKES stage expectations | **Partial** | Stage names and flow are described in text; `expected_spikes_flow` is a string. No machine-readable expectations (e.g. required behaviours per stage, success criteria). |
| Variability / stochastic elements | **No** | No alternate scripts, no randomisation, no branching scenario logic. |

### 3.3 Static Prompt Scripts vs. Structured Scenario Models

**Current state:** Cases are **static prompt scripts**. The case is a single block of instructional text that the LLM receives as context. Behaviour is emergent from the LLM’s interpretation of that text and the conversation history. There is no:

- Formal scenario state (e.g. variables for emotion, knowledge disclosed, patient goals).
- Stage–action or stage–response model that the system (DM or NLG) consults.
- Branching or conditional logic defined in the case (e.g. "if trainee uses jargon, patient asks for clarification" is in prose, not in executable logic).

So cases are **not** structured scenario models; they are **static prompt scripts** with rich narrative but no executable structure.

### 3.4 Recommended Architectural Enhancements

1. **Structured demographics:** Add first-class fields (e.g. age_range, gender, relevant social determinants) to the case model and to the API. Use them for filtering, reporting, and (if required) fairness/research; optionally pass them explicitly into the generator or DM.
2. **Emotional state model:** Define an explicit **emotional state** (or similar) dimension for the patient (e.g. anxiety, anger, acceptance) and either (a) a simple state machine that can be updated by rules/DM as a function of dialogue, or (b) a clear contract so that the generator receives current emotional state. This supports both consistent behaviour and feedback that reasons about emotion.
3. **Machine-readable SPIKES expectations:** Replace or supplement the freeform `expected_spikes_flow` with a **structured model** (e.g. stages with allowed transitions, required behaviours per stage, or success criteria). This enables the DM and feedback to reason about SPIKES in a programmatic way.
4. **Scenario variability:** Introduce a **variability layer**: e.g. multiple persona variants, optional branches (if/then in scenario logic), or parameterised difficulty. Cases would become scenario models that can be instantiated with different parameters rather than a single fixed script.
5. **Separation of script and behaviour logic:** Where possible, separate (a) narrative/instructional content for the LLM from (b) executable behaviour rules (e.g. when to escalate emotion, when to ask for clarification) so that scenario behaviour can be tested and verified independently of natural language.

---

## PART 4 — Audio Architecture Review

### 4.1 Current ASR Flow

- User uploads an audio file to `POST /v1/sessions/{session_id}/audio`.
- Backend: read file → **WhisperAdapter** (OpenAI Whisper API) → transcript text → **S3StorageAdapter** stores file, returns URL → transcript is passed to the **same dialogue pipeline** as a normal text turn (`TurnCreate(text=transcribed_text, audio_url=...)`). The patient reply is generated by the same LLM call as for text input.
- **Audio is not first-class:** The system does not use prosody, tone, or acoustic features for emotion or intent. Audio is a **transport** to obtain text; once transcribed, the pipeline is text-only.

### 4.2 TTS and Closing the Loop

- **TTS adapter:** A `GenericTTSAdapter` exists but is a **placeholder** (logs and returns empty bytes). It is **not** invoked in the session flow. The API can return an `audio_url` for the **user’s** uploaded recording (S3); it does **not** return synthesised speech for the patient reply.
- **Closing the loop:** A full voice loop would be: user speaks → ASR → text → dialogue → patient reply text → **TTS** → audio to user. Currently the loop is **open**: output is text only. Including TTS would **close** the voice loop and align with a "voice conversation" training scenario; without TTS, the system is text-in, text-out with optional voice input.

### 4.3 Fully Integrated vs. Transport

- **Current:** Audio is **a transport mechanism for text**. ASR converts speech to text; that text is processed exactly like typed input. No acoustic information influences dialogue or feedback. TTS is absent. The architecture is **not** fully integrated for voice on both sides.
- **Fully integrated (voice-in, voice-out):** Would require: (1) ASR as today; (2) TTS in the response path so the patient "speaks"; (3) optional use of prosody/emotion from ASR or TTS for feedback or DM (e.g. "trainee spoke in a calming tone", "patient sounded anxious"). That would be a **multimodal** design (text + audio as first-class channels).

### 4.4 What a True Multimodal Architecture Would Require

- **TTS in the response path:** Patient reply text → TTS → audio URL or stream returned to the client so that the trainee can hear the patient. This implies a TTS adapter implementation (e.g. cloud TTS) and a clear contract (e.g. voice_id, language) in the case or session.
- **Optional acoustic features:** If feedback or DM are to use voice: (a) extract or infer features from ASR (e.g. pace, pauses) or from a separate model; (b) pass them into the feedback or DM layer so that "how something was said" can influence scoring or behaviour. This would require defined interfaces for acoustic features.
- **Unified session representation:** Sessions would represent both text and audio artefacts (transcript + audio references) and optionally acoustic metadata, so that research and feedback can reason over multimodal evidence.
- **Access control and retention for audio:** Audio is sensitive. Architecture must specify storage (e.g. S3), access control, retention, and deletion so that it is PIPEDA- and policy-compliant.

---

## PART 5 — Security & Compliance Reality Check

Statements below are deliberate and uns softened.

### 5.1 WebSocket and FR-19

- **FR-19 (WebSocket must not bypass auth):** The WebSocket endpoint `/v1/ws/sessions/{session_id}` **does bypass authentication**. Any client can connect to any `session_id` without a token or user identity. The server does not validate JWT or session ownership before accepting the connection or processing messages. **Therefore the system is not compliant with FR-19.** This is a security defect: unauthenticated and unauthorized access to dialogue and the ability to inject or read turns for arbitrary sessions.

### 5.2 HTTPS and FR-9

- **FR-9 (HTTPS required):** The application code and configuration do **not** enforce HTTPS. There is no redirect from HTTP to HTTPS, no HSTS, and no `require_https`-style setting in the codebase. In a deployment that serves over HTTP, the system **does not comply** with FR-9. Compliance depends entirely on deployment (e.g. reverse proxy or load balancer) and is not guaranteed by the application.

### 5.3 PIPEDA Defensibility

- **Data minimization and purpose:** The project states that no PHI/PII are stored and that research export is anonymized. These are necessary but not sufficient for PIPEDA. Defensibility requires: (1) clear documentation of what is collected, for what purpose, and how long it is retained; (2) consent or lawful basis for processing; (3) individual access and correction where applicable; (4) safeguards (access control, encryption, audit). **Current state:** Anonymization and no-PHI claims support purpose limitation; there is no visible documentation of retention, consent flow, or individual rights handling. **Audit trails** (see below) are partial. Without documented policies and sufficient auditability, **PIPEDA defensibility cannot be asserted**; it must be explicitly addressed (policies, documentation, and possibly legal review).

### 5.4 Audit Trails

- **Current:** Login is not systematically logged (success/failure, user, timestamp). Research export is logged (admin user, timestamp, record count). Session create/close and access to sensitive data (e.g. session transcript, feedback) are **not** consistently audited. There is no unified audit log of who accessed which session or which export.
- **Assessment:** Audit trails are **not sufficient** for accountability and compliance review. To support PIPEDA and security reviews, the architecture should define: (1) authentication events (login/logout, failure); (2) access to sessions and feedback (who, when, which resource); (3) research export and admin actions; (4) secure, tamper-evident or append-only storage of audit records.

---

## PART 6 — Key Demonstration Workflows

### 6.A Supervisor Demo (Research-Depth Focus)

**Objective:** Show that the system is grounded in research and that the architecture supports defensible training and assessment.

**What must be shown:**

- **Dialogue architecture:** Clear explanation that the system uses a **hybrid LLM pipeline** (NLU for analytics, LLM for generation), not a classical NLU→DM→NLG loop. Honest statement that NLU does not currently drive generation and that there is no DM or dialogue-act layer. If roadmap includes a modular loop, outline the intended DM and act-based NLG.
- **Feedback depth:** Presentation of current metrics (AFCE spans, EO–response linking, SPIKES coverage/sequence) with the caveat that they are **keyword/rule-based** and not yet validated against human rubrics. Explicit statement of what is **missing** for academic defensibility: structured rubric scoring, dialogue-act-based evaluation, evidence-grounded qualitative feedback, and validation/calibration. Willingness to discuss architectural upgrades (rubric model, act layer, explanation component, validation pipeline).
- **Cases:** Show that cases are **static prompt scripts** with rich narrative but no structured scenario model (no executable state, no formal demographics, no variability). Discuss roadmap toward structured scenario models and emotional state if relevant to the research plan.
- **Research export:** Demonstrate anonymized export (no PII), read-only API, and logging of export actions. Acknowledge gaps in audit and PIPEDA documentation.

**Emphasis:** Transparency about architecture and depth, not overselling. The research-valid architecture that *should* be visible is: (1) a clear pipeline description (even if hybrid); (2) a path to rubric- and act-based feedback; (3) a path to structured cases; (4) security and compliance gaps and remediation plan.

### 6.B Capstone Professor Demo (SRS + V&V Focus)

**Objective:** Demonstrate that functional and security requirements are met (or explicitly called out as not met) and that key workflows are verifiable.

**Workflows to demonstrate:**

1. **FR compliance — Authentication and roles**
   - Log in as trainee and as admin; show that protected routes and role-based access work (e.g. admin sees admin panel, trainee does not). Show that unauthenticated requests to protected endpoints are rejected.
   - **Call out:** WebSocket does **not** enforce auth (FR-19 not met). HTTPS depends on deployment (FR-9).

2. **Role enforcement**
   - As trainee: list own sessions; create session; submit turns; close session; get feedback. As trainee: attempt to access another user’s session (expect 403). As admin: access admin sessions list and session detail; access research export.
   - Show that research and admin endpoints return 403 for non-admin.

3. **Research read-only**
   - Show that research API supports only GET (list sessions, get session by anon id, export JSON/CSV). No POST/PUT/DELETE on research routes. Show anonymized session IDs and redacted text in export.

4. **Session lifecycle**
   - Create session for a case → submit several text turns → observe patient replies and SPIKES stage updates → close session → retrieve feedback. Show that feedback is only available after close and that it includes scores and metrics. Optionally show session list and resume by session id.

5. **Audio integration**
   - Submit an audio turn (upload file) → show transcript and patient reply. Clarify that TTS is not in scope (patient reply is text only). Show that audio is used as **input** only (ASR → text → same pipeline).

**Proof points:** (1) REST API auth and role checks work. (2) WebSocket is **not** compliant and must be stated. (3) Research is read-only and anonymized. (4) Session create → turns → close → feedback is end-to-end. (5) Audio path is ASR → text; no TTS.

---

## PART 7 — Decision Matrix

| Subsystem | Architecturally Accurate? | Academically Defensible? | Needs Redesign? | Needs Depth? |
|-----------|---------------------------|--------------------------|-----------------|--------------|
| **Dialogue** | No. Documented as NLU→DM→NLG; implemented as hybrid LLM pipeline with NLU for analytics only. No DM; no dialogue acts; NLG is monolithic LLM. | No. Generation is black-box; no act-level control or transparency. | Yes, if a true modular loop (DM, act-based NLG) is required. | Yes: DM, dialogue act taxonomy, NLU→DM→NLG data flow. |
| **Feedback** | Partially. AFCE/SPIKES metrics and span linking are implemented as designed, but the design is heuristic (rules/keywords). | No. No rubric-based scoring, no validation against human ratings, no evidence-grounded qualitative explanation, no dialogue-act evaluation. | Optional redesign toward rubric + act-based evaluation. | Yes: structured rubric, act layer, explanation component, validation/calibration architecture. |
| **Cases** | Partially. Cases serve as LLM context as intended, but are not "structured scenario models." | No. No structured demographics, no emotional state model, no machine-readable SPIKES expectations, no variability. | Optional; depends on training and research goals. | Yes: structured demographics, emotional state, executable SPIKES expectations, variability. |
| **Audio** | Yes for ASR-as-transport. TTS is absent by design (placeholder). | N/A for assessment; TTS would deepen voice-training defensibility. | No full redesign; add TTS and optionally acoustic features if voice loop is required. | Yes if voice-in/voice-out and/or prosody-aware feedback are goals. |
| **Auth** | Yes. JWT, roles, dependencies are coherent. | N/A. | No. | Optional: refresh flow, rate limiting, audit logging. |
| **Sessions** | Yes. Lifecycle, ownership, and feedback hook are coherent. | N/A. | No. | Optional: audit of create/close. |
| **Research** | Yes. Read-only, anonymized, admin-only. | Partial; no fairness/bias metrics. | No. | Yes if FR-15 (fairness) is required: bias/fairness architecture. |
| **WebSocket** | No. No auth; violates documented security model. | N/A. | Yes. Must add authentication and session-ownership check. | Yes: auth, authorization, audit. |
| **Security & Compliance** | HTTPS not enforced in app; audit trails partial. | PIPEDA not documented; audit insufficient. | Enforce HTTPS in deployment and document; add audit architecture. | Yes: audit events, retention, PIPEDA documentation. |

---

*End of Architectural Alignment & Depth Review. No timelines or sprint breakdown are included; the matrix and parts 1–6 provide architectural clarity for PM decisions on ownership, depth, and redesign.*
