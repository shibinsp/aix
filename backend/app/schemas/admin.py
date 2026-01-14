"""Pydantic schemas for admin functionality."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID

from app.models.admin import UserRole, Permission
from app.models.audit import AuditAction, AuditSeverity
from app.models.settings import SettingCategory


# ============== Dashboard Schemas ==============
class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_users: int
    active_users_today: int
    new_users_this_week: int
    total_courses: int
    published_courses: int
    pending_approval: int
    total_labs: int
    active_lab_sessions: int
    active_vms: int


class SystemAlert(BaseModel):
    """System alert/notification."""
    id: str
    level: str  # info, warning, error
    message: str
    timestamp: datetime
    resolved: bool = False


class RecentActivity(BaseModel):
    """Recent admin activity."""
    action: str
    user_email: str
    target: Optional[str]
    timestamp: datetime


# ============== User Management Schemas ==============
class UserListItem(BaseModel):
    """User item for list view."""
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_banned: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_points: int

    class Config:
        from_attributes = True


class UserDetail(UserListItem):
    """Detailed user view."""
    is_verified: bool
    skill_level: str
    learning_style: str
    career_goal: str
    total_labs_completed: int
    total_courses_completed: int
    current_streak: int
    ban_reason: Optional[str]
    banned_at: Optional[datetime]


class UserCreate(BaseModel):
    """Create a new user."""
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    """Update user fields."""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class RoleChange(BaseModel):
    """Change user role."""
    role: UserRole
    reason: Optional[str] = None


class BanUser(BaseModel):
    """Ban a user."""
    reason: str = Field(min_length=10, max_length=1000)


class PermissionOverride(BaseModel):
    """Grant or revoke a specific permission."""
    permission: Permission
    granted: bool
    reason: Optional[str] = None


# ============== Settings Schemas ==============
class SettingResponse(BaseModel):
    """System setting response."""
    id: UUID
    key: str
    value: Optional[str]
    value_type: str
    category: SettingCategory
    label: str
    description: Optional[str]
    is_sensitive: bool
    is_readonly: bool
    requires_restart: bool
    is_super_admin_only: bool
    validation_rules: Optional[Dict[str, Any]]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Update a setting."""
    value: str


class SettingsGroup(BaseModel):
    """Group of settings by category."""
    category: SettingCategory
    settings: List[SettingResponse]


# ============== API Keys Schemas ==============
class APIKeyResponse(BaseModel):
    """API key info (without the actual key)."""
    id: UUID
    service_name: str
    key_hint: Optional[str]
    label: str
    description: Optional[str]
    documentation_url: Optional[str]
    required: bool
    is_configured: bool
    is_valid: Optional[bool]
    last_validated_at: Optional[datetime]
    validation_error: Optional[str]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIKeySet(BaseModel):
    """Set an API key."""
    api_key: str = Field(min_length=10)


class APIKeyTestResult(BaseModel):
    """Result of API key validation."""
    service_name: str
    is_valid: bool
    error: Optional[str] = None
    tested_at: datetime


# ============== Audit Schemas ==============
class AuditLogResponse(BaseModel):
    """Audit log entry."""
    id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    user_role: Optional[str]
    action: AuditAction
    severity: AuditSeverity
    description: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    target_name: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogQuery(BaseModel):
    """Query parameters for audit logs."""
    user_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    target_type: Optional[str] = None
    severity: Optional[AuditSeverity] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=50, le=500)
    offset: int = Field(default=0, ge=0)


# ============== Monitoring Schemas ==============
class ActiveLabSession(BaseModel):
    """Active lab session info."""
    id: UUID
    user_id: UUID
    user_email: str
    lab_title: str
    started_at: datetime
    container_ids: Optional[list[str]] = None


class ActiveVM(BaseModel):
    """Active VM info."""
    id: str
    user_id: UUID
    user_email: str
    lab_title: str
    status: str
    memory: str
    started_at: datetime


class SystemResources(BaseModel):
    """System resource usage."""
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    active_containers: int
    active_vms: int


# ============== Content Moderation Schemas ==============
class PendingContent(BaseModel):
    """Content awaiting approval."""
    id: UUID
    type: str  # "course" or "lab"
    title: str
    author_id: UUID
    author_email: str
    created_at: datetime
    description: Optional[str]


class ContentApproval(BaseModel):
    """Approve or reject content."""
    approved: bool
    feedback: Optional[str] = None
