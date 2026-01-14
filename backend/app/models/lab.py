import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, Text, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class LabType(str, enum.Enum):
    TUTORIAL = "tutorial"
    CHALLENGE = "challenge"
    CTF = "ctf"
    SIMULATION = "simulation"
    RED_VS_BLUE = "red_vs_blue"
    ALPHHA_LINUX = "alphha_linux"


class LabEnvironmentType(str, enum.Enum):
    DOCKER = "docker"
    VM = "vm"
    HYBRID = "hybrid"


class LabStatus(str, enum.Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class Lab(Base):
    __tablename__ = "labs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Lab configuration
    lab_type = Column(Enum(LabType), default=LabType.TUTORIAL)
    environment_type = Column(Enum(LabEnvironmentType), default=LabEnvironmentType.DOCKER)
    difficulty = Column(String(50), default="beginner", index=True)
    estimated_time = Column(Integer, default=30)
    points = Column(Integer, default=50)
    preset = Column(String(50), nullable=True)  # Alphha Linux preset

    # Infrastructure specification
    infrastructure_spec = Column(JSON, nullable=False, default=dict)

    # Flags and objectives
    flags = Column(JSON, default=list)
    objectives = Column(JSON, default=list)

    # Instructions and hints
    instructions = Column(Text, nullable=True)
    hints = Column(JSON, default=list)
    solution = Column(Text, nullable=True)

    # Metadata
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, default=list)
    is_published = Column(Boolean, default=False)
    is_ai_generated = Column(Boolean, default=False)

    # Owner - each user owns their labs
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    sessions = relationship("LabSession", back_populates="lab", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[created_by])


class LabSession(Base):
    __tablename__ = "lab_sessions"
    __table_args__ = (
        Index('ix_lab_sessions_user_id', 'user_id'),
        Index('ix_lab_sessions_status', 'status'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    lab_id = Column(UUID(as_uuid=True), ForeignKey("labs.id"), nullable=True)  # Nullable for standalone environments

    # Course context for lab-course integration
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=True)

    # Environment type (docker, vm, hybrid)
    environment_type = Column(Enum(LabEnvironmentType), default=LabEnvironmentType.DOCKER)
    preset = Column(String(50), nullable=True)  # Alphha Linux preset name

    # Session status
    status = Column(Enum(LabStatus), default=LabStatus.PENDING)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Container/VM information
    container_ids = Column(JSON, default=list)
    vm_id = Column(String(100), nullable=True)  # VM identifier for QEMU/KVM
    network_id = Column(String(100), nullable=True)
    access_url = Column(String(500), nullable=True)
    ssh_credentials = Column(JSON, nullable=True)
    ssh_port = Column(Integer, nullable=True)  # SSH port for access
    vnc_port = Column(Integer, nullable=True)  # VNC port for VM display

    # Progress
    flags_captured = Column(JSON, default=list)
    objectives_completed = Column(JSON, default=list)
    completed_objectives = Column(JSON, default=list)  # For lab-course integration (objective indices)
    score = Column(Integer, default=0)
    attempts = Column(Integer, default=0)

    # Session lifecycle tracking
    last_activity = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Activity log
    activity_log = Column(JSON, default=list)

    # Admin tracking
    terminated_by_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="lab_sessions")
    lab = relationship("Lab", back_populates="sessions")
    course = relationship("Course", foreign_keys=[course_id])
    lesson = relationship("Lesson", foreign_keys=[lesson_id])
