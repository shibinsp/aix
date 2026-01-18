"""API routes for organization management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
import re
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.sanitization import sanitize_like_pattern
from app.models.user import User
from app.models.admin import Permission
from app.models.organization import (
    Organization, OrganizationType, OrgMemberRole,
    Batch, BatchStatus, OrganizationMembership, BatchMembership
)
from app.models.limits import OrganizationResourceLimit
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationListResponse,
    AddMemberRequest, UpdateMemberRoleRequest, OrganizationMemberResponse,
    OrganizationDashboard, PaginatedOrganizations, PaginatedMembers,
)

logger = structlog.get_logger()

router = APIRouter()


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


# ============================================================================
# ORGANIZATION CRUD
# ============================================================================

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(require_permission(Permission.ORG_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization. Requires ORG_CREATE permission."""
    # Generate unique slug
    base_slug = slugify(org_data.slug or org_data.name)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create organization
    organization = Organization(
        name=org_data.name,
        slug=slug,
        description=org_data.description,
        org_type=OrganizationType(org_data.org_type.value) if org_data.org_type else OrganizationType.EDUCATIONAL,
        logo_url=org_data.logo_url,
        website=org_data.website,
        contact_email=org_data.contact_email,
        max_members=org_data.max_members,
        created_by=current_user.id,
    )

    db.add(organization)
    await db.commit()
    await db.refresh(organization)

    # Create default resource limits for the organization
    resource_limits = OrganizationResourceLimit(organization_id=organization.id)
    db.add(resource_limits)

    # Add creator as owner
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=current_user.id,
        org_role=OrgMemberRole.OWNER,
    )
    db.add(membership)

    await db.commit()
    await db.refresh(organization)

    logger.info("Organization created", org_id=str(organization.id), name=organization.name, created_by=str(current_user.id))

    return await _build_org_response(organization, db)


