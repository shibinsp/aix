"""
Lab-Course Integration Service

Handles the connection between courses/lessons and lab environments,
including workspace setup and progress tracking.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.course import Course, Lesson
from app.models.lab import Lab, LabSession, LabStatus
from app.models.environment import PersistentEnvironment, EnvironmentType, EnvironmentStatus, EnvironmentSession
from app.models.user import User
from app.services.environments import persistent_env_manager
from app.core.config import settings

logger = structlog.get_logger()


class LabCourseIntegrationService:
    """
    Service for integrating labs with courses.

    Handles:
    - Starting labs within course context
    - Setting up workspace directories
    - Tracking lab progress per course
    - Managing lab sessions linked to lessons
    """

    def __init__(self):
        self.workspace_base = settings.WORKSPACE_BASE

    async def start_lab_in_course(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str,
        lab_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Start a lab session within a course context.

        This will:
        1. Get the lab configuration (terminal vs desktop)
        2. Start/get the user's persistent environment
        3. Create a lab session linked to the persistent env
        4. Setup workspace at /home/alphha/courses/{course_id}/
        5. Return connection info
        """

        # Get the lab
        lab = await db.get(Lab, lab_id)
        if not lab:
            raise ValueError(f"Lab {lab_id} not found")

        # Get the course
        course = await db.get(Course, course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")

        # Get the lesson
        lesson = await db.get(Lesson, lesson_id)
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")

        # Determine environment type from lab
        env_type = self._get_env_type_for_lab(lab)

        # Check if Docker is available
        docker_available = await persistent_env_manager.check_docker_available()

        if docker_available:
            # Start or get the persistent environment
            connection_info = await persistent_env_manager.start_environment(
                user_id,
                env_type,
                db
            )
        else:
            # Simulation mode - get or create environment record
            connection_info = await self._get_simulation_environment(
                user_id, env_type, db
            )

        # Create or update lab session
        lab_session = await self._create_lab_session(
            user_id=user_id,
            lab_id=lab_id,
            course_id=course_id,
            lesson_id=lesson_id,
            db=db
        )

        # Get workspace path for this course
        workspace_path = self._get_workspace_path(course_id)

        # Setup workspace if Docker is available
        if docker_available and connection_info.get("container_id"):
            await self._setup_workspace(
                container_id=connection_info["container_id"],
                workspace_path=workspace_path,
                lab=lab
            )

        return {
            "lab_session_id": str(lab_session.id),
            "environment": connection_info,
            "workspace_path": workspace_path,
            "lab": {
                "id": str(lab.id),
                "title": lab.title,
                "description": lab.description,
                "difficulty": lab.difficulty,
                "objectives": lab.objectives or [],
                "instructions": lab.instructions,
                "hints": lab.hints or [],
                "estimated_time": lab.estimated_time,
            },
            "course": {
                "id": str(course.id),
                "title": course.title,
            },
            "lesson": {
                "id": str(lesson.id),
                "title": lesson.title,
            },
        }

    def _get_env_type_for_lab(self, lab: Lab) -> str:
        """Determine which environment type to use for a lab."""
        # Check if lab requires desktop (GUI-based)
        if lab.lab_type and "desktop" in lab.lab_type.lower():
            return "desktop"
        if lab.lab_type and "gui" in lab.lab_type.lower():
            return "desktop"

        # Default to terminal for most labs
        return "terminal"

    def _get_workspace_path(self, course_id: str) -> str:
        """Get the workspace path for a course."""
        return f"{self.workspace_base}/{course_id}"

    async def _get_simulation_environment(
        self,
        user_id: str,
        env_type: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get environment info in simulation mode."""
        env_type_enum = EnvironmentType.TERMINAL if env_type == "terminal" else EnvironmentType.DESKTOP

        result = await db.execute(
            select(PersistentEnvironment).where(
                PersistentEnvironment.user_id == user_id,
                PersistentEnvironment.env_type == env_type_enum
            )
        )
        env = result.scalar_one_or_none()

        if env:
            return {
                "id": str(env.id),
                "env_type": env.env_type.value,
                "status": env.status.value,
                "access_url": env.access_url,
                "ssh_port": env.ssh_port,
                "vnc_port": env.vnc_port,
            }

        # Create new environment record
        shared_volume = PersistentEnvironment.get_shared_volume_name(user_id)
        resources = PersistentEnvironment.get_default_resources(env_type_enum)

        env = PersistentEnvironment(
            user_id=user_id,
            env_type=env_type_enum,
            volume_name=shared_volume,
            status=EnvironmentStatus.STOPPED,
            memory_mb=resources["memory_mb"],
            cpu_cores=resources["cpu_cores"],
        )
        db.add(env)
        await db.commit()
        await db.refresh(env)

        return {
            "id": str(env.id),
            "env_type": env.env_type.value,
            "status": env.status.value,
            "access_url": None,
            "ssh_port": None,
            "vnc_port": None,
            "message": "Environment created but not started. Docker not available.",
        }

    async def _create_lab_session(
        self,
        user_id: str,
        lab_id: str,
        course_id: str,
        lesson_id: str,
        db: AsyncSession
    ) -> LabSession:
        """Create or get active lab session."""
        # Check for existing active session
        result = await db.execute(
            select(LabSession).where(
                LabSession.user_id == user_id,
                LabSession.lab_id == lab_id,
                LabSession.status == LabStatus.RUNNING
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update session with course context
            existing.course_id = course_id
            existing.lesson_id = lesson_id
            existing.last_activity = datetime.utcnow()
            await db.commit()
            return existing

        # Create new session
        session = LabSession(
            id=uuid4(),
            user_id=user_id,
            lab_id=lab_id,
            course_id=course_id,
            lesson_id=lesson_id,
            status=LabStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session

    async def _setup_workspace(
        self,
        container_id: str,
        workspace_path: str,
        lab: Lab
    ) -> None:
        """Setup workspace directory in the container."""
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_id)

            # Create workspace directory
            container.exec_run(f"mkdir -p {workspace_path}")

            # Create lab-specific directory
            lab_path = f"{workspace_path}/{lab.id}"
            container.exec_run(f"mkdir -p {lab_path}")

            # If lab has starter files, copy them
            starter_files = getattr(lab, 'starter_files', None)
            if starter_files:
                for filename, content in starter_files.items():
                    file_path = f"{lab_path}/{filename}"
                    # Use echo to write file content
                    container.exec_run(f"bash -c 'cat > {file_path} << EOF\n{content}\nEOF'")

            # Create a README with lab instructions
            if lab.instructions:
                readme_content = f"# {lab.title}\n\n{lab.instructions}"
                container.exec_run(f"bash -c 'cat > {lab_path}/README.md << EOF\n{readme_content}\nEOF'")

            # Set proper permissions
            container.exec_run(f"chown -R alphha:alphha {workspace_path}")

            logger.info(f"Workspace setup complete at {lab_path}")

        except Exception as e:
            logger.error(f"Failed to setup workspace: {e}")
            # Don't raise - lab can still work without workspace setup

    async def complete_lab_objective(
        self,
        user_id: str,
        lab_session_id: str,
        objective_index: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Mark a lab objective as completed."""
        session = await db.get(LabSession, lab_session_id)
        if not session:
            raise ValueError("Lab session not found")

        if str(session.user_id) != user_id:
            raise ValueError("Unauthorized")

        # Update completed objectives
        completed = session.completed_objectives or []
        if objective_index not in completed:
            completed.append(objective_index)
            session.completed_objectives = completed
            session.last_activity = datetime.utcnow()
            await db.commit()

        # Check if all objectives completed
        lab = await db.get(Lab, session.lab_id)
        total_objectives = len(lab.objectives or [])
        all_completed = len(completed) >= total_objectives

        if all_completed and session.status != LabStatus.COMPLETED:
            session.status = LabStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            await db.commit()

        return {
            "completed_objectives": completed,
            "total_objectives": total_objectives,
            "all_completed": all_completed,
        }

    async def get_lab_progress(
        self,
        user_id: str,
        course_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get lab progress for a user in a course."""
        # Get all labs in the course through lessons
        result = await db.execute(
            select(LabSession).where(
                LabSession.user_id == user_id,
                LabSession.course_id == course_id
            )
        )
        sessions = result.scalars().all()

        completed_labs = []
        in_progress_labs = []

        for session in sessions:
            lab_info = {
                "lab_id": str(session.lab_id),
                "session_id": str(session.id),
                "status": session.status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "completed_objectives": session.completed_objectives or [],
            }

            if session.status == "completed":
                completed_labs.append(lab_info)
            else:
                in_progress_labs.append(lab_info)

        return {
            "course_id": course_id,
            "user_id": user_id,
            "completed_labs": completed_labs,
            "in_progress_labs": in_progress_labs,
            "total_completed": len(completed_labs),
        }

    async def end_lab_session(
        self,
        user_id: str,
        lab_session_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """End a lab session."""
        session = await db.get(LabSession, lab_session_id)
        if not session:
            raise ValueError("Lab session not found")

        if str(session.user_id) != user_id:
            raise ValueError("Unauthorized")

        if session.status == LabStatus.RUNNING:
            session.status = LabStatus.TERMINATED
            session.ended_at = datetime.utcnow()

            # Calculate duration
            if session.started_at:
                duration = (datetime.utcnow() - session.started_at).total_seconds() / 60
                session.duration_minutes = int(duration)

            await db.commit()

        return {
            "session_id": str(session.id),
            "status": session.status,
            "duration_minutes": session.duration_minutes,
        }


# Global instance
lab_course_integration = LabCourseIntegrationService()
