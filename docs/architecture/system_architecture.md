# APEX System Architecture

## 1. System Overview

APEX (AI Patient Experience Simulator) is a web-based clinical communication training platform designed to help medical trainees practice empathetic communication, especially in difficult conversations such as breaking bad news. The system combines a learner-facing chat interface, a backend dialogue system, large language model (LLM) based patient simulation, automated feedback generation, and research-oriented data export. Its core instructional goal is to support structured empathy training using the SPIKES protocol while grounding feedback in the Appraisal Framework for Clinical Empathy (AFCE).  

The project follows the dialogue-system objective defined in the SRS: a modular pipeline composed of **NLU → Dialogue Management → NLG**, surrounded by secure storage, frontend interaction, and research access. The SRS also requires automated feedback, anonymized storage, research API access, and extensibility for future multimodal features such as audio, video, and emotion recognition.  

From a software-engineering perspective, APEX is designed as a layered system:

* **Frontend UI**
* **Backend API**
* **Dialogue and Scoring Services**
* **External LLM Adapter Layer**
* **PostgreSQL Persistence Layer**

This separation of concerns supports maintainability, testing, and future replacement of implementation details without changing high-level module contracts. That structure also matches the capstone design expectations for subsystem decomposition, module interfaces, implementation detail, and explicit component relationships.  

---

## 2. Architectural Goals and Design Principles

The architecture is driven by five main goals.

### 2.1 Educational alignment

The system must support communication training, not just general chat. This means conversation flow, state tracking, and feedback must be structured around educational frameworks rather than unconstrained generation. In APEX, this is achieved by combining SPIKES stage tracking with empathy-focused NLU and scoring.  

### 2.2 Modular replaceability

The SRS explicitly requires a modular dialogue system whose components are replaceable. This motivates the use of service boundaries and adapter layers, especially around LLM providers and optional speech modules. 

### 2.3 Research traceability

The system must support anonymized transcript export, metrics export, and research analysis. Therefore, architecture decisions prioritize structured storage of turns, spans, relations, scores, and metadata rather than storing only raw chat text.  

### 2.4 Safety and privacy

Because this is a healthcare-adjacent educational system, it must avoid PHI/PII storage, enforce authenticated access, and support auditability for research export. These requirements shape the authentication, storage, and export architecture.  

### 2.5 Incremental extensibility

The initial deployed system is primarily text-based, but the architecture must support audio input/output, multimodal analysis, and more advanced dialogue control later. This motivates explicit adapters and a service-oriented backend instead of a monolithic prompt-only architecture.  

---

## 3. High-Level System Pipeline

At a high level, APEX processes a training session as the following pipeline:

```text
User message
→ Backend API
→ Dialogue Service
→ NLU analysis
→ SPIKES stage update
→ LLM patient response generation
→ Turn persistence
→ Session state update
→ Feedback scoring
→ Research export availability
```

This maps directly onto the architecture presented in the SRS and later architecture-review slides: **Frontend → Backend API → Dialogue & Scoring Services → External LLM Adapter → PostgreSQL Database**.  

### 3.1 Step-by-step pipeline behavior

#### 1. User interaction

A trainee authenticates, selects a case, and submits a text message through the learner-facing UI. The UI is responsible for session control, message display, and feedback rendering. 

#### 2. API routing

The frontend sends a REST or WebSocket request to the backend controller layer. Controllers validate access, identify the target session, and dispatch to the appropriate service. 

#### 3. Dialogue orchestration

The `DialogueService` becomes the central orchestrator for a conversational turn. It loads session context, current SPIKES stage, relevant case information, and previous turns. 

#### 4. NLU feature extraction

The clinician’s message is analyzed using rule-based NLU components. These detect empathy cues, question types, tone markers, empathy opportunities, elicitation spans, response spans, and AFCE-related dimensions such as Feeling, Judgment, and Appreciation. 

#### 5. Dialogue-state update

