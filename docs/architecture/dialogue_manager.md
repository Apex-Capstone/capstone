# Dialogue Manager

## Overview

The Dialogue Manager is responsible for orchestrating the processing of each conversational turn during an active training session.

It coordinates the interaction between the NLU pipeline, dialogue state model, LLM adapter, and persistence layer.

The Dialogue Manager does not perform NLU or generation itself. Instead it manages the sequence of operations required to process a turn.

## Responsibilities

The Dialogue Manager performs the following tasks:

1. Validate session state
2. Retrieve conversation context
3. Run NLU analysis on learner input
4. Update dialogue state
5. Determine SPIKES stage
6. Persist clinician turn
7. Generate patient response via LLM
8. Analyze patient response for empathy opportunities
9. Persist patient turn
10. Return structured response to the frontend

## Relationship to Other Components

The Dialogue Manager coordinates:

NLU Pipeline  
Dialogue State Model  
SPIKES Stage Tracker  
LLM Adapter  
Turn Repository  
Scoring Engine

## Implementation Location

backend/services/dialogue_service.py

Primary function:

process_turn(session_id, learner_text)