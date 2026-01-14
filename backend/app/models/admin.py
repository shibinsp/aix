"""Admin system models - Roles, Permissions, and Overrides."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    """User role hierarchy: SUPER_ADMIN > ADMIN > MODERATOR > USER"""
    SUPER_ADMIN = "super_admin"  # Full system access, can manage other admins
    ADMIN = "admin"              # Manage users, content, settings (except super admin settings)
    MODERATOR = "moderator"      # Review/approve content, limited user management
    USER = "user"                # Standard user


class Permission(str, enum.Enum):
    """Granular permissions for fine-grained access control."""
    # User Management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ROLE_ASSIGN = "user:role_assign"
    USER_BAN = "user:ban"

    # Content Management
    CONTENT_VIEW = "content:view"
    CONTENT_CREATE = "content:create"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"
    CONTENT_APPROVE = "content:approve"
    CONTENT_PUBLISH = "content:publish"

    # Lab/VM Management
    LAB_VIEW = "lab:view"
    LAB_CREATE = "lab:create"
    LAB_DELETE = "lab:delete"
    LAB_MANAGE_ALL = "lab:manage_all"
    VM_START = "vm:start"
    VM_STOP_ANY = "vm:stop_any"

    # System Settings
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"
    API_KEYS_VIEW = "api_keys:view"
    API_KEYS_MANAGE = "api_keys:manage"

    # Audit
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # System Monitoring
    MONITOR_VIEW = "monitor:view"
    MONITOR_MANAGE = "monitor:manage"

    # Admin Management (Super Admin only)
    ADMIN_MANAGE = "admin:manage"
    SUPER_ADMIN_ACCESS = "super_admin:access"

    # Organization Management
    ORG_CREATE = "org:create"
    ORG_VIEW = "org:view"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    ORG_MANAGE_MEMBERS = "org:manage_members"

    # Batch Management
    BATCH_CREATE = "batch:create"
    BATCH_VIEW = "batch:view"
    BATCH_UPDATE = "batch:update"
    BATCH_DELETE = "batch:delete"
    BATCH_MANAGE_MEMBERS = "batch:manage_members"

    # Resource Limits
    LIMITS_VIEW = "limits:view"
    LIMITS_UPDATE = "limits:update"
    LIMITS_OVERRIDE = "limits:override"

    # Persistent Environments
    ENV_VIEW_ALL = "env:view_all"
    ENV_MANAGE = "env:manage"

    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # Invitations
    INVITE_CREATE = "invite:create"
    INVITE_VIEW = "invite:view"
    INVITE_MANAGE = "invite:manage"

    # Bulk Import
    IMPORT_USERS = "import:users"


# Default permissions for each role
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [
        # User Management
        Permission.USER_VIEW, Permission.USER_CREATE, Permission.USER_UPDATE,
        Permission.USER_DELETE, Permission.USER_ROLE_ASSIGN, Permission.USER_BAN,
        # Content Management
        Permission.CONTENT_VIEW, Permission.CONTENT_CREATE, Permission.CONTENT_UPDATE,
        Permission.CONTENT_DELETE, Permission.CONTENT_APPROVE, Permission.CONTENT_PUBLISH,
        # Lab/VM Management
        Permission.LAB_VIEW, Permission.LAB_CREATE, Permission.LAB_DELETE, Permission.LAB_MANAGE_ALL,
        Permission.VM_START, Permission.VM_STOP_ANY,
        # Settings
        Permission.SETTINGS_VIEW, Permission.SETTINGS_UPDATE,
        Permission.API_KEYS_VIEW, Permission.API_KEYS_MANAGE,
        # Audit & Monitoring
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
        Permission.MONITOR_VIEW, Permission.MONITOR_MANAGE,
        # Admin
        Permission.ADMIN_MANAGE, Permission.SUPER_ADMIN_ACCESS,
        # Organization (full access)
        Permission.ORG_CREATE, Permission.ORG_VIEW, Permission.ORG_UPDATE,
        Permission.ORG_DELETE, Permission.ORG_MANAGE_MEMBERS,
        # Batch (full access)
        Permission.BATCH_CREATE, Permission.BATCH_VIEW, Permission.BATCH_UPDATE,
        Permission.BATCH_DELETE, Permission.BATCH_MANAGE_MEMBERS,
        # Resource Limits (full access)
        Permission.LIMITS_VIEW, Permission.LIMITS_UPDATE, Permission.LIMITS_OVERRIDE,
        # Persistent Environments (full access)
        Permission.ENV_VIEW_ALL, Permission.ENV_MANAGE,
        # Analytics (full access)
        Permission.ANALYTICS_VIEW, Permission.ANALYTICS_EXPORT,
        # Invitations (full access)
        Permission.INVITE_CREATE, Permission.INVITE_VIEW, Permission.INVITE_MANAGE,
        # Bulk Import
        Permission.IMPORT_USERS,
    ],
    UserRole.ADMIN: [
        # User Management
        Permission.USER_VIEW, Permission.USER_CREATE, Permission.USER_UPDATE,
        Permission.USER_DELETE, Permission.USER_BAN,
        # Content Management
        Permission.CONTENT_VIEW, Permission.CONTENT_CREATE, Permission.CONTENT_UPDATE,
        Permission.CONTENT_DELETE, Permission.CONTENT_APPROVE, Permission.CONTENT_PUBLISH,
        # Lab/VM Management
        Permission.LAB_VIEW, Permission.LAB_CREATE, Permission.LAB_DELETE, Permission.LAB_MANAGE_ALL,
        Permission.VM_START, Permission.VM_STOP_ANY,
        # Settings
        Permission.SETTINGS_VIEW, Permission.SETTINGS_UPDATE,
        Permission.API_KEYS_VIEW, Permission.API_KEYS_MANAGE,
        # Audit & Monitoring
        Permission.AUDIT_VIEW,
        Permission.MONITOR_VIEW, Permission.MONITOR_MANAGE,
        # Organization (view and manage, but cannot create - super admin only)
        Permission.ORG_VIEW, Permission.ORG_UPDATE,
        Permission.ORG_MANAGE_MEMBERS,
        # Batch (manage batches in their orgs)
        Permission.BATCH_CREATE, Permission.BATCH_VIEW, Permission.BATCH_UPDATE,
        Permission.BATCH_DELETE, Permission.BATCH_MANAGE_MEMBERS,
        # Resource Limits (view only, no override)
        Permission.LIMITS_VIEW,
        # Analytics
        Permission.ANALYTICS_VIEW,
        # Invitations
        Permission.INVITE_CREATE, Permission.INVITE_VIEW, Permission.INVITE_MANAGE,
        # Bulk Import
        Permission.IMPORT_USERS,
    ],
    UserRole.MODERATOR: [
        Permission.USER_VIEW, Permission.USER_BAN,
        Permission.CONTENT_VIEW, Permission.CONTENT_APPROVE,
        Permission.LAB_VIEW,
        Permission.MONITOR_VIEW,
        Permission.AUDIT_VIEW,
        # Organization (view only)
        Permission.ORG_VIEW,
        Permission.BATCH_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.INVITE_VIEW,
    ],
    UserRole.USER: [],
}


class RolePermission(Base):
    """Maps roles to their default permissions (for DB-based permission lookup)."""
    __tablename__ = "role_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(Enum(UserRole), nullable=False, index=True)
    permission = Column(Enum(Permission), nullable=False)

    __table_args__ = (
        UniqueConstraint('role', 'permission', name='uix_role_permission'),
    )


class UserPermissionOverride(Base):
    """Custom permission overrides for specific users."""
    __tablename__ = "user_permission_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission = Column(Enum(Permission), nullable=False)
    granted = Column(Boolean, default=True)  # True=grant, False=revoke
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), default=utcnow)
    reason = Column(Text, nullable=True)

    # Relationships defined with string references to avoid circular imports
    user = relationship("User", foreign_keys=[user_id], back_populates="permission_overrides")
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'permission', name='uix_user_permission'),
    )
