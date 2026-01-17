"""
Kubernetes-based Persistent Environment Manager

Manages Kubernetes pods for terminal and desktop environments.
Uses Alphha Security OS images for security-focused environments.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from uuid import uuid4

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.client import ApiClient
import structlog
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.environment import PersistentEnvironment, EnvironmentType, EnvironmentStatus, EnvironmentSession
from app.core.config import settings

logger = structlog.get_logger()

# Environment type
EnvType = Literal["terminal", "desktop"]

# Container images - using linuxserver images that work well with web access
# These can be replaced with custom Alphha Security OS images
CONTAINER_IMAGES = {
    "terminal": "linuxserver/webtop:debian-xfce",  # Debian with XFCE desktop (web terminal)
    "desktop": "linuxserver/webtop:debian-xfce",   # Debian with XFCE desktop
}

# Lab namespace for environments
ENV_NAMESPACE = "cyberaix-labs"


class K8sEnvironmentManager:
    """
    Kubernetes-based environment manager for persistent terminal and desktop.

    Creates pods in the cyberaix-labs namespace with web-accessible terminals.
    """

    def __init__(self):
        self._initialized = False
        self._core_api: Optional[client.CoreV1Api] = None
        self._apps_api: Optional[client.AppsV1Api] = None
        self._custom_api: Optional[client.CustomObjectsApi] = None

    async def initialize(self) -> bool:
        """Initialize Kubernetes client."""
        if self._initialized:
            return True

        try:
            # Try in-cluster config first
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            except config.ConfigException:
                # Fall back to kubeconfig
                config.load_kube_config()
                logger.info("Loaded kubeconfig")

            self._core_api = client.CoreV1Api()
            self._apps_api = client.AppsV1Api()
            self._custom_api = client.CustomObjectsApi()
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            return False

    async def check_k8s_available(self) -> bool:
        """Check if Kubernetes is available."""
        if not self._initialized:
            return await self.initialize()

        try:
            self._core_api.list_namespace(limit=1)
            return True
        except Exception:
            return await self.initialize()

    def _get_pod_name(self, user_id: str, env_type: EnvType) -> str:
        """Get pod name for user's environment."""
        # Sanitize user_id for Kubernetes naming
        safe_id = user_id.replace("-", "")[:12]
        return f"env-{env_type}-{safe_id}"

    def _get_service_name(self, user_id: str, env_type: EnvType) -> str:
        """Get service name for user's environment."""
        safe_id = user_id.replace("-", "")[:12]
        return f"env-{env_type}-svc-{safe_id}"

    def _get_pvc_name(self, user_id: str) -> str:
        """Get PVC name for user's shared storage."""
        safe_id = user_id.replace("-", "")[:12]
        return f"env-storage-{safe_id}"

    def _get_ingress_route_name(self, user_id: str, env_type: EnvType) -> str:
        """Get IngressRoute name for user's environment."""
        safe_id = user_id.replace("-", "")[:12]
        return f"env-{env_type}-route-{safe_id}"

    async def _create_ingress_route(self, user_id: str, env_type: EnvType) -> str:
        """Create Traefik IngressRoute and Middleware for environment access."""
        safe_id = user_id.replace("-", "")[:12]
        route_name = self._get_ingress_route_name(user_id, env_type)
        service_name = self._get_service_name(user_id, env_type)
        middleware_name = f"strip-{env_type}-{safe_id}"
        path_prefix = f"/env/{env_type}/{safe_id}"

        # Create Middleware for stripping path prefix
        middleware = {
            "apiVersion": "traefik.io/v1alpha1",
            "kind": "Middleware",
            "metadata": {
                "name": middleware_name,
                "namespace": ENV_NAMESPACE,
                "labels": {
                    "app": "cyberaix-env",
                    "user-id": safe_id,
                    "managed-by": "cyberaix",
                }
            },
            "spec": {
                "stripPrefix": {
                    "prefixes": [path_prefix]
                }
            }
        }

        # Create IngressRoute
        ingress_route = {
            "apiVersion": "traefik.io/v1alpha1",
            "kind": "IngressRoute",
            "metadata": {
                "name": route_name,
                "namespace": ENV_NAMESPACE,
                "labels": {
                    "app": "cyberaix-env",
                    "env-type": env_type,
                    "user-id": safe_id,
                    "managed-by": "cyberaix",
                }
            },
            "spec": {
                "entryPoints": ["web", "websecure"],
                "routes": [
                    {
                        "match": f"Host(`cyyberaix.in`) && PathPrefix(`{path_prefix}`)",
                        "kind": "Rule",
                        "services": [
                            {
                                "name": service_name,
                                "port": 3000
                            }
                        ],
                        "middlewares": [
                            {
                                "name": middleware_name
                            }
                        ]
                    }
                ]
            }
        }

        try:
            # Create Middleware
            try:
                self._custom_api.create_namespaced_custom_object(
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=ENV_NAMESPACE,
                    plural="middlewares",
                    body=middleware
                )
            except ApiException as e:
                if e.status != 409:  # Already exists is OK
                    raise

            # Create IngressRoute
            try:
                self._custom_api.create_namespaced_custom_object(
                    group="traefik.io",
                    version="v1alpha1",
                    namespace=ENV_NAMESPACE,
                    plural="ingressroutes",
                    body=ingress_route
                )
            except ApiException as e:
                if e.status != 409:
                    raise

            logger.info(f"Created IngressRoute {route_name} for {env_type}")
            return path_prefix

        except Exception as e:
            logger.error(f"Failed to create IngressRoute: {e}")
            raise

    async def _delete_ingress_route(self, user_id: str, env_type: EnvType) -> None:
        """Delete Traefik IngressRoute and Middleware."""
        safe_id = user_id.replace("-", "")[:12]
        route_name = self._get_ingress_route_name(user_id, env_type)
        middleware_name = f"strip-{env_type}-{safe_id}"

        try:
            self._custom_api.delete_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=ENV_NAMESPACE,
                plural="ingressroutes",
                name=route_name
            )
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting IngressRoute: {e}")

        try:
            self._custom_api.delete_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=ENV_NAMESPACE,
                plural="middlewares",
                name=middleware_name
            )
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting Middleware: {e}")

    async def _ensure_pvc_exists(self, user_id: str) -> bool:
        """Ensure PVC exists for user's environment data."""
        pvc_name = self._get_pvc_name(user_id)

        try:
            self._core_api.read_namespaced_persistent_volume_claim(
                name=pvc_name,
                namespace=ENV_NAMESPACE
            )
            return True
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error checking PVC: {e}")
                return False

        # Create PVC
        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(
                name=pvc_name,
                namespace=ENV_NAMESPACE,
                labels={
                    "app": "cyberaix-env",
                    "user-id": user_id[:12],
                    "managed-by": "cyberaix",
                }
            ),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": "2Gi"}
                ),
                storage_class_name="local-path",  # k3s default storage class
            )
        )

        try:
            self._core_api.create_namespaced_persistent_volume_claim(
                namespace=ENV_NAMESPACE,
                body=pvc
            )
            logger.info(f"Created PVC {pvc_name}")
            return True
        except ApiException as e:
            logger.error(f"Failed to create PVC: {e}")
            return False

    async def start_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Start a persistent environment pod."""

        if not await self.check_k8s_available():
            raise RuntimeError("Kubernetes is not available")

        # Get or create environment record
        env = await self._get_or_create_environment(user_id, env_type, db)

        # Check if already running
        pod_name = self._get_pod_name(user_id, env_type)
        try:
            pod = self._core_api.read_namespaced_pod(
                name=pod_name,
                namespace=ENV_NAMESPACE
            )
            if pod.status.phase == "Running":
                # Update DB and return connection info
                env.status = EnvironmentStatus.RUNNING
                await db.commit()
                return await self._get_connection_info(user_id, env_type, env, db)
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error checking pod: {e}")

        # Update status to starting
        env.status = EnvironmentStatus.STARTING
        await db.commit()

        try:
            # Ensure PVC exists
            await self._ensure_pvc_exists(user_id)

            # Create the pod and service
            if env_type == "terminal":
                await self._create_terminal_pod(user_id)
            else:
                await self._create_desktop_pod(user_id)

            # Wait for pod to be ready (max 60 seconds)
            ready = await self._wait_for_pod_ready(pod_name, timeout=60)

            if ready:
                # Create IngressRoute for web access
                path_prefix = await self._create_ingress_route(user_id, env_type)

                env.status = EnvironmentStatus.RUNNING
                env.last_started = datetime.utcnow()
                env.container_id = pod_name  # Store pod name as container_id

                # Set access URL
                host = getattr(settings, "ENVIRONMENT_HOST", "cyyberaix.in")
                env.access_url = f"https://{host}{path_prefix}/"

                # Create session
                session = EnvironmentSession(
                    environment_id=env.id,
                    user_id=user_id,
                )
                db.add(session)

                await db.commit()
                await db.refresh(env)

                logger.info(f"Started {env_type} environment for user {user_id}")
                return await self._get_connection_info(user_id, env_type, env, db)
            else:
                raise RuntimeError("Pod failed to become ready")

        except Exception as e:
            env.status = EnvironmentStatus.ERROR
            env.error_message = str(e)
            await db.commit()
            logger.error(f"Failed to start environment: {e}")
            raise

    async def _create_terminal_pod(self, user_id: str) -> None:
        """Create a terminal environment pod with ttyd web terminal."""

        pod_name = self._get_pod_name(user_id, "terminal")
        service_name = self._get_service_name(user_id, "terminal")
        pvc_name = self._get_pvc_name(user_id)

        # Pod definition
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=ENV_NAMESPACE,
                labels={
                    "app": "cyberaix-env",
                    "env-type": "terminal",
                    "user-id": user_id[:12],
                    "managed-by": "cyberaix",
                }
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="terminal",
                        image=CONTAINER_IMAGES["terminal"],
                        ports=[
                            client.V1ContainerPort(container_port=3000, name="web"),
                        ],
                        env=[
                            client.V1EnvVar(name="PUID", value="1000"),
                            client.V1EnvVar(name="PGID", value="1000"),
                            client.V1EnvVar(name="TZ", value="UTC"),
                            client.V1EnvVar(name="TITLE", value="Alphha Terminal"),
                        ],
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="user-data",
                                mount_path="/config",
                            )
                        ],
                        resources=client.V1ResourceRequirements(
                            requests={"memory": "256Mi", "cpu": "100m"},
                            limits={"memory": "1Gi", "cpu": "500m"},
                        ),
                        security_context=client.V1SecurityContext(
                            run_as_non_root=False,  # linuxserver needs root
                        ),
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="user-data",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        )
                    )
                ],
                restart_policy="Always",
            )
        )

        # Service definition
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=ENV_NAMESPACE,
                labels={
                    "app": "cyberaix-env",
                    "env-type": "terminal",
                    "user-id": user_id[:12],
                }
            ),
            spec=client.V1ServiceSpec(
                selector={
                    "app": "cyberaix-env",
                    "env-type": "terminal",
                    "user-id": user_id[:12],
                },
                ports=[
                    client.V1ServicePort(
                        name="web",
                        port=3000,
                        target_port=3000,
                    )
                ],
                type="ClusterIP",
            )
        )

        # Create pod and service
        try:
            self._core_api.create_namespaced_pod(namespace=ENV_NAMESPACE, body=pod)
        except ApiException as e:
            if e.status != 409:  # Already exists is OK
                raise

        try:
            self._core_api.create_namespaced_service(namespace=ENV_NAMESPACE, body=service)
        except ApiException as e:
            if e.status != 409:
                raise

    async def _create_desktop_pod(self, user_id: str) -> None:
        """Create a desktop environment pod with noVNC."""

        pod_name = self._get_pod_name(user_id, "desktop")
        service_name = self._get_service_name(user_id, "desktop")
        pvc_name = self._get_pvc_name(user_id)

        # Pod definition
        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=ENV_NAMESPACE,
                labels={
                    "app": "cyberaix-env",
                    "env-type": "desktop",
                    "user-id": user_id[:12],
                    "managed-by": "cyberaix",
                }
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="desktop",
                        image=CONTAINER_IMAGES["desktop"],
                        ports=[
                            client.V1ContainerPort(container_port=3000, name="web"),
                        ],
                        env=[
                            client.V1EnvVar(name="PUID", value="1000"),
                            client.V1EnvVar(name="PGID", value="1000"),
                            client.V1EnvVar(name="TZ", value="UTC"),
                            client.V1EnvVar(name="TITLE", value="Alphha Desktop"),
                        ],
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="user-data",
                                mount_path="/config",
                            ),
                            client.V1VolumeMount(
                                name="shm",
                                mount_path="/dev/shm",
                            )
                        ],
                        resources=client.V1ResourceRequirements(
                            requests={"memory": "512Mi", "cpu": "200m"},
                            limits={"memory": "2Gi", "cpu": "1000m"},
                        ),
                        security_context=client.V1SecurityContext(
                            run_as_non_root=False,
                        ),
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="user-data",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        )
                    ),
                    client.V1Volume(
                        name="shm",
                        empty_dir=client.V1EmptyDirVolumeSource(
                            medium="Memory",
                            size_limit="512Mi"
                        )
                    )
                ],
                restart_policy="Always",
            )
        )

        # Service definition
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=ENV_NAMESPACE,
                labels={
                    "app": "cyberaix-env",
                    "env-type": "desktop",
                    "user-id": user_id[:12],
                }
            ),
            spec=client.V1ServiceSpec(
                selector={
                    "app": "cyberaix-env",
                    "env-type": "desktop",
                    "user-id": user_id[:12],
                },
                ports=[
                    client.V1ServicePort(
                        name="web",
                        port=3000,
                        target_port=3000,
                    )
                ],
                type="ClusterIP",
            )
        )

        # Create pod and service
        try:
            self._core_api.create_namespaced_pod(namespace=ENV_NAMESPACE, body=pod)
        except ApiException as e:
            if e.status != 409:
                raise

        try:
            self._core_api.create_namespaced_service(namespace=ENV_NAMESPACE, body=service)
        except ApiException as e:
            if e.status != 409:
                raise

    async def _wait_for_pod_ready(self, pod_name: str, timeout: int = 60) -> bool:
        """Wait for pod to be ready."""
        start_time = datetime.utcnow()

        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                pod = self._core_api.read_namespaced_pod(
                    name=pod_name,
                    namespace=ENV_NAMESPACE
                )

                if pod.status.phase == "Running":
                    # Check if containers are ready
                    if pod.status.container_statuses:
                        all_ready = all(cs.ready for cs in pod.status.container_statuses)
                        if all_ready:
                            return True

                elif pod.status.phase in ("Failed", "Unknown"):
                    return False

            except ApiException:
                pass

            await asyncio.sleep(2)

        return False

    async def stop_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> bool:
        """Stop a user's environment."""

        if not await self.check_k8s_available():
            return False

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

        # End active session
        session_result = await db.execute(
            select(EnvironmentSession).where(
                EnvironmentSession.environment_id == env.id,
                EnvironmentSession.ended_at.is_(None)
            )
        )
        active_session = session_result.scalar_one_or_none()
        if active_session:
            active_session.end_session("user_stopped")

        # Delete pod and service
        pod_name = self._get_pod_name(user_id, env_type)
        service_name = self._get_service_name(user_id, env_type)

        try:
            self._core_api.delete_namespaced_pod(
                name=pod_name,
                namespace=ENV_NAMESPACE,
                grace_period_seconds=10
            )
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting pod: {e}")

        try:
            self._core_api.delete_namespaced_service(
                name=service_name,
                namespace=ENV_NAMESPACE
            )
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting service: {e}")

        # Delete IngressRoute and Middleware
        await self._delete_ingress_route(user_id, env_type)

        # Update environment record
        env.status = EnvironmentStatus.STOPPED
        env.last_stopped = datetime.utcnow()
        env.container_id = None
        env.access_url = None

        await db.commit()

        logger.info(f"Stopped {env_type} environment for user {user_id}")
        return True

    async def _get_or_create_environment(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> PersistentEnvironment:
        """Get existing environment or create new record."""

        env_type_enum = EnvironmentType.TERMINAL if env_type == "terminal" else EnvironmentType.DESKTOP

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

        return env

    async def _get_connection_info(
        self,
        user_id: str,
        env_type: EnvType,
        env: PersistentEnvironment,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get connection info for a running environment."""

        service_name = self._get_service_name(user_id, env_type)

        # Use the existing access_url if set (from IngressRoute), otherwise generate it
        if not env.access_url:
            safe_id = user_id.replace("-", "")[:12]
            host = getattr(settings, "ENVIRONMENT_HOST", "cyyberaix.in")
            path_prefix = f"/env/{env_type}/{safe_id}"
            env.access_url = f"https://{host}{path_prefix}/"
            await db.commit()

        return {
            "id": str(env.id),
            "env_type": env.env_type.value,
            "status": env.status.value,
            "access_url": env.access_url,
            "service_name": service_name,
            "namespace": ENV_NAMESPACE,
        }

    async def get_environment_status(
        self,
        user_id: str,
        env_type: EnvType,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get current status of an environment."""

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

        # Verify pod is actually running
        if env.status == EnvironmentStatus.RUNNING:
            pod_name = self._get_pod_name(user_id, env_type)
            try:
                pod = self._core_api.read_namespaced_pod(
                    name=pod_name,
                    namespace=ENV_NAMESPACE
                )
                if pod.status.phase != "Running":
                    env.status = EnvironmentStatus.STOPPED
                    await db.commit()
            except ApiException as e:
                if e.status == 404:
                    env.status = EnvironmentStatus.STOPPED
                    env.container_id = None
                    await db.commit()

        return {
            "id": str(env.id),
            "env_type": env.env_type.value,
            "status": env.status.value,
            "access_url": env.access_url if env.status == EnvironmentStatus.RUNNING else None,
            "total_usage_minutes": env.total_usage_minutes,
            "monthly_usage_minutes": env.monthly_usage_minutes,
        }


# Global instance
k8s_env_manager = K8sEnvironmentManager()
