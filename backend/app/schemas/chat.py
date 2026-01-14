from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    teaching_mode: str = "lecture"
    topic: Optional[str] = None
    context: Dict[str, Any] = {}


class ChatSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    teaching_mode: str
    topic: Optional[str] = None
    context: Dict[str, Any]
    is_active: bool
    message_count: int
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class RAGSource(BaseModel):
    title: str
    url: Optional[str] = None
    content_preview: Optional[str] = None
    relevance: float


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    rag_context: Optional[Dict[str, Any]] = None
    tokens_used: int
    feedback_rating: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatStreamChunk(BaseModel):
    type: str  # "content", "rag_sources", "done", "error"
    content: Optional[str] = None
    sources: Optional[List[RAGSource]] = None
    error: Optional[str] = None


class ChatHistory(BaseModel):
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
