"""Admin monitoring routes."""
import psutil
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.user import User
from app.models.lab import Lab, LabSession
from app.models.audit import AuditAction
from app.schemas.admin import ActiveLabSession, SystemResources
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/monitoring")


@router.get("/resources", response_model=SystemResources)
async def get_system_resources(
    current_user: User = Depends(get_current_admin),
):
    """Get current system resource usage."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Memory
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_used_gb = memory.used / (1024**3)
    memory_total_gb = memory.total / (1024**3)

    # Disk
    disk = psutil.disk_usage("/")
    disk_percent = disk.percent
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)

    # Count active containers/VMs (would need Docker/Podman integration)
    active_containers = 0
    active_vms = 0

    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list()
        active_containers = len([c for c in containers if "cyberx" in c.name.lower()])
    except Exception:
        pass  # Docker not available or not running

    return SystemResources(
        cpu_percent=round(cpu_percent, 1),
        memory_percent=round(memory_percent, 1),
        memory_used_gb=round(memory_used_gb, 2),
        memory_total_gb=round(memory_total_gb, 2),
        disk_percent=round(disk_percent, 1),
        disk_used_gb=round(disk_used_gb, 2),
        disk_total_gb=round(disk_total_gb, 2),
        active_containers=active_containers,
        active_vms=active_vms,
    )


@router.get("/labs/active", response_model=list[ActiveLabSession])
async def get_active_lab_sessions(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all active lab sessions."""
    result = await db.execute(
        select(LabSession)
        .options(joinedload(LabSession.user), joinedload(LabSession.lab))
        .where(LabSession.status == "active")
        .order_by(LabSession.started_at.desc())
    )
    sessions = result.scalars().all()

    return [
        ActiveLabSession(
            id=session.id,
            user_id=session.user_id,
            user_email=session.user.email if session.user else "Unknown",
            lab_title=session.lab.title if session.lab else "Unknown",
            started_at=session.started_at,
            container_ids=session.container_ids,
        )
        for session in sessions
    ]


@router.post("/labs/{session_id}/stop")
async def force_stop_lab_session(
    session_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force stop a lab session."""
    result = await db.execute(
        select(LabSession)
        .options(joinedload(LabSession.user), joinedload(LabSession.lab))
        .where(LabSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Stop the containers if exist
    if session.container_ids:
        try:
            import docker
            client = docker.from_env()
            for container_id in session.container_ids:
                try:
                    container = client.containers.get(container_id)
                    container.stop(timeout=5)
                    container.remove(force=True)
                except Exception:
                    pass  # Container might already be gone
        except Exception:
            pass  # Docker not available

    session.status = "terminated"
    session.terminated_by_admin = True
    await db.commit()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action=AuditAction.LAB_SESSION_FORCE_STOP,
        user=current_user,
        target_type="lab_session",
        target_id=session.id,
        target_name=session.lab.title if session.lab else None,
        request=request,
        extra_data={
            "user_id": str(session.user_id),
            "user_email": session.user.email if session.user else None,
        },
    )

    return {"message": "Lab session stopped"}


@router.get("/labs/count")
async def get_lab_session_counts(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get lab session counts by status."""
    from sqlalchemy import func

    result = await db.execute(
        select(LabSession.status, func.count(LabSession.id))
        .group_by(LabSession.status)
    )
    counts = {status: count for status, count in result.all()}

    return {
        "active": counts.get("active", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "terminated": counts.get("terminated", 0),
        "total": sum(counts.values()),
    }
