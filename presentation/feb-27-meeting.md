---
marp: true
theme: default
paginate: true
---

# APEX  
## AI Patient Experience Simulator  

### Architectural Rebaseline & Forward Roadmap  

From Stable PoC to Defensible Training Platform

---

# Project Refresher

## What is APEX?

APEX is an AI-powered patient communication training simulator designed to help medical trainees practice difficult conversations using the SPIKES framework.

### Core Goals

- Simulate realistic patient interactions  
- Provide structured feedback on empathy and communication  
- Support research-driven evaluation of training effectiveness  
- Enable role-based access for trainees, instructors, and researchers  

> APEX is not just a chatbot.  
> It is a structured training and evaluation system for high-stakes clinical communication.

---

# Core Training Loop

1. Trainee logs in  
2. Selects a structured case  
3. Conducts patient conversation (text + optional audio input)  
4. System tracks dialogue state and SPIKES progression  
5. Session is closed  
6. Structured feedback is generated  
7. Admin / research view anonymized session data  

---

# System Architecture Overview

### High-Level Flow

Frontend  
→ Auth Layer  
→ Session Controller  
→ Dialogue Service  
→ LLM Adapter  
→ Feedback Engine  
→ Research API  

The system is currently implemented as a **hybrid LLM-driven dialogue architecture** with structured analytics and post-session evaluation.

---

# Architectural Rebaseline

We conducted a full alignment review between:

- Implementation  
- SRS claims  
- V&V expectations  

### Outcomes

- Stabilized integration branch  
- Enforced role and session ownership  
- Removed mock dependencies  
- Structured research read-only endpoints  
- Identified architectural depth gaps  

This marks the transition from PoC stability to architectural refinement.

---

# Architectural Alignment Priorities (Sprint 6)

## Primary Focus Areas

### 1. Security & Compliance Corrections
- WebSocket authentication  
- HTTPS enforcement  
- Audit logging  

### 2. Dialogue Architecture Alignment
- Formalize NLU → DM → NLG loop  
- Introduce dialogue act layer  

### 3. Case Model Structural Improvements
- Structured demographics  
- Emotional state modeling  
- SPIKES stage formalization  

---

# Secondary Focus Areas

- Feedback depth and rubric-based evaluation  
- Audio capability completion  
- System validation & requirement conformance  

These will be phased in after core architectural risks are addressed.

---

# Forward Roadmap

## Phase 1 — Security Closure
- WebSocket authentication  
- HTTPS enforcement  
- Audit logging  

## Phase 2 — Dialogue & Case Structural Alignment
- Introduce Dialogue Manager layer  
- Define dialogue act taxonomy  
- Structured case models  

## Phase 3 — Feedback Depth Expansion
- Rubric-based scoring  
- Evidence-grounded explanations  
- Validation framework  

## Phase 4 — Audio & Validation
- TTS integration  
- Multimodal interaction loop  
- Requirement conformance testing  

## Phase 5 — P2 Video Integration (Optional)
- Session recording  
- Research artifact generation  
- Demonstration-ready workflows  

---

# Questions & Alignment

- Does this architectural direction align with expectations?
- Is dialogue modularization a priority for the final deliverable?
- Should feedback depth or audio take precedence?
- Any scope adjustments recommended?

---

# APEX

From functional prototype  
to  
architecturally defensible system.