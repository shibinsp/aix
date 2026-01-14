import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class SkillDomain(Base):
    __tablename__ = "skill_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    skills = relationship("Skill", back_populates="domain", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SkillDomain {self.name}>"


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("skill_domains.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Skill metadata
    max_level = Column(Integer, default=5)  # 0-5 proficiency scale
    prerequisites = Column(JSON, default=list)  # List of skill IDs
    related_skills = Column(JSON, default=list)

    # Learning resources
    resources = Column(JSON, default=list)  # Links to courses, labs, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    domain = relationship("SkillDomain", back_populates="skills")
    user_skills = relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Skill {self.name}>"


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False)

    # Proficiency tracking
    proficiency_level = Column(Float, default=0.0)  # 0.0 - 5.0
    confidence_score = Column(Float, default=0.5)  # 0.0 - 1.0 (IRT-based)

    # Activity metrics
    total_practice_time = Column(Integer, default=0)  # minutes
    questions_attempted = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    labs_completed = Column(Integer, default=0)

    # Assessment history (for IRT calculations)
    assessment_history = Column(JSON, default=list)
    # Example: [{"timestamp": "...", "question_id": "...", "correct": true, "difficulty": 0.7}]

    # Timestamps
    last_practiced = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="user_skills")

    def __repr__(self):
        return f"<UserSkill {self.user_id}:{self.skill_id}>"
