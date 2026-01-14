"""API routes for resource limits management."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.admin import Permission
from app.models.organization import Organization, OrganizationMembership, Batch
from app.models.limits import (
    OrganizationResourceLimit, BatchResourceLimit, UserResourceLimit,
    UserUsageTracking, DEFAULT_LIMITS
)
from app.schemas.limits import (
    OrganizationLimitsCreate, OrganizationLimitsUpdate, OrganizationLimitsResponse,
    BatchLimitsUpdate, BatchLimitsResponse,
    UserLimitsCreate, UserLimitsUpdate, UserLimitsResponse,
    UsageTrackingResponse, EffectiveLimitsResponse, UsageSummaryResponse,
    DefaultLimitsResponse, UpdateDefaultLimitsRequest,
)
from app.services.limits import limit_enforcer

logger = structlog.get_logger()

router = APIRouter()


# ============================================================================
# SYSTEM DEFAULT LIMITS
# ============================================================================

@router.get("/defaults", response_model=DefaultLimitsResponse)
async def get_default_limits(
    current_user: User = Depends(require_permission(Permission.LIMITS_VIEW)),
):
    """Get system default resource limits."""
    return DefaultLimitsResponse(
        max_courses_per_user=DEFAULT_LIMITS["max_courses_per_user"],
        max_ai_generated_courses=DEFAULT_LIMITS["max_ai_generated_courses"],
        max_concurrent_labs=DEFAULT_LIMITS["max_concurrent_labs"],
        max_lab_duration_minutes=DEFAULT_LIMITS["max_lab_duration_minutes"],
        max_terminal_hours_monthly=DEFAULT_LIMITS["max_terminal_hours_monthly"],
        max_desktop_hours_monthly=DEFAULT_LIMITS["max_desktop_hours_monthly"],
        max_storage_gb=DEFAULT_LIMITS["max_storage_gb"],
        enable_persistent_vm=DEFAULT_LIMITS["enable_persistent_vm"],
    )


@router.patch("/defaults", response_model=DefaultLimitsResponse)
async def update_default_limits(
    limits_data: UpdateDefaultLimitsRequest,
    current_user: User = Depends(require_permission(Permission.LIMITS_UPDATE)),
):
    """Update system default resource limits (Super Admin only).

    Note: These changes persist only during runtime. For permanent changes,
    update the DEFAULT_LIMITS in the limits model file.
    """
    global DEFAULT_LIMITS

    update_data = limits_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            DEFAULT_LIMITS[field] = value

    logger.info("System default limits updated", updated_by=str(current_user.id), changes=update_data)

    return DefaultLimitsResponse(
        max_courses_per_user=DEFAULT_LIMITS["max_courses_per_user"],
        max_ai_generated_courses=DEFAULT_LIMITS["max_ai_generated_courses"],
        max_concurrent_labs=DEFAULT_LIMITS["max_concurrent_labs"],
        max_lab_duration_minutes=DEFAULT_LIMITS["max_lab_duration_minutes"],
        max_terminal_hours_monthly=DEFAULT_LIMITS["max_terminal_hours_monthly"],
        max_desktop_hours_monthly=DEFAULT_LIMITS["max_desktop_hours_monthly"],
        max_storage_gb=DEFAULT_LIMITS["max_storage_gb"],
        enable_persistent_vm=DEFAULT_LIMITS["enable_persistent_vm"],
    )


# ============================================================================
# USER LIMITS (CURRENT USER)
# ============================================================================

@router.get("/my", response_model=UsageSummaryResponse)
async def get_my_limits_and_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's effective limits and usage."""
    summary = await limit_enforcer.get_usage_summary(current_user.id, db)

    return UsageSummaryResponse(
        limits=EffectiveLimitsResponse(
            max_courses_per_user=summary["limits"]["max_courses_per_user"],
            max_ai_generated_courses=summary["limits"]["max_ai_generated_courses"],
            max_concurrent_labs=summary["limits"]["max_concurrent_labs"],
            max_lab_duration_minutes=summary["limits"]["max_lab_duration_minutes"],
            max_terminal_hours_monthly=summary["limits"]["max_terminal_hours_monthly"],
            max_desktop_hours_monthly=summary["limits"]["max_desktop_hours_monthly"],
            max_storage_gb=summary["limits"]["max_storage_gb"],
            enable_persistent_vm=summary["limits"]["enable_persistent_vm"],
            source=summary["limits"]["source"],
        ),
        usage=UsageTrackingResponse(
            id=UUID(int=0),  # Placeholder
            user_id=current_user.id,
            courses_created_total=summary["usage"]["courses_created_total"],
            ai_courses_this_month=summary["usage"]["ai_courses_this_month"],
            ai_courses_reset_date=None,
            active_lab_sessions=summary["usage"]["active_lab_sessions"],
            terminal_minutes_this_month=summary["usage"]["terminal_minutes_this_month"],
            desktop_minutes_this_month=summary["usage"]["desktop_minutes_this_month"],
            usage_reset_date=None,
            storage_used_mb=summary["usage"]["storage_used_mb"],
            last_updated=None,
        ),
        courses_remaining=summary["remaining"]["courses_remaining"],
        ai_courses_remaining_this_month=summary["remaining"]["ai_courses_remaining_this_month"],
        can_start_lab=summary["remaining"]["can_start_lab"],
        terminal_hours_remaining=summary["remaining"]["terminal_hours_remaining"],
        desktop_hours_remaining=summary["remaining"]["desktop_hours_remaining"],
        storage_remaining_gb=summary["remaining"]["storage_remaining_gb"],
    )