The system updates conversation state, including current SPIKES stage and turn-level annotations. SPIKES progression is currently deterministic and rule-based, which supports explainability and testability. 

#### 6. Patient response generation

The dialogue layer calls an LLM adapter such as `OpenAIAdapter` or `GeminiAdapter`, passing case background, session history, current stage, and patient constraints. The LLM returns the simulated patient’s next utterance. 

#### 7. Persistence

Both learner and patient turns, plus derived metadata such as stage, spans, and relations, are stored in the database through repository-layer abstractions.  

#### 8. Feedback generation

When the session closes, `ScoringService` computes empathy, SPIKES, and communication metrics. This includes EO-response linking, EO-elicitation linking, missed opportunity computation, question breakdown, and latency-related metrics.  

#### 9. Research access

Closed sessions become available to admin and research interfaces through anonymized endpoints and export tools such as CSV and session JSON. Closed sessions are treated as immutable research artifacts.  

---

## 4. High-Level Component Architecture

The major architectural components are shown conceptually below.

```text
[Frontend UI]
    ↓
[API Controllers / Gateway]
    ↓
[Application Services]
    ├─ CaseService
    ├─ SessionService
    ├─ DialogueService
    └─ ScoringService
             ↓
      [NLU Components]
      ├─ SimpleRuleNLU
      └─ SpanDetector
             ↓
      [LLM Adapter Layer]
      ├─ OpenAIAdapter
      └─ GeminiAdapter
             ↓
      [Repository Layer]
      ├─ UserRepository
      ├─ CaseRepository
      ├─ SessionRepository
      ├─ TurnRepository
      └─ FeedbackRepository
             ↓
         [PostgreSQL]
```

This layered design matches the backend structure already documented in the team’s architecture review and design draft: **Controllers → Services → NLU + Dialogue Engine → Scoring Engine → Repository Layer**. 

---

## 5. Core System Components

## 5.1 Frontend UI

### Responsibility

The frontend provides the learner and admin/research interfaces. For trainees, it handles login, case selection, active session interaction, viewing closed sessions, and feedback display. For admins and researchers, it supports transcript inspection, case management, and analytics/export workflows. 

### Inputs

* Authentication tokens or login credentials
* Case selection actions
* User chat messages
* Session control actions

### Outputs

* Session creation requests
* Turn submission requests
* Session closure requests
* Requests for metrics, transcripts, and exports

### Design rationale

The frontend is intentionally kept separate from dialogue intelligence. This ensures that dialogue logic remains testable and reusable through the backend API, while the UI can evolve independently.

---

## 5.2 API Controller Layer

### Responsibility

Controllers expose the system’s external contract. They translate HTTP/WebSocket traffic into service calls, enforce authorization, validate request shape, and normalize responses.

### Main controller areas

* Authentication / role-based access
* Cases controller
* Sessions controller
* Research/admin endpoints

### Design rationale

This layer isolates transport concerns from domain logic. It prevents service classes from being tightly coupled to REST or UI details, which improves maintainability and testability. This also aligns with the course expectation that modules should expose a stable interface while hiding implementation details. 

---

## 5.3 Case Management Layer

### Responsibility

`CaseService` and related repositories manage predefined patient cases, including script/background, learning objectives, difficulty, and expected SPIKES flow. 

### Why it exists

Clinical communication training is scenario-dependent. The case layer provides the structural anchor that prevents the LLM from behaving like an unconstrained chatbot. Instead, each session is grounded in a patient role, pedagogical scenario, and expected communicative arc.

### Inputs

* Case metadata
* Admin CRUD actions
* Filtering and lookup requests

### Outputs

* Case records
* Scenario context for dialogue generation
* Structured case metadata for frontend presentation

---

## 5.4 Session Management Layer

### Responsibility

`SessionService` manages lifecycle state for each training session:

* session creation
* active vs completed state
* timestamps
* current SPIKES stage
* session duration
* retrieval of turn history

