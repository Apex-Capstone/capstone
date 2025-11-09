# MedLLM Interface – Capstone Project

Welcome to the MedLLM Interface Capstone Project.

## Overview

The MedLLM Interface is an AI-powered empathy-training platform designed for medical trainees.
It allows learners to engage in simulated patient conversations and receive structured feedback aligned with the **SPIKES communication framework**.
The system integrates an interactive frontend built with React and a FastAPI backend with modular services, data persistence, and authentication.

## Features

* **Role-based authentication** (Trainee, Instructor, Admin)
* **Virtual patient cases** with structured scripts and difficulty levels
* **Interactive chat interface** simulating patient dialogue
* **Feedback dashboard** with empathy and communication metrics
* **Admin panel** for case management and analytics
* **SPIKES-aligned metrics** (Setting, Perception, Invitation, Knowledge, Emotions, Strategy)
* **Secure JWT authentication** and persistent state management

## Project Structure

```
project-root/
├── backend/         # FastAPI application (API + database)
│   ├── src/
│   │   ├── app.py
│   │   ├── core/
│   │   ├── domain/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── controllers/
│   │   └── scripts/seed.py   # database seeding script
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
└── README.md        # root project overview (this file)
```

## Getting Started

### 1. Backend Setup

Navigate to the backend directory:

```bash
cd backend
poetry install
```

Create a `.env` file in `/backend`:

```
APP_ENV=development
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=supersecretkey
ACCESS_TOKEN_EXPIRE_MINUTES=120
BACKEND_CORS_ORIGINS=http://localhost:5173
API_V1_PREFIX=/v1
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
```

Run the development server:

```bash
npm run dev
```

The interface will be available at `http://localhost:5173`.

---

## Seeding Development Data

You can populate the database with example users and cases for testing.

Run the seeding script from `/backend`:

```bash
poetry run python -m src.scripts.seed
```

This creates demo accounts:

| Role       | Email                                                         | Password      |
| ---------- | ------------------------------------------------------------- | ------------- |
| Admin      | [admin@example.com](mailto:admin@example.com)                 | admin123      |
| Instructor | [instructor@example.com](mailto:instructor@example.com)       | instructor123 |
| Trainee    | [alice.trainee@example.com](mailto:alice.trainee@example.com) | changeme      |

You can re-run with `--reset` to clear and reseed:

```bash
poetry run python -m src.scripts.seed --reset
```

---

## Roles and Permissions

| Role           | Access                                                   |
| -------------- | -------------------------------------------------------- |
| **Trainee**    | Access to virtual cases, chat, and feedback              |
| **Instructor** | Manage and review cases, limited analytics               |
| **Admin**      | Full CRUD on cases, user management, analytics dashboard |

---

## Technologies Used

**Backend**

* FastAPI
* SQLAlchemy ORM
* Poetry for dependency management
* JWT authentication
* Pytest for testing

**Frontend**

* React 18 + Vite
* TypeScript
* TailwindCSS
* Zustand for global state
* shadcn/ui + lucide-react for UI
* Axios for API communication

---

## Development Workflow

1. Start backend (`poetry run uvicorn src.app:app --reload`)
2. Start frontend (`npm run dev`)
3. Log in with a seeded account
4. Navigate through:

   * `/dashboard` → trainee dashboard
   * `/case/:id` → chat interface
   * `/feedback/:sessionId` → feedback summary
   * `/admin` → admin analytics and case management
   * `/research` → research analytics view

---

## Team

Developed by
**Tung Ho**, **Asher Haroon**, **Michael Fedotov**, **Hammad Ur Rehman**, **Christian Canlas**, **Aaryan Kandwal**, and **Samir Matani**
as part of the McMaster University 4ZP6A Capstone Project.


