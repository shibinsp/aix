"""Admin audit log routes."""
from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.models.user import User
from app.models.audit import AuditAction, AuditSeverity
from app.schemas.admin import AuditLogResponse
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/audit")


@router.get("/logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter by actor user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    severity: Optional[AuditSeverity] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None, description="Filter logs after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter logs before this date"),
    limit: int = Query(50, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Query audit logs with optional filters.

    Admins can view all logs. Moderators can only view their own actions.
    """
    audit_service = AuditService(db)

    # Moderators can only see their own logs
    if current_user.role.value == "moderator":
        user_id = current_user.id

    logs = await audit_service.query(
        user_id=user_id,
        action=action,
        target_type=target_type,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=log.user_email,
            user_role=log.user_role,
            action=log.action,
            severity=log.severity,
            description=log.description,
            target_type=log.target_type,
            target_id=log.target_id,
            target_name=log.target_name,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=str(log.ip_address) if log.ip_address else None,
            user_agent=log.user_agent,
            timestamp=log.timestamp,
        )
        for log in logs
    ]


@router.get("/logs/count")
async def count_audit_logs(
    user_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    target_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get count of audit logs matching filters."""
    audit_service = AuditService(db)

    # Moderators can only see their own logs
    if current_user.role.value == "moderator":
        user_id = current_user.id

    count = await audit_service.count(
        user_id=user_id,
        action=action,
        target_type=target_type,
    )

    return {"count": count}


@router.get("/logs/export")
async def export_audit_logs(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Export audit logs as CSV (super admin only).

    Returns a CSV file with all audit logs in the date range.
    """
    audit_service = AuditService(db)

    logs = await audit_service.query(
        start_date=start_date,
        end_date=end_date,
        limit=10000,  # Max export
    )

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "timestamp",
        "user_email",
        "user_role",
        "action",
        "severity",
        "target_type",
        "target_id",
        "target_name",
        "description",
        "ip_address",
    ])

    # Data
    for log in logs:
        writer.writerow([
            log.timestamp.isoformat() if log.timestamp else "",
            log.user_email or "",
            log.user_role or "",
            log.action.value,
            log.severity.value,
            log.target_type or "",
            log.target_id or "",
            log.target_name or "",
            log.description or "",
            str(log.ip_address) if log.ip_address else "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get("/actions", response_model=list[str])
async def get_action_types(
    current_user: User = Depends(get_current_admin),
):
    """Get all available audit action types."""
    return [action.value for action in AuditAction]


@router.get("/severities", response_model=list[str])
async def get_severity_levels(
    current_user: User = Depends(get_current_admin),
):
    """Get all available severity levels."""
    return [severity.value for severity in AuditSeverity]
