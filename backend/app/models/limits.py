"""Resource limits models for organizations, batches, and users."""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization, Batch


# Default system limits
DEFAULT_LIMITS = {
    "max_courses_per_user": 5,           # Lifetime total
    "max_ai_generated_courses": 3,       # Per month
    "max_concurrent_labs": 1,            # Active sessions
    "max_lab_duration_minutes": 60,      # Auto-terminate
    "max_terminal_hours_monthly": 30,    # Persistent terminal
    "max_desktop_hours_monthly": 10,     # Persistent desktop
    "max_storage_gb": 2,                 # Per user storage
    "enable_persistent_vm": True,        # Allow persistent environments
}


class OrganizationResourceLimit(Base):
    """Resource limits for an organization (applies to all members)."""
    __tablename__ = "organization_resource_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Course limits
    max_courses_per_user = Column(Integer, default=10, nullable=False)
    max_ai_generated_courses = Column(Integer, default=5, nullable=False)  # Per month

    # Lab limits
    max_concurrent_labs = Column(Integer, default=2, nullable=False)
    max_lab_duration_minutes = Column(Integer, default=120, nullable=False)

    # VM/Terminal limits
    max_terminal_hours_monthly = Column(Integer, default=50, nullable=False)
    max_desktop_hours_monthly = Column(Integer, default=20, nullable=False)
    enable_persistent_vm = Column(Boolean, default=True, nullable=False)

    # Storage limits
    max_storage_gb = Column(Integer, default=5, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="resource_limits")

    def __repr__(self):
        return f"<OrgResourceLimit org={self.organization_id}>"

    def to_dict(self) -> dict:
        """Convert limits to dictionary."""
        return {
            "max_courses_per_user": self.max_courses_per_user,
            "max_ai_generated_courses": self.max_ai_generated_courses,
            "max_concurrent_labs": self.max_concurrent_labs,
            "max_lab_duration_minutes": self.max_lab_duration_minutes,
            "max_terminal_hours_monthly": self.max_terminal_hours_monthly,
            "max_desktop_hours_monthly": self.max_desktop_hours_monthly,
            "enable_persistent_vm": self.enable_persistent_vm,
            "max_storage_gb": self.max_storage_gb,
        }


class BatchResourceLimit(Base):
    """Resource limit overrides for a specific batch."""
    __tablename__ = "batch_resource_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Override org limits for this batch (null = use org default)
    max_courses_per_user = Column(Integer, nullable=True)
    max_concurrent_labs = Column(Integer, nullable=True)
    max_lab_duration_minutes = Column(Integer, nullable=True)
    max_terminal_hours_monthly = Column(Integer, nullable=True)
    max_desktop_hours_monthly = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", back_populates="resource_limits")

    def __repr__(self):
        return f"<BatchResourceLimit batch={self.batch_id}>"

    def get_effective_value(self, key: str, org_value: int) -> int:
        """Get effective value, falling back to org value if not set."""
        batch_value = getattr(self, key, None)
        return batch_value if batch_value is not None else org_value


class UserResourceLimit(Base):
    """Per-user resource limit overrides (set by Super Admin)."""
    __tablename__ = "user_resource_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Override limits for this specific user
    max_courses = Column(Integer, nullable=True)
    max_concurrent_labs = Column(Integer, nullable=True)
    max_lab_duration_minutes = Column(Integer, nullable=True)
    max_terminal_hours_monthly = Column(Integer, nullable=True)
    max_desktop_hours_monthly = Column(Integer, nullable=True)
    max_storage_gb = Column(Integer, nullable=True)

    # Special flag for unlimited access
    unlimited_access = Column(Boolean, default=False, nullable=False)

    # Admin tracking
    set_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="resource_limits")
    admin = relationship("User", foreign_keys=[set_by])

    def __repr__(self):
        return f"<UserResourceLimit user={self.user_id} unlimited={self.unlimited_access}>"

    def get_effective_value(self, key: str, default_value: int) -> int:
        """Get effective value, returning default if not set."""
        if self.unlimited_access:
            return 999999  # Effectively unlimited
        user_value = getattr(self, key, None)
        return user_value if user_value is not None else default_value


class UserUsageTracking(Base):
    """Track user's resource usage for limit enforcement."""
    __tablename__ = "user_usage_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Course usage
    courses_created_total = Column(Integer, default=0, nullable=False)
    ai_courses_this_month = Column(Integer, default=0, nullable=False)

    # Lab usage
    active_lab_sessions = Column(Integer, default=0, nullable=False)

    # Environment usage (minutes)
    terminal_minutes_this_month = Column(Integer, default=0, nullable=False)
    desktop_minutes_this_month = Column(Integer, default=0, nullable=False)

    # Storage usage (MB)
    storage_used_mb = Column(Integer, default=0, nullable=False)

    # Reset tracking
    usage_month = Column(Integer, nullable=True)  # Month number for resetting monthly limits
    usage_year = Column(Integer, nullable=True)   # Year for resetting monthly limits

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="usage_tracking")

    def __repr__(self):
        return f"<UserUsageTracking user={self.user_id}>"

    def reset_monthly_usage(self, month: int, year: int) -> None:
        """Reset monthly usage counters."""
        if self.usage_month != month or self.usage_year != year:
            self.ai_courses_this_month = 0
            self.terminal_minutes_this_month = 0
            self.desktop_minutes_this_month = 0
            self.usage_month = month
            self.usage_year = year

    def increment_course_count(self) -> None:
        """Increment total courses created."""
        self.courses_created_total += 1

    def increment_ai_course_count(self) -> None:
        """Increment AI-generated courses this month."""
        self.ai_courses_this_month += 1

    def add_terminal_usage(self, minutes: int) -> None:
        """Add terminal usage minutes."""
        self.terminal_minutes_this_month += minutes

    def add_desktop_usage(self, minutes: int) -> None:
        """Add desktop usage minutes."""
        self.desktop_minutes_this_month += minutes

    def to_dict(self) -> dict:
        """Convert usage to dictionary."""
        return {
            "courses_created_total": self.courses_created_total,
            "ai_courses_this_month": self.ai_courses_this_month,
            "active_lab_sessions": self.active_lab_sessions,
            "terminal_minutes_this_month": self.terminal_minutes_this_month,
            "desktop_minutes_this_month": self.desktop_minutes_this_month,
            "storage_used_mb": self.storage_used_mb,
        }
