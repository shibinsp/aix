"""API routes for analytics and progress tracking."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import datetime, timedelta, date
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.admin import Permission
from app.models.organization import (
    Organization, OrganizationMembership, Batch, BatchMembership, OrgMemberRole
)
from app.models.limits import UserUsageTracking
from app.schemas.analytics import (
    UserProgressSummary, CourseProgress, LeaderboardEntry, BatchAnalytics,
    OrganizationAnalytics, UserAnalytics, ProgressReport, ActivityFeed,
    ActivityFeedResponse, BenchmarkComparison, ExportRequest, ExportResponse,
)

logger = structlog.get_logger()

router = APIRouter()


# ============================================================================
# USER'S OWN ANALYTICS
# ============================================================================

@router.get("/my", response_model=UserAnalytics)
async def get_my_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's learning analytics."""
    return await _build_user_analytics(current_user.id, db)


@router.get("/my/progress", response_model=List[CourseProgress])
async def get_my_course_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's progress in all courses."""
    # Get user's course enrollments/progress
    # This would integrate with actual course enrollment model
    # For now, return based on usage tracking
    progress_list = []

    # TODO: Integrate with actual course progress model
    # This is a placeholder implementation

    return progress_list


@router.get("/my/benchmark", response_model=BenchmarkComparison)
async def get_my_benchmark(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare current user's progress to peers."""
    # Get user's membership
    membership_result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.organization))
        .where(OrganizationMembership.user_id == current_user.id)
    )
    membership = membership_result.scalar_one_or_none()

    # Get user's batch memberships
    batch_result = await db.execute(
        select(BatchMembership).where(BatchMembership.user_id == current_user.id)
    )
    batch_membership = batch_result.scalar_one_or_none()

    user_progress = 0.0
    batch_avg = 0.0
    org_avg = 0.0
    platform_avg = 0.0

    if batch_membership:
        user_progress = float(batch_membership.progress_percent or 0)

        # Get batch average
        batch_avg_result = await db.execute(
            select(func.avg(BatchMembership.progress_percent)).where(
                BatchMembership.batch_id == batch_membership.batch_id
            )
        )
        batch_avg = float(batch_avg_result.scalar() or 0)

    if membership:
        # Get org average
        org_members = await db.execute(
            select(OrganizationMembership.user_id).where(
                OrganizationMembership.organization_id == membership.organization_id
            )
        )
        member_ids = [row[0] for row in org_members.fetchall()]

        if member_ids:
            org_avg_result = await db.execute(
                select(func.avg(BatchMembership.progress_percent)).where(
                    BatchMembership.user_id.in_(member_ids)
                )
            )
            org_avg = float(org_avg_result.scalar() or 0)

    # Platform average
    platform_result = await db.execute(
        select(func.avg(BatchMembership.progress_percent))
    )
    platform_avg = float(platform_result.scalar() or 0)

    # Calculate percentiles (simplified)
    batch_percentile = 50  # Placeholder
    org_percentile = 50

    return BenchmarkComparison(
        user_progress_percent=user_progress,
        batch_avg_percent=batch_avg,
        org_avg_percent=org_avg,
        platform_avg_percent=platform_avg,
        percentile_in_batch=batch_percentile,
        percentile_in_org=org_percentile,
    )


# ============================================================================
# ORGANIZATION ANALYTICS
# ============================================================================

@router.get("/organizations/{org_id}", response_model=OrganizationAnalytics)
async def get_organization_analytics(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for an organization."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check access
    if not current_user.is_super_admin:
        membership = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.org_role.in_([OrgMemberRole.OWNER, OrgMemberRole.ADMIN])
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied")

    # Get member counts
    member_count = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.is_active == True
        )
    )
    total_members = member_count.scalar() or 0

    # Active in last 7 days (based on user last_login)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_result = await db.execute(
        select(func.count(User.id)).where(
            User.last_login >= seven_days_ago,
            User.id.in_(
                select(OrganizationMembership.user_id).where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.is_active == True
                )
            )
        )
    )
    active_members = active_result.scalar() or 0

    # New members this month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.joined_at >= month_start
        )
    )
    new_members = new_result.scalar() or 0

    # Batch counts
    batch_count = await db.execute(
        select(func.count(Batch.id)).where(Batch.organization_id == org_id)
    )
    total_batches = batch_count.scalar() or 0

    active_batch_result = await db.execute(
        select(func.count(Batch.id)).where(
            Batch.organization_id == org_id,
            Batch.status == "active"
        )
    )
    active_batches = active_batch_result.scalar() or 0

    # Get usage stats
    member_ids_result = await db.execute(
        select(OrganizationMembership.user_id).where(
            OrganizationMembership.organization_id == org_id
        )
    )
    member_ids = [row[0] for row in member_ids_result.fetchall()]

    total_terminal = 0.0
    total_desktop = 0.0
    avg_storage = 0.0

    if member_ids:
        usage_result = await db.execute(
            select(
                func.sum(UserUsageTracking.terminal_minutes_this_month),
                func.sum(UserUsageTracking.desktop_minutes_this_month),
                func.avg(UserUsageTracking.storage_used_mb)
            ).where(UserUsageTracking.user_id.in_(member_ids))
        )
        row = usage_result.fetchone()
        if row:
            total_terminal = float(row[0] or 0) / 60
            total_desktop = float(row[1] or 0) / 60
            avg_storage = float(row[2] or 0)

    # Daily active users (last 14 days)
    daily_active = []
    for i in range(14):
        day = datetime.utcnow().date() - timedelta(days=i)
        daily_active.append({"date": day.isoformat(), "count": 0})  # Placeholder

    return OrganizationAnalytics(
        organization_id=org_id,
        organization_name=org.name,
        total_members=total_members,
        active_members=active_members,
        new_members_this_month=new_members,
        total_batches=total_batches,
        active_batches=active_batches,
        total_courses_completed=0,  # TODO: Integrate with course model
        total_labs_completed=0,
        avg_progress_percent=0.0,
        total_learning_hours=total_terminal + total_desktop,
        terminal_hours=total_terminal,
        desktop_hours=total_desktop,
        avg_storage_used_mb=avg_storage,
        daily_active_users=daily_active,
        weekly_completions=[],
    )


