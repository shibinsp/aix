import asyncio
import json
from typing import Dict, Optional, Union
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.lab import LabSession, LabStatus
from app.services.labs.terminal_service import TerminalService
from app.services.labs.lab_manager import is_running_in_kubernetes

logger = structlog.get_logger()
router = APIRouter()


def get_terminal_service(container_or_pod_name: str, namespace: str = None):
    """
    Get the appropriate terminal service based on environment.

    In Kubernetes: Uses K8sTerminalServiceAlt (kubectl-based PTY)
    In Docker: Uses TerminalService (docker exec-based PTY)
    """
    if is_running_in_kubernetes():
        from app.services.labs.k8s_terminal_service import K8sTerminalServiceAlt
        return K8sTerminalServiceAlt(
            pod_name=container_or_pod_name,
            namespace=namespace or settings.K8S_LAB_NAMESPACE,
        )
    else:
        return TerminalService(container_name=container_or_pod_name)


class TerminalConnectionManager:
    """Manage terminal WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.terminal_services: Dict[str, Union[TerminalService, any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        container_or_pod_name: str,
        user_id: str,
        namespace: str = None,
    ) -> Optional[Union[TerminalService, any]]:
        """Connect a WebSocket to a container or pod terminal.

        Note: websocket.accept() should be called before this method.
        """
        connection_key = f"{session_id}:{container_or_pod_name}:{user_id}"
        self.active_connections[connection_key] = websocket

        # Create terminal service for this connection (auto-detects K8s vs Docker)
        terminal = get_terminal_service(container_or_pod_name, namespace)
        started = await terminal.start()

        if started:
            self.terminal_services[connection_key] = terminal
            logger.info(
                "Terminal connected",
                session_id=session_id,
                target=container_or_pod_name,
                user_id=user_id,
                backend="kubernetes" if is_running_in_kubernetes() else "docker",
            )
            return terminal
        else:
            logger.error(
                "Failed to start terminal",
                session_id=session_id,
                target=container_or_pod_name,
            )
            return None

    async def disconnect(self, session_id: str, container_or_pod_name: str, user_id: str):
        """Disconnect and cleanup terminal connection."""
        connection_key = f"{session_id}:{container_or_pod_name}:{user_id}"

        if connection_key in self.terminal_services:
            await self.terminal_services[connection_key].stop()
            del self.terminal_services[connection_key]

        if connection_key in self.active_connections:
            del self.active_connections[connection_key]

        logger.info(
            "Terminal disconnected",
            session_id=session_id,
            target=container_or_pod_name,
        )


terminal_manager = TerminalConnectionManager()


@router.websocket("/terminal/{session_id}")
async def websocket_terminal(
    websocket: WebSocket,
    session_id: str,
    container: str = Query(default="target"),
):
    """WebSocket endpoint for container terminal access.

    Query params:
        - token: JWT authentication token
        - container: Container role name (default: "target")
    """
    logger.info(f"WebSocket terminal request received: session_id={session_id}, container={container}")
    logger.debug(f"Query params: {dict(websocket.query_params)}")

    # IMPORTANT: Accept the WebSocket connection first before any validation
    # This is required by the WebSocket protocol - we must accept before we can send/close
    await websocket.accept()

    # Get token from query params
    token = websocket.query_params.get("token")
    logger.debug(f"Token present: {bool(token)}")
    if not token:
        await websocket.send_json({"type": "error", "message": "Missing authentication token"})
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    # Validate token
    payload = decode_access_token(token)
    if not payload:
        await websocket.send_json({"type": "error", "message": "Invalid authentication token"})
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.send_json({"type": "error", "message": "Invalid token payload"})
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Verify lab session exists and belongs to user
    async with AsyncSessionLocal() as db:
        try:
            # Convert string IDs to UUID for proper database comparison
            session_uuid = UUID(session_id)
            user_uuid = UUID(user_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID format: session_id={session_id}, user_id={user_id}, error={e}")
            await websocket.send_json({"type": "error", "message": "Invalid session or user ID format"})
            await websocket.close(code=4001, reason="Invalid session or user ID format")
            return

        result = await db.execute(
            select(LabSession).where(
                LabSession.id == session_uuid,
                LabSession.user_id == user_uuid,
                LabSession.status == LabStatus.RUNNING,
            )
        )
        lab_session = result.scalar_one_or_none()

        if not lab_session:
            # Debug: Check what's in the database
            all_sessions = await db.execute(
                select(LabSession).where(LabSession.id == session_uuid)
            )
            session_info = all_sessions.scalar_one_or_none()
            if session_info:
                logger.warning(
                    f"Session found but check failed: status={session_info.status}, "
                    f"user_id={session_info.user_id}, expected_user={user_uuid}"
                )
            else:
                logger.warning(f"Session not found in database: {session_id}")

            await websocket.send_json({"type": "error", "message": "Lab session not found or not running"})
            await websocket.close(code=4004, reason="Lab session not found or not running")
            return

        # Build container or pod name from session based on environment
        if is_running_in_kubernetes():
            # In Kubernetes, pod names follow: lab-{session_id[:8]}-{role}
            target_name = f"lab-{session_id[:8]}-{container}"
            namespace = settings.K8S_LAB_NAMESPACE
            logger.info(f"Terminal connecting to pod: {target_name} in namespace {namespace}")
        else:
            # In Docker, container names follow: cyberx_{session_id[:8]}_{role}
            target_name = f"cyberx_{session_id[:8]}_{container}"
            namespace = None
            logger.info(f"Terminal connecting to container: {target_name}")

    # Connect terminal
    terminal = await terminal_manager.connect(
        websocket=websocket,
        session_id=session_id,
        container_or_pod_name=target_name,
        user_id=user_id,
        namespace=namespace,
    )

    if not terminal:
        await websocket.send_json({
            "type": "error",
            "message": "Failed to connect to terminal. Target may not be running.",
        })
        await websocket.close(code=1011, reason="Failed to start terminal")
        return

    # Send connection success
    await websocket.send_json({
        "type": "connected",
        "target": target_name,
        "backend": "kubernetes" if is_running_in_kubernetes() else "docker",
        "message": f"Connected to {container} terminal",
    })

    try:
        # Start output reader task
        output_task = asyncio.create_task(
            read_terminal_output(websocket, terminal)
        )

        # Process incoming messages
        while True:
            try:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if "text" in message:
                    data = json.loads(message["text"])
                    await handle_terminal_message(terminal, data)
                elif "bytes" in message:
                    # Direct binary input
                    await terminal.write(message["bytes"].decode("utf-8", errors="replace"))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Treat as raw input
                if "text" in message:
                    await terminal.write(message["text"])

    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
    finally:
        # Cleanup
        output_task.cancel()
        try:
            await output_task
        except asyncio.CancelledError:
            pass
        await terminal_manager.disconnect(session_id, target_name, user_id)


async def read_terminal_output(websocket: WebSocket, terminal: TerminalService):
    """Read output from terminal and send to WebSocket."""
    try:
        async for output in terminal.read():
            try:
                await websocket.send_json({
                    "type": "output",
                    "data": output,
                })
            except Exception:
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error reading terminal output: {e}")


async def handle_terminal_message(terminal: TerminalService, data: dict):
    """Handle incoming terminal messages."""
    msg_type = data.get("type", "input")

    if msg_type == "input":
        # Regular input
        content = data.get("data", "")
        if content:
            await terminal.write(content)

    elif msg_type == "resize":
        # Terminal resize
        cols = data.get("cols", 80)
        rows = data.get("rows", 24)
        await terminal.resize(cols, rows)

    elif msg_type == "ping":
        # Keep-alive ping (handled by WebSocket layer)
        pass