The architecture review slides describe this as session lifecycle management with persistence and active/closed distinction. 

### Why it exists

Dialogue processing depends on context continuity. Session state ensures each turn is interpreted relative to prior interaction rather than in isolation.

---

## 5.5 Dialogue Service

### Responsibility

`DialogueService` is the central orchestration engine for a turn. It performs the following sequence:

1. Load session and case context
2. Analyze user input with NLU
3. Update SPIKES stage
4. Persist clinician turn and annotations
5. Generate patient response through LLM adapter
6. Persist patient response
7. Return structured output to frontend

This matches the backend description in the current design draft. 

### Why it exists

Instead of letting the LLM own dialogue control, APEX places orchestration in a deterministic backend service. This is an important design choice because:

* session state must remain explicit
* SPIKES tracking must be inspectable
* turn persistence must be reliable
* feedback data must be derivable later
* LLM providers must remain replaceable

### Inputs

* session ID
* learner utterance
* case data
* prior turn history
* current SPIKES stage

### Outputs

* patient response
* updated stage
* turn annotations and metrics
* persisted turn records

---

## 5.6 NLU Architecture

### Responsibility

The NLU subsystem extracts structured communicative signals from learner utterances before and after generation. It does not aim for general semantic understanding. Instead, it focuses on the educationally relevant markers needed for feedback and dialogue control.

### Main modules

* `SimpleRuleNLU`
* `SpanDetector`

### NLU tasks currently supported

* empathy cue detection
* open vs closed question detection
* tone classification
* EO detection
* elicitation span detection
* empathic response span detection
* AFCE dimension tagging
* SPIKES keyword/stage cues

### Why rule-based first

The current design intentionally uses rule-based NLU because it is:

* transparent
* easy to validate against rubric logic
* stable across small data regimes
* easier to debug in a capstone setting

This comes with limitations, including brittleness, English-only behavior, and weak contextual reasoning, which the team has already identified as an architectural risk.  

---

## 5.7 LLM Patient Simulation Layer

### Responsibility

The LLM adapter layer converts structured conversation context into patient dialogue. It encapsulates provider-specific prompt formatting and API invocation.

### Current adapters

* `OpenAIAdapter`
* `GeminiAdapter`

### Inputs

* case description
* patient background
* conversation history
* current SPIKES stage
* optional dialogue constraints

### Outputs

* generated patient utterance

### Design rationale

This is deliberately implemented as an adapter layer rather than embedding provider logic inside the dialogue service. The SRS explicitly requires model switching capability as an enhanced requirement, and this architecture supports that goal. 

### Important architectural note

The LLM is used for **response generation**, not as the sole dialogue manager. This hybrid approach is more defensible than a pure prompt-only design because educational state, scoring inputs, and storage semantics remain system-controlled.

---

## 5.8 Scoring and Feedback Layer

### Responsibility

`ScoringService` computes post-session feedback aligned with empathy theory and SPIKES structure.

### Current metric families

* Empathy metrics

  * EO coverage
  * dimension matching
  * response timing
* SPIKES metrics

  * stage coverage
  * order/sequence quality
  * empathy behavior during relevant stages
* Communication metrics

  * open-question ratio
  * elicitation use
  * reassurance/support markers
* Technical metrics

  * latency and logging-related measures

These scoring categories are consistent with the SRS metrics table and the architecture review slides.  

### Core logic

The design draft documents the following logic:

* link EOs to elicitation attempts
* link EOs to empathic responses
* compute missed opportunities
* score SPIKES progression
* store structured feedback in a dedicated feedback record 

### Why scoring is post-session

Scoring is currently triggered on session close. This reduces coupling between real-time dialogue latency and evaluation logic, and it guarantees one consolidated feedback record per completed session. That design is already reflected in the review deck. 

---

## 5.9 Persistence Layer

### Responsibility

The repository and database layers store all durable system state:

* users
* cases
* sessions
* turns
* feedback
* exported analytics metadata