@router.get("/organizations/{org_id}/users", response_model=List[UserProgressSummary])
async def get_organization_user_progress(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get progress summary for all users in an organization."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Get members with their user info
    offset = (page - 1) * page_size
    members_result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.is_active == True
        )
        .offset(offset)
        .limit(page_size)
    )
    members = members_result.scalars().all()

    summaries = []
    for member in members:
        user = member.user
        if not user:
            continue

        # Get usage tracking
        tracking_result = await db.execute(
            select(UserUsageTracking).where(UserUsageTracking.user_id == user.id)
        )
        tracking = tracking_result.scalar_one_or_none()

        terminal_hours = 0.0
        desktop_hours = 0.0
        if tracking:
            terminal_hours = tracking.terminal_minutes_this_month / 60
            desktop_hours = tracking.desktop_minutes_this_month / 60

        summaries.append(UserProgressSummary(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            courses_completed=0,  # TODO: Integrate
            courses_in_progress=0,
            labs_completed=0,
            total_points=0,
            current_streak=0,
            total_learning_hours=terminal_hours + desktop_hours,
            terminal_hours=terminal_hours,
            desktop_hours=desktop_hours,
            last_activity=tracking.last_updated if tracking else None,
            joined_at=member.joined_at or user.created_at,
        ))

    return summaries


# ============================================================================
# BATCH ANALYTICS
# ============================================================================

