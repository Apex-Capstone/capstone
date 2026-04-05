# APEX (AI Patient Experience Simulator) – Capstone Project

Welcome to the APEX (AI Patient Experience Simulator) Capstone Project.

## Project Overview

APEX is an AI-powered patient communication training platform for medical trainees.
It simulates doctor–patient conversations and provides structured feedback aligned with the **SPIKES communication framework** and the **Appraisal Framework for Clinical Empathy (AFCE)**.

The system combines a React + TypeScript frontend with a FastAPI backend and a plugin-based dialogue/scoring engine to:

- **Simulate realistic patient dialogue** with configurable virtual patient cases.
- **Evaluate communication quality and empathy**, including SPIKES stage coverage and AFCE-aligned metrics.
- **Provide analytics and research exports** so educators and researchers can study communication patterns over time.

Role-based access currently supports:

- **Trainee**: practice conversations, view feedback.
- **Admin**: manage cases, configure plugins, access analytics and research exports.

## Repository Structure

```
project-root/
├── backend/         # FastAPI application (API + database, plugins, services)
│   ├── src/
│   │   ├── app.py
│   │   ├── core/
│   │   ├── domain/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── controllers/
│   │   └── scripts/
│   └── README.md
│
├── frontend/        # React + Vite + TypeScript client
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/
│   │   └── types/
│   └── README.md
│
├── docs/            # architecture, design, and research documentation
└── README.md        # root project overview (this file)
```

---

## Core Features

- **Simulated patient interactions** – Trainees engage with virtual patients via a structured chat interface.
- **Structured empathy evaluation (SPIKES / AFCE)** – Automated metrics for stage coverage, question style, and empathic opportunity handling.
- **Session lifecycle management** – Create, resume, and close sessions with full transcript history.
- **Feedback and scoring engine** – Session summary, empathy scores, SPIKES completion, AFCE-style breakdowns, and conversation timelines.
- **Admin dashboard and research analytics** – Case management, session metrics, fairness-oriented analytics, and anonymized data export for research.
- **Bias & fairness views** – Visualizations to inspect score consistency across anonymized cohorts (where data is available).
- **Security & role-based access** – Supabase Auth with email verification, JWT-based API authorization, trainee/admin roles, and separation between training and research views.

---

## System Architecture

At a high level, APEX uses a layered, service-oriented architecture:

- **Frontend (React + TypeScript)** → SPA that handles authentication, role-aware routing, chat UI, feedback dashboards, admin and research views.
- **Backend API (FastAPI)** → RESTful endpoints for sessions, cases, feedback, admin operations, and research exports.
- **Dialogue & Scoring Services** → domain services for dialogue management, SPIKES/AFCE scoring, session lifecycle, and feedback generation.
- **LLM Adapter & NLU Pipeline** → abstraction layer for calling LLMs (e.g., OpenAI / Gemini) and running the NLU / turn analysis pipeline.
- **Database (PostgreSQL via SQLAlchemy)** → stores users, cases, sessions, turns, feedback, and plugin configuration.

Internally, the backend follows a layered structure:

- **Controllers** (`controllers/`) – FastAPI route handlers and request/response models.
- **Services** (`services/`) – business logic for dialogue, scoring, case management, sessions, and research/export flows.
- **Repositories** (`repositories/`) – database access using SQLAlchemy models.
- **Domain entities/models** (`domain/`) – core domain types and invariants.
- **Plugins** (`plugins/`) – patient models, evaluators, and metrics providers loaded through explicit imports and a small **registry**.

At startup, the app imports a fixed list of plugin modules (`PLUGIN_MODULES` in `backend/src/plugins/load_plugins.py`). Each module registers its classes with **`PluginRegistry`**. There is **no filesystem discovery**—add your module to that list (or ensure it is imported by a module already in the list) so registration runs.

**Registering a new plugin (short version):**

1. Add a Python module under `backend/src/plugins/` (e.g. `plugins/evaluators/my_evaluator.py`) implementing the right **Protocol** (`interfaces/`).
2. At module bottom, call `PluginRegistry.register_evaluator(MyEvaluator.name, MyEvaluator)` (or the matching register helper for patient/metrics). Set class attribute **`name`** to your stable registry key (typically `module.path:ClassName`).
3. Append your module path to **`PLUGIN_MODULES`** in `load_plugins.py`.
4. Point **settings** (or case/session overrides where supported) at that **`name`** string.
5. Run **`pytest`** under `backend/tests/plugins/` and add tests for your plugin.

---

## Plugin Architecture

APEX exposes a plugin system that allows researchers to extend patient behavior, evaluation logic, and metrics without modifying core services.
There are three main plugin types (see `backend/src/plugins` and `backend/src/interfaces`):

