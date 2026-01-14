from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import re

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
    """List labs created by the current user."""
    query = select(Lab).where(Lab.created_by == user_id)

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
    """Start a new lab session."""
    # Check if user can start a new lab session
    can_start, reason = await limit_enforcer.check_can_start_lab(UUID(user_id), db)
    if not can_start:
        raise HTTPException(status_code=403, detail=reason)

    # Check lab exists
    result = await db.execute(select(Lab).where(Lab.id == lab_id))
    lab = result.scalar_one_or_none()

    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # Check for existing active session
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

    # Create session record
    session = LabSession(
        user_id=user_id,
        lab_id=lab_id,
        status=LabStatus.PROVISIONING,
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Start lab infrastructure
    lab_result = await lab_manager.start_lab_session(
        session_id=str(session.id),
        user_id=user_id,
        infrastructure_spec=lab.infrastructure_spec,
    )

    # Update session with results
    if lab_result["status"] == "running":
        session.status = LabStatus.RUNNING
        session.container_ids = [c["id"] for c in lab_result.get("containers", [])]
        session.network_id = lab_result.get("network")
        # Generate proper access URL from infrastructure spec
        access_urls = []
        for container in lab.infrastructure_spec.get("containers", []):
            ports = container.get("ports", [])
            for port in ports:
                # Parse port mapping like "80:80" or "8080:80"
                if ":" in port:
                    host_port = port.split(":")[0]
                    access_urls.append(f"http://{settings.SERVER_HOST}:{host_port}")
        session.access_url = access_urls[0] if access_urls else None
        # Record lab started for limit tracking
        await limit_enforcer.record_lab_started(UUID(user_id), db)
    else:
        session.status = LabStatus.FAILED

    await db.commit()
    await db.refresh(session)

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
    """Stop a lab session."""
    result = await db.execute(
        select(LabSession).where(
            LabSession.id == session_id,
            LabSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Stop infrastructure
    await lab_manager.stop_lab_session(str(session_id))

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
            session_dict['vnc_password'] = 'toor'
            # Extract port from URL (e.g., http://ip:port -> port)
            port_match = re.search(r':(\d+)$', s.access_url)
            if port_match:
                session_dict['novnc_port'] = int(port_match.group(1))
        
        response_sessions.append(LabSessionResponse(**session_dict))
    
    return response_sessions

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
            session_dict['vnc_password'] = 'toor'
            # Extract port from URL (e.g., http://ip:port -> port)
            port_match = re.search(r':(\d+)$', s.access_url)
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
        response["vnc_password"] = "toor"

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
