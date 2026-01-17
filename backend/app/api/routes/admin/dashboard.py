"""Admin dashboard routes."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.course import Course
from app.models.lab import Lab, LabSession, LabStatus
from app.schemas.admin import DashboardStats, RecentActivity
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/dashboard")


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard statistics."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Total users
    total_users = await db.scalar(select(func.count(User.id)))

    # Active users today (logged in today)
    active_today = await db.scalar(
        select(func.count(User.id)).where(
            and_(User.last_login >= today_start, User.is_active == True)
        )
    )

    # New users this week
    new_this_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )

    # Course stats
    total_courses = await db.scalar(select(func.count(Course.id)))
    published_courses = await db.scalar(
        select(func.count(Course.id)).where(Course.is_published == True)
    )

    # Pending approval (draft/unpublished courses)
    pending_approval = await db.scalar(
        select(func.count(Course.id)).where(Course.is_published == False)
    )

    # Lab stats
    total_labs = await db.scalar(select(func.count(Lab.id)))

    # Active lab sessions
    active_sessions = await db.scalar(
        select(func.count(LabSession.id)).where(LabSession.status == LabStatus.RUNNING)
    )

    # Active VMs (sessions with container_id or environment has VM)
    # For now, estimate based on active sessions
    active_vms = 0  # Will be updated when VM tracking is implemented

    return DashboardStats(
        total_users=total_users or 0,
        active_users_today=active_today or 0,
        new_users_this_week=new_this_week or 0,
        total_courses=total_courses or 0,
        published_courses=published_courses or 0,
        pending_approval=pending_approval or 0,
        total_labs=total_labs or 0,
        active_lab_sessions=active_sessions or 0,
        active_vms=active_vms,
    )


@router.get("/activity", response_model=list[RecentActivity])
async def get_recent_activity(
    limit: int = 10,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get recent admin activity."""
    audit_service = AuditService(db)
    logs = await audit_service.get_recent_activity(limit=limit)

    return [
        RecentActivity(
            action=log.action.value,
            user_email=log.user_email or "System",
            target=log.target_name,
            timestamp=log.timestamp,
        )
        for log in logs
    ]
