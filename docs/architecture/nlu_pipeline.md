# NLU Pipeline

## Overview

The NLU pipeline extracts structured communication signals from learner and patient utterances.

These signals support dialogue state updates and post-session scoring.

The system uses a hybrid rule-based approach rather than a full machine learning classifier.

## Detected Signals

The pipeline identifies:

• open vs closed questions  
• empathy statements  
• elicitation attempts  
• emotional expressions from patients  
• tone indicators  

## Span Detection

The span detector identifies structured spans required for AFCE analysis.

Supported spans:

response spans  
elicitation spans  
empathic opportunity spans

## Example Output

{
  "question_type": "open",
  "tone": "supportive",
  "empathy_detected": true
}

## Implementation Location

backend/nlu/simple_rule_nlu.py  
backend/nlu/span_detector.py