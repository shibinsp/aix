import asyncio
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID
import structlog
import json

from app.core.config import settings

logger = structlog.get_logger()

# Alphha Linux Docker image presets
# Custom images (built from our Dockerfiles) and fallback public images
ALPHHA_LINUX_IMAGES = {
    # Terminal presets
    "minimal": {
        "custom": "alphha-linux:minimal",
        "public": "alpine:latest",
    },
    "server": {
        "custom": "alphha-linux:server",
        "public": "alpine:latest",
    },
    "developer": {
        "custom": "alphha-linux:developer",
        "public": "python:3.11-slim",
    },
    "pentest": {
        "custom": "alphha-linux:pentest",
        "public": "kalilinux/kali-rolling",
    },
    # Desktop presets with VNC
    "desktop": {
        "custom": "alphha-linux:desktop",
        "public": "consol/ubuntu-xfce-vnc:latest",
    },
    "desktop-kali": {
        "custom": "alphha-linux:desktop-kali",
        "public": "kasmweb/kali-rolling-desktop:1.14.0",
    },
}


def utcnow():
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


def get_preset_images(preset: str) -> dict:
    """Get image configuration for a preset."""
    return ALPHHA_LINUX_IMAGES.get(preset, ALPHHA_LINUX_IMAGES["minimal"])


