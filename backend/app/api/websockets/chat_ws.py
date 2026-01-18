import json
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.services.ai import teaching_engine
from app.services.rag import knowledge_base

logger = structlog.get_logger()
router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: {user_id}")

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)


manager = ConnectionManager()


@router.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat."""
    # Get token from query params
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    # Validate token
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Accept connection
    await manager.connect(websocket, user_id)

    try:
        async with AsyncSessionLocal() as db:
            # Verify session belongs to user
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                await websocket.send_json({
                    "type": "error",
                    "message": "Chat session not found",
                })
                await websocket.close()
                return

            # Get user for context
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()

            # Send session info
            await websocket.send_json({
                "type": "session_info",
                "session_id": session_id,
                "teaching_mode": session.teaching_mode,
                "topic": session.topic,
            })

            while True:
                try:
                    # Receive message
                    data = await websocket.receive_json()

                    if data.get("type") == "message":
                        content = data.get("content", "")
                        if not content:
                            continue

                        # Save user message
                        user_message = ChatMessage(
                            session_id=session_id,
                            role=MessageRole.USER,
                            content=content,
                        )
                        db.add(user_message)
                        await db.commit()

                        # Get RAG context
                        rag_context = knowledge_base.knowledge_base.get_context_for_query(content)
                        rag_sources = knowledge_base.knowledge_base.get_sources_for_query(content)

                        # Send sources first
                        if rag_sources:
                            await websocket.send_json({
                                "type": "sources",
                                "data": rag_sources,
                            })

                        # Get message history
                        messages_result = await db.execute(
                            select(ChatMessage)
                            .where(ChatMessage.session_id == session_id)
                            .order_by(ChatMessage.created_at)
                            .limit(20)
                        )
                        history = messages_result.scalars().all()

                        messages = [
                            {"role": msg.role.value, "content": msg.content}
                            for msg in history
                        ]

                        # Stream AI response
                        full_response = ""
                        await websocket.send_json({"type": "stream_start"})

                        try:
                            async for chunk in teaching_engine.generate_stream(
                                messages=messages,
                                teaching_mode=session.teaching_mode,
                                skill_level=user.skill_level.value if user else "beginner",
                                rag_context=rag_context if rag_context else None,
                            ):
                                full_response += chunk
                                await websocket.send_json({
                                    "type": "stream_chunk",
                                    "content": chunk,
                                })
                        except Exception as stream_error:
                            logger.error(f"AI streaming error: {stream_error}", session_id=session_id)
                            await websocket.send_json({
                                "type": "error",
                                "message": "Failed to generate AI response. Please try again.",
                            })
                            continue

                        # Save AI response
                        ai_message = ChatMessage(
                            session_id=session_id,
                            role=MessageRole.ASSISTANT,
                            content=full_response,
                            rag_context={"sources": rag_sources} if rag_sources else None,
                        )
                        db.add(ai_message)
                        session.message_count += 2
                        await db.commit()

                        # Send completion
                        await websocket.send_json({
                            "type": "stream_end",
                            "message_id": str(ai_message.id),
                        })

                    elif data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from WebSocket: {user_id}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid message format",
                    })
                except Exception as loop_error:
                    logger.error(f"Error in WebSocket message loop: {loop_error}", user_id=user_id, session_id=session_id)
                    await websocket.send_json({
                        "type": "error",
                        "message": "An error occurred. Please try again.",
                    })
                    # Don't break the loop for recoverable errors

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id)
        try:
            await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass  # Connection already closed
