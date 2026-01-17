"""Resource limit enforcement service.

This service handles checking and enforcing resource limits for users,
taking into account the priority hierarchy:
User override > Batch > Organization > System default
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import structlog

from app.models.user import User
from app.models.organization import OrganizationMembership, BatchMembership
from app.models.limits import (
    OrganizationResourceLimit, BatchResourceLimit, UserResourceLimit,
    UserUsageTracking, DEFAULT_LIMITS
)

logger = structlog.get_logger()


class ResourceLimitEnforcer:
    """Service for checking and enforcing resource limits."""

    async def get_effective_limits(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Get effective resource limits for a user.

        Priority: User override > Batch > Organization > System default
        """
        # Start with system defaults
        limits = DEFAULT_LIMITS.copy()
        source = "default"

        # Get user with relationships
        user_result = await db.execute(
            select(User)
            .options(
                selectinload(User.organization_membership).selectinload(
                    OrganizationMembership.organization
                ),
                selectinload(User.batch_memberships).selectinload(
                    BatchMembership.batch
                ),
                selectinload(User.resource_limits),
                selectinload(User.usage_tracking),
            )
            .where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            return {**limits, "source": source}

        # Apply organization limits
        if user.organization_membership and user.organization_membership.is_active:
            org = user.organization_membership.organization
            if org:
                org_limits_result = await db.execute(
                    select(OrganizationResourceLimit).where(
                        OrganizationResourceLimit.organization_id == org.id
                    )
                )
                org_limits = org_limits_result.scalar_one_or_none()

                if org_limits:
                    source = "organization"
                    self._apply_limits(limits, org_limits)

        # Apply batch limits (use first active batch with limits)
        for batch_membership in user.batch_memberships:
            batch = batch_membership.batch
            if batch:
                batch_limits_result = await db.execute(
                    select(BatchResourceLimit).where(
                        BatchResourceLimit.batch_id == batch.id
                    )
                )
                batch_limits = batch_limits_result.scalar_one_or_none()

                if batch_limits:
                    source = "batch"
                    self._apply_limits(limits, batch_limits)
                    break  # Only use first batch's limits

        # Apply user-specific overrides (highest priority)
        if user.resource_limits:
            source = "user"
            if user.resource_limits.unlimited_access:
                # Unlimited access - set very high limits
                for key in limits.keys():
                    if isinstance(limits[key], int):
                        limits[key] = 999999
            else:
                self._apply_limits(limits, user.resource_limits)

        return {**limits, "source": source}

    def _apply_limits(self, base: Dict[str, Any], override: Any) -> None:
        """Apply override limits to base limits."""
        for key in base.keys():
            value = getattr(override, key, None)
            if value is not None:
                base[key] = value

    async def get_usage_tracking(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> Optional[UserUsageTracking]:
        """Get or create usage tracking for a user."""
        result = await db.execute(
            select(UserUsageTracking).where(UserUsageTracking.user_id == user_id)
        )
        tracking = result.scalar_one_or_none()

        if not tracking:
            tracking = UserUsageTracking(user_id=user_id)
            db.add(tracking)
            await db.commit()
            await db.refresh(tracking)

        # Check if we need to reset monthly counters
        today = date.today()
        if tracking.usage_month != today.month or tracking.usage_year != today.year:
            tracking.ai_courses_this_month = 0
            tracking.terminal_minutes_this_month = 0
            tracking.desktop_minutes_this_month = 0
            tracking.usage_month = today.month
            tracking.usage_year = today.year
            await db.commit()

        return tracking

    async def check_can_create_course(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> tuple[bool, str]:
        """
        Check if user can create a new course.

        Returns: (can_create, reason)
        """
        limits = await self.get_effective_limits(user_id, db)
        tracking = await self.get_usage_tracking(user_id, db)

        max_courses = limits.get("max_courses_per_user", 5)

        if tracking.courses_created_total >= max_courses:
            return False, f"You have reached the maximum of {max_courses} courses"

        return True, "OK"

    async def check_can_generate_ai_course(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> tuple[bool, str]:
        """
        Check if user can generate an AI course.

        The limit is based on the actual number of AI-generated courses the user
        currently has, not cumulative usage. Deleting a course frees up a slot.

        Returns: (can_generate, reason)
        """
        from app.models.course import Course

        limits = await self.get_effective_limits(user_id, db)
        max_ai_courses = limits.get("max_ai_generated_courses", 10)

        # Count actual AI-generated courses the user currently has
        result = await db.execute(
            select(Course).where(
                Course.created_by == user_id,
                Course.is_ai_generated == True
            )
        )
        current_ai_courses = len(result.scalars().all())

        if current_ai_courses >= max_ai_courses:
            return False, f"You have reached the limit of {max_ai_courses} AI-generated courses. Delete an existing course to create a new one."

        return True, "OK"

    async def check_can_start_lab(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> tuple[bool, str]:
        """
        Check if user can start a new lab session.

        Returns: (can_start, reason)
        """
        limits = await self.get_effective_limits(user_id, db)
        tracking = await self.get_usage_tracking(user_id, db)

        max_concurrent = limits.get("max_concurrent_labs", 1)

        if tracking.active_lab_sessions >= max_concurrent:
            return False, f"You already have {max_concurrent} active lab session(s). Please stop one before starting another."

        return True, "OK"

    async def check_can_start_environment(
        self,
        user_id: UUID,
        env_type: str,
        db: AsyncSession,
    ) -> tuple[bool, str]:
        """
        Check if user can start a persistent environment.

        Returns: (can_start, reason)
        """
        limits = await self.get_effective_limits(user_id, db)
        tracking = await self.get_usage_tracking(user_id, db)

        if not limits.get("enable_persistent_vm", True):
            return False, "Persistent environments are not enabled for your account"

        if env_type == "terminal":
            max_hours = limits.get("max_terminal_hours_monthly", 30)
            used_minutes = tracking.terminal_minutes_this_month
        else:
            max_hours = limits.get("max_desktop_hours_monthly", 10)
            used_minutes = tracking.desktop_minutes_this_month

        if used_minutes >= max_hours * 60:
            return False, f"You have used all {max_hours} hours of monthly {env_type} time"

        return True, "OK"

    async def record_course_created(
        self,
        user_id: UUID,
        is_ai_generated: bool,
        db: AsyncSession,
    ) -> None:
        """Record that a course was created."""
        tracking = await self.get_usage_tracking(user_id, db)
        tracking.courses_created_total += 1
        if is_ai_generated:
            tracking.ai_courses_this_month += 1
        await db.commit()

        logger.info(
            "Course creation recorded",
            user_id=str(user_id),
            total_courses=tracking.courses_created_total,
            ai_this_month=tracking.ai_courses_this_month,
        )

    async def record_lab_started(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Record that a lab session was started."""
        tracking = await self.get_usage_tracking(user_id, db)
        tracking.active_lab_sessions += 1
        await db.commit()

    async def record_lab_stopped(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Record that a lab session was stopped."""
        tracking = await self.get_usage_tracking(user_id, db)
        if tracking.active_lab_sessions > 0:
            tracking.active_lab_sessions -= 1
        await db.commit()

    async def record_environment_usage(
        self,
        user_id: UUID,
        env_type: str,
        minutes: int,
        db: AsyncSession,
    ) -> None:
        """Record environment usage time."""
        tracking = await self.get_usage_tracking(user_id, db)

        if env_type == "terminal":
            tracking.terminal_minutes_this_month += minutes
        else:
            tracking.desktop_minutes_this_month += minutes

        await db.commit()

    async def get_usage_summary(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Get a summary of user's limits and usage."""
        from app.models.course import Course

        limits = await self.get_effective_limits(user_id, db)
        tracking = await self.get_usage_tracking(user_id, db)

        max_courses = limits.get("max_courses_per_user", 50)
        max_ai_courses = limits.get("max_ai_generated_courses", 10)
        max_concurrent_labs = limits.get("max_concurrent_labs", 1)
        max_terminal_hours = limits.get("max_terminal_hours_monthly", 30)
        max_desktop_hours = limits.get("max_desktop_hours_monthly", 10)
        max_storage_gb = limits.get("max_storage_gb", 2)

        # Count actual AI-generated courses (not cumulative usage)
        result = await db.execute(
            select(Course).where(
                Course.created_by == user_id,
                Course.is_ai_generated == True
            )
        )
        current_ai_courses = len(result.scalars().all())

        return {
            "limits": {
                "max_courses_per_user": max_courses,
                "max_ai_generated_courses": max_ai_courses,
                "max_concurrent_labs": max_concurrent_labs,
                "max_lab_duration_minutes": limits.get("max_lab_duration_minutes", 60),
                "max_terminal_hours_monthly": max_terminal_hours,
                "max_desktop_hours_monthly": max_desktop_hours,
                "max_storage_gb": max_storage_gb,
                "enable_persistent_vm": limits.get("enable_persistent_vm", True),
                "source": limits.get("source", "default"),
            },
            "usage": {
                "courses_created_total": tracking.courses_created_total,
                "ai_courses_this_month": current_ai_courses,  # Now shows actual count
                "active_lab_sessions": tracking.active_lab_sessions,
                "terminal_minutes_this_month": tracking.terminal_minutes_this_month,
                "desktop_minutes_this_month": tracking.desktop_minutes_this_month,
                "storage_used_mb": tracking.storage_used_mb,
            },
            "remaining": {
                "courses_remaining": max(0, max_courses - tracking.courses_created_total),
                "ai_courses_remaining_this_month": max(0, max_ai_courses - current_ai_courses),
                "can_start_lab": tracking.active_lab_sessions < max_concurrent_labs,
                "terminal_hours_remaining": max(0, max_terminal_hours - (tracking.terminal_minutes_this_month / 60)),
                "desktop_hours_remaining": max(0, max_desktop_hours - (tracking.desktop_minutes_this_month / 60)),
                "storage_remaining_gb": max(0, max_storage_gb - (tracking.storage_used_mb / 1024)),
            },
        }


# Singleton instance
limit_enforcer = ResourceLimitEnforcer()