@router.get("", response_model=PaginatedOrganizations)
async def list_organizations(
    current_user: User = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    org_type: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """
    List organizations.
    - Super Admin sees all organizations
    - Others see organizations they have access to
    """
    query = select(Organization)

    # Apply filters
    if search:
        search_pattern = sanitize_like_pattern(search)
        query = query.where(
            Organization.name.ilike(f"%{search_pattern}%") |
            Organization.slug.ilike(f"%{search_pattern}%")
        )
    if org_type:
        query = query.where(Organization.org_type == OrganizationType(org_type))
    if is_active is not None:
        query = query.where(Organization.is_active == is_active)

    # Non-super admins only see their organizations
    if not current_user.is_super_admin:
        query = query.join(OrganizationMembership).where(
            OrganizationMembership.user_id == current_user.id
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Organization.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    organizations = result.scalars().all()

    # Build response with counts
    items = []
    for org in organizations:
        member_count = await _get_member_count(org.id, db)
        batch_count = await _get_batch_count(org.id, db)
        items.append(OrganizationListResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            org_type=org.org_type,
            is_active=org.is_active,
            logo_url=org.logo_url,
            member_count=member_count,
            batch_count=batch_count,
            created_at=org.created_at,
        ))

    pages = (total + page_size - 1) // page_size

    return PaginatedOrganizations(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get organization details."""
    organization = await _get_organization_with_access_check(org_id, current_user, db)
    return await _build_org_response(organization, db)


@router.get("/slug/{slug}", response_model=OrganizationResponse)
async def get_organization_by_slug(
    slug: str,
    current_user: User = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get organization by slug."""
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check access
    if not current_user.is_super_admin:
        await _verify_org_access(organization.id, current_user.id, db)

    return await _build_org_response(organization, db)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    current_user: User = Depends(require_permission(Permission.ORG_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    """Update organization details."""
    organization = await _get_organization_with_access_check(org_id, current_user, db, require_admin=True)

    # Update fields
    update_data = org_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "org_type" and value:
            value = OrganizationType(value.value)
        setattr(organization, field, value)

    await db.commit()
    await db.refresh(organization)

    logger.info("Organization updated", org_id=str(org_id), updated_by=str(current_user.id))

    return await _build_org_response(organization, db)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ORG_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    """Delete an organization. Requires ORG_DELETE permission (Super Admin only)."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    await db.delete(organization)
    await db.commit()

    logger.info("Organization deleted", org_id=str(org_id), deleted_by=str(current_user.id))


# ============================================================================
# MEMBER MANAGEMENT
# ============================================================================

@router.get("/{org_id}/members", response_model=PaginatedMembers)
async def list_organization_members(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
):
    """List members of an organization."""
    await _get_organization_with_access_check(org_id, current_user, db)

    query = (
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .where(OrganizationMembership.organization_id == org_id)
    )

    if role:
        query = query.where(OrganizationMembership.org_role == OrgMemberRole(role))

    if search:
        search_pattern = sanitize_like_pattern(search)
        query = query.join(User).where(
            User.username.ilike(f"%{search_pattern}%") |
            User.email.ilike(f"%{search_pattern}%") |
            User.full_name.ilike(f"%{search_pattern}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(OrganizationMembership.joined_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    memberships = result.scalars().all()

    items = [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            org_role=m.org_role,
            is_active=m.is_active,
            joined_at=m.joined_at,
            notes=m.notes,
            user_email=m.user.email if m.user else None,
            user_username=m.user.username if m.user else None,
            user_full_name=m.user.full_name if m.user else None,
        )
        for m in memberships
    ]

    pages = (total + page_size - 1) // page_size

    return PaginatedMembers(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{org_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    org_id: UUID,
    member_data: AddMemberRequest,
    current_user: User = Depends(require_permission(Permission.ORG_MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
):
    """Add a member to an organization."""
    organization = await _get_organization_with_access_check(org_id, current_user, db, require_admin=True)

    # Check if user exists
    user = await db.get(User, member_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is already in an organization
    existing_membership = await db.execute(
        select(OrganizationMembership).where(OrganizationMembership.user_id == member_data.user_id)
    )
    if existing_membership.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member of an organization")

    # Check max members limit
    if organization.max_members:
        member_count = await _get_member_count(org_id, db)
        if member_count >= organization.max_members:
            raise HTTPException(status_code=400, detail="Organization has reached maximum member limit")

    # Create membership
    membership = OrganizationMembership(
        organization_id=org_id,
        user_id=member_data.user_id,
        org_role=OrgMemberRole(member_data.org_role.value) if member_data.org_role else OrgMemberRole.MEMBER,
        notes=member_data.notes,
        invited_by=current_user.id,
    )

    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    logger.info("Member added to organization", org_id=str(org_id), user_id=str(member_data.user_id))

    return OrganizationMemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        org_role=membership.org_role,
        is_active=membership.is_active,
        joined_at=membership.joined_at,
        notes=membership.notes,
        user_email=user.email,
        user_username=user.username,
        user_full_name=user.full_name,
    )


@router.patch("/{org_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_id: UUID,
    user_id: UUID,
    role_data: UpdateMemberRoleRequest,
    current_user: User = Depends(require_permission(Permission.ORG_MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role in the organization."""
    await _get_organization_with_access_check(org_id, current_user, db, require_admin=True)

    # Get membership
    result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    # Cannot change owner's role unless you're an owner
    if membership.org_role == OrgMemberRole.OWNER:
        current_membership = await _get_user_membership(org_id, current_user.id, db)
        if not current_membership or current_membership.org_role != OrgMemberRole.OWNER:
            raise HTTPException(status_code=403, detail="Only owners can modify owner roles")

    # Update role
    membership.org_role = OrgMemberRole(role_data.org_role.value)
    if role_data.notes is not None:
        membership.notes = role_data.notes

    await db.commit()
    await db.refresh(membership)

    logger.info("Member role updated", org_id=str(org_id), user_id=str(user_id), new_role=role_data.org_role.value)

    return OrganizationMemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        org_role=membership.org_role,
        is_active=membership.is_active,
        joined_at=membership.joined_at,
        notes=membership.notes,
        user_email=membership.user.email if membership.user else None,
        user_username=membership.user.username if membership.user else None,
        user_full_name=membership.user.full_name if membership.user else None,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    org_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_permission(Permission.ORG_MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from an organization."""
    await _get_organization_with_access_check(org_id, current_user, db, require_admin=True)

    # Get membership
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in organization")

    # Cannot remove owner unless you're also an owner
    if membership.org_role == OrgMemberRole.OWNER:
        current_membership = await _get_user_membership(org_id, current_user.id, db)
        if not current_membership or current_membership.org_role != OrgMemberRole.OWNER:
            raise HTTPException(status_code=403, detail="Only owners can remove owners")

    # Remove from all batches in this organization first
    await db.execute(
        select(BatchMembership)
        .join(Batch)
        .where(
            Batch.organization_id == org_id,
            BatchMembership.user_id == user_id
        )
    )

    await db.delete(membership)
    await db.commit()

    logger.info("Member removed from organization", org_id=str(org_id), user_id=str(user_id))


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/{org_id}/dashboard", response_model=OrganizationDashboard)
async def get_organization_dashboard(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ORG_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get organization dashboard with stats."""
    organization = await _get_organization_with_access_check(org_id, current_user, db)

    # Get member counts
    total_members = await _get_member_count(org_id, db)
    active_members = await _get_active_member_count(org_id, db)

    # Get batch counts
    total_batches = await _get_batch_count(org_id, db)
    active_batches_result = await db.execute(
        select(func.count(Batch.id)).where(
            Batch.organization_id == org_id,
            Batch.status == BatchStatus.ACTIVE
        )
    )
    active_batches = active_batches_result.scalar()

    # Get completion stats (placeholder - would need actual tracking)
    total_courses_completed = 0
    total_labs_completed = 0
    avg_progress = 0.0

    # Get recent activity (placeholder)
    recent_activity = []

    org_response = await _build_org_response(organization, db)

    return OrganizationDashboard(
        organization=org_response,
        total_members=total_members,
        active_members=active_members,
        total_batches=total_batches,
        active_batches=active_batches,
        total_courses_completed=total_courses_completed,
        total_labs_completed=total_labs_completed,
        avg_progress=avg_progress,
        recent_activity=recent_activity,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_organization_with_access_check(
    org_id: UUID,
    current_user: User,
    db: AsyncSession,
    require_admin: bool = False,
) -> Organization:
    """Get organization and verify user has access."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Super admin has access to all
    if current_user.is_super_admin:
        return organization

    # Check user's membership
    membership = await _get_user_membership(org_id, current_user.id, db)

    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    if require_admin and membership.org_role not in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")

    return organization


async def _get_user_membership(
    org_id: UUID,
    user_id: UUID,
    db: AsyncSession,
) -> Optional[OrganizationMembership]:
    """Get user's membership in an organization."""
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def _verify_org_access(org_id: UUID, user_id: UUID, db: AsyncSession):
    """Verify user has access to organization."""
    membership = await _get_user_membership(org_id, user_id, db)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")


async def _get_member_count(org_id: UUID, db: AsyncSession) -> int:
    """Get total member count for an organization."""
    result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id
        )
    )
    return result.scalar() or 0


async def _get_active_member_count(org_id: UUID, db: AsyncSession) -> int:
    """Get active member count for an organization."""
    result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.is_active == True
        )
    )
    return result.scalar() or 0


async def _get_batch_count(org_id: UUID, db: AsyncSession) -> int:
    """Get total batch count for an organization."""
    result = await db.execute(
        select(func.count(Batch.id)).where(Batch.organization_id == org_id)
    )
    return result.scalar() or 0


async def _build_org_response(organization: Organization, db: AsyncSession) -> OrganizationResponse:
    """Build organization response with counts."""
    member_count = await _get_member_count(organization.id, db)
    batch_count = await _get_batch_count(organization.id, db)

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        org_type=organization.org_type,
        is_active=organization.is_active,
        logo_url=organization.logo_url,
        website=organization.website,
        contact_email=organization.contact_email,
        max_members=organization.max_members,
        subscription_tier=organization.subscription_tier,
        subscription_expires_at=organization.subscription_expires_at,
        created_by=organization.created_by,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
        member_count=member_count,
        batch_count=batch_count,
    )
