"""API routes for batch management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.sanitization import sanitize_like_pattern
from app.models.user import User
from app.models.admin import Permission
from app.models.organization import (
    Organization, OrgMemberRole, Batch, BatchStatus,
    OrganizationMembership, BatchMembership
)
from app.models.limits import BatchResourceLimit
from app.schemas.organization import (
    BatchCreate, BatchUpdate, BatchResponse, BatchListResponse,
    AddBatchMemberRequest, BatchMemberResponse,
    BatchDashboard, PaginatedBatches,
)

logger = structlog.get_logger()

router = APIRouter()


# ============================================================================
# BATCH CRUD
# ============================================================================

@router.post("/organizations/{org_id}/batches", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    org_id: UUID,
    batch_data: BatchCreate,
    current_user: User = Depends(require_permission(Permission.BATCH_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new batch in an organization."""
    # Verify organization access
    organization = await _get_organization_with_admin_check(org_id, current_user, db)

    # Create batch
    batch = Batch(
        organization_id=org_id,
        name=batch_data.name,
        description=batch_data.description,
        status=BatchStatus(batch_data.status.value) if batch_data.status else BatchStatus.ACTIVE,
        start_date=batch_data.start_date,
        end_date=batch_data.end_date,
        max_users=batch_data.max_users,
        curriculum_courses=batch_data.curriculum_courses,
        settings=batch_data.settings,
        created_by=current_user.id,
    )

    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    # Create default resource limits for the batch
    resource_limits = BatchResourceLimit(batch_id=batch.id)
    db.add(resource_limits)
    await db.commit()

    logger.info("Batch created", batch_id=str(batch.id), org_id=str(org_id), name=batch.name)

    return await _build_batch_response(batch, db)


