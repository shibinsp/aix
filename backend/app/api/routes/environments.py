"""API routes for persistent environments (terminal & desktop)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
import os
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.config import settings
from app.models.user import User
from app.models.admin import Permission
from app.models.environment import (
    PersistentEnvironment, EnvironmentType, EnvironmentStatus, EnvironmentSession
)
from app.schemas.environment import (
    EnvironmentStartRequest, EnvironmentStopRequest, EnvironmentResetRequest,
    ConnectionInfo, EnvironmentResponse, MyEnvironmentsResponse,
    EnvironmentStatusResponse, AdminEnvironmentListResponse, AdminEnvironmentResponse,
    AdminStopEnvironmentRequest, EnvironmentUsageStats,
)
from app.services.environments import persistent_env_manager

logger = structlog.get_logger()


def is_running_in_kubernetes() -> bool:
    """Check if we're running inside a Kubernetes cluster."""
    return (
        settings.K8S_IN_CLUSTER or
        os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
    )

router = APIRouter()


# ============================================================================
# USER ENVIRONMENT ENDPOINTS
# ============================================================================

@router.get("/my", response_model=MyEnvironmentsResponse)
async def get_my_environments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's persistent environments (terminal and desktop)."""
    # Get or create terminal environment
    terminal_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == EnvironmentType.TERMINAL
        )
    )
    terminal = terminal_result.scalar_one_or_none()

    # Get or create desktop environment
    desktop_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == EnvironmentType.DESKTOP
        )
    )
    desktop = desktop_result.scalar_one_or_none()

    # Shared volume name
    shared_volume = PersistentEnvironment.get_shared_volume_name(str(current_user.id))

    return MyEnvironmentsResponse(
        terminal=EnvironmentResponse.model_validate(terminal) if terminal else None,
        desktop=EnvironmentResponse.model_validate(desktop) if desktop else None,
        shared_volume=shared_volume,
    )


