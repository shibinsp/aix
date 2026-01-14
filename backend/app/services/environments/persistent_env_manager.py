"""
Persistent Environment Manager Service

Manages Docker-based persistent terminal and desktop environments for users.
Terminal and Desktop share the same Docker volume mounted at /home/alphha.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from uuid import uuid4

import docker
from docker.errors import NotFound, APIError
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.environment import PersistentEnvironment, EnvironmentType, EnvironmentStatus, EnvironmentSession
from app.core.config import settings

logger = structlog.get_logger()

# Environment type
EnvType = Literal["terminal", "desktop"]

# Docker image configurations
DOCKER_IMAGES = {
    "terminal": "cyberaix/terminal:latest",  # Alpine/Ubuntu with SSH
    "desktop": "cyberaix/desktop:latest",    # noVNC + XFCE desktop
}

# Fallback images if custom images not available
FALLBACK_IMAGES = {
    "terminal": "linuxserver/openssh-server:latest",
    "desktop": "linuxserver/webtop:alpine-xfce",
}

# Port ranges for allocation
PORT_RANGES = {
    "terminal_ssh": (10000, 10999),
    "desktop_vnc": (11000, 11999),
    "desktop_web": (12000, 12999),
}


class PersistentEnvironmentManager:
    """
    Manages persistent Docker environments for users.

    Key features:
    - Shared volume between terminal and desktop (/home/alphha)
    - Automatic port allocation
    - Usage tracking
    - Container lifecycle management
    """

    def __init__(self):
        self.docker_client: Optional[docker.DockerClient] = None
        self.allocated_ports: Dict[str, int] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Docker client connection."""
        if self._initialized:
            return True

        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self._initialized = True
            logger.info("Docker client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.docker_client = None
            return False

    async def check_docker_available(self) -> bool:
        """Check if Docker is available."""
        if not self.docker_client:
            return await self.initialize()
        try:
            self.docker_client.ping()
            return True
        except Exception:
            return False

    def _get_volume_name(self, user_id: str) -> str:
        """Get the shared volume name for a user."""
        return f"cyberaix_user_{user_id}_data"

    def _get_container_name(self, user_id: str, env_type: EnvType) -> str:
        """Get container name for user's environment."""
        return f"cyberaix_{env_type}_{user_id}"

    async def _ensure_volume_exists(self, volume_name: str) -> bool:
        """Ensure the Docker volume exists, create if not."""
        if not self.docker_client:
            return False

        try:
            self.docker_client.volumes.get(volume_name)
            logger.debug(f"Volume {volume_name} already exists")
            return True
        except NotFound:
            try:
                self.docker_client.volumes.create(
                    name=volume_name,
                    driver="local",
                    labels={"managed_by": "cyberaix"}
                )
                logger.info(f"Created volume {volume_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create volume {volume_name}: {e}")
                return False

    def _allocate_port(self, port_type: str) -> int:
        """Allocate an available port from the specified range."""
        start, end = PORT_RANGES.get(port_type, (20000, 20999))

        # Get list of used ports
        used_ports = set(self.allocated_ports.values())

        # Try to find an available port
        for _ in range(100):  # Max 100 attempts
            port = random.randint(start, end)
            if port not in used_ports:
                return port

        # Fallback: sequential search
        for port in range(start, end + 1):
            if port not in used_ports:
                return port

        raise RuntimeError(f"No available ports in range {start}-{end}")

    async def get_or_create_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> PersistentEnvironment:
        """Get existing environment or create a new one."""

        # Convert string to enum
        env_type_enum = EnvironmentType.TERMINAL if env_type == "terminal" else EnvironmentType.DESKTOP

        # Check for existing environment
        result = await db.execute(
            select(PersistentEnvironment).where(
                PersistentEnvironment.user_id == user_id,
                PersistentEnvironment.env_type == env_type_enum
            )
        )
        env = result.scalar_one_or_none()

        if env:
            return env

        # Create new environment record
        volume_name = PersistentEnvironment.get_shared_volume_name(user_id)
        resources = PersistentEnvironment.get_default_resources(env_type_enum)

        env = PersistentEnvironment(
            user_id=user_id,
            env_type=env_type_enum,
            volume_name=volume_name,
            status=EnvironmentStatus.STOPPED,
            total_usage_minutes=0,
            monthly_usage_minutes=0,
            memory_mb=resources["memory_mb"],
            cpu_cores=resources["cpu_cores"],
        )

        db.add(env)
        await db.commit()
        await db.refresh(env)

        logger.info(f"Created environment record for user {user_id}, type {env_type}")
        return env

    async def start_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Start a persistent environment for the user.

        Returns connection info (URL, ports, credentials).
        """
        if not await self.check_docker_available():
            raise RuntimeError("Docker is not available")

        # Get or create environment record
        env = await self.get_or_create_environment(user_id, env_type, db)

        # Check if already running
        if env.status == EnvironmentStatus.RUNNING and env.container_id:
            try:
                container = self.docker_client.containers.get(env.container_id)
                if container.status == "running":
                    return self._get_connection_info(env)
            except NotFound:
                pass  # Container no longer exists, will recreate

        # Update status to starting
        env.status = EnvironmentStatus.STARTING
        await db.commit()

        try:
            # Ensure shared volume exists
            volume_name = env.volume_name
            if not await self._ensure_volume_exists(volume_name):
                raise RuntimeError("Failed to create storage volume")

            # Start the appropriate container
            if env_type == "terminal":
                container_info = await self._start_terminal_container(str(user_id), volume_name)
            else:
                container_info = await self._start_desktop_container(str(user_id), volume_name)

            # Update environment record using model method
            env.mark_started(container_id=container_info["container_id"])
            env.ssh_port = container_info.get("ssh_port")
            env.vnc_port = container_info.get("vnc_port")
            env.novnc_port = container_info.get("web_port")
            env.access_url = container_info.get("access_url")

            # Create session record
            session = EnvironmentSession(
                environment_id=env.id,
                user_id=user_id,
            )
            db.add(session)

            await db.commit()
            await db.refresh(env)

            logger.info(f"Started {env_type} environment for user {user_id}")
            return self._get_connection_info(env)

        except Exception as e:
            env.mark_error(str(e))
            await db.commit()
            logger.error(f"Failed to start environment: {e}")
            raise

    async def _start_terminal_container(
        self,
        user_id: str,
        volume_name: str
    ) -> Dict[str, Any]:
        """Start a terminal container with SSH access."""

        container_name = self._get_container_name(user_id, "terminal")
        ssh_port = self._allocate_port("terminal_ssh")

        # Remove existing container if any
        try:
            old_container = self.docker_client.containers.get(container_name)
            old_container.remove(force=True)
        except NotFound:
            pass

        # Try custom image first, fall back to linuxserver image
        image = DOCKER_IMAGES["terminal"]
        try:
            self.docker_client.images.get(image)
        except NotFound:
            image = FALLBACK_IMAGES["terminal"]
            try:
                self.docker_client.images.pull(image)
            except Exception as e:
                logger.warning(f"Failed to pull {image}: {e}")

        # Environment variables for the container
        environment = {
            "PUID": "1000",
            "PGID": "1000",
            "TZ": "UTC",
            "SUDO_ACCESS": "true",
            "PASSWORD_ACCESS": "true",
            "USER_PASSWORD": "cyberaix",  # Default password
            "USER_NAME": "alphha",
        }

        # Create and start container
        container = self.docker_client.containers.run(
            image,
            name=container_name,
            detach=True,
            ports={"2222/tcp": ssh_port},
            volumes={volume_name: {"bind": "/home/alphha", "mode": "rw"}},
            environment=environment,
            labels={
                "managed_by": "cyberaix",
                "user_id": user_id,
                "env_type": "terminal",
            },
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 50% CPU
            restart_policy={"Name": "unless-stopped"},
        )

        self.allocated_ports[f"terminal_{user_id}"] = ssh_port

        # Get host IP (for local development, use localhost)
        host = getattr(settings, "ENVIRONMENT_HOST", "localhost")

        return {
            "container_id": container.id,
            "ssh_port": ssh_port,
            "access_url": f"ssh://alphha@{host}:{ssh_port}",
        }

    async def _start_desktop_container(
        self,
        user_id: str,
        volume_name: str
    ) -> Dict[str, Any]:
        """Start a desktop container with VNC/noVNC access."""

        container_name = self._get_container_name(user_id, "desktop")
        vnc_port = self._allocate_port("desktop_vnc")
        web_port = self._allocate_port("desktop_web")

        # Remove existing container if any
        try:
            old_container = self.docker_client.containers.get(container_name)
            old_container.remove(force=True)
        except NotFound:
            pass

        # Try custom image first, fall back to linuxserver webtop
        image = DOCKER_IMAGES["desktop"]
        try:
            self.docker_client.images.get(image)
        except NotFound:
            image = FALLBACK_IMAGES["desktop"]
            try:
                self.docker_client.images.pull(image)
            except Exception as e:
                logger.warning(f"Failed to pull {image}: {e}")

        # Environment variables
        environment = {
            "PUID": "1000",
            "PGID": "1000",
            "TZ": "UTC",
            "SUBFOLDER": "/",
            "TITLE": "CyberAIx Desktop",
        }

        # Create and start container
        container = self.docker_client.containers.run(
            image,
            name=container_name,
            detach=True,
            ports={
                "3000/tcp": web_port,   # noVNC web interface
                "3001/tcp": vnc_port,   # VNC port
            },
            volumes={volume_name: {"bind": "/home/alphha", "mode": "rw"}},
            environment=environment,
            labels={
                "managed_by": "cyberaix",
                "user_id": user_id,
                "env_type": "desktop",
            },
            mem_limit="2g",
            cpu_period=100000,
            cpu_quota=100000,  # 100% of 1 CPU
            shm_size="512m",  # Shared memory for desktop
            restart_policy={"Name": "unless-stopped"},
        )

        self.allocated_ports[f"desktop_vnc_{user_id}"] = vnc_port
        self.allocated_ports[f"desktop_web_{user_id}"] = web_port

        # Get host IP
        host = getattr(settings, "ENVIRONMENT_HOST", "localhost")

        return {
            "container_id": container.id,
            "vnc_port": vnc_port,
            "web_port": web_port,
            "access_url": f"http://{host}:{web_port}",
        }

    async def stop_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> bool:
        """Stop a user's environment."""

        # Convert string to enum
        env_type_enum = EnvironmentType.TERMINAL if env_type == "terminal" else EnvironmentType.DESKTOP

        # Get environment record
        result = await db.execute(
            select(PersistentEnvironment).where(
                PersistentEnvironment.user_id == user_id,
                PersistentEnvironment.env_type == env_type_enum
            )
        )
        env = result.scalar_one_or_none()

        if not env:
            return False

        # End any active session
        session_result = await db.execute(
            select(EnvironmentSession).where(
                EnvironmentSession.environment_id == env.id,
                EnvironmentSession.ended_at.is_(None)
            )
        )
        active_session = session_result.scalar_one_or_none()
        if active_session:
            active_session.end_session("user_stopped")

        # Stop and remove container
        if env.container_id and self.docker_client:
            try:
                container = self.docker_client.containers.get(env.container_id)
                container.stop(timeout=10)
                container.remove()
                logger.info(f"Stopped container {env.container_id}")
            except NotFound:
                pass
            except Exception as e:
                logger.error(f"Error stopping container: {e}")

        # Update environment record using model method
        env.mark_stopped()

        # Clean up allocated ports
        user_id_str = str(user_id)
        self.allocated_ports.pop(f"terminal_{user_id_str}", None)
        self.allocated_ports.pop(f"desktop_vnc_{user_id_str}", None)
        self.allocated_ports.pop(f"desktop_web_{user_id_str}", None)

        await db.commit()

        logger.info(f"Stopped {env_type} environment for user {user_id}")
        return True

    async def reset_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> bool:
        """
        Reset environment by deleting volume and recreating.
        This deletes all user data in the environment.
        """

        # First stop the environment
        await self.stop_environment(user_id, env_type, db)

        # Also stop the other environment type since they share the volume
        other_type: EnvType = "desktop" if env_type == "terminal" else "terminal"
        await self.stop_environment(user_id, other_type, db)

        # Delete the shared volume
        volume_name = self._get_volume_name(user_id)
        if self.docker_client:
            try:
                volume = self.docker_client.volumes.get(volume_name)
                volume.remove()
                logger.info(f"Deleted volume {volume_name}")
            except NotFound:
                pass
            except Exception as e:
                logger.error(f"Error deleting volume: {e}")

        return True

    async def get_environment_status(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get current status of an environment."""

        # Convert string to enum
        env_type_enum = EnvironmentType.TERMINAL if env_type == "terminal" else EnvironmentType.DESKTOP

        result = await db.execute(
            select(PersistentEnvironment).where(
                PersistentEnvironment.user_id == user_id,
                PersistentEnvironment.env_type == env_type_enum
            )
        )
        env = result.scalar_one_or_none()

        if not env:
            return {
                "status": "not_created",
                "env_type": env_type,
            }

        # Verify container is actually running
        actual_status = env.status
        if env.status == EnvironmentStatus.RUNNING and env.container_id and self.docker_client:
            try:
                container = self.docker_client.containers.get(env.container_id)
                if container.status != "running":
                    actual_status = EnvironmentStatus.STOPPED
                    env.status = EnvironmentStatus.STOPPED
                    await db.commit()
            except NotFound:
                actual_status = EnvironmentStatus.STOPPED
                env.status = EnvironmentStatus.STOPPED
                env.container_id = None
                await db.commit()

        is_running = actual_status == EnvironmentStatus.RUNNING

        return {
            "id": str(env.id),
            "env_type": env.env_type.value,
            "status": actual_status.value,
            "access_url": env.access_url if is_running else None,
            "ssh_port": env.ssh_port if is_running else None,
            "vnc_port": env.vnc_port if is_running else None,
            "novnc_port": env.novnc_port if is_running else None,
            "total_usage_minutes": env.total_usage_minutes,
            "monthly_usage_minutes": env.monthly_usage_minutes,
            "last_started_at": env.last_started.isoformat() if env.last_started else None,
        }

    def _get_connection_info(self, env: PersistentEnvironment) -> Dict[str, Any]:
        """Get connection info for a running environment."""
        return {
            "id": str(env.id),
            "env_type": env.env_type.value,
            "status": env.status.value,
            "access_url": env.access_url,
            "ssh_port": env.ssh_port,
            "vnc_port": env.vnc_port,
            "novnc_port": env.novnc_port,
            "container_id": env.container_id,
            "volume_name": env.volume_name,
        }

    async def get_all_user_environments(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get both terminal and desktop environments for a user."""

        terminal = await self.get_environment_status(user_id, "terminal", db)
        desktop = await self.get_environment_status(user_id, "desktop", db)

        return {
            "terminal": terminal,
            "desktop": desktop,
            "volume_name": PersistentEnvironment.get_shared_volume_name(str(user_id)),
        }

    async def track_usage(
        self,
        user_id: str,
        env_type: EnvType,
        minutes: int,
        db: AsyncSession
    ) -> None:
        """Track usage time for an environment."""

        await db.execute(
            update(PersistentEnvironment)
            .where(
                PersistentEnvironment.user_id == user_id,
                PersistentEnvironment.env_type == env_type
            )
            .values(
                total_usage_minutes=PersistentEnvironment.total_usage_minutes + minutes,
                monthly_usage_minutes=PersistentEnvironment.monthly_usage_minutes + minutes,
            )
        )
        await db.commit()

    async def reset_monthly_usage(self, db: AsyncSession) -> int:
        """Reset monthly usage for all environments. Call at start of each month."""

        result = await db.execute(
            update(PersistentEnvironment)
            .values(monthly_usage_minutes=0)
        )
        await db.commit()

        return result.rowcount

    async def cleanup_inactive_environments(
        self,
        inactive_hours: int = 24,
        db: AsyncSession = None
    ) -> int:
        """Stop environments that have been running for too long."""

        if not self.docker_client:
            return 0

        cleaned = 0
        cutoff = datetime.utcnow() - timedelta(hours=inactive_hours)

        try:
            containers = self.docker_client.containers.list(
                filters={"label": "managed_by=cyberaix"}
            )

            for container in containers:
                # Check if container has been running too long
                # This is a simplified check - in production you'd check the DB
                labels = container.labels
                if container.status == "running":
                    # Get container start time
                    started_at = container.attrs.get("State", {}).get("StartedAt")
                    if started_at:
                        # Parse ISO format time
                        start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                        if start_time.replace(tzinfo=None) < cutoff:
                            container.stop(timeout=10)
                            container.remove()
                            cleaned += 1
                            logger.info(f"Cleaned up inactive container {container.id}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        return cleaned


# Global instance
persistent_env_manager = PersistentEnvironmentManager()
