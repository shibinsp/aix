"""Persistent environment models for terminal and desktop VMs."""
import uuid
import enum
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, Date,
    ForeignKey, Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EnvironmentType(str, enum.Enum):
    """Types of persistent environments."""
    TERMINAL = "terminal"
    DESKTOP = "desktop"


class EnvironmentStatus(str, enum.Enum):
    """Status of a persistent environment."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class PersistentEnvironment(Base):
    """Persistent terminal/desktop environment for each user.

    Terminal and Desktop share the SAME Docker volume (volume_name).
    Both mount to /home/alphha - files are shared between environments.
    """
    __tablename__ = "persistent_environments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Environment type
    env_type = Column(Enum(EnvironmentType), nullable=False)

    # Container/VM information
    container_id = Column(String(100), nullable=True)
    vm_id = Column(String(100), nullable=True)

    # Docker volume for persistence - SHARED between terminal & desktop
    # Format: "user_{user_id_prefix}_data"
    volume_name = Column(String(100), nullable=False)

    # Connection information
    ssh_port = Column(Integer, nullable=True)
    vnc_port = Column(Integer, nullable=True)
    novnc_port = Column(Integer, nullable=True)
    access_url = Column(String(500), nullable=True)

    # Credentials (for desktop VNC)
    vnc_password = Column(String(100), nullable=True)

    # Status tracking
    status = Column(Enum(EnvironmentStatus), default=EnvironmentStatus.STOPPED, nullable=False)
    last_started = Column(DateTime(timezone=True), nullable=True)
    last_stopped = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Usage tracking
    total_usage_minutes = Column(Integer, default=0, nullable=False)
    monthly_usage_minutes = Column(Integer, default=0, nullable=False)
    usage_reset_date = Column(Date, nullable=True)

    # Resource allocation
    memory_mb = Column(Integer, default=512, nullable=False)  # Terminal: 512, Desktop: 2048
    cpu_cores = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="persistent_environments")

    __table_args__ = (
        UniqueConstraint('user_id', 'env_type', name='uix_user_env_type'),
        Index('ix_persistent_env_status', 'status'),
    )

    def __repr__(self):
        return f"<PersistentEnvironment user={self.user_id} type={self.env_type.value} status={self.status.value}>"

    @property
    def is_running(self) -> bool:
        """Check if environment is running."""
        return self.status == EnvironmentStatus.RUNNING

    @property
    def is_available(self) -> bool:
        """Check if environment can be started."""
        return self.status in (EnvironmentStatus.STOPPED, EnvironmentStatus.ERROR)

    @property
    def connection_info(self) -> dict:
        """Get connection information for the environment."""
        info = {
            "env_type": self.env_type.value,
            "status": self.status.value,
        }

        if self.env_type == EnvironmentType.TERMINAL:
            info["ssh_port"] = self.ssh_port
            info["connection_string"] = f"ssh -p {self.ssh_port} alphha@localhost" if self.ssh_port else None
        else:  # DESKTOP
            info["vnc_port"] = self.vnc_port
            info["novnc_port"] = self.novnc_port
            info["access_url"] = self.access_url
            info["vnc_password"] = self.vnc_password

        return info

    def mark_started(self, container_id: str = None, vm_id: str = None) -> None:
        """Mark environment as started."""
        self.status = EnvironmentStatus.RUNNING
        self.last_started = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.error_message = None
        if container_id:
            self.container_id = container_id
        if vm_id:
            self.vm_id = vm_id

    def mark_stopped(self) -> None:
        """Mark environment as stopped and calculate usage."""
        if self.last_started and self.status == EnvironmentStatus.RUNNING:
            # Calculate session duration
            duration = datetime.utcnow() - self.last_started
            minutes = int(duration.total_seconds() / 60)
            self.total_usage_minutes += minutes
            self.monthly_usage_minutes += minutes

        self.status = EnvironmentStatus.STOPPED
        self.last_stopped = datetime.utcnow()
        self.container_id = None
        self.vm_id = None
        self.ssh_port = None
        self.vnc_port = None
        self.novnc_port = None
        self.access_url = None

    def mark_error(self, message: str) -> None:
        """Mark environment as error state."""
        self.status = EnvironmentStatus.ERROR
        self.error_message = message

    def reset_monthly_usage(self) -> None:
        """Reset monthly usage counter."""
        today = date.today()
        if self.usage_reset_date is None or self.usage_reset_date.month != today.month:
            self.monthly_usage_minutes = 0
            self.usage_reset_date = today

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    @staticmethod
    def get_shared_volume_name(user_id: str) -> str:
        """Generate shared volume name for a user.

        Both terminal and desktop use the SAME volume.
        """
        return f"user_{str(user_id)[:8]}_data"

    @classmethod
    def get_default_resources(cls, env_type: EnvironmentType) -> dict:
        """Get default resource allocation for environment type."""
        if env_type == EnvironmentType.TERMINAL:
            return {"memory_mb": 512, "cpu_cores": 1}
        else:  # DESKTOP
            return {"memory_mb": 2048, "cpu_cores": 2}


class EnvironmentSession(Base):
    """Track individual sessions for a persistent environment.

    Used for detailed usage analytics and billing.
    """
    __tablename__ = "environment_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    environment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persistent_environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Session timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    # Session context
    lab_id = Column(UUID(as_uuid=True), nullable=True)  # If started for a specific lab
    course_id = Column(UUID(as_uuid=True), nullable=True)  # If started for a course lab

    # Resource usage
    peak_memory_mb = Column(Integer, nullable=True)
    peak_cpu_percent = Column(Integer, nullable=True)

    # Termination reason
    termination_reason = Column(String(100), nullable=True)  # user_stopped, timeout, error, admin_stopped

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    environment = relationship("PersistentEnvironment")
    user = relationship("User")

    __table_args__ = (
        Index('ix_env_sessions_user_dates', 'user_id', 'started_at'),
    )

    def __repr__(self):
        return f"<EnvironmentSession env={self.environment_id} user={self.user_id}>"

    def end_session(self, reason: str = "user_stopped") -> None:
        """End the session and calculate duration."""
        self.ended_at = datetime.utcnow()
        if self.started_at:
            duration = self.ended_at - self.started_at
            self.duration_minutes = int(duration.total_seconds() / 60)
        self.termination_reason = reason
