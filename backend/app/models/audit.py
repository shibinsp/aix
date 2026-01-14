"""Audit logging model for tracking admin actions."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Index, Enum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""
    # Auth events
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password_change"
    PASSWORD_RESET = "auth.password_reset"

    # User management
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ROLE_CHANGE = "user.role_change"
    USER_BAN = "user.ban"
    USER_UNBAN = "user.unban"
    USER_PERMISSION_OVERRIDE = "user.permission_override"

    # Content management
    COURSE_CREATE = "course.create"
    COURSE_UPDATE = "course.update"
    COURSE_DELETE = "course.delete"
    COURSE_PUBLISH = "course.publish"
    COURSE_UNPUBLISH = "course.unpublish"
    COURSE_APPROVE = "course.approve"
    COURSE_REJECT = "course.reject"

    LAB_CREATE = "lab.create"
    LAB_UPDATE = "lab.update"
    LAB_DELETE = "lab.delete"
    LAB_PUBLISH = "lab.publish"
    LAB_APPROVE = "lab.approve"
    LAB_REJECT = "lab.reject"

    # Settings
    SETTING_UPDATE = "setting.update"
    API_KEY_CREATE = "api_key.create"
    API_KEY_UPDATE = "api_key.update"
    API_KEY_DELETE = "api_key.delete"
    API_KEY_VIEW = "api_key.view"

    # Lab/VM operations
    LAB_SESSION_START = "lab_session.start"
    LAB_SESSION_STOP = "lab_session.stop"
    LAB_SESSION_FORCE_STOP = "lab_session.force_stop"
    VM_START = "vm.start"
    VM_STOP = "vm.stop"
    VM_FORCE_STOP = "vm.force_stop"

    # System operations
    SYSTEM_RESTART = "system.restart"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"
    SETTINGS_EXPORT = "settings.export"
    SETTINGS_IMPORT = "settings.import"
    AUDIT_EXPORT = "audit.export"


class AuditSeverity(str, enum.Enum):
    """Severity level for audit entries."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditLog(Base):
    """Comprehensive audit logging for admin actions."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who performed the action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)  # Stored for historical reference
    user_role = Column(String(50), nullable=True)

    # What action was performed
    action = Column(Enum(AuditAction), nullable=False, index=True)
    severity = Column(Enum(AuditSeverity), default=AuditSeverity.INFO)
    description = Column(Text, nullable=True)

    # Target (what was affected)
    target_type = Column(String(50), nullable=True, index=True)  # "user", "course", "lab", "setting"
    target_id = Column(String(100), nullable=True)
    target_name = Column(String(255), nullable=True)  # Human-readable identifier

    # Details of the change
    old_value = Column(JSON, nullable=True)  # Previous state (for updates)
    new_value = Column(JSON, nullable=True)  # New state (for creates/updates)
    extra_data = Column(JSON, nullable=True)   # Additional context

    # Request context
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(100), nullable=True)  # For correlating related actions

    # Timestamp
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationship
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('ix_audit_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_audit_logs_action_timestamp', 'action', 'timestamp'),
        Index('ix_audit_logs_target', 'target_type', 'target_id'),
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "action": self.action.value,
            "severity": self.severity.value,
            "description": self.description,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "extra_data": self.extra_data,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
