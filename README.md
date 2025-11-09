# 🧠 MedLLM Interface – Capstone Project Team 16

Welcome to the **MedLLM Interface**, a McMaster University Capstone Project (COMPSCI 4ZP6A) supervised by **Dr. Allison Lahnala** and **Dr. Mehdi Moradi**.

---

## 📘 Overview

**MedLLM Interface** is an AI-powered training platform that helps medical trainees improve empathy and communication skills through realistic, simulated patient dialogues.

Leveraging large language models (LLMs) and structured empathy frameworks such as **SPIKES** and the **Appraisal Framework for Clinical Empathy**, MedLLM provides measurable, data-driven feedback on communication quality and empathy performance.  

This platform allows learners to practice delivering difficult diagnoses or counseling sessions in a controlled, repeatable, and ethical environment — offering instructors actionable insight into learner progress and skill development.

---

## ✨ Features

- **Interactive Empathy Training** – Trainees engage with simulated patients through text or voice conversations.
- **Real-Time Feedback** – Automated empathy analytics including:
  - Empathy Score (0 – 1)
  - Open-Question Ratio
  - Reassurance Count
  - SPIKES Stage Coverage
- **Instructor Dashboard** – View transcripts, empathy metrics, and export anonymized session data.
- **Bias & Fairness Mode** – Evaluate empathy-score consistency across demographics.
- **Audio Integration (PoC)** – Speech input/output using Whisper ASR and Wispr Flow TTS.
- **Research API** – Secure, read-only endpoints for session export and validation.
- **Security & Compliance** – PIPEDA-compliant; no PHI/PII stored; HTTPS + role-based access.

---

## 🧩 System Architecture

| Layer | Technology / Framework | Description |
|-------|------------------------|--------------|
| **Frontend** | React (TypeScript), Tailwind CSS | Real-time chat UI, feedback visualization, and responsive design. |
| **Backend / API** | Python FastAPI, Pydantic | Dialogue pipeline (NLU → DM → NLG), authentication, API gateway. |
| **Database** | PostgreSQL | Stores user sessions, feedback metrics, and SPIKES case data. |
| **Machine Learning** | GPT-4 / Gemini API, Hugging Face | Empathy analysis and model testing engine. |
| **Deployment** | Docker / OpenShift (GCP Canada) | Containerized deployment and portability. |
| **Testing** | PyTest, React Testing Library, Locust | Automated CI and load testing for performance validation. |

---

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/AsherHaroon/capstone.git
   cd capstone


## Team

Developed by Tung Ho, Asher Haroon, Michael Fedotov, Hammad Ur Rehman, Christian Canlas, Aaryan Kandwal, and Samir Matani as part of the final year capstone.