# ============================================================================
# ORGANIZATION LIMITS
# ============================================================================

@router.get("/organizations/{org_id}", response_model=OrganizationLimitsResponse)
async def get_organization_limits(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.LIMITS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get resource limits for an organization."""
    # Verify organization exists
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check access
    if not current_user.is_super_admin:
        membership = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.user_id == current_user.id
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    # Get limits
    result = await db.execute(
        select(OrganizationResourceLimit).where(
            OrganizationResourceLimit.organization_id == org_id
        )
    )
    limits = result.scalar_one_or_none()

    if not limits:
        # Create default limits
        limits = OrganizationResourceLimit(organization_id=org_id)
        db.add(limits)
        await db.commit()
        await db.refresh(limits)

    return OrganizationLimitsResponse.model_validate(limits)


@router.patch("/organizations/{org_id}", response_model=OrganizationLimitsResponse)
async def update_organization_limits(
    org_id: UUID,
    limits_data: OrganizationLimitsUpdate,
    current_user: User = Depends(require_permission(Permission.LIMITS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    """Update resource limits for an organization."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    result = await db.execute(
        select(OrganizationResourceLimit).where(
            OrganizationResourceLimit.organization_id == org_id
        )
    )
    limits = result.scalar_one_or_none()

    if not limits:
        limits = OrganizationResourceLimit(organization_id=org_id)
        db.add(limits)

    # Update fields
    update_data = limits_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(limits, field, value)

    await db.commit()
    await db.refresh(limits)

    logger.info("Organization limits updated", org_id=str(org_id), updated_by=str(current_user.id))

    return OrganizationLimitsResponse.model_validate(limits)


# ============================================================================
# BATCH LIMITS
# ============================================================================

