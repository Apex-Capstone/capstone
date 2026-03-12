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

## Implementation Location

backend/services/scoring_service.py