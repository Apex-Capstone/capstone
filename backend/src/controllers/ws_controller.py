"""WebSocket controller for optional conversation mode."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from adapters.llm.openai_adapter import OpenAIAdapter
from adapters.nlu.simple_rule_nlu import SimpleRuleNLU
from adapters.storage import get_storage_adapter
from adapters.tts import get_tts_adapter
from config.logging import get_logger
from core.deps import verify_session_access
from core.errors import AuthorizationError
from core.security import decode_supabase_token
from db.base import SessionLocal
from domain.models.sessions import TurnCreate, WebSocketMessage
from repositories.session_repo import SessionRepository
from repositories.user_repo import UserRepository
from services.dialogue_service import DialogueService
from controllers.sessions_controller import _build_turn_audio_url

logger = get_logger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


async def _authenticate_websocket(websocket: WebSocket, session_id: int):
    """Validate the websocket token and confirm access to the requested session."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return None, None

    payload = decode_supabase_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None, None

    db = SessionLocal()
    try:
        supabase_user_id = payload.get("sub")
        if not supabase_user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
            db.close()
            return None, None

        user = UserRepository(db).get_by_supabase_id(supabase_user_id)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            db.close()
            return None, None

        session = SessionRepository(db).get_by_id(session_id)
        if session is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Session not found")
            db.close()
            return None, None

        try:
            verify_session_access(session, user)
        except AuthorizationError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden")
            db.close()
            return None, None
        return db, user
    except Exception:
        db.close()
        raise


@router.websocket("/sessions/{session_id}")
async def websocket_dialogue(websocket: WebSocket, session_id: int):
    """Authenticated websocket endpoint used by optional conversation mode."""
    db, current_user = await _authenticate_websocket(websocket, session_id)
    if db is None or current_user is None:
        return

    await websocket.accept()
    logger.info("WebSocket connection established for session %s", session_id)

    try:
        dialogue_service = DialogueService(
            db,
            OpenAIAdapter(),
            SimpleRuleNLU(),
            tts_adapter=get_tts_adapter(),
            storage_adapter=get_storage_adapter(),
        )

        await websocket.send_json(
            WebSocketMessage(
                type="connected",
                content="Conversation mode connected.",
                meta={"session_id": session_id, "user_id": current_user.id},
            ).model_dump()
        )

        while True:
            message_data = await websocket.receive_json()
            user_message = (message_data.get("content") or "").strip()
            message_meta = message_data.get("meta") or {}
            enable_tts = bool(message_meta.get("enable_tts"))

            if not user_message:
                await websocket.send_json(
                    WebSocketMessage(
                        type="error",
                        content="Message content cannot be empty.",
                    ).model_dump()
                )
                continue

            logger.info("Received websocket turn for session %s", session_id)

            try:
                response_turn = await dialogue_service.process_user_turn(
                    session_id,
                    TurnCreate(text=user_message, enable_tts=enable_tts),
                )
                assistant_audio_url = _build_turn_audio_url(
                    response_turn.id,
                    response_turn.audio_url,
                    response_turn.audio_expires_at,
                )

                await websocket.send_json(
                    WebSocketMessage(
                        type="assistant_message",
                        content=response_turn.text,
                        meta={
                            "turn_id": response_turn.id,
                            "spikes_stage": response_turn.spikes_stage,
                            "assistant_audio_url": assistant_audio_url,
                        },
                    ).model_dump()
                )

                if response_turn.spikes_stage:
                    await websocket.send_json(
                        WebSocketMessage(
                            type="stage_update",
                            content=response_turn.spikes_stage,
                            meta={"spikes_stage": response_turn.spikes_stage},
                        ).model_dump()
                    )
            except Exception as exc:
                logger.error("Error processing websocket turn for session %s: %s", session_id, exc)
                await websocket.send_json(
                    WebSocketMessage(
                        type="error",
                        content="An error occurred processing your message.",
                    ).model_dump()
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as exc:
        logger.error("WebSocket error for session %s: %s", session_id, exc)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except RuntimeError:
            pass
    finally:
        db.close()