- **PatientModel** – defines how the virtual patient responds to clinician turns (e.g., default LLM-based patient model).
- **Evaluator** – computes overall feedback for a session, combining SPIKES coverage, AFCE-style empathy analysis, and other scores.
- **MetricsPlugin** – optional research metrics via a `compute` method; session metadata can record which metrics plugins were selected for a run.

Plugins are **registered in code** (on import) and **selected** via configuration and the **PluginRegistry**. Paths use the form `module.path:ClassName`. The **plugin manager** (`core/plugin_manager.py`) can also load classes from those path strings for settings-based defaults and tests.

---

## Tech Stack

**Backend**

- FastAPI (Python) for the REST API and controllers
- SQLAlchemy ORM and Alembic migrations for PostgreSQL
- Pydantic and pydantic-settings for configuration
- Plugin-based services for dialogue, evaluation, and metrics
- Poetry for dependency management
- Pytest for automated testing

**Frontend**

- React 18 + Vite
- TypeScript
- TailwindCSS
- Zustand for global state
- shadcn/ui + lucide-react for UI components and icons
- Axios for API communication

---

## Running the Project Locally

---

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/AsherHaroon/capstone.git
   cd capstone
   ```

### 1. Backend Setup

Navigate to the backend directory:

```bash
cd backend
poetry install
```

Create a `.env` file in `/backend` (see `.env.example` for reference):

```
# Database
database_url=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE?sslmode=require

# LLM keys
openai_api_key=your-openai-key
gemini_api_key=your-gemini-key

# Supabase storage (for assistant audio)
supabase_url=https://your-project.supabase.co
supabase_service_role_key=your-service-role-key
supabase_storage_bucket="patient audio files"

# Supabase Auth JWT verification
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Local paths
local_storage_path=./storage
public_base_url=http://localhost:8000
```

The `SUPABASE_JWT_SECRET` is found in your Supabase dashboard under **Project Settings > API > JWT Settings > Legacy JWT Secret**.

Set `PYTHONPATH` so the backend imports resolve before running:

PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

macOS / Linux:

```bash
export PYTHONPATH="$PWD/src"
```

Run the FastAPI server:

```bash
poetry run uvicorn src.app:app --reload
```

Access the API at `http://localhost:8000/v1`
OpenAPI documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup

Navigate to the frontend directory:

```bash
cd frontend
npm install
```

Create a `.env` file in `/frontend`:

```
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

The `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are found in your Supabase dashboard under **Project Settings > API**. The anon key is safe for frontend use.

Run the development server:

```bash
npm run dev
```

The interface will be available at `http://localhost:5173`.

---

## Creating Users

Authentication is handled by **Supabase Auth**. Users sign up through the frontend at `/signup` with email verification.

To create an admin user:

1. Create the user through the `/signup` page or the Supabase dashboard (**Authentication > Users > Add user**).
2. Set their role to admin MANUALLY in the database:

```sql
UPDATE core.users SET role = 'admin' WHERE email = 'admin@example.com';
```

---

## Roles and Permissions

| Role        | Access                                                                  |
| ----------- | ----------------------------------------------------------------------- |
| **Trainee** | Access to virtual cases, simulated patient chat, and feedback views     |
| **Admin**   | Full CRUD on cases, user/session oversight, analytics, and research API |

---

## Development Workflow

1. Start backend (`poetry run uvicorn src.app:app --reload`)
2. Start frontend (`npm run dev`)
3. Sign up at `/signup` or log in with an existing account
4. Navigate through:
   - `/dashboard` → trainee dashboard
   - `/case/:id` → chat interface
   - `/feedback/:sessionId` → feedback summary
   - `/admin` → admin analytics and case management
   - `/research` → research analytics view

---

## Research Orientation

APEX is designed to support research in clinical communication training and LLM-based dialogue evaluation:

- **Anonymized research exports** – Admins can export metrics and transcripts through dedicated research endpoints for offline analysis.
- **Fairness and bias analysis** – Research views surface aggregate metrics that can be used to study score consistency across anonymized cohorts.
- **Extensible evaluation stack** – The plugin architecture allows new evaluators and metrics to be introduced for experimental studies without changing core APIs.
- **Reproducible session data** – Session transcripts, SPIKES/AFCE metrics, and feedback summaries are stored in a structured form for downstream quantitative and qualitative analysis.

---

## Team

Developed by
**Tung Ho**, **Asher Haroon**, **Michael Fedotov**, **Hammad Ur Rehman**, **Christian Canlas**, **Aaryan Kandwal**, and **Samir Matani**
as part of the McMaster University 4ZP6A Capstone Project.
