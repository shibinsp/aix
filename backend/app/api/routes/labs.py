from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import re
import os

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.dependencies import get_current_admin
from app.core.sanitization import validate_pagination
from app.core.config import settings
from app.models.user import User
from app.models.lab import Lab, LabSession, LabStatus, LabEnvironmentType
from app.schemas.lab import (
    LabCreate,
    LabResponse,
    LabSessionCreate,
    LabSessionResponse,
    FlagSubmission,
)
from app.services.labs.lab_manager import lab_manager, ALPHHA_LINUX_IMAGES
from app.services.labs.vm_manager import vm_manager
from app.services.labs.lab_course_integration import lab_course_integration
from app.services.ai import teaching_engine
from app.services.limits import limit_enforcer
import json
from pathlib import Path

router = APIRouter()


def is_running_in_kubernetes() -> bool:
    """Check if we're running inside a Kubernetes cluster."""
    return (
        settings.K8S_IN_CLUSTER or
        os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
    )


# Path to Alphha Linux lab templates
ALPHHA_LABS_PATH = Path("/app/data/lab_templates/alphha_labs.json")


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


@router.get("", response_model=List[LabResponse])
async def list_labs(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    lab_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
):
    """List all published labs."""
    query = select(Lab).where(Lab.is_published == True)

    if lab_type:
        query = query.where(Lab.lab_type == lab_type)
    if difficulty:
        query = query.where(Lab.difficulty == difficulty)
    if category:
        query = query.where(Lab.category == category)

    skip, limit = validate_pagination(skip, limit, max_limit=50)
    query = query.order_by(Lab.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    labs = result.scalars().all()

    return [LabResponse.model_validate(lab) for lab in labs]


@router.get("/{lab_id}", response_model=LabResponse)
async def get_lab(
    lab_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get lab details."""
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    return LabResponse.model_validate(lab)


@router.post("", response_model=LabResponse, status_code=status.HTTP_201_CREATED)
async def create_lab(
    lab_data: LabCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new lab (admin only)."""
    # Generate slug
    base_slug = slugify(lab_data.title)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Lab).where(Lab.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    lab = Lab(
        title=lab_data.title,
        slug=slug,
        description=lab_data.description,
        lab_type=lab_data.lab_type,
        difficulty=lab_data.difficulty,
        estimated_time=lab_data.estimated_time,
        points=lab_data.points,
        infrastructure_spec=lab_data.infrastructure_spec,
        flags=lab_data.flags,
        objectives=lab_data.objectives,
        instructions=lab_data.instructions,
        hints=lab_data.hints,
        category=lab_data.category,
        tags=lab_data.tags,
        created_by=admin.id,
    )

    db.add(lab)
    await db.commit()
    await db.refresh(lab)

    return LabResponse.model_validate(lab)


@router.post("/generate", response_model=LabResponse)
async def generate_lab(
    topic: str = Query(..., description="Topic for the lab"),
    lab_type: str = Query("challenge", description="Lab type"),
    difficulty: str = Query("intermediate", description="Lab difficulty"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a lab scenario using AI."""
    lab_content = await teaching_engine.generate_lab_scenario(
        topic=topic,
        lab_type=lab_type,
        difficulty=difficulty,
    )

    if "error" in lab_content:
        raise HTTPException(status_code=500, detail=lab_content["error"])

    # Generate slug
    base_slug = slugify(lab_content.get("title", topic))
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Lab).where(Lab.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    lab = Lab(
        title=lab_content.get("title", topic),
        slug=slug,
        description=lab_content.get("description", ""),
        lab_type=lab_type,
        difficulty=difficulty,
        estimated_time=lab_content.get("estimated_time", 45),
        infrastructure_spec=lab_content.get("infrastructure_spec", {}),
        flags=lab_content.get("flags", []),
        objectives=lab_content.get("objectives", []),
        instructions=lab_content.get("instructions", ""),
        is_ai_generated=True,
        is_published=False,
        created_by=user_id,
    )

    db.add(lab)
    await db.commit()
    await db.refresh(lab)

    return LabResponse.model_validate(lab)


# Lab Sessions

@router.post("/{lab_id}/sessions", response_model=LabSessionResponse)
async def start_lab_session(
    lab_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new lab session using the user's persistent desktop environment.

    Labs no longer create ephemeral containers - they use the user's existing
    desktop environment from "My Environment". This provides a consistent
    workspace where users can work on multiple labs without losing their setup.
    """
    # Check if user can start a new lab session
    can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
    if not can_start:
        raise HTTPException(status_code=403, detail=reason)

    # Check lab exists
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Check for existing active session for this lab
    existing = await db.execute(
        select(LabSession).where(
            LabSession.user_id == user_id,
            LabSession.lab_id == lab_id,
            LabSession.status.in_([LabStatus.RUNNING, LabStatus.PROVISIONING]),
        )
    )
    existing_session = existing.scalar_one_or_none()

    if existing_session:
        return LabSessionResponse.model_validate(existing_session)

    # Start user's persistent desktop environment
    # Route to appropriate backend based on environment (K8s, Docker, or simulation)
    try:
        if is_running_in_kubernetes():
            # Use Kubernetes-based environment manager
            from app.services.environments.k8s_env_manager import k8s_env_manager
            connection_info = await k8s_env_manager.start_environment(
                str(user_id), "desktop", db
            )
        else:
            # Use Docker-based environment manager
            from app.services.environments import persistent_env_manager
            docker_available = await persistent_env_manager.check_docker_available()

            if docker_available:
                connection_info = await persistent_env_manager.start_environment(
                    str(user_id), "desktop", db
                )
            else:
                # Simulation mode - return mock connection info for development
                connection_info = {
                    "access_url": f"http://localhost:6080",
                    "vnc_port": 5900,
                    "novnc_port": 6080,
                    "vnc_password": "cyberaix",
                    "status": "simulation"
                }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start desktop environment: {str(e)}"
        )

    # Create session record for tracking lab progress
    session = LabSession(
        user_id=user_id,
        lab_id=lab_id,
        status=LabStatus.RUNNING,
        preset="desktop",  # Mark as using desktop environment
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
        access_url=connection_info.get("access_url"),
        container_ids=[],  # No dedicated lab containers
        network_id=None,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Record lab started for limit tracking
    await limit_enforcer.record_lab_started(UUID(user_id), db)

    return LabSessionResponse.model_validate(session)


@router.get("/{lab_id}/sessions/active", response_model=Optional[LabSessionResponse])
async def get_active_session(
    lab_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get user's active session for a lab."""
    result = await db.execute(
        select(LabSession).where(
            LabSession.user_id == user_id,
            LabSession.lab_id == lab_id,
            LabSession.status == LabStatus.RUNNING,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        return None

    return LabSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/flags")
async def submit_flag(
    session_id: UUID,
    submission: FlagSubmission,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit a flag for the lab session."""
    # Get session
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != LabStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Session is not active")

    # Get lab to check flags
    lab_result = await db.execute(select(Lab).where(Lab.id == session.lab_id))
    lab = lab_result.scalar_one_or_none()

    # Check flag
    for flag in lab.flags:
        if flag.get("value") == submission.flag:
            # Correct flag
            if flag["name"] not in session.flags_captured:
                session.flags_captured = session.flags_captured + [flag["name"]]
                session.score += flag.get("points", 10)
                session.attempts += 1

                await db.commit()

                return {
                    "correct": True,
                    "flag_name": flag["name"],
                    "points": flag.get("points", 10),
                    "message": "Correct! Flag captured.",
                }
            else:
                return {
                    "correct": True,
                    "flag_name": flag["name"],
                    "points": 0,
                    "message": "Flag already captured.",
                }

    # Wrong flag
    session.attempts += 1
    await db.commit()

    return {
        "correct": False,
        "message": "Incorrect flag. Try again!",
    }


@router.post("/sessions/{session_id}/stop")
async def stop_lab_session(
    session_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Stop a lab session.

    This marks the lab session as ended but does NOT stop the user's
    desktop environment - they can continue using it for other labs or work.
    """
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Note: We do NOT stop the desktop environment here.
    # The user's persistent desktop continues running so they can
    # work on other labs or continue their work.

    # Update session status
    session.status = LabStatus.TERMINATED
    session.completed_at = datetime.utcnow()

    # Record lab stopped for limit tracking
    await limit_enforcer.record_lab_stopped(UUID(user_id), db)

    await db.commit()

    return {"message": "Lab session stopped"}


@router.get("/sessions/my", response_model=List[LabSessionResponse])
async def list_my_sessions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """List user's lab sessions."""
    result = await db.execute(
        select(LabSession)
        .where(LabSession.user_id == user_id)
        .order_by(LabSession.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()

    # Convert to response models and add VNC info for desktop sessions
    response_sessions = []
    for s in sessions:
        session_dict = {
            'id': s.id,
            'user_id': s.user_id,
            'lab_id': s.lab_id,
            'status': s.status.value if hasattr(s.status, 'value') else s.status,
            'started_at': s.started_at,
            'completed_at': s.completed_at,
            'expires_at': s.expires_at,
            'access_url': s.access_url,
            'flags_captured': s.flags_captured or [],
            'objectives_completed': s.objectives_completed or [],
            'score': s.score or 0,
            'attempts': s.attempts or 0,
            'created_at': s.created_at,
            'preset': s.preset,
        }
        
        # Add VNC fields for desktop sessions
        if s.preset == 'desktop' and s.access_url:
            session_dict['vnc_url'] = s.access_url
            # VNC password should be stored in session or retrieved from active session
            # For now, we indicate it's not available in the list view for security
            session_dict['vnc_password'] = '[see active session]'
            # Extract port from URL (e.g., http://ip:port -> port)
            access_url_str = str(s.access_url) if s.access_url else ''
            port_match = re.search(r':(\d+)$', access_url_str)
            if port_match:
                session_dict['novnc_port'] = int(port_match.group(1))
        
        response_sessions.append(LabSessionResponse(**session_dict))
    
    return response_sessions


# ============================================================
# Alphha Linux Lab Endpoints
# ============================================================

@router.get("/alphha/presets")
async def get_alphha_presets():
    """Get available Alphha Linux presets."""
    return await lab_manager.get_alphha_linux_presets()


@router.get("/alphha/images")
async def check_alphha_images():
    """Check which Alphha Linux Docker images are available."""
    return await lab_manager.check_alphha_linux_images()


@router.post("/alphha/build")
async def build_alphha_images(
    admin: User = Depends(get_current_admin),
):
    """Build Alphha Linux Docker images (admin only)."""
    return await lab_manager.build_alphha_linux_images()


@router.get("/alphha/templates")
async def get_alphha_lab_templates():
    """Get pre-built Alphha Linux lab templates."""
    if not ALPHHA_LABS_PATH.exists():
        return {"labs": [], "presets": {}}

    with open(ALPHHA_LABS_PATH, 'r') as f:
        return json.load(f)


@router.post("/alphha/start")
async def start_alphha_lab(
    preset: str = Query("minimal", description="Alphha Linux preset"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Start an Alphha Linux lab session."""
    import uuid

    # Check if user can start a new lab session
    can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
    if not can_start:
        raise HTTPException(status_code=403, detail=reason)

    # Create session record
    session = LabSession(
        user_id=user_id,
        lab_id=None,  # No specific lab, just the environment
        environment_type=LabEnvironmentType.DOCKER,
        preset=preset,
        status=LabStatus.PROVISIONING,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Start Alphha Linux lab
    lab_result = await lab_manager.start_alphha_linux_lab(
        session_id=str(session.id),
        user_id=user_id,
        preset=preset,
    )

    # Update session with results
    ssh_port = lab_result.get("ssh_port", 2222)
    vnc_url = lab_result.get("vnc_url")
    novnc_port = lab_result.get("novnc_port")

    if lab_result["status"] == "running":
        session.status = LabStatus.RUNNING
        session.container_ids = [c.get("id", "") for c in lab_result.get("containers", [])]
        session.network_id = lab_result.get("network")
        # Generate access URL based on preset type
        if preset.startswith("desktop"):
            session.access_url = vnc_url
        else:
            session.access_url = f"ssh://{settings.SERVER_HOST}:{ssh_port}"
        # Record lab started for limit tracking
        await limit_enforcer.record_lab_started(UUID(user_id), db)
    else:
        session.status = LabStatus.FAILED

    await db.commit()
    await db.refresh(session)

    # Get VNC password from lab result (dynamically generated)
    vnc_password = lab_result.get("vnc_password", "")
    
    response = {
        "session_id": str(session.id),
        "status": session.status.value,
        "preset": preset,
        "ssh_port": ssh_port,
        "access_info": lab_result.get("access_info", {}),
        "expires_at": session.expires_at.isoformat(),
        "credentials": {
            "username": "alphha",
            "password": "alphha",
        },
    }

    # Add VNC info for desktop presets
    if preset.startswith("desktop") and vnc_url:
        response["vnc_url"] = vnc_url
        response["novnc_port"] = novnc_port
        response["vnc_password"] = vnc_password

    return response


@router.post("/alphha/template/{template_id}/start")
async def start_alphha_template_lab(
    template_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Start a lab from an Alphha Linux template."""
    # Check if user can start a new lab session
    can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
    if not can_start:
        raise HTTPException(status_code=403, detail=reason)

    # Load templates
    if not ALPHHA_LABS_PATH.exists():
        raise HTTPException(status_code=404, detail="Lab templates not found")

    with open(ALPHHA_LABS_PATH, 'r') as f:
        templates = json.load(f)

    # Find template
    template = None
    for lab in templates.get("labs", []):
        if lab["id"] == template_id:
            template = lab
            break

    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    # Create session record
    session = LabSession(
        user_id=user_id,
        lab_id=None,
        status=LabStatus.PROVISIONING,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=template.get("duration_minutes", 60)),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Start lab with template's infrastructure spec
    lab_result = await lab_manager.start_lab_session(
        session_id=str(session.id),
        user_id=user_id,
        infrastructure_spec=template["infrastructure_spec"],
    )

    # Update session
    if lab_result["status"] == "running":
        session.status = LabStatus.RUNNING
        session.container_ids = [c.get("id", "") for c in lab_result.get("containers", [])]
        session.network_id = lab_result.get("network")
        # Record lab started for limit tracking
        await limit_enforcer.record_lab_started(UUID(user_id), db)
    else:
        session.status = LabStatus.FAILED

    await db.commit()
    await db.refresh(session)

    return {
        "session_id": str(session.id),
        "status": session.status.value,
        "template": template_id,
        "title": template["title"],
        "description": template["description"],
        "objectives": template.get("objectives", []),
        "flags": [{"id": f["id"], "description": f["description"], "points": f["points"]}
                  for f in template.get("flags", [])],
        "access_info": lab_result.get("access_info", {}),
        "expires_at": session.expires_at.isoformat(),
        "credentials": {
            "username": "alphha",
            "password": "alphha",
        },
    }


# ============================================================
# VM-based Lab Endpoints (QEMU/KVM)
# ============================================================

@router.get("/vm/status")
async def get_vm_status():
    """Check VM system availability."""
    qemu_available = await vm_manager.check_qemu_available()
    kvm_available = await vm_manager.check_kvm_available()
    libvirt_available = await vm_manager.check_libvirt_available()

    return {
        "qemu_available": qemu_available,
        "kvm_available": kvm_available,
        "libvirt_available": libvirt_available,
        "recommended_mode": "kvm" if kvm_available else ("qemu" if qemu_available else "docker"),
    }


@router.get("/vm/templates")
async def get_vm_templates():
    """Get available VM templates."""
    return await vm_manager.list_available_templates()


@router.post("/vm/start")
async def start_vm_lab(
    template: str = Query("alphha-linux", description="VM template name"),
    memory: str = Query("512M", description="Memory allocation"),
    cpus: int = Query(1, description="Number of CPUs"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Start a VM-based lab session."""
    import uuid

    # Check if user can start a new lab session
    can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
    if not can_start:
        raise HTTPException(status_code=403, detail=reason)

    session_id = str(uuid.uuid4())

    vm_result = await vm_manager.start_vm(
        session_id=session_id,
        user_id=user_id,
        vm_spec={
            "template": template,
            "memory": memory,
            "cpus": cpus,
        },
    )

    if vm_result["status"] == "failed":
        raise HTTPException(status_code=500, detail=vm_result.get("error", "Failed to start VM"))

    return vm_result


@router.post("/vm/{session_id}/stop")
async def stop_vm_lab(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Stop a VM-based lab session."""
    # Verify the VM belongs to the user
    vm_status = await vm_manager.get_vm_status(session_id)
    if vm_status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="VM session not found")
    
    if vm_status.get("user_id") and vm_status.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="You can only stop your own VM sessions")

    success = await vm_manager.stop_vm(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="VM session not found")

    return {"message": "VM stopped successfully"}


@router.get("/vm/{session_id}/status")
async def get_vm_session_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get status of a VM session."""
    return await vm_manager.get_vm_status(session_id)


@router.get("/vm/active")
async def list_active_vms(
    admin: User = Depends(get_current_admin),
):
    """List all active VM sessions (admin only)."""
    return await vm_manager.list_active_vms()


# ============================================================
# Lab-Course Integration Endpoints
# ============================================================

from pydantic import BaseModel

class StartLabInCourseRequest(BaseModel):
    course_id: str
    lesson_id: str
    lab_id: str


@router.post("/start-in-course")
async def start_lab_in_course(
    request: StartLabInCourseRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a lab session within a course context.

    This starts the user's persistent environment (terminal or desktop),
    creates a lab session linked to the course/lesson, and sets up
    the workspace at /home/alphha/courses/{course_id}/.
    """
    try:
        # Check if user can start a new lab session
        can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
        if not can_start:
            raise HTTPException(status_code=403, detail=reason)

        result = await lab_course_integration.start_lab_in_course(
            user_id=user_id,
            course_id=request.course_id,
            lesson_id=request.lesson_id,
            lab_id=request.lab_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/objectives/{objective_index}/complete")
async def complete_lab_objective(
    session_id: str,
    objective_index: int,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a lab objective as completed.

    Returns the updated list of completed objectives and whether
    all objectives have been completed.
    """
    try:
        result = await lab_course_integration.complete_lab_objective(
            user_id=user_id,
            lab_session_id=session_id,
            objective_index=objective_index,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/progress/{course_id}")
async def get_lab_progress(
    course_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get lab progress for a user in a course.

    Returns completed labs, in-progress labs, and overall progress.
    """
    result = await lab_course_integration.get_lab_progress(
        user_id=user_id,
        course_id=course_id,
        db=db,
    )
    return result


@router.post("/sessions/{session_id}/end")
async def end_lab_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    End a lab session.

    This marks the session as ended but does NOT stop the persistent
    environment - the user can continue using their environment for
    other labs or work.
    """
    try:
        result = await lab_course_integration.end_lab_session(
            user_id=user_id,
            lab_session_id=session_id,
            db=db,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{session_id}/mark-complete")
async def mark_lab_complete(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually mark a lab session as complete.

    This allows users to mark a lab as completed even if not all
    objectives were auto-detected. Updates user stats and progress.
    """
    # Get the session
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Lab session not found")

    if session.status == LabStatus.COMPLETED:
        return {"message": "Lab already marked as complete", "status": "completed"}

    # Mark session as completed
    session.status = LabStatus.COMPLETED
    session.completed_at = datetime.utcnow()

    # Mark all objectives as completed if not already
    total_objectives = 0
    if session.lab_id:
        lab_result = await db.execute(select(Lab).where(Lab.id == session.lab_id))
        lab = lab_result.scalar_one_or_none()
        if lab and lab.objectives:
            total_objectives = len(lab.objectives)
            session.completed_objectives = list(range(total_objectives))

    await db.commit()

    # Update user stats
    user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = user_result.scalar_one_or_none()
    if user:
        user.total_labs_completed = (user.total_labs_completed or 0) + 1
        await db.commit()

    # Record lab completion for limit tracking
    await limit_enforcer.record_lab_stopped(UUID(user_id), db)

    return {
        "message": "Lab marked as complete",
        "status": "completed",
        "completed_objectives": session.completed_objectives,
        "total_objectives": total_objectives,
    }


@router.post("/sessions/{session_id}/check-objectives")
async def check_objectives(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Check which objectives have been completed via auto-detection.

    This endpoint analyzes the command history logged during the lab session
    and checks if any objectives match their verification patterns.

    Objectives can define verification criteria in their configuration:
    - command_pattern: Single regex pattern that must match a logged command
    - command_patterns: List of patterns that must all match
    - any_command_pattern: List of patterns where at least one must match

    Returns:
        completed_objectives: List of objective indices that are complete
        total: Total number of objectives
        all_completed: Whether all objectives are complete
    """
    from app.services.labs.objective_verifier import objective_verifier

    # Get the session
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Lab session not found")

    # Get the lab for objectives configuration
    if not session.lab_id:
        return {
            "completed_objectives": list(session.completed_objectives or []),
            "total": 0,
            "all_completed": True,
        }

    lab_result = await db.execute(select(Lab).where(Lab.id == session.lab_id))
    lab = lab_result.scalar_one_or_none()

    if not lab or not lab.objectives:
        return {
            "completed_objectives": list(session.completed_objectives or []),
            "total": 0,
            "all_completed": True,
        }

    # Start with already completed objectives
    completed = set(session.completed_objectives or [])
    total_objectives = len(lab.objectives)

    # Check each objective
    for i, objective in enumerate(lab.objectives):
        if i in completed:
            continue

        # Objectives can be either strings (simple) or dicts (with verification config)
        if isinstance(objective, dict) and "verification" in objective:
            verification_config = objective["verification"]
            is_complete = await objective_verifier.verify_objective(
                session_id,
                verification_config,
            )
            if is_complete:
                completed.add(i)
        elif isinstance(objective, dict) and "command_pattern" in objective:
            # Shorthand: verification config at objective level
            is_complete = await objective_verifier.verify_objective(
                session_id,
                objective,
            )
            if is_complete:
                completed.add(i)

    # Update session if new completions found
    completed_list = sorted(list(completed))
    if completed_list != sorted(list(session.completed_objectives or [])):
        session.completed_objectives = completed_list
        await db.commit()

    return {
        "completed_objectives": completed_list,
        "total": total_objectives,
        "all_completed": len(completed_list) >= total_objectives,
        "newly_completed": [i for i in completed_list if i not in (session.completed_objectives or [])],
    }


@router.get("/sessions/{session_id}/command-history")
async def get_command_history(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the command history for a lab session.

    This is useful for debugging auto-detection and reviewing
    what commands a user has executed during a lab.

    Returns:
        commands: List of command entries with timestamps
        total: Total number of commands logged
    """
    from app.services.labs.objective_verifier import objective_verifier

    # Verify session belongs to user
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Lab session not found")

    # Get command history
    history = objective_verifier.get_command_history(session_id)

    return {
        "session_id": session_id,
        "commands": history,
        "total": len(history),
    }
