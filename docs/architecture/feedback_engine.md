# Feedback Engine

## Overview

The Feedback Engine evaluates the learner’s communication performance after a session is completed.

The engine analyzes stored conversation turns and computes structured feedback metrics.

## Evaluation Dimensions

The current scoring system evaluates:

• empathy
• SPIKES stage coverage
• communication quality

## Empathy Evaluation

Empathy evaluation follows the AFCE framework.

The engine identifies:

empathic opportunities (EO)  
responses to EO  
elicitation attempts  
missed EO

## SPIKES Evaluation

The system tracks progression through SPIKES stages:

setting  
perception  
invitation  
knowledge  
empathy  
strategy_summary

## Communication Metrics

Additional metrics include:

open question ratio  
supportive tone detection  
elicitation attempts

## Output

The scoring engine produces a structured feedback report.

Example:

{
  "empathy_score": 82,
  "communication_score": 85,
  "spikes_score": 90
}

## Plugin-based Evaluator

The feedback engine is designed so that evaluation logic can evolve without changing the external API contract. To support this, the `ScoringService` will delegate its core evaluation work to a pluggable **`Evaluator`** component.

- `ScoringService` remains the stable entry point used by controllers and higher-level services.
- Internally, it will call an `Evaluator` plugin that:
  - reads session and turn data (including SPIKES stages and EO spans)
  - computes empathy, communication, and SPIKES metrics
  - constructs and returns a `FeedbackResponse` instance

The **`Evaluator` plugin must always return a `FeedbackResponse`** object that conforms to the existing schema in `domain.models.sessions`. This guarantees that:

- the API responses from endpoints that expose feedback remain stable, and
- experimental scoring algorithms can be swapped in or out without requiring any changes to frontend clients or external integrations.

In this design, the evaluator plugins are free to change *how* scores are calculated, but **`FeedbackResponse` remains the canonical API schema** for post-session feedback.

## Implementation Location

backend/services/scoring_service.py