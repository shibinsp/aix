"""Pydantic schemas for organizations, batches, and memberships."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum


class OrganizationType(str, Enum):
    ENTERPRISE = "enterprise"
    EDUCATIONAL = "educational"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"


class OrgMemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    MEMBER = "member"


class BatchStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# Organization Schemas
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    org_type: OrganizationType = OrganizationType.EDUCATIONAL
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    slug: Optional[str] = Field(None, min_length=2, max_length=255, pattern=r'^[a-z0-9-]+$')
    max_members: Optional[int] = None

    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v, info):
        if v is None and 'name' in info.data:
            # Auto-generate slug from name
            import re
            name = info.data['name']
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            return slug
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    org_type: Optional[OrganizationType] = None
    is_active: Optional[bool] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    max_members: Optional[int] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None


class OrganizationResponse(OrganizationBase):
    id: UUID
    slug: str
    is_active: bool
    max_members: Optional[int]
    subscription_tier: Optional[str]
    subscription_expires_at: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None
    batch_count: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    org_type: OrganizationType
    is_active: bool
    logo_url: Optional[str]
    member_count: int = 0
    batch_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# Batch Schemas
class BatchBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    status: BatchStatus = BatchStatus.ACTIVE
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_users: Optional[int] = None


class BatchCreate(BatchBase):
    curriculum_courses: Optional[List[UUID]] = None
    settings: Optional[dict] = None


class BatchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[BatchStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_users: Optional[int] = None
    curriculum_courses: Optional[List[UUID]] = None
    settings: Optional[dict] = None


class BatchResponse(BatchBase):
    id: UUID
    organization_id: UUID
    curriculum_courses: Optional[List[UUID]]
    settings: Optional[dict]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None
    progress_avg: Optional[float] = None

    class Config:
        from_attributes = True


class BatchListResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    status: BatchStatus
    start_date: Optional[date]
    end_date: Optional[date]
    member_count: int = 0
    progress_avg: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


# Membership Schemas
class OrganizationMembershipBase(BaseModel):
    org_role: OrgMemberRole = OrgMemberRole.MEMBER
    notes: Optional[str] = None


class AddMemberRequest(OrganizationMembershipBase):
    user_id: UUID


class UpdateMemberRoleRequest(BaseModel):
    org_role: OrgMemberRole
    notes: Optional[str] = None


class OrganizationMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    org_role: OrgMemberRole
    is_active: bool
    joined_at: datetime
    notes: Optional[str]
    # User details
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    user_full_name: Optional[str] = None

    class Config:
        from_attributes = True


class BatchMembershipBase(BaseModel):
    pass


class AddBatchMemberRequest(BaseModel):
    user_ids: List[UUID]


class BatchMemberResponse(BaseModel):
    id: UUID
    batch_id: UUID
    user_id: UUID
    enrolled_at: datetime
    completed_at: Optional[datetime]
    progress_percent: int
    courses_completed: Optional[List[UUID]]
    labs_completed: Optional[List[UUID]]
    last_activity_at: Optional[datetime]
    # User details
    user_email: Optional[str] = None
    user_username: Optional[str] = None
    user_full_name: Optional[str] = None

    class Config:
        from_attributes = True


# Dashboard/Stats Schemas
class OrganizationDashboard(BaseModel):
    organization: OrganizationResponse
    total_members: int
    active_members: int
    total_batches: int
    active_batches: int
    total_courses_completed: int
    total_labs_completed: int
    avg_progress: float
    recent_activity: List[dict]


class BatchDashboard(BaseModel):
    batch: BatchResponse
    total_members: int
    active_members: int
    avg_progress: float
    courses_in_curriculum: int
    completion_rate: float
    leaderboard: List[dict]


# Pagination
class PaginatedOrganizations(BaseModel):
    items: List[OrganizationListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedBatches(BaseModel):
    items: List[BatchListResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedMembers(BaseModel):
    items: List[OrganizationMemberResponse]
    total: int
    page: int
    page_size: int
    pages: int