@router.post("/my/{env_type}/start", response_model=EnvironmentResponse)
async def start_environment(
    env_type: str,
    request: EnvironmentStartRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a persistent environment (terminal or desktop)."""
    # Validate environment type
    if env_type not in ("terminal", "desktop"):
        raise HTTPException(status_code=400, detail="Invalid environment type. Use 'terminal' or 'desktop'")

    environment_type = EnvironmentType(env_type)

    # Check resource limits - use default limits if method not available
    try:
        limits = current_user.get_effective_limits()
    except Exception as e:
        logger.warning(f"Could not get effective limits: {e}, using defaults")
        limits = {
            "enable_persistent_vm": True,
            "max_terminal_hours_monthly": 30,
            "max_desktop_hours_monthly": 10,
        }

    if not limits.get("enable_persistent_vm", True):
        raise HTTPException(status_code=403, detail="Persistent environments are not enabled for your account")

    # Get existing environment to check limits
    env_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == environment_type
        )
    )
    environment = env_result.scalar_one_or_none()

    # Check usage limits
    if environment_type == EnvironmentType.TERMINAL:
        max_hours = limits.get("max_terminal_hours_monthly", 30)
        used_minutes = environment.monthly_usage_minutes if environment else 0
    else:
        max_hours = limits.get("max_desktop_hours_monthly", 10)
        used_minutes = environment.monthly_usage_minutes if environment else 0

    if used_minutes >= max_hours * 60:
        raise HTTPException(status_code=403, detail=f"Monthly {env_type} usage limit exceeded")

    # Use Kubernetes manager if running in K8s
    if is_running_in_kubernetes():
        from app.services.environments.k8s_env_manager import k8s_env_manager

        try:
            connection_info = await k8s_env_manager.start_environment(
                str(current_user.id),
                env_type,
                db
            )

            # Get refreshed environment
            env_result = await db.execute(
                select(PersistentEnvironment).where(
                    PersistentEnvironment.user_id == current_user.id,
                    PersistentEnvironment.env_type == environment_type
                )
            )
            environment = env_result.scalar_one_or_none()

            logger.info("Environment started with Kubernetes",
                       env_id=str(environment.id), env_type=env_type, user_id=str(current_user.id))

            return EnvironmentResponse.model_validate(environment)

        except Exception as e:
            logger.error("Failed to start Kubernetes environment", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to start environment: {str(e)}")

    # Check if Docker is available
    docker_available = await persistent_env_manager.check_docker_available()

    if docker_available:
        # Use actual Docker container management
        try:
            connection_info = await persistent_env_manager.start_environment(
                str(current_user.id),
                env_type,
                db
            )

            # Get refreshed environment
            env_result = await db.execute(
                select(PersistentEnvironment).where(
                    PersistentEnvironment.user_id == current_user.id,
                    PersistentEnvironment.env_type == environment_type
                )
            )
            environment = env_result.scalar_one_or_none()

            logger.info("Environment started with Docker",
                       env_id=str(environment.id), env_type=env_type, user_id=str(current_user.id))

            return EnvironmentResponse.model_validate(environment)

        except Exception as e:
            logger.error("Failed to start Docker environment", error=str(e))
            raise HTTPException(status_code=500, detail=f"Failed to start environment: {str(e)}")
    else:
        # Fallback to simulation mode (for development without Docker)
        shared_volume = PersistentEnvironment.get_shared_volume_name(str(current_user.id))

        if not environment:
            resources = PersistentEnvironment.get_default_resources(environment_type)
            environment = PersistentEnvironment(
                user_id=current_user.id,
                env_type=environment_type,
                volume_name=shared_volume,
                memory_mb=resources["memory_mb"],
                cpu_cores=resources["cpu_cores"],
            )
            db.add(environment)
            await db.commit()
            await db.refresh(environment)

        if environment.status == EnvironmentStatus.RUNNING:
            return EnvironmentResponse.model_validate(environment)

        if environment.status == EnvironmentStatus.STARTING:
            raise HTTPException(status_code=409, detail="Environment is already starting")

        # Clear error state if retrying
        if environment.status == EnvironmentStatus.ERROR:
            environment.error_message = None

        environment.reset_monthly_usage()
        environment.status = EnvironmentStatus.STARTING
        await db.commit()

        try:
            # Simulation mode: assign fake ports
            if environment_type == EnvironmentType.TERMINAL:
                environment.ssh_port = 10000 + (hash(str(current_user.id)) % 10000)
                environment.access_url = f"ssh://alphha@localhost:{environment.ssh_port}"
            else:
                environment.vnc_port = 20000 + (hash(str(current_user.id)) % 10000)
                environment.novnc_port = 30000 + (hash(str(current_user.id)) % 10000)
                environment.vnc_password = "cyberaix"
                environment.access_url = f"http://localhost:{environment.novnc_port}"

            environment.mark_started()

            session = EnvironmentSession(
                environment_id=environment.id,
                user_id=current_user.id,
                lab_id=request.lab_id if request else None,
                course_id=request.course_id if request else None,
            )
            db.add(session)

            await db.commit()
            await db.refresh(environment)

            logger.info("Environment started in simulation mode",
                       env_id=str(environment.id), env_type=env_type, user_id=str(current_user.id))

            return EnvironmentResponse.model_validate(environment)

        except Exception as e:
            environment.mark_error(str(e))
            await db.commit()
            logger.error("Failed to start environment", error=str(e), env_id=str(environment.id))
            raise HTTPException(status_code=500, detail=f"Failed to start environment: {str(e)}")


@router.post("/my/{env_type}/stop", response_model=EnvironmentResponse)
async def stop_environment(
    env_type: str,
    request: EnvironmentStopRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop a persistent environment."""
    if env_type not in ("terminal", "desktop"):
        raise HTTPException(status_code=400, detail="Invalid environment type")

    environment_type = EnvironmentType(env_type)

    env_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == environment_type
        )
    )
    environment = env_result.scalar_one_or_none()

    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    if environment.status not in (EnvironmentStatus.RUNNING, EnvironmentStatus.ERROR):
        raise HTTPException(status_code=400, detail="Environment is not running")

    try:
        # Use Kubernetes manager if running in K8s
        if is_running_in_kubernetes():
            from app.services.environments.k8s_env_manager import k8s_env_manager

            await k8s_env_manager.stop_environment(
                str(current_user.id),
                env_type,
                db
            )

            await db.refresh(environment)
            logger.info("Environment stopped via Kubernetes", env_id=str(environment.id), env_type=env_type)
            return EnvironmentResponse.model_validate(environment)

        # Check if Docker is available for actual container stop
        docker_available = await persistent_env_manager.check_docker_available()

        if docker_available and environment.container_id:
            # Use Docker manager to stop container
            await persistent_env_manager.stop_environment(
                str(current_user.id),
                env_type,
                db
            )
        else:
            # Simulation mode: just update the database
            environment.status = EnvironmentStatus.STOPPING
            await db.commit()

            # End active session
            session_result = await db.execute(
                select(EnvironmentSession).where(
                    EnvironmentSession.environment_id == environment.id,
                    EnvironmentSession.ended_at.is_(None)
                )
            )
            active_session = session_result.scalar_one_or_none()
            if active_session:
                active_session.end_session(reason=request.reason if request else "user_stopped")

            environment.mark_stopped()
            await db.commit()

        # Refresh to get updated state
        await db.refresh(environment)

        logger.info("Environment stopped", env_id=str(environment.id), env_type=env_type)

        return EnvironmentResponse.model_validate(environment)

    except Exception as e:
        environment.mark_error(str(e))
        await db.commit()
        logger.error("Failed to stop environment", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to stop environment: {str(e)}")


@router.get("/my/{env_type}/status", response_model=EnvironmentStatusResponse)
async def get_environment_status(
    env_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of a specific environment."""
    try:
        environment_type = EnvironmentType(env_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid environment type")

    env_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == environment_type
        )
    )
    environment = env_result.scalar_one_or_none()

    if not environment:
        return EnvironmentStatusResponse(
            env_type=environment_type,
            status=EnvironmentStatus.STOPPED,
            is_running=False,
            is_available=True,
        )

    connection_info = None
    if environment.status == EnvironmentStatus.RUNNING:
        connection_info = ConnectionInfo(
            env_type=environment.env_type,
            status=environment.status,
            ssh_port=environment.ssh_port,
            connection_string=f"ssh -p {environment.ssh_port} alphha@localhost" if environment.ssh_port else None,
            vnc_port=environment.vnc_port,
            novnc_port=environment.novnc_port,
            access_url=environment.access_url,
            vnc_password=environment.vnc_password,
        )

    return EnvironmentStatusResponse(
        env_type=environment.env_type,
        status=environment.status,
        is_running=environment.is_running,
        is_available=environment.is_available,
        error_message=environment.error_message,
        connection_info=connection_info,
    )


@router.post("/my/{env_type}/reset")
async def reset_environment(
    env_type: str,
    request: EnvironmentResetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset an environment (delete all data in volume)."""
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to reset environment")

    try:
        environment_type = EnvironmentType(env_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid environment type")

    env_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == environment_type
        )
    )
    environment = env_result.scalar_one_or_none()

    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    if environment.status == EnvironmentStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Stop the environment before resetting")

    # TODO: Actually reset the volume
    # await reset_volume(environment.volume_name)

    environment.total_usage_minutes = 0
    environment.monthly_usage_minutes = 0
    environment.error_message = None
    await db.commit()

    logger.info("Environment reset", env_id=str(environment.id), env_type=env_type)

    return {"message": "Environment reset successfully", "env_type": env_type}


@router.get("/my/usage", response_model=EnvironmentUsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage statistics for environments."""
    limits = current_user.get_effective_limits()

    terminal_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == EnvironmentType.TERMINAL
        )
    )
    terminal = terminal_result.scalar_one_or_none()

    desktop_result = await db.execute(
        select(PersistentEnvironment).where(
            PersistentEnvironment.user_id == current_user.id,
            PersistentEnvironment.env_type == EnvironmentType.DESKTOP
        )
    )
    desktop = desktop_result.scalar_one_or_none()

    terminal_hours_limit = limits.get("max_terminal_hours_monthly", 30)
    desktop_hours_limit = limits.get("max_desktop_hours_monthly", 10)

    terminal_minutes = terminal.monthly_usage_minutes if terminal else 0
    desktop_minutes = desktop.monthly_usage_minutes if desktop else 0

    return EnvironmentUsageStats(
        total_terminal_minutes=terminal.total_usage_minutes if terminal else 0,
        total_desktop_minutes=desktop.total_usage_minutes if desktop else 0,
        monthly_terminal_minutes=terminal_minutes,
        monthly_desktop_minutes=desktop_minutes,
        terminal_hours_limit=terminal_hours_limit,
        desktop_hours_limit=desktop_hours_limit,
        terminal_hours_remaining=max(0, (terminal_hours_limit * 60 - terminal_minutes) / 60),
        desktop_hours_remaining=max(0, (desktop_hours_limit * 60 - desktop_minutes) / 60),
    )


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin", response_model=AdminEnvironmentListResponse)
async def admin_list_environments(
    current_user: User = Depends(require_permission(Permission.ENV_VIEW_ALL)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    env_type: Optional[str] = None,
):
    """Admin: List all environments."""
    query = select(PersistentEnvironment).options(selectinload(PersistentEnvironment.user))

    if status:
        query = query.where(PersistentEnvironment.status == EnvironmentStatus(status))

    if env_type:
        query = query.where(PersistentEnvironment.env_type == EnvironmentType(env_type))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Count running
    running_result = await db.execute(
        select(func.count(PersistentEnvironment.id)).where(
            PersistentEnvironment.status == EnvironmentStatus.RUNNING
        )
    )
    running_count = running_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(PersistentEnvironment.last_activity.desc().nullslast()).offset(offset).limit(page_size)

    result = await db.execute(query)
    environments = result.scalars().all()

    items = []
    for env in environments:
        items.append(AdminEnvironmentResponse(
            id=env.id,
            user_id=env.user_id,
            env_type=env.env_type,
            status=env.status,
            container_id=env.container_id,
            volume_name=env.volume_name,
            ssh_port=env.ssh_port,
            vnc_port=env.vnc_port,
            novnc_port=env.novnc_port,
            access_url=env.access_url,
            vnc_password=None,  # Don't expose password in admin list
            last_started=env.last_started,
            last_stopped=env.last_stopped,
            last_activity=env.last_activity,
            error_message=env.error_message,
            total_usage_minutes=env.total_usage_minutes,
            monthly_usage_minutes=env.monthly_usage_minutes,
            usage_reset_date=env.usage_reset_date,
            memory_mb=env.memory_mb,
            cpu_cores=env.cpu_cores,
            created_at=env.created_at,
            updated_at=env.updated_at,
            user_email=env.user.email if env.user else None,
            user_username=env.user.username if env.user else None,
            organization_name=None,  # Would need to join
        ))

    return AdminEnvironmentListResponse(
        items=items,
        total=total,
        running_count=running_count,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/{env_id}/stop")
async def admin_stop_environment(
    env_id: UUID,
    request: AdminStopEnvironmentRequest,
    current_user: User = Depends(require_permission(Permission.ENV_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Force stop an environment."""
    environment = await db.get(PersistentEnvironment, env_id)

    if not environment:
        raise HTTPException(status_code=404, detail="Environment not found")

    if environment.status not in (EnvironmentStatus.RUNNING, EnvironmentStatus.ERROR, EnvironmentStatus.STARTING):
        raise HTTPException(status_code=400, detail="Environment is not running")

    # TODO: Force stop container
    # await force_stop_container(environment)

    # End active session
    session_result = await db.execute(
        select(EnvironmentSession).where(
            EnvironmentSession.environment_id == environment.id,
            EnvironmentSession.ended_at.is_(None)
        )
    )
    active_session = session_result.scalar_one_or_none()
    if active_session:
        active_session.end_session(reason=f"admin_stopped: {request.reason}")

    environment.mark_stopped()
    await db.commit()

    logger.info("Environment force stopped by admin",
                env_id=str(env_id),
                admin_id=str(current_user.id),
                reason=request.reason)

    return {"message": "Environment stopped", "env_id": str(env_id)}