### Stored turn-level data

Turns include:

* role
* text
* timestamp
* stage
* spans/relations
* serialized metrics or annotations

### Stored session-level data

Sessions include:

* state
* current SPIKES stage
* started/ended timestamps
* duration
* metadata

### Stored feedback-level data

Feedback includes:

* empathy score
* communication score
* SPIKES completion score
* overall score
* EO statistics
* linkage statistics
* missed opportunities
* question breakdown
* bias probe metadata
* average latency 

### Why this matters

This storage model is richer than a simple transcript log. It preserves the analytical structure needed for:

* learner feedback
* instructor oversight
* research export
* future V&V and reliability analysis

---

## 5.10 Research Export Layer

### Responsibility

The research layer exposes anonymized session data, transcript summaries, metrics, and export artifacts through read-only endpoints and CSV/JSON output.

### Current research-oriented outputs

* anonymized session lists
* session JSON
* transcript CSV
* metrics CSV
* aggregated analytics
* bias probe metadata 

### Design rationale

Research export is not an afterthought; it is one of the system goals in the SRS. That means architecture must preserve anonymization boundaries and separate learner-facing concerns from research-facing concerns. 

---

## 6. Data Flow Through the System

The following example shows how one learner utterance moves through APEX.

### Example input

Learner:

> “I can see this is really overwhelming. Can you tell me what worries you most right now?”

### Step 1: Session lookup

The controller identifies the session and retrieves:

* case ID
* prior turns
* current SPIKES stage
* session state

### Step 2: NLU processing

`SimpleRuleNLU` and `SpanDetector` may detect:

* open question
* empathic response language
* elicitation
* AFCE dimension candidates such as Feeling
* possible SPIKES stage cues

Example structured result:

```json
{
  "question_type": "open",
  "tone": "supportive",
  "spans": [
    {
      "type": "response",
      "dimension": "Feeling",
      "text": "I can see this is really overwhelming",
      "confidence": 0.88
    },
    {
      "type": "elicitation",
      "dimension": "Feeling",
      "text": "what worries you most right now",
      "confidence": 0.91
    }
  ]
}
```

### Step 3: Dialogue-state update

The dialogue service may confirm or advance the SPIKES stage, for example remaining in or entering the Empathy stage depending on the existing conversational context. SPIKES tracking is explicit because the protocol’s six stages are central to the training design. 

### Step 4: LLM response generation

The service packages:

* patient background
* the learner’s latest turn
* prior conversation history
* current SPIKES stage
* case constraints

The selected adapter returns a patient response.

Example:

> “I’m scared that this means my treatment isn’t working.”

### Step 5: Persistence

The system stores:

* learner turn
* assistant turn
* derived spans
* relations
* stage metadata
* timestamps

### Step 6: Session close and scoring

When the session ends, the scoring layer evaluates whether:

* the learner responded to EOs
* elicitation deepened understanding
* stage order was reasonable
* empathy was expressed when needed
* open-question usage supported patient exploration

### Step 7: Export and analytics

The completed session becomes visible in admin/research views with anonymized metadata and closed-session immutability. 

---

## 7. Dialogue State Model

The dialogue state model is the set of variables APEX maintains across turns so the system behaves as a structured training simulator rather than a stateless chatbot.

## 7.1 Current tracked state

### Session state

* active / completed lifecycle state

### Conversational state

* turn history
* timestamps
* current SPIKES stage

### Case grounding state

* case ID
* patient persona/background
* expected communication context

### Derived learner behavior state

* detected empathy attempts
* open-question usage
* interruption or support markers
* turn-level annotations

This matches the SRS data schema direction, which already anticipates tracked patient state, learner patterns, and conversation state over time.  

## 7.2 Why explicit state matters

Without explicit dialogue state:

* stage progression becomes hidden inside prompts
* scoring becomes harder to justify
* the frontend cannot reliably show session progress
* researchers cannot reconstruct interaction structure
* V&V becomes weaker because behavior is less testable

