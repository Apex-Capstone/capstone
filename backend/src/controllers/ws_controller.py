"""WebSocket controller for real-time dialogue."""

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from config.logging import get_logger
from core.deps import get_db
from domain.models.sessions import TurnCreate, WebSocketMessage
from services.dialogue_service import DialogueService

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/sessions/{session_id}")
async def websocket_dialogue(
    websocket: WebSocket,
    session_id: int,
):
    """WebSocket endpoint for real-time dialogue."""
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        # Initialize services
        # Note: We need to handle DB session properly in WebSocket context
        from db.base import SessionLocal
        db = SessionLocal()
        
        try:
            llm_adapter = OpenAIAdapter()
            nlu_adapter = SimpleRuleNLU()
            dialogue_service = DialogueService(db, llm_adapter, nlu_adapter)
            
            # Send welcome message
            await websocket.send_json(
                WebSocketMessage(
                    type="system_message",
                    content="Connected. You can start the conversation.",
                ).model_dump()
            )
            
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process user message
                user_message = message_data.get("content", "")
                logger.info(f"Received message: {user_message[:50]}...")
                
                # Create turn
                turn_data = TurnCreate(text=user_message)
                
                try:
                    # Process turn and get response
                    response_turn = await dialogue_service.process_user_turn(
                        session_id,
                        turn_data,
                    )
                    
                    # Send assistant response
                    await websocket.send_json(
                        WebSocketMessage(
                            type="assistant_message",
                            content=response_turn.text,
                            metadata={
                                "turn_id": response_turn.id,
                                "spikes_stage": response_turn.spikes_stage,
                            },
                        ).model_dump()
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing turn: {e}")
                    await websocket.send_json(
                        WebSocketMessage(
                            type="error",
                            content="An error occurred processing your message.",
                        ).model_dump()
                    )
        
        finally:
            db.close()
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

