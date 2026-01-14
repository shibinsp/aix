"""Pydantic schemas for invitations and bulk imports."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DECLINED = "declined"


class OrgMemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    MEMBER = "member"


# Single invitation
class InvitationCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: OrgMemberRole = OrgMemberRole.MEMBER
    batch_id: Optional[UUID] = None
    message: Optional[str] = None
    expires_days: int = Field(default=7, ge=1, le=30)


class BulkInvitationCreate(BaseModel):
    """Create multiple invitations at once."""
    invitations: List[InvitationCreate]


class InvitationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    full_name: Optional[str]
    role: OrgMemberRole
    batch_id: Optional[UUID]
    status: InvitationStatus
    expires_at: datetime
    message: Optional[str]
    invited_by: Optional[UUID]
    accepted_by: Optional[UUID]
    accepted_at: Optional[datetime]
    email_sent: bool
    email_sent_at: Optional[datetime]
    reminder_sent: bool
    created_at: datetime
    # Computed
    is_valid: bool
    days_until_expiry: int
    invite_url: str

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    items: List[InvitationResponse]
    total: int
    pending_count: int
    page: int
    page_size: int


# Public invitation view (for acceptance page)
class PublicInvitationResponse(BaseModel):
    id: UUID
    organization_name: Optional[str]
    organization_logo: Optional[str]
    email: str
    full_name: Optional[str]
    role: OrgMemberRole
    message: Optional[str]
    expires_at: datetime
    is_valid: bool
    days_until_expiry: int


class AcceptInvitationRequest(BaseModel):
    """Accept invitation - creates account if needed."""
    # For new users
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    # For existing users
    use_existing_account: bool = False


class AcceptInvitationResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[UUID]
    organization_id: UUID
    organization_name: str
    redirect_url: str


class DeclineInvitationResponse(BaseModel):
    success: bool
    message: str


# Resend invitation
class ResendInvitationRequest(BaseModel):
    send_email: bool = True


# Bulk import
class BulkImportRequest(BaseModel):
    """Request to import users from CSV."""
    send_invitations: bool = True
    default_role: OrgMemberRole = OrgMemberRole.MEMBER
    default_batch_id: Optional[UUID] = None


class BulkImportRowResult(BaseModel):
    row: int
    email: str
    success: bool
    error: Optional[str] = None
    user_id: Optional[UUID] = None


class BulkImportJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    status: str
    filename: Optional[str]
    file_size: Optional[int]
    total_rows: int
    processed_rows: int
    successful_rows: int
    failed_rows: int
    progress_percent: int
    errors: Optional[List[dict]]
    send_invitations: bool
    default_role: OrgMemberRole
    default_batch_id: Optional[UUID]
    started_by: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class BulkImportJobListResponse(BaseModel):
    items: List[BulkImportJobResponse]
    total: int
    page: int
    page_size: int


# CSV template
class CSVTemplateColumn(BaseModel):
    name: str
    required: bool
    description: str
    example: str


class CSVTemplateResponse(BaseModel):
    columns: List[CSVTemplateColumn]
    sample_csv: str