## 7.3 Recommended future state extensions

The SRS and current architecture suggest natural future extensions:

* **patient emotional state**

  * anxious, confused, angry, resigned
* **conversation goals**

  * diagnosis disclosure, reassurance, treatment planning
* **knowledge state**

  * what the patient has already been told
* **uncertainty/conflict state**

  * unresolved concerns, unaddressed EO clusters
* **adaptation state**

  * whether patient cooperates more or less in response to communication quality

These would move APEX closer to adaptive virtual patient systems while staying compatible with the current layered design.

---

## 8. NLU Architecture in Detail

The APEX NLU layer is intentionally scoped around clinically relevant discourse signals.

## 8.1 Empathy Opportunity detection

AFCE-guided NLU identifies spans in patient turns that represent empathic opportunities. Following the research framing, these opportunities may be explicit or implicit and can correspond to different attitudinal dimensions such as Feeling, Judgment, or Appreciation. 

## 8.2 Elicitation detection

The system detects clinician phrases that invite the patient to elaborate on a feeling, judgment, or appraisal. This maps to the AFCE notion of eliciting opportunities rather than merely answering them. 

## 8.3 Empathic response detection

The system also identifies clinician responses that acknowledge, validate, or align with patient affective content. These responses form the basis for EO-response linkage during feedback generation. 

## 8.4 Question-type detection

Open and closed questions are tracked because open-ended questioning is both educationally relevant and directly referenced in the SRS metrics. 

## 8.5 Tone detection

Tone features provide coarse cues such as supportive, neutral, or potentially dismissive language. Tone contributes to feedback but remains secondary to span-based empathy logic.

## 8.6 AFCE span representation

Each detected span is stored as structured metadata, including:

* type
* dimension
* text
* character offsets
* confidence

This provides explainability and allows later auditing or export.

## 8.7 Limits of the current NLU design

The current rule-based architecture has known weaknesses:

* limited contextual reasoning
* fragile negation handling
* language rigidity
* heuristic confidence values
* imperfect overlap resolution for complex spans 

This is acceptable for the current stage because interpretability is prioritized, but it is one of the clearest future-upgrade paths.

---

## 9. Feedback Evaluation Architecture

The feedback architecture converts stored conversation traces into educational evaluation.

## 9.1 Core evaluation logic

### EO detection

Identify patient opportunities for empathy.

### EO-response linking

Determine whether the learner responded to an EO with a clinically appropriate empathic move.

### EO-elicitation linking

Determine whether the learner meaningfully explored an implicit or explicit opportunity.

### Missed opportunity detection

Identify cases where the learner redirected or failed to respond to a relevant empathic cue.

### SPIKES stage evaluation

Measure:

* stage coverage
* order consistency
* empathy-related performance within relevant stages

### Communication behavior scoring

Measure:

* open-question ratio
* elicitation use
* support/reassurance indicators
* turn timing and latency-related data

This structure is directly consistent with both the current design draft and the SRS metrics section.  

## 9.2 Why this architecture is stronger than a single LLM score

A single holistic LLM score would be easy to generate but weak for educational explanation. APEX instead stores interpretable sub-signals:

* what the patient expressed
* whether it was explored
* whether it was acknowledged
* where it happened in the protocol

That makes feedback more defensible to instructors and more useful to learners.

## 9.3 Output structure

The feedback entity stores:

* overall scores
* dimension counts
* linkage stats
* missed opportunities
* SPIKES coverage/timestamps
* question breakdown
* evaluator metadata 

---

## 10. Research Dataset Generation

Research export is a first-class subsystem in APEX, not just an admin convenience.

## 10.1 Export goals

* support transcript review
* enable anonymized research analysis
* study bias and fairness
* compare automated scores to instructor judgments
* support future publication-quality evaluation pipelines

These goals are stated in the SRS through research API access, fairness metrics, and feedback reliability targets. 

