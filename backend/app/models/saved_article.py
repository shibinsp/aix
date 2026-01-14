"""
Saved News Articles model.
Allows users to save and favorite news articles to their account.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class SavedArticle(Base):
    """User's saved news articles."""
    __tablename__ = "saved_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Article identifiers
    article_id = Column(String(255), nullable=False)  # External article ID from news source

    # Article data (stored locally since news is ephemeral)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=True)
    source = Column(String(255), nullable=False)
    source_url = Column(String(1000), nullable=True)
    article_date = Column(String(50), nullable=False)  # Original article date string
    tags = Column(ARRAY(String), default=[])

    # User preferences
    is_favorite = Column(Boolean, default=False)

    # Timestamps
    saved_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="saved_articles")

    # Indexes
    __table_args__ = (
        Index('ix_saved_articles_user_article', 'user_id', 'article_id', unique=True),
        Index('ix_saved_articles_user_favorite', 'user_id', 'is_favorite'),
    )

    def to_dict(self):
        return {
            "id": str(self.article_id),  # Return article_id as id for frontend compatibility
            "title": self.title,
            "summary": self.summary,
            "category": self.category,
            "severity": self.severity,
            "source": self.source,
            "source_url": self.source_url,
            "date": self.article_date,
            "tags": self.tags or [],
            "is_favorite": self.is_favorite,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
        }

    def __repr__(self):
        return f"<SavedArticle {self.article_id} by user {self.user_id}>"
