"""
Kubernetes Lab Manager for AI CyberX.

This module manages lab environments as Kubernetes pods instead of Docker containers.
It uses the Kubernetes Python client to create, manage, and delete lab pods.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID
import structlog

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from app.core.config import settings

logger = structlog.get_logger()


def utcnow():
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


# Lab image presets for Kubernetes pods
K8S_LAB_IMAGES = {
    "minimal": {
        "image": "alpine:latest",
        "command": ["/bin/sh", "-c", "apk add --no-cache bash curl wget htop && while true; do sleep 3600; done"],
        "resources": {"cpu": "100m", "memory": "128Mi", "cpu_limit": "500m", "memory_limit": "512Mi"},
    },
    "server": {
        "image": "alpine:latest",
        "command": ["/bin/sh", "-c", "apk add --no-cache bash curl wget htop nmap tcpdump git tmux && while true; do sleep 3600; done"],
        "resources": {"cpu": "200m", "memory": "256Mi", "cpu_limit": "1", "memory_limit": "1Gi"},
    },
    "developer": {
        "image": "python:3.11-slim",
        "command": ["/bin/sh", "-c", "apt-get update && apt-get install -y --no-install-recommends curl wget git && while true; do sleep 3600; done"],
        "resources": {"cpu": "250m", "memory": "512Mi", "cpu_limit": "2", "memory_limit": "2Gi"},
    },
    "pentest": {
        "image": "kalilinux/kali-rolling",
        "command": ["/bin/bash", "-c", "while true; do sleep 3600; done"],
        "resources": {"cpu": "500m", "memory": "1Gi", "cpu_limit": "2", "memory_limit": "4Gi"},
    },
    "desktop": {
        "image": "consol/ubuntu-xfce-vnc:latest",
        "command": None,  # Use default entrypoint
        "resources": {"cpu": "500m", "memory": "1Gi", "cpu_limit": "2", "memory_limit": "2Gi"},
        "ports": [{"name": "vnc", "port": 5901}, {"name": "novnc", "port": 6901}],
    },
    "desktop-kali": {
        "image": "kasmweb/kali-rolling-desktop:1.14.0",
        "command": None,
        "resources": {"cpu": "500m", "memory": "2Gi", "cpu_limit": "4", "memory_limit": "4Gi"},
        "ports": [{"name": "vnc", "port": 5901}, {"name": "novnc", "port": 6901}],
    },
}


class K8sLabManager:
    """Manage cybersecurity lab environments using Kubernetes pods."""

    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self._k8s_available: Optional[bool] = None
        self._core_api: Optional[client.CoreV1Api] = None
        self._initialized = False

    async def _init_k8s_client(self):
        """Initialize the Kubernetes client."""
        if self._initialized:
            return

        try:
            if settings.K8S_IN_CLUSTER:
                # Running inside a Kubernetes cluster
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            else:
                # Running outside cluster (development)
                config.load_kube_config()
                logger.info("Loaded kubeconfig from default location")

            self._core_api = client.CoreV1Api()
            self._k8s_available = True
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            self._k8s_available = False
            self._initialized = True

    async def check_k8s_available(self) -> bool:
        """Check if Kubernetes API is available."""
        await self._init_k8s_client()
        return self._k8s_available or False

    def _get_pod_name(self, session_id: str, role: str = "target") -> str:
        """Generate pod name from session ID."""
        return f"lab-{session_id[:8]}-{role}"

    def _get_service_name(self, session_id: str) -> str:
        """Generate service name from session ID."""
        return f"lab-{session_id[:8]}-svc"

    async def start_lab_session(
        self,
        session_id: str,
        user_id: str,
        preset: str = "minimal",
        lab_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Start a new lab session by creating a Kubernetes pod."""
        await self._init_k8s_client()

        result = {
            "session_id": session_id,
            "status": "provisioning",
            "pods": [],
            "access_info": {},
            "error": None,
        }

        if not self._k8s_available:
            logger.warning("Kubernetes not available, returning error")
            result["status"] = "failed"
            result["error"] = "Kubernetes API not available"
            return result

        try:
            preset_config = K8S_LAB_IMAGES.get(preset, K8S_LAB_IMAGES["minimal"])
            config_override = lab_config or {}

            pod_name = self._get_pod_name(session_id)
            namespace = settings.K8S_LAB_NAMESPACE

            # Build pod spec
            pod = self._build_pod_spec(
                pod_name=pod_name,
                session_id=session_id,
                user_id=user_id,
                preset=preset,
                preset_config=preset_config,
                config_override=config_override,
            )

            # Create the pod
            logger.info(f"Creating lab pod: {pod_name} in namespace {namespace}")
            created_pod = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._core_api.create_namespaced_pod(namespace=namespace, body=pod)
            )

            # Wait for pod to be ready
            pod_ready = await self._wait_for_pod_ready(pod_name, namespace)

            if not pod_ready:
                result["status"] = "failed"
                result["error"] = "Pod failed to become ready"
                await self.stop_lab_session(session_id)
                return result

            # Create service for desktop presets
            if preset.startswith("desktop"):
                svc = await self._create_lab_service(session_id, preset_config)
                if svc:
                    result["access_info"]["vnc_service"] = svc

            # Store session info
            expires_at = utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES)
            self.active_sessions[session_id] = {
                "user_id": user_id,
                "pod_name": pod_name,
                "preset": preset,
                "namespace": namespace,
                "started_at": utcnow(),
                "expires_at": expires_at,
            }

            result["status"] = "running"
            result["pods"].append({
                "name": pod_name,
                "role": "target",
                "status": "running",
                "image": preset_config["image"],
            })
            result["expires_at"] = expires_at.isoformat()
            result["preset"] = preset

            logger.info(f"Lab session started: {session_id}", pod=pod_name)

        except ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            result["status"] = "failed"
            result["error"] = f"Kubernetes API error: {e.reason}"
        except Exception as e:
            logger.error(f"Failed to start lab session: {e}")
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def _build_pod_spec(
        self,
        pod_name: str,
        session_id: str,
        user_id: str,
        preset: str,
        preset_config: Dict[str, Any],
        config_override: Dict[str, Any],
    ) -> client.V1Pod:
        """Build Kubernetes pod specification."""

        resources = preset_config["resources"]
        image = config_override.get("image", preset_config["image"])
        command = preset_config.get("command")

        # Resource requirements
        resource_requirements = client.V1ResourceRequirements(
            requests={
                "cpu": resources["cpu"],
                "memory": resources["memory"],
            },
            limits={
                "cpu": resources["cpu_limit"],
                "memory": resources["memory_limit"],
            },
        )

        # Environment variables
        env = [
            client.V1EnvVar(name="LAB_SESSION_ID", value=session_id),
            client.V1EnvVar(name="LAB_PRESET", value=preset),
            client.V1EnvVar(name="TERM", value="xterm-256color"),
            client.V1EnvVar(name="PS1", value="\\u@lab:\\w\\$ "),
        ]

        # For desktop presets
        if preset.startswith("desktop"):
            env.extend([
                client.V1EnvVar(name="VNC_PW", value="toor"),
                client.V1EnvVar(name="VNC_RESOLUTION", value="1280x720"),
            ])

        # Container ports
        ports = []
        if "ports" in preset_config:
            for p in preset_config["ports"]:
                ports.append(client.V1ContainerPort(
                    name=p["name"],
                    container_port=p["port"],
                    protocol="TCP",
                ))

        # Security context
        security_context = client.V1SecurityContext(
            allow_privilege_escalation=False,
            capabilities=client.V1Capabilities(
                drop=["ALL"],
                add=["NET_RAW"],  # For ping, traceroute
            ),
        )

        # Some presets need root
        if preset in ["desktop", "desktop-kali", "pentest"]:
            security_context = client.V1SecurityContext(
                run_as_user=0,
            )

        # Container spec
        container = client.V1Container(
            name="lab",
            image=image,
            image_pull_policy="IfNotPresent",
            env=env,
            resources=resource_requirements,
            security_context=security_context,
            ports=ports if ports else None,
            volume_mounts=[
                client.V1VolumeMount(
                    name="lab-workspace",
                    mount_path="/workspace",
                ),
            ],
        )

        if command:
            container.command = command[:1]
            if len(command) > 1:
                container.args = command[1:]

        # Pod spec
        pod_spec = client.V1PodSpec(
            restart_policy="Never",
            automount_service_account_token=False,
            containers=[container],
            volumes=[
                client.V1Volume(
                    name="lab-workspace",
                    empty_dir=client.V1EmptyDirVolumeSource(
                        size_limit="1Gi",
                    ),
                ),
            ],
            active_deadline_seconds=settings.K8S_POD_TTL,
            termination_grace_period_seconds=10,
        )

        # Add shared memory for desktop presets
        if preset.startswith("desktop"):
            pod_spec.volumes.append(
                client.V1Volume(
                    name="shm",
                    empty_dir=client.V1EmptyDirVolumeSource(
                        medium="Memory",
                        size_limit="512Mi",
                    ),
                )
            )
            container.volume_mounts.append(
                client.V1VolumeMount(
                    name="shm",
                    mount_path="/dev/shm",
                )
            )

        # Pod metadata
        pod = client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=settings.K8S_LAB_NAMESPACE,
                labels={
                    "app": "cyberaix-lab",
                    "session-id": session_id[:63],  # K8s label max length
                    "user-id": user_id[:63],
                    "preset": preset,
                    "cyberaix.role": "target",
                },
                annotations={
                    "cyberaix.io/created-at": utcnow().isoformat(),
                    "cyberaix.io/expires-at": (utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES)).isoformat(),
                },
            ),
            spec=pod_spec,
        )

        return pod

    async def _wait_for_pod_ready(self, pod_name: str, namespace: str) -> bool:
        """Wait for pod to be in Running state."""
        timeout = settings.K8S_POD_TIMEOUT
        interval = 2
        elapsed = 0

        while elapsed < timeout:
            try:
                pod = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
                )

                if pod.status.phase == "Running":
                    # Check if all containers are ready
                    if pod.status.container_statuses:
                        all_ready = all(cs.ready for cs in pod.status.container_statuses)
                        if all_ready:
                            logger.info(f"Pod {pod_name} is ready")
                            return True

                elif pod.status.phase in ["Failed", "Succeeded"]:
                    logger.error(f"Pod {pod_name} ended with phase: {pod.status.phase}")
                    return False

            except ApiException as e:
                if e.status != 404:
                    logger.error(f"Error checking pod status: {e}")

            await asyncio.sleep(interval)
            elapsed += interval

        logger.error(f"Timeout waiting for pod {pod_name}")
        return False

    async def _create_lab_service(
        self,
        session_id: str,
        preset_config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create a service for VNC access to desktop labs."""
        if "ports" not in preset_config:
            return None

        try:
            svc_name = self._get_service_name(session_id)
            namespace = settings.K8S_LAB_NAMESPACE

            ports = [
                client.V1ServicePort(
                    name=p["name"],
                    port=p["port"],
                    target_port=p["port"],
                    protocol="TCP",
                )
                for p in preset_config["ports"]
            ]

            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=svc_name,
                    namespace=namespace,
                    labels={
                        "app": "cyberaix-lab",
                        "session-id": session_id[:63],
                    },
                ),
                spec=client.V1ServiceSpec(
                    type="ClusterIP",
                    ports=ports,
                    selector={
                        "session-id": session_id[:63],
                    },
                ),
            )

            created_svc = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._core_api.create_namespaced_service(namespace=namespace, body=service)
            )

            logger.info(f"Created service: {svc_name}")
            return {
                "name": svc_name,
                "cluster_ip": created_svc.spec.cluster_ip,
                "ports": {p["name"]: p["port"] for p in preset_config["ports"]},
            }

        except ApiException as e:
            logger.error(f"Failed to create service: {e}")
            return None

    async def stop_lab_session(self, session_id: str) -> bool:
        """Stop and cleanup a lab session by deleting the pod and service."""
        await self._init_k8s_client()

        if not self._k8s_available:
            return False

        try:
            namespace = settings.K8S_LAB_NAMESPACE
            pod_name = self._get_pod_name(session_id)
            svc_name = self._get_service_name(session_id)

            # Delete pod
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._core_api.delete_namespaced_pod(
                        name=pod_name,
                        namespace=namespace,
                        grace_period_seconds=5,
                    )
                )
                logger.info(f"Deleted pod: {pod_name}")
            except ApiException as e:
                if e.status != 404:
                    logger.error(f"Error deleting pod: {e}")

            # Delete service
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._core_api.delete_namespaced_service(
                        name=svc_name,
                        namespace=namespace,
                    )
                )
                logger.info(f"Deleted service: {svc_name}")
            except ApiException as e:
                if e.status != 404:
                    pass  # Service might not exist

            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            logger.info(f"Lab session stopped: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping lab session: {e}")
            return False

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a lab session."""
        await self._init_k8s_client()

        session = self.active_sessions.get(session_id)
        if not session:
            return {"status": "not_found", "session_id": session_id}

        if not self._k8s_available:
            return {"status": "unknown", "session_id": session_id, "error": "K8s not available"}

        try:
            pod_name = self._get_pod_name(session_id)
            namespace = settings.K8S_LAB_NAMESPACE

            pod = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._core_api.read_namespaced_pod(name=pod_name, namespace=namespace)
            )

            is_expired = utcnow() > session["expires_at"]

            return {
                "session_id": session_id,
                "status": "expired" if is_expired else pod.status.phase.lower(),
                "started_at": session["started_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
                "pod_name": pod_name,
                "preset": session["preset"],
            }

        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found", "session_id": session_id}
            logger.error(f"Error getting session status: {e}")
            return {"status": "error", "session_id": session_id, "error": str(e)}

    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active lab sessions."""
        sessions = []
        for session_id, session in self.active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "user_id": session["user_id"],
                "pod_name": session["pod_name"],
                "preset": session["preset"],
                "started_at": session["started_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
            })
        return sessions

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

    async def get_pod_name_for_session(self, session_id: str, role: str = "target") -> Optional[str]:
        """Get the pod name for a session."""
        session = self.active_sessions.get(session_id)
        if session:
            return session["pod_name"]
        return None


# Singleton instance
k8s_lab_manager = K8sLabManager()