## 10.2 Exported artifacts

The architecture supports export of:

* transcript CSV
* metrics CSV
* session JSON
* anonymized session summaries
* bias probe metadata and analytics 

## 10.3 Anonymization strategy

The system avoids PHI/PII storage and relies on anonymized IDs and synthetic patient cases. This design reduces privacy risk and simplifies research sharing. 

## 10.4 Why structured export matters

Structured export allows downstream tasks such as:

* score validation
* error analysis
* rubric comparison
* fairness audits across demographic variants
* empirical analysis of empathy-event patterns

---

## 11. Relationship Between Research Framework and Architecture

One of the most important design decisions in APEX is that the research framework is not merely cited in documentation; it is encoded into system responsibilities.

## 11.1 AFCE to architecture mapping

### Empathic Opportunity

Mapped to:

* patient-turn span detection
* structured EO representation
* EO counts by dimension
* missed opportunity analysis

### Elicitation

Mapped to:

* clinician-turn span detection
* question classification
* EO-elicitation linkage

### Empathic Response

Mapped to:

* clinician-turn span detection
* EO-response linkage
* response-type summaries

### Feeling / Judgment / Appreciation

Mapped to:

* AFCE dimension labels within span metadata
* dimension-wise metrics
* dimension matching in scoring

This follows the AFCE paper’s emphasis on identifying spans and relations among EOs, elicitations, and responses to support more fine-grained and explainable clinical empathy analysis. 

## 11.2 SPIKES to architecture mapping

### Setting / Perception / Invitation / Knowledge / Empathy / Strategy-Summary

Mapped to:

* stage detection in dialogue service
* stage persistence in session and turn records
* stage coverage and order metrics
* case design expectations for training flow

The AFCE/SPIKES paper explicitly frames SPIKES as a six-stage structure for breaking bad news and highlights its integration with empathy annotation as useful for training tools.  

## 11.3 Why this mapping matters

This architecture is not just “LLM chat plus scoring.” It is a research-aligned educational system in which:

* theory determines what gets detected
* state determines how dialogue is interpreted
* metrics determine what gets fed back
* storage determines what can be validated later

That is the main reason the hybrid architecture is defensible for a capstone design document.

---

## 12. Relationship Between Components and SRS Requirements

The course design document expects an explicit mapping between components and requirements. 

| SRS Requirement              | Main Architectural Component(s)                             |
| ---------------------------- | ----------------------------------------------------------- |
| FR-1 Login System            | Frontend UI, Auth/API Layer                                 |
| FR-2 Case Selection          | Frontend UI, CaseService, CaseRepository                    |
| FR-3 Chat Interface          | Frontend UI, Sessions Controller, DialogueService           |
| FR-4 Dialogue System Core    | DialogueService, SimpleRuleNLU, SpanDetector, LLM Adapters  |
| FR-5 Session Logging         | SessionService, TurnRepository, SessionRepository, Database |
| FR-6 Feedback Summary        | ScoringService, FeedbackRepository, Frontend Feedback View  |
| FR-7 Admin Logs              | Admin UI, Research/Admin API, Repository Layer              |
| FR-8 Research API            | Research Export Layer, Feedback/Session Repositories        |
| FR-9 HTTPS + Security        | API Layer, Auth Layer, Deployment/Infrastructure            |
| FR-10 Audio Processing       | Speech Adapter, DialogueService extension path              |
| FR-11 Model Gateway          | LLM Adapter Layer                                           |
| FR-12 Feedback Visualization | Frontend Feedback UI, ScoringService                        |
| FR-13 Analytics Dashboard    | Admin/Research UI, Export Layer                             |
| FR-14 Case Authoring         | Admin UI, CaseService                                       |
| FR-15 Bias Probe Mode        | Research Layer, Scoring metadata, Case variation tooling    |

This mapping is consistent with the SRS functional requirements and the current architecture review presentation.  

---