@router.get("/organizations/{org_id}/batches", response_model=PaginatedBatches)
async def list_batches(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """List batches in an organization."""
    await _verify_org_access(org_id, current_user, db)

    query = select(Batch).where(Batch.organization_id == org_id)

    if status:
        query = query.where(Batch.status == BatchStatus(status))

    if search:
        search_pattern = sanitize_like_pattern(search)
        query = query.where(Batch.name.ilike(f"%{search_pattern}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Batch.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    batches = result.scalars().all()

    items = []
    for batch in batches:
        member_count = await _get_batch_member_count(batch.id, db)
        progress_avg = await _get_batch_progress_avg(batch.id, db)
        items.append(BatchListResponse(
            id=batch.id,
            organization_id=batch.organization_id,
            name=batch.name,
            status=batch.status,
            start_date=batch.start_date,
            end_date=batch.end_date,
            member_count=member_count,
            progress_avg=progress_avg,
            created_at=batch.created_at,
        ))

    pages = (total + page_size - 1) // page_size

    return PaginatedBatches(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/batches/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get batch details."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db)
    return await _build_batch_response(batch, db)


@router.patch("/batches/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: UUID,
    batch_data: BatchUpdate,
    current_user: User = Depends(require_permission(Permission.BATCH_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    """Update batch details."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db, require_admin=True)

    # Update fields
    update_data = batch_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = BatchStatus(value.value)
        setattr(batch, field, value)

    await db.commit()
    await db.refresh(batch)

    logger.info("Batch updated", batch_id=str(batch_id))

    return await _build_batch_response(batch, db)


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a batch."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db, require_admin=True)

    await db.delete(batch)
    await db.commit()

    logger.info("Batch deleted", batch_id=str(batch_id))


# ============================================================================
# BATCH MEMBER MANAGEMENT
# ============================================================================

@router.get("/batches/{batch_id}/members", response_model=List[BatchMemberResponse])
async def list_batch_members(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List members of a batch."""
    await _get_batch_with_access_check(batch_id, current_user, db)

    offset = (page - 1) * page_size
    result = await db.execute(
        select(BatchMembership)
        .options(selectinload(BatchMembership.user))
        .where(BatchMembership.batch_id == batch_id)
        .order_by(BatchMembership.enrolled_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    memberships = result.scalars().all()

    return [
        BatchMemberResponse(
            id=m.id,
            batch_id=m.batch_id,
            user_id=m.user_id,
            enrolled_at=m.enrolled_at,
            completed_at=m.completed_at,
            progress_percent=m.progress_percent,
            courses_completed=m.courses_completed,
            labs_completed=m.labs_completed,
            last_activity_at=m.last_activity_at,
            user_email=m.user.email if m.user else None,
            user_username=m.user.username if m.user else None,
            user_full_name=m.user.full_name if m.user else None,
        )
        for m in memberships
    ]


@router.post("/batches/{batch_id}/members", response_model=List[BatchMemberResponse], status_code=status.HTTP_201_CREATED)
async def add_batch_members(
    batch_id: UUID,
    member_data: AddBatchMemberRequest,
    current_user: User = Depends(require_permission(Permission.BATCH_MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
):
    """Add members to a batch."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db, require_admin=True)

    # Check max users limit
    if batch.max_users:
        current_count = await _get_batch_member_count(batch_id, db)
        if current_count + len(member_data.user_ids) > batch.max_users:
            raise HTTPException(status_code=400, detail="Adding these users would exceed batch member limit")

    added_members = []

    for user_id in member_data.user_ids:
        # Verify user exists and is in the organization
        user = await db.get(User, user_id)
        if not user:
            continue  # Skip non-existent users

        # Check if user is in the organization
        org_membership = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == batch.organization_id,
                OrganizationMembership.user_id == user_id
            )
        )
        if not org_membership.scalar_one_or_none():
            continue  # Skip users not in organization

        # Check if already in batch
        existing = await db.execute(
            select(BatchMembership).where(
                BatchMembership.batch_id == batch_id,
                BatchMembership.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            continue  # Skip if already enrolled

        # Create batch membership
        membership = BatchMembership(
            batch_id=batch_id,
            user_id=user_id,
        )
        db.add(membership)
        await db.flush()

        added_members.append(BatchMemberResponse(
            id=membership.id,
            batch_id=membership.batch_id,
            user_id=membership.user_id,
            enrolled_at=membership.enrolled_at,
            completed_at=None,
            progress_percent=0,
            courses_completed=None,
            labs_completed=None,
            last_activity_at=None,
            user_email=user.email,
            user_username=user.username,
            user_full_name=user.full_name,
        ))

    await db.commit()

    logger.info("Members added to batch", batch_id=str(batch_id), count=len(added_members))

    return added_members


@router.delete("/batches/{batch_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_batch_member(
    batch_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_MANAGE_MEMBERS)),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from a batch."""
    await _get_batch_with_access_check(batch_id, current_user, db, require_admin=True)

    result = await db.execute(
        select(BatchMembership).where(
            BatchMembership.batch_id == batch_id,
            BatchMembership.user_id == user_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(status_code=404, detail="Member not found in batch")

    await db.delete(membership)
    await db.commit()

    logger.info("Member removed from batch", batch_id=str(batch_id), user_id=str(user_id))


# ============================================================================
# CURRICULUM MANAGEMENT
# ============================================================================

@router.patch("/batches/{batch_id}/curriculum")
async def update_batch_curriculum(
    batch_id: UUID,
    courses: List[UUID],
    current_user: User = Depends(require_permission(Permission.BATCH_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    """Update the curriculum (assigned courses) for a batch."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db, require_admin=True)

    batch.curriculum_courses = [str(c) for c in courses]
    await db.commit()

    logger.info("Batch curriculum updated", batch_id=str(batch_id), course_count=len(courses))

    return {"message": "Curriculum updated successfully", "courses": courses}


# ============================================================================
# LEADERBOARD
# ============================================================================

@router.get("/batches/{batch_id}/leaderboard")
async def get_batch_leaderboard(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_VIEW)),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """Get leaderboard for a batch based on progress."""
    await _get_batch_with_access_check(batch_id, current_user, db)

    result = await db.execute(
        select(BatchMembership)
        .options(selectinload(BatchMembership.user))
        .where(BatchMembership.batch_id == batch_id)
        .order_by(BatchMembership.progress_percent.desc())
        .limit(limit)
    )
    memberships = result.scalars().all()

    leaderboard = []
    for i, m in enumerate(memberships, 1):
        leaderboard.append({
            "rank": i,
            "user_id": str(m.user_id),
            "username": m.user.username if m.user else None,
            "full_name": m.user.full_name if m.user else None,
            "progress_percent": m.progress_percent,
            "courses_completed": len(m.courses_completed or []),
            "labs_completed": len(m.labs_completed or []),
        })

    return {"leaderboard": leaderboard, "batch_id": str(batch_id)}


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get("/batches/{batch_id}/dashboard", response_model=BatchDashboard)
async def get_batch_dashboard(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.BATCH_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get batch dashboard with stats."""
    batch = await _get_batch_with_access_check(batch_id, current_user, db)

    total_members = await _get_batch_member_count(batch_id, db)

    # Active members (those with activity in last 7 days)
    active_members = total_members  # Placeholder - need activity tracking

    avg_progress = await _get_batch_progress_avg(batch_id, db)

    courses_in_curriculum = len(batch.curriculum_courses or [])

    # Completion rate
    completion_result = await db.execute(
        select(func.count(BatchMembership.id)).where(
            BatchMembership.batch_id == batch_id,
            BatchMembership.completed_at.isnot(None)
        )
    )
    completed_count = completion_result.scalar() or 0
    completion_rate = (completed_count / total_members * 100) if total_members > 0 else 0

    # Leaderboard (top 5)
    leaderboard_result = await db.execute(
        select(BatchMembership)
        .options(selectinload(BatchMembership.user))
        .where(BatchMembership.batch_id == batch_id)
        .order_by(BatchMembership.progress_percent.desc())
        .limit(5)
    )
    leaderboard_members = leaderboard_result.scalars().all()

    leaderboard = []
    for i, m in enumerate(leaderboard_members, 1):
        leaderboard.append({
            "rank": i,
            "user_id": str(m.user_id),
            "username": m.user.username if m.user else None,
            "full_name": m.user.full_name if m.user else None,
            "progress_percent": m.progress_percent,
        })

    batch_response = await _build_batch_response(batch, db)

    return BatchDashboard(
        batch=batch_response,
        total_members=total_members,
        active_members=active_members,
        avg_progress=avg_progress,
        courses_in_curriculum=courses_in_curriculum,
        completion_rate=completion_rate,
        leaderboard=leaderboard,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_organization_with_admin_check(
    org_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> Organization:
    """Get organization and verify user has admin access."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    organization = result.scalar_one_or_none()

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    if current_user.is_super_admin:
        return organization

    # Check membership
    membership = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == current_user.id
        )
    )
    mem = membership.scalar_one_or_none()

    if not mem:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    if mem.org_role not in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN, OrgMemberRole.INSTRUCTOR):
        raise HTTPException(status_code=403, detail="You don't have permission to manage batches")

    return organization


async def _verify_org_access(
    org_id: UUID,
    current_user: User,
    db: AsyncSession,
):
    """Verify user has access to organization."""
    if current_user.is_super_admin:
        return

    membership = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == current_user.id
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not a member of this organization")


async def _get_batch_with_access_check(
    batch_id: UUID,
    current_user: User,
    db: AsyncSession,
    require_admin: bool = False,
) -> Batch:
    """Get batch and verify user has access."""
    result = await db.execute(select(Batch).where(Batch.id == batch_id))
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if current_user.is_super_admin:
        return batch

    # Check organization membership
    membership = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == batch.organization_id,
            OrganizationMembership.user_id == current_user.id
        )
    )
    mem = membership.scalar_one_or_none()

    if not mem:
        raise HTTPException(status_code=403, detail="You are not a member of this organization")

    if require_admin and mem.org_role not in (OrgMemberRole.OWNER, OrgMemberRole.ADMIN, OrgMemberRole.INSTRUCTOR):
        raise HTTPException(status_code=403, detail="Admin access required")

    return batch


async def _get_batch_member_count(batch_id: UUID, db: AsyncSession) -> int:
    """Get member count for a batch."""
    result = await db.execute(
        select(func.count(BatchMembership.id)).where(BatchMembership.batch_id == batch_id)
    )
    return result.scalar() or 0


async def _get_batch_progress_avg(batch_id: UUID, db: AsyncSession) -> float:
    """Get average progress for a batch."""
    result = await db.execute(
        select(func.avg(BatchMembership.progress_percent)).where(BatchMembership.batch_id == batch_id)
    )
    avg = result.scalar()
    return float(avg) if avg else 0.0


async def _build_batch_response(batch: Batch, db: AsyncSession) -> BatchResponse:
    """Build batch response with counts."""
    member_count = await _get_batch_member_count(batch.id, db)
    progress_avg = await _get_batch_progress_avg(batch.id, db)

    return BatchResponse(
        id=batch.id,
        organization_id=batch.organization_id,
        name=batch.name,
        description=batch.description,
        status=batch.status,
        start_date=batch.start_date,
        end_date=batch.end_date,
        max_users=batch.max_users,
        curriculum_courses=batch.curriculum_courses,
        settings=batch.settings,
        created_by=batch.created_by,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        member_count=member_count,
        progress_avg=progress_avg,
    )
