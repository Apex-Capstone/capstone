"""Debug script to run test conversation through the pipeline.

Usage:
    poetry run python -m scripts.debug_test_conversation
    
Or if you have the poetry environment activated:
    python -m scripts.debug_test_conversation
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
except ImportError as e:
    print("ERROR: Missing dependencies. Please run:")
    print("  poetry install")
    print("  poetry run python -m scripts.debug_test_conversation")
    print("\nOr activate the poetry environment:")
    print("  poetry shell")
    print("  python -m scripts.debug_test_conversation")
    sys.exit(1)

from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from domain.entities.case import Case
from domain.entities.session import Session
from domain.entities.turn import Turn
from domain.entities.user import User
from repositories.case_repo import CaseRepository
from repositories.feedback_repo import FeedbackRepository
from repositories.session_repo import SessionRepository
from repositories.turn_repo import TurnRepository
from services.dialogue_service import DialogueService
from services.scoring_service import ScoringService
from tests.fixtures.conversation_fixture import TEST_CONVERSATION_GOOD

# Setup database
DATABASE_URL = "sqlite:///./dev.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

async def run_test_conversation():
    """Run test conversation through the pipeline."""
    print("=" * 80)
    print("RUNNING TEST CONVERSATION THROUGH PIPELINE")
    print("=" * 80)
    
    # Create test user if needed
    from repositories.user_repo import UserRepository
    user_repo = UserRepository(db)
    test_user = user_repo.get_by_email("test@example.com")
    if not test_user:
        test_user = User(
            email="test@example.com",
            hashed_password="test",  # Use plain password for testing
            role="trainee",
        )
        test_user = user_repo.create(test_user)
    
    # Create test case
    case_repo = CaseRepository(db)
    test_case = Case(
        title="Test Case - AFCE + SPIKES",
        description="Test case for debugging AFCE and SPIKES pipeline",
        script="Test script for AFCE + SPIKES pipeline debugging",  # Required field
        patient_background="Test patient",
    )
    test_case = case_repo.create(test_case)
    
    # Create session
    session_repo = SessionRepository(db)
    session = Session(
        user_id=test_user.id,
        case_id=test_case.id,
        state="active",  # Required field: active, paused, completed, abandoned
        current_spikes_stage="setting",
    )
    session = session_repo.create(session)
    
    print(f"\nCreated session {session.id} for case {test_case.id}")
    print("\n" + "=" * 80)
    
    # Initialize services
    llm_adapter = OpenAIAdapter()
    nlu_adapter = SimpleRuleNLU()
    dialogue_service = DialogueService(db, llm_adapter, nlu_adapter)
    turn_repo = TurnRepository(db)
    
    # Process each turn
    print("\nPROCESSING TURNS:")
    print("-" * 80)
    
    for i, turn_data in enumerate(TEST_CONVERSATION_GOOD):
        print(f"\nTurn {turn_data['turn_number']} ({turn_data['role']}):")
        print(f"  Text: {turn_data['text'][:80]}...")
        
        if turn_data['role'] == "user":
            # Process clinician turn
            from domain.models.sessions import TurnCreate
            turn_create = TurnCreate(
                text=turn_data['text'],
                audio_url=None,
            )
            
            # Note: This will generate a patient response via LLM
            # For testing, we might want to use the expected patient response instead
            # For now, we'll use the LLM but could override
            
            # Actually, let's create turns directly for more control
            # Create user turn manually
            user_turn = Turn(
                session_id=session.id,
                turn_number=turn_data['turn_number'],
                role="user",
                text=turn_data['text'],
                spikes_stage=turn_data.get('expected_spikes'),
            )
            
            # Analyze user input for spans
            user_metrics, user_spans = await dialogue_service._analyze_user_input(turn_data['text'])
            user_turn.metrics_json = json.dumps(user_metrics)
            user_turn.spans_json = json.dumps(user_spans) if user_spans else None
            
            user_turn = turn_repo.create(user_turn)
            print(f"  Created user turn {user_turn.id}")
            print(f"  Detected elicitations: {len([s for s in user_spans if s.get('span_type') == 'elicitation'])}")
            print(f"  Detected responses: {len([s for s in user_spans if s.get('span_type') == 'response'])}")
            
            # Create corresponding patient turn (from fixture, not LLM)
            if i + 1 < len(TEST_CONVERSATION_GOOD) and TEST_CONVERSATION_GOOD[i + 1]['role'] == "assistant":
                next_turn_data = TEST_CONVERSATION_GOOD[i + 1]
                patient_text = next_turn_data['text']
                
                # Analyze patient response
                assistant_metrics, assistant_spans = await dialogue_service._analyze_assistant_response(
                    patient_text,
                    user_turn,
                    0.0,  # No latency for test
                )
                
                patient_turn = Turn(
                    session_id=session.id,
                    turn_number=next_turn_data['turn_number'],
                    role="assistant",
                    text=patient_text,
                    metrics_json=json.dumps(assistant_metrics),
                    spans_json=json.dumps(assistant_spans) if assistant_spans else None,
                    spikes_stage=session.current_spikes_stage,
                )
                patient_turn = turn_repo.create(patient_turn)
                print(f"  Created patient turn {patient_turn.id}")
                print(f"  Detected EOs: {len(assistant_spans)}")
                
                # Skip next iteration since we already processed it
                # Actually, let's not skip - let's handle both roles
                # But we need to track this
    
    # Update SPIKES stages based on content (we'll implement this later)
    # For now, manually set SPIKES stages
    for turn_data in TEST_CONVERSATION_GOOD:
        if 'expected_spikes' in turn_data:
            turn = turn_repo.get_by_session_and_number(session.id, turn_data['turn_number'])
            if turn:
                turn.spikes_stage = turn_data['expected_spikes']
                db.commit()
    
    print("\n" + "=" * 80)
    print("GENERATING FEEDBACK:")
    print("-" * 80)
    
    # Generate feedback
    scoring_service = ScoringService(db)
    feedback = await scoring_service.generate_feedback(session.id)
    
    # Print feedback
    print("\nFEEDBACK SUMMARY:")
    print(f"  Empathy Score: {feedback.empathy_score}")
    print(f"  SPIKES Score: {feedback.spikes_completion_score}")
    print(f"  Overall Score: {feedback.overall_score}")
    
    print(f"\n  EO Spans: {len(feedback.eo_spans) if feedback.eo_spans else 0}")
    if feedback.eo_spans:
        for eo in feedback.eo_spans:
            print(f"    - {eo.get('dimension')} ({eo.get('explicit_or_implicit')}): {eo.get('text')}")
    
    print(f"\n  Elicitation Spans: {len(feedback.elicitation_spans) if feedback.elicitation_spans else 0}")
    if feedback.elicitation_spans:
        for el in feedback.elicitation_spans:
            print(f"    - {el.get('type')} {el.get('dimension')}: {el.get('text')}")
    
    print(f"\n  Response Spans: {len(feedback.response_spans) if feedback.response_spans else 0}")
    if feedback.response_spans:
        for resp in feedback.response_spans:
            print(f"    - {resp.get('type')}: {resp.get('text')}")
    
    print(f"\n  EO→Response Links: {feedback.eo_to_response_links}")
    print(f"  EO→Elicitation Links: {feedback.eo_to_elicitation_links}")
    print(f"  Missed Opportunities: {feedback.missed_opportunities}")
    print(f"  Linkage Stats: {feedback.linkage_stats}")
    
    print(f"\n  SPIKES Coverage: {feedback.spikes_coverage}")
    
    print("\n" + "=" * 80)
    print("FULL FEEDBACK JSON:")
    print("-" * 80)
    
    # Convert datetime objects to strings for JSON serialization
    import json as json_lib
    from datetime import datetime
    
    def json_serial(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    feedback_dict = feedback.model_dump(exclude_none=True)
    print(json_lib.dumps(feedback_dict, indent=2, default=json_serial))
    
    db.close()

if __name__ == "__main__":
    asyncio.run(run_test_conversation())