## 13. Key Design Decisions and Justification

## 13.1 Hybrid dialogue architecture instead of pure LLM orchestration

APEX does not rely on a single prompt to both control dialogue and generate feedback. Dialogue control, persistence, and scoring are backend responsibilities, while the LLM primarily generates patient turns.

**Why:** better explainability, modularity, and validation.

## 13.2 Rule-based NLU for current stage

A rule-based NLU layer is used for early-stage educational feature extraction.

**Why:** transparent, debuggable, easier to align with SRS/V&V, and feasible without a large annotated English training corpus.

## 13.3 Feedback based on explicit relations

Feedback is based on EO-response and EO-elicitation relations rather than only generic sentiment or overall impressions.

**Why:** better alignment with AFCE and more pedagogically meaningful explanations.

## 13.4 Closed-session immutability

Once a session is closed, the exported research representation is treated as fixed.

**Why:** improves auditability, reproducibility, and trust in post-session feedback and analytics. This is also reflected in the team’s architecture slides. 

## 13.5 Adapter-based external services

LLM and speech integrations sit behind adapters.

**Why:** avoids vendor lock-in and supports FR-11 model gateway evolution. 

---

## 14. Current Architectural Risks

The team has already identified several credible architecture risks. 

### 14.1 LLM latency and variability

External generation may produce inconsistent formatting or slow responses.

### 14.2 Rule-based NLU brittleness

Current detection logic may fail on paraphrases, negation, or subtle implicit emotion.

### 14.3 Adapter instantiation overhead

Per-request adapter recreation may add unnecessary performance cost.

### 14.4 Audio validation and file handling gaps

Future speech paths require stronger validation and temporary-file lifecycle guarantees.

### 14.5 Feedback validity ceiling

If scoring depends too heavily on heuristics, it may not correlate strongly enough with instructor judgment.

These risks are architecturally important because they directly affect non-functional requirements such as latency, maintainability, and feedback reliability. 

---

## 15. Future Architectural Evolution

The current system is a strong hybrid baseline, but the architecture is intentionally designed to evolve.

### Likely next improvements

* dialogue act abstraction layer
* richer state model for patient affect and cooperation
* output validation layer for LLM responses
* rubric-based feedback expansion
* stronger fairness/bias-probe tooling
* audio stabilization and TTS/ASR hardening
* eventual learned NLU upgrades if annotated data becomes available

These directions are already consistent with the roadmap identified in the architecture review. 

---

## 16. Conclusion

The APEX architecture is designed as a modular, research-aligned clinical communication training system rather than a generic chatbot. Its structure separates user interaction, orchestration, language understanding, patient response generation, scoring, and data persistence into distinct responsibilities. This enables the system to satisfy the SRS requirement for a replaceable dialogue pipeline, support structured SPIKES-based training, provide explainable AFCE-informed feedback, and generate anonymized research artifacts for further study.  

Most importantly, the architecture translates theory into software structure:

* AFCE drives what is detected and linked
* SPIKES drives dialogue-state interpretation
* scoring logic converts interaction traces into educational feedback
* persistence and export make the system analyzable, testable, and extensible

For capstone purposes, this makes APEX not only functionally complete, but also architecturally defensible.  

---

## 17. Plugin Architecture: Stable vs Experimental Components

The APEX backend separates **stable, theory-grounded infrastructure** from **experimental, research-driven components**. This is necessary to support extensibility for clinical research while preserving the validated educational constructs implemented in the core dialogue engine.

SPIKES stage tracking and empathic opportunity (EO) detection are treated as **stable infrastructure** because they encode constructs that have already been validated in the literature:

- SPIKES protocol for delivering bad news: Baile et al., 2000
- Empathic opportunity analysis in physician–patient communication: Suchman et al., 1997

These frameworks define how conversations should be structured and how empathy events are theorized and annotated. In APEX, they are implemented through:

