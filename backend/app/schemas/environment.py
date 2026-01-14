"""Pydantic schemas for persistent environments."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class EnvironmentType(str, Enum):
    TERMINAL = "terminal"
    DESKTOP = "desktop"


class EnvironmentStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class EnvironmentStartRequest(BaseModel):
    """Request to start an environment."""
    lab_id: Optional[UUID] = None
    course_id: Optional[UUID] = None


class EnvironmentStopRequest(BaseModel):
    """Request to stop an environment."""
    reason: Optional[str] = None


class EnvironmentResetRequest(BaseModel):
    """Request to reset an environment (delete data)."""
    confirm: bool = False


class ConnectionInfo(BaseModel):
    """Connection information for an environment."""
    env_type: EnvironmentType
    status: EnvironmentStatus
    # Terminal
    ssh_port: Optional[int] = None
    connection_string: Optional[str] = None
    # Desktop
    vnc_port: Optional[int] = None
    novnc_port: Optional[int] = None
    access_url: Optional[str] = None
    vnc_password: Optional[str] = None


class EnvironmentResponse(BaseModel):
    """Response for a persistent environment."""
    id: UUID
    user_id: UUID
    env_type: EnvironmentType
    status: EnvironmentStatus
    container_id: Optional[str]
    volume_name: str
    # Connection
    ssh_port: Optional[int]
    vnc_port: Optional[int]
    novnc_port: Optional[int]
    access_url: Optional[str]
    # Status
    last_started: Optional[datetime]
    last_stopped: Optional[datetime]
    last_activity: Optional[datetime]
    error_message: Optional[str]
    # Usage
    total_usage_minutes: int
    monthly_usage_minutes: int
    usage_reset_date: Optional[date]
    # Resources
    memory_mb: int
    cpu_cores: int
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MyEnvironmentsResponse(BaseModel):
    """Response containing user's terminal and desktop environments."""
    terminal: Optional[EnvironmentResponse] = None
    desktop: Optional[EnvironmentResponse] = None
    shared_volume: str


class EnvironmentSessionResponse(BaseModel):
    """Response for an environment session."""
    id: UUID
    environment_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: Optional[datetime]
    duration_minutes: Optional[int]
    lab_id: Optional[UUID]
    course_id: Optional[UUID]
    peak_memory_mb: Optional[int]
    peak_cpu_percent: Optional[int]
    termination_reason: Optional[str]

    class Config:
        from_attributes = True


class EnvironmentStatusResponse(BaseModel):
    """Quick status check response."""
    env_type: EnvironmentType
    status: EnvironmentStatus
    is_running: bool
    is_available: bool
    error_message: Optional[str] = None
    connection_info: Optional[ConnectionInfo] = None


# Admin schemas
class AdminEnvironmentResponse(EnvironmentResponse):
    """Admin view of environment with additional details."""
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    organization_name: Optional[str] = None


class AdminEnvironmentListResponse(BaseModel):
    """List of environments for admin view."""
    items: List[AdminEnvironmentResponse]
    total: int
    running_count: int
    page: int
    page_size: int


class AdminStopEnvironmentRequest(BaseModel):
    """Admin request to force-stop an environment."""
    reason: str


class EnvironmentUsageStats(BaseModel):
    """Usage statistics for environments."""
    total_terminal_minutes: int
    total_desktop_minutes: int
    monthly_terminal_minutes: int
    monthly_desktop_minutes: int
    terminal_hours_limit: int
    desktop_hours_limit: int
    terminal_hours_remaining: float
    desktop_hours_remaining: float