class LabManager:
    """Manage cybersecurity lab environments using Docker."""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._docker_available: Optional[bool] = None

    async def _run_docker_command(self, *args) -> tuple[str, str, int]:
        """Run a docker command asynchronously."""
        cmd = ["docker"] + list(args)
        logger.debug(f"Running docker command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            return stdout.decode(), stderr.decode(), process.returncode
        except FileNotFoundError:
            logger.error("Docker CLI not found")
            return "", "Docker CLI not found", 1
        except Exception as e:
            logger.error(f"Error running docker command: {e}")
            return "", str(e), 1

    async def check_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        if self._docker_available is not None:
            return self._docker_available

        try:
            stdout, stderr, returncode = await self._run_docker_command("--version")
            if returncode == 0:
                logger.info(f"Docker available: {stdout.strip()}")
                self._docker_available = True
                return True
            logger.warning(f"Docker check failed: {stderr}")
            self._docker_available = False
            return False
        except Exception as e:
            logger.error(f"Docker not available: {e}")
            self._docker_available = False
            return False

    # Alias for backward compatibility
    async def check_podman_available(self) -> bool:
        """Alias for check_docker_available for backward compatibility."""
        return await self.check_docker_available()

    async def create_lab_network(self, session_id: str) -> Optional[str]:
        """Create an isolated network for the lab session."""
        network_name = f"{settings.LAB_NETWORK_PREFIX}{session_id[:8]}"

        # Check if network already exists
        stdout, stderr, returncode = await self._run_docker_command(
            "network", "ls", "--filter", f"name={network_name}", "--format", "{{.Name}}"
        )

        if returncode == 0 and network_name in stdout:
            logger.info(f"Lab network already exists: {network_name}")
            return network_name

        stdout, stderr, returncode = await self._run_docker_command(
            "network", "create",
            "--driver", "bridge",
            network_name,
        )

        if returncode == 0:
            logger.info(f"Created lab network: {network_name}")
            return network_name
        else:
            logger.error(f"Failed to create network: {stderr}")
            return None

    async def start_lab_session(
        self,
        session_id: str,
        user_id: str,
        infrastructure_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Start a new lab session with the specified infrastructure."""

        result = {
            "session_id": session_id,
            "status": "provisioning",
            "containers": [],
            "network": None,
            "access_info": {},
            "error": None,
        }

        # Check if Docker is available
        if not await self.check_docker_available():
            logger.warning("Docker not available, running in simulation mode")
            return await self._start_simulated_session(session_id, user_id, infrastructure_spec)

        try:
            # Create isolated network
            network_name = await self.create_lab_network(session_id)
            if not network_name:
                result["status"] = "failed"
                result["error"] = "Failed to create lab network"
                return result

            result["network"] = network_name

            # Start containers
            containers = infrastructure_spec.get("containers", [])
            container_ids = []

            for container_spec in containers:
                container_result = await self._start_container(
                    session_id=session_id,
                    container_spec=container_spec,
                    network_name=network_name,
                )

                if container_result.get("error"):
                    result["status"] = "failed"
                    result["error"] = container_result["error"]
                    # Cleanup on failure
                    await self.stop_lab_session(session_id)
                    return result

                container_ids.append(container_result)
                result["containers"].append(container_result)

            # Store session info
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "network": network_name,
                "containers": container_ids,
                "started_at": utcnow(),
                "expires_at": utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
            }

            # Generate access information
            result["status"] = "running"
            result["access_info"] = await self._generate_access_info(result["containers"])
            result["expires_at"] = self.active_sessions[session_id]["expires_at"].isoformat()

            logger.info(f"Lab session started: {session_id}", containers=len(container_ids))

        except Exception as e:
            logger.error(f"Failed to start lab session: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
            await self.stop_lab_session(session_id)

        return result

    async def _start_simulated_session(
        self,
        session_id: str,
        user_id: str,
        infrastructure_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Start a simulated lab session when Docker is not available."""
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "network": f"mock_network_{session_id[:8]}",
            "containers": [],
            "started_at": utcnow(),
            "expires_at": utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
            "simulated": True,
        }

        logger.info(f"Mock lab session started: {session_id}")

        return {
            "session_id": session_id,
            "status": "running",
            "containers": [{"name": "mock_target", "status": "simulated"}],
            "network": self.active_sessions[session_id]["network"],
            "access_info": {"note": "Lab running in simulation mode - Docker not available"},
            "expires_at": self.active_sessions[session_id]["expires_at"].isoformat(),
        }

    async def _start_container(
        self,
        session_id: str,
        container_spec: Dict[str, Any],
        network_name: str,
    ) -> Dict[str, Any]:
        """Start a single container for the lab."""

        container_name = f"cyberx_{session_id[:8]}_{container_spec['name']}"
        image = container_spec.get("image", "alpine:latest")
        ports = container_spec.get("ports", [])
        env_vars = container_spec.get("environment", {})
        resources = container_spec.get("resources", {})

        # Build command
        cmd_args = [
            "run", "-d",
            "--name", container_name,
            "--network", network_name,
            "--hostname", container_spec["name"],
        ]

        # Add resource limits
        if resources.get("memory"):
            cmd_args.extend(["--memory", resources["memory"]])
        if resources.get("cpu"):
            cmd_args.extend(["--cpus", str(resources["cpu"])])

        # Add port mappings (only for exposed services)
        for port in ports:
            cmd_args.extend(["-p", port])

        # Add environment variables
        for key, value in env_vars.items():
            cmd_args.extend(["-e", f"{key}={value}"])

        # Add labels for management
        cmd_args.extend([
            "--label", f"cyberx.session={session_id}",
            "--label", f"cyberx.role={container_spec['name']}",
        ])

        # Add the image
        cmd_args.append(image)

        # Add command - use specified command or default to keep container running
        # Desktop images (consol/ubuntu-xfce-vnc, kasmweb/*) have their own entrypoint
        is_desktop_image = any(x in image for x in ["vnc", "kasm", "desktop"])

        if container_spec.get("command"):
            cmd_args.extend(container_spec["command"])
        elif not is_desktop_image:
            # Default command to keep container running for terminal access
            # Only for non-desktop images that don't have their own entrypoint
            cmd_args.extend(["/bin/sh", "-c", "while true; do sleep 3600; done"])

        stdout, stderr, returncode = await self._run_docker_command(*cmd_args)

        if returncode == 0:
            container_id = stdout.strip()
            return {
                "id": container_id,
                "name": container_name,
                "role": container_spec["name"],
                "image": image,
                "ports": ports,
                "status": "running",
            }
        else:
            logger.error(f"Failed to start container: {stderr}")
            return {
                "error": f"Failed to start container {container_spec['name']}: {stderr}",
            }

    async def _generate_access_info(self, containers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate access information for the lab session."""
        access_info = {}

        for container in containers:
            if container.get("ports"):
                # Get the mapped ports
                stdout, stderr, returncode = await self._run_docker_command(
                    "port", container["name"],
                )

                if returncode == 0 and stdout:
                    ports_map = {}
                    for line in stdout.strip().split("\n"):
                        if "->" in line:
                            parts = line.split("->")
                            container_port = parts[0].strip()
                            host_binding = parts[1].strip()
                            ports_map[container_port] = host_binding

                    access_info[container["role"]] = {
                        "container_name": container["name"],
                        "ports": ports_map,
                    }

        return access_info

    async def stop_lab_session(self, session_id: str) -> bool:
        """Stop and cleanup a lab session."""
        try:
            session = self.active_sessions.get(session_id)

            # Check if this was a simulated session
            if session and session.get("simulated"):
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                logger.info(f"Mock lab session stopped: {session_id}")
                return True

            # Stop and remove containers with the session label
            stdout, stderr, returncode = await self._run_docker_command(
                "ps", "-a", "-q",
                "--filter", f"label=cyberx.session={session_id}",
            )

            if stdout:
                container_ids = stdout.strip().split("\n")
                for container_id in container_ids:
                    if container_id:
                        await self._run_docker_command("stop", "-t", "5", container_id)
                        await self._run_docker_command("rm", "-f", container_id)

            # Remove the network
            if session and session.get("network"):
                await self._run_docker_command("network", "rm", "-f", session["network"])

            # Clean up session tracking
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            logger.info(f"Lab session stopped: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping lab session: {e}")
            return False

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a lab session."""
        session = self.active_sessions.get(session_id)

        if not session:
            return {"status": "not_found", "session_id": session_id}

        # Check if this was a simulated session
        if session.get("simulated"):
            is_expired = utcnow() > session["expires_at"]
            return {
                "session_id": session_id,
                "status": "expired" if is_expired else "running",
                "started_at": session["started_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
                "network": session["network"],
                "containers": [{"name": "mock_target", "status": "simulated"}],
            }

        # Check container status
        stdout, stderr, returncode = await self._run_docker_command(
            "ps", "-a",
            "--filter", f"label=cyberx.session={session_id}",
            "--format", "{{json .}}",
        )

        containers = []
        if returncode == 0 and stdout:
            try:
                for line in stdout.strip().split("\n"):
                    if line:
                        c = json.loads(line)
                        containers.append({
                            "name": c.get("Names", "unknown"),
                            "status": c.get("State", "unknown"),
                            "image": c.get("Image", "unknown"),
                        })
            except json.JSONDecodeError:
                pass

        # Check if session is expired
        is_expired = utcnow() > session["expires_at"]

        return {
            "session_id": session_id,
            "status": "expired" if is_expired else "running",
            "started_at": session["started_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat(),
            "network": session["network"],
            "containers": containers,
        }

    async def execute_in_container(
        self,
        session_id: str,
        container_role: str,
        command: List[str],
    ) -> Dict[str, Any]:
        """Execute a command in a lab container."""
        session = self.active_sessions.get(session_id)

        if not session:
            return {"error": "Session not found", "output": ""}

        # Check if this was a simulated session
        if session.get("simulated"):
            return {
                "output": f"[Simulation] Command executed: {' '.join(command)}",
                "error": "",
                "exit_code": 0,
            }

        # Find container by role
        container_name = None
        for container in session.get("containers", []):
            if container.get("role") == container_role:
                container_name = container["name"]
                break

        if not container_name:
            return {"error": f"Container with role '{container_role}' not found", "output": ""}

        # Execute command
        stdout, stderr, returncode = await self._run_docker_command(
            "exec", container_name, *command
        )

        return {
            "output": stdout,
            "error": stderr if returncode != 0 else "",
            "exit_code": returncode,
        }

    async def check_flag(
        self,
        session_id: str,
        submitted_flag: str,
        correct_flag: str,
    ) -> bool:
        """Check if a submitted flag is correct."""
        # Simple comparison - could be enhanced with hash comparison
        return submitted_flag.strip() == correct_flag.strip()

    async def cleanup_expired_sessions(self) -> int:
        """Cleanup all expired lab sessions."""
        cleaned = 0
        now = utcnow()

        expired_sessions = [
            sid for sid, session in self.active_sessions.items()
            if now > session["expires_at"]
        ]

        for session_id in expired_sessions:
            if await self.stop_lab_session(session_id):
                cleaned += 1

        if cleaned:
            logger.info(f"Cleaned up {cleaned} expired lab sessions")

        return cleaned

    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active lab sessions."""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "user_id": session["user_id"],
                "started_at": session["started_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
                "container_count": len(session.get("containers", [])),
                "simulated": session.get("simulated", False),
            })
        return sessions

    async def _get_available_image(self, preset: str) -> str:
        """Get the best available image for a preset (custom or public fallback)."""
        preset_config = get_preset_images(preset)

        # Try custom image first
        custom_image = preset_config.get("custom", "")
        if custom_image:
            stdout, stderr, returncode = await self._run_docker_command(
                "images", "-q", custom_image
            )
            if returncode == 0 and stdout.strip():
                logger.info(f"Using custom image: {custom_image}")
                return custom_image

        # Fall back to public image
        public_image = preset_config.get("public", "alpine:latest")
        logger.info(f"Using public image: {public_image}")
        return public_image

    async def start_alphha_linux_lab(
        self,
        session_id: str,
        user_id: str,
        preset: str = "minimal",
        lab_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start an Alphha Linux lab environment.

        Args:
            session_id: Unique session identifier
            user_id: User ID
            preset: Alphha Linux preset (minimal, server, developer, pentest, desktop, desktop-kali)
            lab_config: Optional configuration overrides

        Returns:
            Lab session information
        """
        config = lab_config or {}

        # Get the best available image for the preset
        image = await self._get_available_image(preset)

        # Check if it's a desktop preset (needs VNC)
        is_desktop = preset.startswith("desktop")

        # Generate dynamic ports to avoid conflicts
        import random
        base_port = random.randint(10000, 60000)
        ssh_port = base_port
        vnc_port = base_port + 1
        novnc_port = base_port + 2

        # Build ports list based on preset type
        if is_desktop:
            # Desktop images typically expose VNC on 5901 and noVNC on 6901
            ports = [
                f"{novnc_port}:6901",  # noVNC web access
                f"{vnc_port}:5901",     # VNC port
            ]
            environment = {
                "LAB_SESSION_ID": session_id,
                "LAB_PRESET": preset,
                "VNC_PW": "toor",
                "VNC_RESOLUTION": "1280x720",
            }
            memory = config.get("memory", "2g")
            cpu = config.get("cpu", 2)
            # Desktop containers have their own entrypoint, no need for keep-alive command
            command = None
        else:
            ports = [f"{ssh_port}:22"]
            environment = {
                "LAB_SESSION_ID": session_id,
                "LAB_PRESET": preset,
            }
            memory = config.get("memory", "512m")
            cpu = config.get("cpu", 1)
            command = config.get("command")

        # Build infrastructure spec
        infrastructure_spec = {
            "type": "alphha-linux",
            "preset": preset,
            "is_desktop": is_desktop,
            "containers": [
                {
                    "name": "target",
                    "image": image,
                    "ports": ports,
                    "environment": environment,
                    "resources": {
                        "memory": memory,
                        "cpu": cpu,
                    },
                    "command": command,
                }
            ],
        }

        # Add additional containers if specified
        if config.get("additional_containers"):
            infrastructure_spec["containers"].extend(config["additional_containers"])

        result = await self.start_lab_session(session_id, user_id, infrastructure_spec)

        # Add VNC URL for desktop presets
        if is_desktop and result.get("status") == "running":
            result["vnc_url"] = f"http://{settings.SERVER_HOST}:{novnc_port}"
            result["vnc_port"] = vnc_port
            result["novnc_port"] = novnc_port

        result["ssh_port"] = ssh_port
        result["preset"] = preset

        return result

    async def get_alphha_linux_presets(self) -> List[Dict[str, Any]]:
        """Get available Alphha Linux presets."""
        return [
            # Terminal presets
            {
                "name": "minimal",
                "images": ALPHHA_LINUX_IMAGES["minimal"],
                "description": "Lightweight CLI environment (~400MB)",
                "ram_required": "128MB",
                "type": "terminal",
                "features": ["SSH", "curl", "wget", "htop"],
            },
            {
                "name": "server",
                "images": ALPHHA_LINUX_IMAGES["server"],
                "description": "Server administration tools (~600MB)",
                "ram_required": "256MB",
                "type": "terminal",
                "features": ["SSH", "tmux", "git", "nmap", "tcpdump", "iptables"],
            },
            {
                "name": "developer",
                "images": ALPHHA_LINUX_IMAGES["developer"],
                "description": "Development environment (~1.5GB)",
                "ram_required": "512MB",
                "type": "terminal",
                "features": ["Python3", "GCC", "GDB", "Docker", "pwntools"],
            },
            # Desktop presets
            {
                "name": "desktop",
                "images": ALPHHA_LINUX_IMAGES["desktop"],
                "description": "Ubuntu XFCE Desktop with browser and tools (~2GB)",
                "ram_required": "2GB",
                "type": "desktop",
                "features": ["VNC Desktop", "Firefox", "Terminal", "File Manager"],
            },
            {
                "name": "desktop-kali",
                "images": ALPHHA_LINUX_IMAGES["desktop-kali"],
                "description": "Kali Linux Desktop with security tools (~3GB)",
                "ram_required": "2GB",
                "type": "desktop",
                "features": ["VNC Desktop", "nmap", "Metasploit", "Burp Suite", "Wireshark"],
            },
        ]

    async def build_alphha_linux_images(self) -> Dict[str, Any]:
        """Build Alphha Linux Docker images from Dockerfiles."""
        result = {
            "status": "building",
            "images": [],
            "errors": [],
        }

        build_context = f"{settings.LAB_TEMPLATE_PATH}/docker"

        for preset, image_config in ALPHHA_LINUX_IMAGES.items():
            dockerfile = f"Dockerfile.{preset}"
            custom_image = image_config.get("custom", f"alphha-linux:{preset}")
            logger.info(f"Building {custom_image} from {dockerfile}")

            stdout, stderr, returncode = await self._run_docker_command(
                "build",
                "-t", custom_image,
                "-f", f"{build_context}/{dockerfile}",
                build_context,
            )

            if returncode == 0:
                result["images"].append({
                    "preset": preset,
                    "image": custom_image,
                    "status": "built",
                })
                logger.info(f"Built {custom_image}")
            else:
                result["errors"].append({
                    "preset": preset,
                    "error": stderr[:500],
                })
                logger.error(f"Failed to build {custom_image}: {stderr[:200]}")

        result["status"] = "completed" if not result["errors"] else "partial"
        return result

    async def check_alphha_linux_images(self) -> Dict[str, Any]:
        """Check which Alphha Linux images are available."""
        available = {}

        for preset, image_config in ALPHHA_LINUX_IMAGES.items():
            custom_image = image_config.get("custom", "")
            public_image = image_config.get("public", "")

            # Check custom image
            custom_available = False
            if custom_image:
                stdout, stderr, returncode = await self._run_docker_command(
                    "images", "-q", custom_image
                )
                custom_available = bool(stdout.strip())

            # Check public image
            public_available = False
            if public_image:
                stdout, stderr, returncode = await self._run_docker_command(
                    "images", "-q", public_image
                )
                public_available = bool(stdout.strip())

            available[preset] = {
                "custom": {"image": custom_image, "available": custom_available},
                "public": {"image": public_image, "available": public_available},
                "any_available": custom_available or public_available,
            }

        return available


# Singleton instance
lab_manager = LabManager()
