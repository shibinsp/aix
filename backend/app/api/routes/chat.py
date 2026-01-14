from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.sanitization import sanitize_for_prompt, validate_pagination
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage, MessageRole
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatHistory,
)
from app.services.ai import teaching_engine
from app.services.rag import knowledge_base

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_data: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=user_id,
        title=session_data.title,
        teaching_mode=session_data.teaching_mode,
        topic=session_data.topic,
        context=session_data.context,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse.model_validate(session)


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List user's chat sessions."""
    skip, limit = validate_pagination(skip, limit, max_limit=50)
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatHistory)
async def get_chat_session(
    session_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a chat session with messages."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get messages
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = messages_result.scalars().all()

    return ChatHistory(
        session=ChatSessionResponse.model_validate(session),
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    message: ChatMessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response."""
    # Get session
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get user for context
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    # Sanitize user message
    sanitized_content = sanitize_for_prompt(message.content)
    
    # Save user message
    user_message = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=sanitized_content,
    )
    db.add(user_message)

    # Get RAG context
    rag_context = knowledge_base.knowledge_base.get_context_for_query(sanitized_content)
    rag_sources = knowledge_base.knowledge_base.get_sources_for_query(sanitized_content)

    # Build message history
    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .limit(20)  # Last 20 messages for context
    )
    history = messages_result.scalars().all()

    messages = [
        {"role": msg.role.value, "content": msg.content}
        for msg in history
    ]
    messages.append({"role": "user", "content": message.content})

    # Generate AI response
    ai_response = await teaching_engine.generate_response(
        messages=messages,
        teaching_mode=session.teaching_mode,
        skill_level=user.skill_level.value if user else "beginner",
        rag_context=rag_context if rag_context else None,
    )

    # Save AI response
    ai_message = ChatMessage(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=ai_response,
        rag_context={"sources": rag_sources} if rag_sources else None,
    )
    db.add(ai_message)

    # Update session
    session.message_count += 2
    session.last_message_at = datetime.utcnow()

    await db.commit()
    await db.refresh(ai_message)

    return ChatMessageResponse.model_validate(ai_message)


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: UUID,
    message: ChatMessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get streaming AI response."""
    # Get session
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    # Save user message
    user_message = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=message.content,
    )
    db.add(user_message)
    await db.commit()

    # Get RAG context
    rag_context = knowledge_base.knowledge_base.get_context_for_query(message.content)
    rag_sources = knowledge_base.knowledge_base.get_sources_for_query(message.content)

    # Build message history
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

    async def generate():
        full_response = ""

        # Send RAG sources first
        if rag_sources:
            yield f"data: {json.dumps({'type': 'sources', 'data': rag_sources})}\n\n"

        # Stream AI response
        async for chunk in teaching_engine.generate_stream(
            messages=messages,
            teaching_mode=session.teaching_mode,
            skill_level=user.skill_level.value if user else "beginner",
            rag_context=rag_context if rag_context else None,
        ):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"

        # Save complete response
        ai_message = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=full_response,
            rag_context={"sources": rag_sources} if rag_sources else None,
        )
        db.add(ai_message)
        session.message_count += 2
        session.last_message_at = datetime.utcnow()
        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(ai_message.id)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    await db.delete(session)
    await db.commit()

    return {"message": "Chat session deleted"}


class RenameSessionRequest(BaseModel):
    title: str


@router.patch("/sessions/{session_id}")
async def rename_chat_session(
    session_id: UUID,
    request: RenameSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Rename a chat session."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.title = request.title
    await db.commit()
    await db.refresh(session)

    return ChatSessionResponse.model_validate(session)


@router.post("/quick-ask")
async def quick_ask(
    message: ChatMessageCreate,
    teaching_mode: str = "lecture",
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Quick ask without creating a session."""
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    # Get RAG context
    rag_context = knowledge_base.knowledge_base.get_context_for_query(message.content)
    rag_sources = knowledge_base.knowledge_base.get_sources_for_query(message.content)

    # Generate response
    messages = [{"role": "user", "content": message.content}]

    response = await teaching_engine.generate_response(
        messages=messages,
        teaching_mode=teaching_mode,
        skill_level=user.skill_level.value if user else "beginner",
        rag_context=rag_context if rag_context else None,
    )

    return {
        "response": response,
        "sources": rag_sources,
    }