@router.get("/batches/{batch_id}", response_model=BatchAnalytics)
async def get_batch_analytics(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics for a batch."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Get member count
    member_count = await db.execute(
        select(func.count(BatchMembership.id)).where(
            BatchMembership.batch_id == batch_id
        )
    )
    total_members = member_count.scalar() or 0

    # Active members
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_result = await db.execute(
        select(func.count(BatchMembership.id)).where(
            BatchMembership.batch_id == batch_id,
            BatchMembership.last_activity_at >= seven_days_ago
        )
    )
    active_members = active_result.scalar() or 0

    # Average progress
    avg_progress_result = await db.execute(
        select(func.avg(BatchMembership.progress_percent)).where(
            BatchMembership.batch_id == batch_id
        )
    )
    avg_progress = float(avg_progress_result.scalar() or 0)

    # Completion rate
    completed_result = await db.execute(
        select(func.count(BatchMembership.id)).where(
            BatchMembership.batch_id == batch_id,
            BatchMembership.completed_at.isnot(None)
        )
    )
    completed_count = completed_result.scalar() or 0
    completion_rate = (completed_count / total_members * 100) if total_members > 0 else 0

    # Count curriculum courses
    curriculum_count = len(batch.curriculum_courses or [])

    # Get member user IDs for usage stats
    member_ids_result = await db.execute(
        select(BatchMembership.user_id).where(BatchMembership.batch_id == batch_id)
    )
    member_ids = [row[0] for row in member_ids_result.fetchall()]

    total_hours = 0.0
    if member_ids:
        usage_result = await db.execute(
            select(
                func.sum(UserUsageTracking.terminal_minutes_this_month +
                         UserUsageTracking.desktop_minutes_this_month)
            ).where(UserUsageTracking.user_id.in_(member_ids))
        )
        total_minutes = usage_result.scalar() or 0
        total_hours = total_minutes / 60

    # Get top performers (by progress)
    top_result = await db.execute(
        select(BatchMembership)
        .options(selectinload(BatchMembership.user))
        .where(BatchMembership.batch_id == batch_id)
        .order_by(BatchMembership.progress_percent.desc())
        .limit(5)
    )
    top_members = top_result.scalars().all()

    top_performers = []
    for rank, member in enumerate(top_members, 1):
        if member.user:
            top_performers.append(LeaderboardEntry(
                rank=rank,
                user_id=member.user.id,
                username=member.user.username,
                full_name=member.user.full_name,
                avatar_url=member.user.avatar_url,
                points=0,
                courses_completed=len(member.courses_completed or []),
                labs_completed=len(member.labs_completed or []),
                streak=0,
            ))

    return BatchAnalytics(
        batch_id=batch_id,
        batch_name=batch.name,
        total_members=total_members,
        active_members=active_members,
        inactive_members=total_members - active_members,
        avg_progress_percent=avg_progress,
        completion_rate=completion_rate,
        courses_in_curriculum=curriculum_count,
        avg_courses_completed=0.0,  # TODO: Calculate
        total_labs_completed=0,
        avg_labs_per_member=0.0,
        total_learning_hours=total_hours,
        avg_hours_per_member=total_hours / total_members if total_members > 0 else 0,
        top_performers=top_performers,
    )


@router.get("/batches/{batch_id}/leaderboard", response_model=List[LeaderboardEntry])
async def get_batch_leaderboard(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
):
    """Get leaderboard for a batch."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Get members ordered by progress
    result = await db.execute(
        select(BatchMembership)
        .options(selectinload(BatchMembership.user))
        .where(BatchMembership.batch_id == batch_id)
        .order_by(BatchMembership.progress_percent.desc())
        .limit(limit)
    )
    members = result.scalars().all()

    leaderboard = []
    for rank, member in enumerate(members, 1):
        if member.user:
            leaderboard.append(LeaderboardEntry(
                rank=rank,
                user_id=member.user.id,
                username=member.user.username,
                full_name=member.user.full_name,
                avatar_url=member.user.avatar_url,
                points=0,  # TODO: Implement points system
                courses_completed=len(member.courses_completed or []),
                labs_completed=len(member.labs_completed or []),
                streak=0,
            ))

    return leaderboard


# ============================================================================
# ADMIN USER ANALYTICS
# ============================================================================

@router.get("/users/{user_id}", response_model=UserAnalytics)
async def get_user_analytics(
    user_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed analytics for a specific user (admin only)."""
    return await _build_user_analytics(user_id, db)


# ============================================================================
# ACTIVITY FEED
# ============================================================================

@router.get("/organizations/{org_id}/activity", response_model=ActivityFeedResponse)
async def get_organization_activity(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get activity feed for an organization."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # TODO: Implement activity tracking model and retrieve
    # For now return empty
    return ActivityFeedResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


@router.get("/batches/{batch_id}/activity", response_model=ActivityFeedResponse)
async def get_batch_activity(
    batch_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get activity feed for a batch."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return ActivityFeedResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
    )


# ============================================================================
# EXPORT
# ============================================================================

@router.post("/organizations/{org_id}/export", response_model=ExportResponse)
async def export_organization_analytics(
    org_id: UUID,
    export_request: ExportRequest,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_EXPORT)),
    db: AsyncSession = Depends(get_db),
):
    """Export organization analytics data."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # TODO: Implement export generation (CSV/XLSX/JSON)
    # For now return placeholder
    return ExportResponse(
        download_url=f"/api/v1/exports/org_{org_id}_{datetime.utcnow().isoformat()}.{export_request.format}",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        format=export_request.format,
        rows=0,
    )


@router.post("/batches/{batch_id}/export", response_model=ExportResponse)
async def export_batch_analytics(
    batch_id: UUID,
    export_request: ExportRequest,
    current_user: User = Depends(require_permission(Permission.ANALYTICS_EXPORT)),
    db: AsyncSession = Depends(get_db),
):
    """Export batch analytics data."""
    batch = await db.get(Batch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return ExportResponse(
        download_url=f"/api/v1/exports/batch_{batch_id}_{datetime.utcnow().isoformat()}.{export_request.format}",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        format=export_request.format,
        rows=0,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _build_user_analytics(user_id: UUID, db: AsyncSession) -> UserAnalytics:
    """Build detailed analytics for a user."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get usage tracking
    tracking_result = await db.execute(
        select(UserUsageTracking).where(UserUsageTracking.user_id == user_id)
    )
    tracking = tracking_result.scalar_one_or_none()

    terminal_hours = 0.0
    desktop_hours = 0.0
    if tracking:
        terminal_hours = tracking.terminal_minutes_this_month / 60
        desktop_hours = tracking.desktop_minutes_this_month / 60

    # Get batch progress
    batch_result = await db.execute(
        select(BatchMembership).where(BatchMembership.user_id == user_id)
    )
    batch_memberships = batch_result.scalars().all()

    courses_completed = 0
    labs_completed = 0
    for bm in batch_memberships:
        courses_completed += len(bm.courses_completed or [])
        labs_completed += len(bm.labs_completed or [])

    return UserAnalytics(
        user_id=user_id,
        username=user.username,
        full_name=user.full_name,
        courses_completed=courses_completed,
        courses_in_progress=0,  # TODO: Integrate with course enrollment
        total_courses_started=0,
        labs_completed=labs_completed,
        total_points=0,
        current_streak=0,
        longest_streak=0,
        total_learning_hours=terminal_hours + desktop_hours,
        terminal_hours=terminal_hours,
        desktop_hours=desktop_hours,
        avg_session_duration_minutes=0,
        course_progress=[],  # TODO: Integrate with course progress
        activity_by_day=[],
        skills_acquired=[],
        days_active_this_month=0,
        last_activity=tracking.last_updated if tracking else None,
    )
