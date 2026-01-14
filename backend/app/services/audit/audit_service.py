"""Audit logging service for tracking admin actions."""
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import Request

from app.models.audit import AuditLog, AuditAction, AuditSeverity
from app.models.user import User


def utcnow():
    return datetime.now(timezone.utc)


class AuditService:
    """Service for creating and querying audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: AuditAction,
        user: Optional[User] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        request: Optional[Request] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action being logged
            user: The user performing the action
            target_type: Type of target (user, course, lab, setting, etc.)
            target_id: ID of the target
            target_name: Human-readable name of target
            old_value: Previous state (for updates)
            new_value: New state (for creates/updates)
            description: Optional description
            severity: Severity level
            request: FastAPI request for IP/user agent
            extra_data: Additional context

        Returns:
            The created AuditLog entry
        """
        # Extract request info if available
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:500]

        audit_log = AuditLog(
            user_id=user.id if user else None,
            user_email=user.email if user else None,
            user_role=user.role.value if user else None,
            action=action,
            severity=severity,
            description=description,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            target_name=target_name,
            old_value=old_value,
            new_value=new_value,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=utcnow(),
        )

        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)

        return audit_log

    async def log_login(
        self, user: User, success: bool, request: Optional[Request] = None
    ) -> AuditLog:
        """Log a login attempt."""
        action = AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED
        severity = AuditSeverity.INFO if success else AuditSeverity.WARNING

        return await self.log(
            action=action,
            user=user if success else None,
            target_type="user",
            target_id=user.id,
            target_name=user.email,
            severity=severity,
            request=request,
            extra_data={"email": user.email} if not success else None,
        )

    async def log_user_change(
        self,
        action: AuditAction,
        actor: User,
        target_user: User,
        old_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        description: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log a user-related change."""
        severity = AuditSeverity.WARNING if action in (
            AuditAction.USER_BAN,
            AuditAction.USER_ROLE_CHANGE,
            AuditAction.USER_DELETE,
        ) else AuditSeverity.INFO

        return await self.log(
            action=action,
            user=actor,
            target_type="user",
            target_id=target_user.id,
            target_name=target_user.email,
            old_value=old_data,
            new_value=new_data,
            description=description,
            severity=severity,
            request=request,
        )

    async def log_setting_change(
        self,
        actor: User,
        setting_key: str,
        old_value: Any,
        new_value: Any,
        is_sensitive: bool = False,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log a setting change."""
        # Mask sensitive values
        old_masked = "***" if is_sensitive else old_value
        new_masked = "***" if is_sensitive else new_value

        return await self.log(
            action=AuditAction.SETTING_UPDATE,
            user=actor,
            target_type="setting",
            target_id=setting_key,
            target_name=setting_key,
            old_value={"value": old_masked},
            new_value={"value": new_masked},
            severity=AuditSeverity.WARNING,
            request=request,
        )

    async def log_api_key_change(
        self,
        action: AuditAction,
        actor: User,
        service_name: str,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Log an API key change."""
        return await self.log(
            action=action,
            user=actor,
            target_type="api_key",
            target_id=service_name,
            target_name=service_name,
            severity=AuditSeverity.WARNING,
            request=request,
        )

    async def query(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        target_type: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        """
        Query audit logs with filters.

        Args:
            user_id: Filter by actor user ID
            action: Filter by action type
            target_type: Filter by target type
            severity: Filter by severity
            start_date: Filter logs after this date
            end_date: Filter logs before this date
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching AuditLog entries
        """
        query = select(AuditLog)
        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if target_type:
            conditions.append(AuditLog.target_type == target_type)
        if severity:
            conditions.append(AuditLog.severity == severity)
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLog.timestamp.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_activity(self, limit: int = 10) -> list[AuditLog]:
        """Get recent audit activity."""
        query = (
            select(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        user_id: Optional[UUID] = None,
        action: Optional[AuditAction] = None,
        target_type: Optional[str] = None,
    ) -> int:
        """Count audit logs matching filters."""
        from sqlalchemy import func

        query = select(func.count(AuditLog.id))
        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if target_type:
            conditions.append(AuditLog.target_type == target_type)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0
