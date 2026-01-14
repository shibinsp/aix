import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.admin import UserRole


class SkillLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LearningStyle(str, enum.Enum):
    VISUAL = "visual"
    KINESTHETIC = "kinesthetic"
    AUDITORY = "auditory"
    READING = "reading"


class CareerGoal(str, enum.Enum):
    SOC_ANALYST = "soc_analyst"
    PENTESTER = "pentester"
    SECURITY_ENGINEER = "security_engineer"
    MALWARE_ANALYST = "malware_analyst"
    INCIDENT_RESPONDER = "incident_responder"
    SECURITY_ARCHITECT = "security_architect"
    GENERAL = "general"


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)

    # Profile
    skill_level = Column(Enum(SkillLevel), default=SkillLevel.BEGINNER)
    learning_style = Column(Enum(LearningStyle), default=LearningStyle.KINESTHETIC)
    career_goal = Column(Enum(CareerGoal), default=CareerGoal.GENERAL)
    time_commitment = Column(Integer, default=10)  # hours per week
    bio = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Role-based access control
    role = Column(Enum(UserRole), default=UserRole.USER, index=True)

    # Ban tracking
    is_banned = Column(Boolean, default=False)
    banned_at = Column(DateTime(timezone=True), nullable=True)
    banned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ban_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Progress tracking
    total_points = Column(Integer, default=0)
    total_labs_completed = Column(Integer, default=0)
    total_courses_completed = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)  # days

    # Relationships - Core
    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    lab_sessions = relationship("LabSession", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    permission_overrides = relationship(
        "UserPermissionOverride",
        back_populates="user",
        foreign_keys="UserPermissionOverride.user_id",
        cascade="all, delete-orphan"
    )
    banned_by_user = relationship("User", remote_side="User.id", foreign_keys=[banned_by])

    # Relationships - Organizations (single org per user)
    organization_membership = relationship(
        "OrganizationMembership",
        back_populates="user",
        foreign_keys="OrganizationMembership.user_id",
        uselist=False,  # Single organization per user
        cascade="all, delete-orphan"
    )
    owned_organizations = relationship(
        "Organization",
        back_populates="owner",
        foreign_keys="Organization.created_by"
    )

    # Relationships - Batches
    batch_memberships = relationship(
        "BatchMembership",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Relationships - Persistent Environments
    persistent_environments = relationship(
        "PersistentEnvironment",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Relationships - Resource Limits & Usage
    resource_limits = relationship(
        "UserResourceLimit",
        back_populates="user",
        foreign_keys="UserResourceLimit.user_id",
        uselist=False,
        cascade="all, delete-orphan"
    )
    usage_tracking = relationship(
        "UserUsageTracking",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Relationships - Saved Articles
    saved_articles = relationship(
        "SavedArticle",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        """Backwards compatibility property - returns True if user has admin or super_admin role."""
        return self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        """Check if user is a super admin."""
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_moderator(self) -> bool:
        """Check if user has at least moderator privileges."""
        return self.role in (UserRole.MODERATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)

    def has_permission(self, permission) -> bool:
        """Check if user has a specific permission based on role and overrides."""
        from app.models.admin import ROLE_PERMISSIONS, Permission

        # Check permission overrides first
        for override in self.permission_overrides:
            if override.permission == permission:
                return override.granted

        # Fall back to role-based permissions
        role_perms = ROLE_PERMISSIONS.get(self.role, [])
        return permission in role_perms

    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"

    # Organization helpers
    @property
    def organization(self):
        """Get user's organization (if any)."""
        if self.organization_membership and self.organization_membership.is_active:
            return self.organization_membership.organization
        return None

    @property
    def org_role(self):
        """Get user's role within their organization."""
        if self.organization_membership:
            return self.organization_membership.org_role
        return None

    @property
    def is_org_admin(self) -> bool:
        """Check if user is an admin in their organization."""
        if self.organization_membership:
            return self.organization_membership.is_admin
        return False

    def get_effective_limits(self) -> dict:
        """Get effective resource limits for this user.

        Priority: User override > Batch > Organization > System default
        """
        from app.models.limits import DEFAULT_LIMITS

        # Start with system defaults
        limits = DEFAULT_LIMITS.copy()

        # Apply organization limits if user is in an org
        if self.organization and self.organization.resource_limits:
            org_limits = self.organization.resource_limits.to_dict()
            for key, value in org_limits.items():
                if key in limits:
                    limits[key] = value

        # Apply batch limits (highest priority batch if in multiple)
        # For simplicity, use first active batch with limits
        for batch_membership in self.batch_memberships:
            if batch_membership.batch and batch_membership.batch.resource_limits:
                batch_limits = batch_membership.batch.resource_limits
                for key in limits.keys():
                    batch_value = getattr(batch_limits, key, None)
                    if batch_value is not None:
                        limits[key] = batch_value
                break  # Only apply first batch's limits

        # Apply user-specific overrides (highest priority)
        if self.resource_limits:
            if self.resource_limits.unlimited_access:
                # Unlimited access - set very high limits
                for key in limits.keys():
                    if isinstance(limits[key], int):
                        limits[key] = 999999
            else:
                for key in limits.keys():
                    user_value = getattr(self.resource_limits, key, None)
                    if user_value is not None:
                        limits[key] = user_value

        return limits

    def can_create_course(self) -> bool:
        """Check if user can create a new course based on limits."""
        limits = self.get_effective_limits()
        max_courses = limits.get("max_courses_per_user", 5)

        if self.usage_tracking:
            return self.usage_tracking.courses_created_total < max_courses
        return True  # No tracking yet, allow creation

    def can_start_lab(self) -> bool:
        """Check if user can start a new lab based on limits."""
        limits = self.get_effective_limits()
        max_concurrent = limits.get("max_concurrent_labs", 1)

        if self.usage_tracking:
            return self.usage_tracking.active_lab_sessions < max_concurrent
        return True
