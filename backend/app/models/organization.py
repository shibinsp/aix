"""Organization, Batch, and Membership models for multi-tenant support."""
import uuid
import enum
from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, Date,
    ForeignKey, Enum, JSON, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class OrganizationType(str, enum.Enum):
    """Types of organizations."""
    ENTERPRISE = "enterprise"
    EDUCATIONAL = "educational"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    INDIVIDUAL = "individual"


class OrgMemberRole(str, enum.Enum):
    """Roles within an organization."""
    OWNER = "owner"           # Full control of organization
    ADMIN = "admin"           # Manage users, batches, settings
    INSTRUCTOR = "instructor" # View progress, manage content
    MEMBER = "member"         # Standard member access


class BatchStatus(str, enum.Enum):
    """Status of a batch."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Organization(Base):
    """Organization model for multi-tenant support."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    # Organization type and status
    org_type = Column(
        Enum(OrganizationType),
        default=OrganizationType.EDUCATIONAL,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color like #00ff9d

    # Contact info
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    website = Column(String(500), nullable=True)

    # Capacity
    max_members = Column(Integer, nullable=True)  # null = unlimited

    # Subscription/billing (for future use)
    subscription_tier = Column(String(50), default="free", nullable=False)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    settings = Column(JSON, default=dict, nullable=False)

    # Ownership
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[created_by], back_populates="owned_organizations")
    batches = relationship("Batch", back_populates="organization", cascade="all, delete-orphan")
    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    resource_limits = relationship(
        "OrganizationResourceLimit",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan"
    )
    invitations = relationship("Invitation", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"

    @property
    def member_count(self) -> int:
        """Get count of active members."""
        return len([m for m in self.memberships if m.is_active])

    @property
    def batch_count(self) -> int:
        """Get count of active batches."""
        return len([b for b in self.batches if b.status == BatchStatus.ACTIVE])


class Batch(Base):
    """Batch model for grouping users (cohorts, classes, teams)."""
    __tablename__ = "batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Batch configuration
    status = Column(Enum(BatchStatus), default=BatchStatus.ACTIVE, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Capacity
    max_users = Column(Integer, nullable=True)  # null = unlimited

    # Curriculum - list of course IDs assigned to this batch
    curriculum_courses = Column(JSON, default=list, nullable=False)

    # Metadata
    settings = Column(JSON, default=dict, nullable=False)

    # Ownership
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="batches")
    creator = relationship("User", foreign_keys=[created_by])
    memberships = relationship("BatchMembership", back_populates="batch", cascade="all, delete-orphan")
    resource_limits = relationship(
        "BatchResourceLimit",
        back_populates="batch",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_batches_org_status', 'organization_id', 'status'),
    )

    def __repr__(self):
        return f"<Batch {self.name} ({self.status.value})>"

    @property
    def member_count(self) -> int:
        """Get count of enrolled members."""
        return len(self.memberships)

    @property
    def is_full(self) -> bool:
        """Check if batch has reached max capacity."""
        if self.max_users is None:
            return False
        return self.member_count >= self.max_users


class OrganizationMembership(Base):
    """Membership linking users to organizations (single org per user)."""
    __tablename__ = "organization_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # user_id is UNIQUE - user can only belong to ONE organization
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Single organization per user
        index=True
    )

    # Role within organization
    org_role = Column(Enum(OrgMemberRole), default=OrgMemberRole.MEMBER, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Invitation tracking
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id], back_populates="organization_membership")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<OrgMembership user={self.user_id} org={self.organization_id} role={self.org_role.value}>"

    @property
    def is_admin(self) -> bool:
        """Check if member has admin privileges."""
        return self.org_role in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN)

    @property
    def is_owner(self) -> bool:
        """Check if member is the owner."""
        return self.org_role == OrgMemberRole.OWNER

    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members."""
        return self.org_role in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN)

    @property
    def can_manage_batches(self) -> bool:
        """Check if member can manage batches."""
        return self.org_role in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN, OrgMemberRole.INSTRUCTOR)


class BatchMembership(Base):
    """Membership linking users to batches."""
    __tablename__ = "batch_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Progress tracking
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress_percent = Column(Integer, default=0, nullable=False)

    # Course/lab completion tracking
    courses_completed = Column(JSON, default=list, nullable=False)  # List of course IDs
    labs_completed = Column(JSON, default=list, nullable=False)     # List of lab IDs

    # Points earned in this batch
    points_earned = Column(Integer, default=0, nullable=False)

    # Activity tracking
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    batch = relationship("Batch", back_populates="memberships")
    user = relationship("User", back_populates="batch_memberships")

    __table_args__ = (
        UniqueConstraint('batch_id', 'user_id', name='uix_batch_user'),
        Index('ix_batch_memberships_progress', 'batch_id', 'progress_percent'),
    )

    def __repr__(self):
        return f"<BatchMembership user={self.user_id} batch={self.batch_id} progress={self.progress_percent}%>"

    @property
    def is_completed(self) -> bool:
        """Check if member has completed the batch curriculum."""
        return self.completed_at is not None or self.progress_percent >= 100

    def mark_course_completed(self, course_id: str) -> None:
        """Mark a course as completed."""
        if course_id not in self.courses_completed:
            self.courses_completed = [*self.courses_completed, course_id]
            self._recalculate_progress()

    def mark_lab_completed(self, lab_id: str) -> None:
        """Mark a lab as completed."""
        if lab_id not in self.labs_completed:
            self.labs_completed = [*self.labs_completed, lab_id]

    def _recalculate_progress(self) -> None:
        """Recalculate progress based on curriculum completion."""
        if self.batch and self.batch.curriculum_courses:
            total = len(self.batch.curriculum_courses)
            completed = len([c for c in self.courses_completed if c in self.batch.curriculum_courses])
            self.progress_percent = int((completed / total) * 100) if total > 0 else 0

            if self.progress_percent >= 100 and not self.completed_at:
                self.completed_at = datetime.utcnow()
