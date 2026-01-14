"""Pydantic schemas for resource limits and usage tracking."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class ResourceLimitsBase(BaseModel):
    max_courses_per_user: Optional[int] = Field(None, ge=0)
    max_ai_generated_courses: Optional[int] = Field(None, ge=0)
    max_concurrent_labs: Optional[int] = Field(None, ge=0)
    max_lab_duration_minutes: Optional[int] = Field(None, ge=0)
    max_terminal_hours_monthly: Optional[int] = Field(None, ge=0)
    max_desktop_hours_monthly: Optional[int] = Field(None, ge=0)
    max_storage_gb: Optional[int] = Field(None, ge=0)
    enable_persistent_vm: Optional[bool] = None


class OrganizationLimitsCreate(ResourceLimitsBase):
    pass


class OrganizationLimitsUpdate(ResourceLimitsBase):
    custom_limits: Optional[dict] = None


class OrganizationLimitsResponse(ResourceLimitsBase):
    id: UUID
    organization_id: UUID
    custom_limits: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchLimitsUpdate(ResourceLimitsBase):
    custom_limits: Optional[dict] = None


class BatchLimitsResponse(ResourceLimitsBase):
    id: UUID
    batch_id: UUID
    custom_limits: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLimitsCreate(ResourceLimitsBase):
    unlimited_access: bool = False
    reason: Optional[str] = None


class UserLimitsUpdate(ResourceLimitsBase):
    unlimited_access: Optional[bool] = None
    reason: Optional[str] = None
    custom_limits: Optional[dict] = None


class UserLimitsResponse(ResourceLimitsBase):
    id: UUID
    user_id: UUID
    unlimited_access: bool
    set_by: Optional[UUID]
    reason: Optional[str]
    custom_limits: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UsageTrackingResponse(BaseModel):
    id: UUID
    user_id: UUID
    courses_created_total: int
    ai_courses_this_month: int
    ai_courses_reset_date: Optional[date] = None
    active_lab_sessions: int
    terminal_minutes_this_month: int
    desktop_minutes_this_month: int
    usage_reset_date: Optional[date] = None
    storage_used_mb: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True


class EffectiveLimitsResponse(BaseModel):
    """Effective limits for a user after applying all overrides."""
    max_courses_per_user: int
    max_ai_generated_courses: int
    max_concurrent_labs: int
    max_lab_duration_minutes: int
    max_terminal_hours_monthly: int
    max_desktop_hours_monthly: int
    max_storage_gb: int
    enable_persistent_vm: bool
    # Source info
    source: str  # "default", "organization", "batch", "user"


class UsageSummaryResponse(BaseModel):
    """Combined limits and usage for a user."""
    limits: EffectiveLimitsResponse
    usage: UsageTrackingResponse
    # Computed fields
    courses_remaining: int
    ai_courses_remaining_this_month: int
    can_start_lab: bool
    terminal_hours_remaining: float
    desktop_hours_remaining: float
    storage_remaining_gb: float


class DefaultLimitsResponse(BaseModel):
    """System default limits."""
    max_courses_per_user: int
    max_ai_generated_courses: int
    max_concurrent_labs: int
    max_lab_duration_minutes: int
    max_terminal_hours_monthly: int
    max_desktop_hours_monthly: int
    max_storage_gb: int
    enable_persistent_vm: bool


class UpdateDefaultLimitsRequest(BaseModel):
    """Request to update system default limits."""
    max_courses_per_user: Optional[int] = Field(None, ge=1)
    max_ai_generated_courses: Optional[int] = Field(None, ge=0)
    max_concurrent_labs: Optional[int] = Field(None, ge=1)
    max_lab_duration_minutes: Optional[int] = Field(None, ge=10)
    max_terminal_hours_monthly: Optional[int] = Field(None, ge=1)
    max_desktop_hours_monthly: Optional[int] = Field(None, ge=1)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    enable_persistent_vm: Optional[bool] = None
