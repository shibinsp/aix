import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Integer, Text, ForeignKey, JSON, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class TeachingMode(str, enum.Enum):
    LECTURE = "lecture"
    SOCRATIC = "socratic"
    HANDS_ON = "hands_on"
    CHALLENGE = "challenge"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index('ix_chat_sessions_user_id', 'user_id'),
        Index('ix_chat_sessions_updated_at', 'updated_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)

    # Session configuration
    teaching_mode = Column(Enum(TeachingMode), default=TeachingMode.LECTURE)
    topic = Column(String(255), nullable=True)
    context = Column(JSON, default=dict)

    # Status
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)

    # AI model used
    model = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index('ix_chat_messages_session_id', 'session_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)

    # Message content
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # RAG context
    rag_context = Column(JSON, nullable=True)

    # Token usage
    tokens_used = Column(Integer, default=0)

    # Feedback
    feedback_rating = Column(Integer, nullable=True)
    feedback_text = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