@router.get("/batches/{batch_id}", response_model=BatchLimitsResponse)
async def get_batch_limits(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.LIMITS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get resource limits for a batch."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    result = await db.execute(
        select(BatchResourceLimit).where(BatchResourceLimit.batch_id == batch_id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        limits = BatchResourceLimit(batch_id=batch_id)
        db.add(limits)
        await db.commit()
        await db.refresh(limits)

    return BatchLimitsResponse.model_validate(limits)


@router.patch("/batches/{batch_id}", response_model=BatchLimitsResponse)
async def update_batch_limits(
    batch_id: UUID,
    limits_data: BatchLimitsUpdate,
    current_user: User = Depends(require_permission(Permission.LIMITS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    """Update resource limits for a batch."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    result = await db.execute(
        select(BatchResourceLimit).where(BatchResourceLimit.batch_id == batch_id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        limits = BatchResourceLimit(batch_id=batch_id)
        db.add(limits)

    update_data = limits_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(limits, field, value)

    await db.commit()
    await db.refresh(limits)

    logger.info("Batch limits updated", batch_id=str(batch_id), updated_by=str(current_user.id))

    return BatchLimitsResponse.model_validate(limits)


# ============================================================================
# USER LIMITS (ADMIN)
# ============================================================================

@router.get("/users/{user_id}", response_model=UsageSummaryResponse)
async def get_user_limits(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permission.LIMITS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get effective limits and usage for a specific user (admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    summary = await limit_enforcer.get_usage_summary(user_id, db)

    # Get actual tracking record for full details
    tracking = await limit_enforcer.get_usage_tracking(user_id, db)

    return UsageSummaryResponse(
        limits=EffectiveLimitsResponse(
            max_courses_per_user=summary["limits"]["max_courses_per_user"],
            max_ai_generated_courses=summary["limits"]["max_ai_generated_courses"],
            max_concurrent_labs=summary["limits"]["max_concurrent_labs"],
            max_lab_duration_minutes=summary["limits"]["max_lab_duration_minutes"],
            max_terminal_hours_monthly=summary["limits"]["max_terminal_hours_monthly"],
            max_desktop_hours_monthly=summary["limits"]["max_desktop_hours_monthly"],
            max_storage_gb=summary["limits"]["max_storage_gb"],
            enable_persistent_vm=summary["limits"]["enable_persistent_vm"],
            source=summary["limits"]["source"],
        ),
        usage=UsageTrackingResponse.model_validate(tracking),
        courses_remaining=summary["remaining"]["courses_remaining"],
        ai_courses_remaining_this_month=summary["remaining"]["ai_courses_remaining_this_month"],
        can_start_lab=summary["remaining"]["can_start_lab"],
        terminal_hours_remaining=summary["remaining"]["terminal_hours_remaining"],
        desktop_hours_remaining=summary["remaining"]["desktop_hours_remaining"],
        storage_remaining_gb=summary["remaining"]["storage_remaining_gb"],
    )


@router.post("/users/{user_id}", response_model=UserLimitsResponse, status_code=status.HTTP_201_CREATED)
async def set_user_limit_override(
    user_id: UUID,
    limits_data: UserLimitsCreate,
    current_user: User = Depends(require_permission(Permission.LIMITS_OVERRIDE)),
    db: AsyncSession = Depends(get_db),
):
    """Set a limit override for a specific user (super admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if override already exists
    result = await db.execute(
        select(UserResourceLimit).where(UserResourceLimit.user_id == user_id)
    )
    limits = result.scalar_one_or_none()

    if limits:
        raise HTTPException(status_code=400, detail="User already has limit override. Use PATCH to update.")

    # Create new override
    limits = UserResourceLimit(
        user_id=user_id,
        set_by=current_user.id,
        **limits_data.model_dump()
    )
    db.add(limits)
    await db.commit()
    await db.refresh(limits)

    logger.info("User limit override created", user_id=str(user_id), set_by=str(current_user.id))

    return UserLimitsResponse.model_validate(limits)


@router.patch("/users/{user_id}", response_model=UserLimitsResponse)
async def update_user_limit_override(
    user_id: UUID,
    limits_data: UserLimitsUpdate,
    current_user: User = Depends(require_permission(Permission.LIMITS_OVERRIDE)),
    db: AsyncSession = Depends(get_db),
):
    """Update limit override for a specific user (super admin only)."""
    result = await db.execute(
        select(UserResourceLimit).where(UserResourceLimit.user_id == user_id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        raise HTTPException(status_code=404, detail="User limit override not found. Use POST to create.")

    update_data = limits_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(limits, field, value)

    limits.set_by = current_user.id
    await db.commit()
    await db.refresh(limits)

    logger.info("User limit override updated", user_id=str(user_id), updated_by=str(current_user.id))

    return UserLimitsResponse.model_validate(limits)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_limit_override(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permission.LIMITS_OVERRIDE)),
    db: AsyncSession = Depends(get_db),
):
    """Remove limit override for a user (reverts to batch/org/default limits)."""
    result = await db.execute(
        select(UserResourceLimit).where(UserResourceLimit.user_id == user_id)
    )
    limits = result.scalar_one_or_none()

    if not limits:
        raise HTTPException(status_code=404, detail="User limit override not found")

    await db.delete(limits)
    await db.commit()

    logger.info("User limit override removed", user_id=str(user_id), removed_by=str(current_user.id))