- explicit SPIKES stage tracking in the dialogue engine
- EO span detection and AFCE-aligned span types
- turn- and session-level persistence of these annotations for scoring and export

Because these constructs are part of the **definition of the training task itself**, they are not experimental and must remain stable.

### 17.1 Stable Core Components

The following backend components are considered **stable infrastructure** and must preserve their contracts over time:

- **DialogueService**: orchestrates turn processing, NLU, SPIKES stage updates, patient response generation, and turn persistence.
- **SPIKES stage tracker** (`StageTracker` and related logic): implements protocol-aware stage progression and storage.
- **EO detection pipeline** (`NLUPipeline`, `SimpleRuleNLU`, `SpanDetector` and span logic): detects empathic opportunities, elicitation, and empathic responses aligned with AFCE.
- **Session lifecycle** (`SessionService`, `Session` model): manages session creation, active/closed state, timestamps, and SPIKES state.
- **TurnResponse schema**: defines the API contract for returning individual turns from the dialogue system.
- **FeedbackResponse schema**: defines the API contract for returning post-session feedback and metrics.

These components encode the educational and research constructs that define what a “session”, “turn”, “SPIKES stage”, and “empathic opportunity” mean in APEX. Changing them would alter the semantics of the system rather than just the implementation.

### 17.2 Experimental / Plugin Components

Researchers need to experiment with different models and scoring approaches **around** this stable core. For that reason, APEX introduces a **plugin layer** for components whose internal behavior may change while their external contracts remain fixed:

- **Patient simulation models**:
  - Alternative implementations of the simulated patient (e.g., different LLM prompts, different model providers, or hybrid scripted/LLM behavior).
  - Exposed via a `PatientModel` plugin interface.
- **Evaluators / scoring algorithms**:
  - Alternative scoring pipelines that interpret the same stored turns, spans, and SPIKES stages in different ways.
  - Exposed via an `Evaluator` plugin interface that always returns `FeedbackResponse`.
- **Metrics calculators**:
  - Additional research-oriented metrics or analytic summaries derived from persisted sessions and feedback.
  - Exposed via `Metrics` plugin interfaces that compute extra, non-breaking analytics.

These components are **experimental** in the sense that researchers are expected to swap them in and out without touching controllers, session lifecycle, or database schemas.

### 17.3 Research Extensibility

The plugin architecture supports research extensibility in several ways:

- **Model experimentation**: new patient simulators can be introduced (e.g., different LLM configurations or non-LLM models) without changing `DialogueService` inputs/outputs or the `TurnResponse` schema.
- **Evaluation experimentation**: novel scoring algorithms can be evaluated side-by-side with the existing hybrid evaluator by implementing new `Evaluator` plugins that read the same structured turns and spans and still return `FeedbackResponse`.
- **Metrics experimentation**: additional analytics (e.g., new EO clustering metrics, timing features, or bias probes) can be added as metrics plugins that operate on existing persisted data without altering the core API.

In all cases, the plugin surface is **strictly bounded**: plugins can change *how* patient text, scores, or research metrics are computed, but they cannot:

- redefine what a `TurnResponse` or `FeedbackResponse` looks like
- bypass `DialogueService`, SPIKES tracking, or EO detection
- mutate session lifecycle semantics

### 17.4 Core / Plugin Relationship Diagram

The relationship between the stable core and the plugin layer can be summarized as:

```text
Core System
   |
   |-- Dialogue Engine (DialogueService, DialogueState)
   |-- SPIKES Tracker (StageTracker, session.current_spikes_stage)
   |-- EO Detection (NLUPipeline, SimpleRuleNLU, SpanDetector)
   |
   +-- Plugin Layer
          |-- Patient Models (PatientModel plugins)
          |-- Evaluators (Evaluator plugins)
          |-- Metrics (Metrics plugins)
```

This diagram emphasizes that plugins **attach to** the dialogue and scoring pipeline but do not replace the underlying SPIKES/EO infrastructure or the public API schemas.