"""
Kubernetes Terminal Service for AI CyberX.

This module provides terminal access to Kubernetes pods using kubectl exec
via the Kubernetes Python client's streaming capabilities.
"""

import asyncio
from typing import AsyncGenerator, Optional
import structlog

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
from kubernetes.stream.ws_client import WSClient

from app.core.config import settings

logger = structlog.get_logger()


class K8sTerminalService:
    """Service to manage terminal connections to Kubernetes pods."""

    def __init__(self, pod_name: str, namespace: str = None, shell: str = "/bin/sh"):
        self.pod_name = pod_name
        self.namespace = namespace or settings.K8S_LAB_NAMESPACE
        self.shell = shell
        self._ws_client: Optional[WSClient] = None
        self._running = False
        self._core_api: Optional[client.CoreV1Api] = None
        self._initialized = False
        self._detected_shell: Optional[str] = None

    async def _init_k8s_client(self):
        """Initialize the Kubernetes client."""
        if self._initialized:
            return

        try:
            if settings.K8S_IN_CLUSTER:
                config.load_incluster_config()
            else:
                config.load_kube_config()

            self._core_api = client.CoreV1Api()
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise

    async def _detect_shell(self) -> str:
        """Detect available shell in the pod."""
        await self._init_k8s_client()

        for shell in ["/bin/bash", "/bin/sh"]:
            try:
                # Try to execute the shell to check if it exists
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda s=shell: stream(
                        self._core_api.connect_get_namespaced_pod_exec,
                        self.pod_name,
                        self.namespace,
                        command=["test", "-x", s],
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )
                )
                logger.debug(f"Detected shell: {shell}", pod=self.pod_name)
                return shell
            except ApiException:
                continue

        return "/bin/sh"

    async def start(self) -> bool:
        """Start the terminal connection to the pod."""
        try:
            await self._init_k8s_client()

            # Check if pod exists and is running
            try:
                pod = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._core_api.read_namespaced_pod(
                        name=self.pod_name,
                        namespace=self.namespace,
                    )
                )

                if pod.status.phase != "Running":
                    logger.error(
                        "Pod not running",
                        pod=self.pod_name,
                        phase=pod.status.phase,
                    )
                    return False

            except ApiException as e:
                logger.error(f"Pod not found: {e}", pod=self.pod_name)
                return False

            # Detect available shell
            self._detected_shell = await self._detect_shell()

            # Build exec command
            exec_command = [self._detected_shell]
            if self._detected_shell == "/bin/bash":
                exec_command.append("--login")

            # Create WebSocket connection for interactive exec
            self._ws_client = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stream(
                    self._core_api.connect_get_namespaced_pod_exec,
                    self.pod_name,
                    self.namespace,
                    command=exec_command,
                    stderr=True,
                    stdin=True,
                    stdout=True,
                    tty=True,
                    _preload_content=False,
                )
            )

            self._running = True
            logger.info("Terminal started", pod=self.pod_name)
            return True

        except Exception as e:
            logger.error(f"Failed to start terminal: {e}", pod=self.pod_name)
            await self.stop()
            return False

    async def stop(self):
        """Stop the terminal connection."""
        self._running = False

        if self._ws_client:
            try:
                self._ws_client.close()
            except Exception:
                pass
            self._ws_client = None

        logger.info("Terminal stopped", pod=self.pod_name)

    async def write(self, data: str):
        """Write data to the terminal."""
        if not self._running or not self._ws_client:
            return

        try:
            # Write to stdin (channel 0)
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._ws_client.write_stdin(data)
            )
        except Exception as e:
            logger.error(f"Error writing to terminal: {e}")
            self._running = False

    async def read(self) -> AsyncGenerator[str, None]:
        """Read output from the terminal as an async generator."""
        if not self._ws_client:
            return

        while self._running and self._ws_client.is_open():
            try:
                # Read with timeout
                output = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._ws_client.read_stdout(timeout=0.1)
                )

                if output:
                    yield output

                # Also check stderr
                stderr = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._ws_client.read_stderr(timeout=0.01)
                )

                if stderr:
                    yield stderr

                await asyncio.sleep(0.01)

            except Exception as e:
                if "timed out" not in str(e).lower():
                    logger.error(f"Error reading from terminal: {e}")
                    break
                await asyncio.sleep(0.01)

    async def resize(self, cols: int, rows: int):
        """Resize the terminal.

        Note: The Kubernetes exec API supports resize through SPDY but the
        websocket-client based stream doesn't support resize directly.
        This is a known limitation.
        """
        # Terminal resize is not directly supported via the stream API
        # The resize would need to be done via kubectl or a SPDY-based client
        logger.debug(f"Terminal resize requested to {cols}x{rows} (not supported via stream API)")

    @property
    def is_running(self) -> bool:
        """Check if terminal is still running."""
        if not self._running:
            return False
        if self._ws_client and not self._ws_client.is_open():
            self._running = False
            return False
        return True


class K8sTerminalServiceAlt:
    """
    Alternative Kubernetes terminal service using subprocess with kubectl.

    This approach uses kubectl exec directly and provides better PTY support
    but requires kubectl to be installed in the backend container.
    """

    def __init__(self, pod_name: str, namespace: str = None, shell: str = "/bin/sh"):
        self.pod_name = pod_name
        self.namespace = namespace or settings.K8S_LAB_NAMESPACE
        self.shell = shell
        self.process = None
        self.master_fd = None
        self.slave_fd = None
        self._running = False
        self._detected_shell = None

    async def _detect_shell(self) -> str:
        """Detect available shell in the pod."""
        for shell in ["/bin/bash", "/bin/sh"]:
            check = await asyncio.create_subprocess_exec(
                "kubectl", "exec", "-n", self.namespace, self.pod_name,
                "--", "test", "-x", shell,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()
            if check.returncode == 0:
                logger.debug(f"Detected shell: {shell}", pod=self.pod_name)
                return shell
        return "/bin/sh"

    async def start(self) -> bool:
        """Start the terminal connection using kubectl exec."""
        import os
        import pty
        import subprocess

        try:
            # Check if pod is running
            check_result = await asyncio.create_subprocess_exec(
                "kubectl", "get", "pod", "-n", self.namespace, self.pod_name,
                "-o", "jsonpath={.status.phase}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await check_result.communicate()

            if check_result.returncode != 0 or stdout.decode().strip() != "Running":
                logger.error(
                    "Pod not running",
                    pod=self.pod_name,
                    error=stderr.decode() if stderr else "Not running",
                )
                return False

            # Detect available shell
            self._detected_shell = await self._detect_shell()

            # Create PTY
            self.master_fd, self.slave_fd = pty.openpty()

            # Build kubectl exec command
            exec_cmd = [
                "kubectl", "exec", "-it",
                "-n", self.namespace,
                self.pod_name,
                "--",
            ]

            if self._detected_shell == "/bin/bash":
                exec_cmd.extend([self._detected_shell, "--login"])
            else:
                exec_cmd.append(self._detected_shell)

            # Set environment for PTY
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            self.process = subprocess.Popen(
                exec_cmd,
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                preexec_fn=os.setsid,
                close_fds=True,
                env=env,
            )

            # Close slave in parent process
            os.close(self.slave_fd)
            self.slave_fd = None

            # Set non-blocking mode on master
            import fcntl
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            self._running = True
            logger.info("Terminal started (kubectl)", pod=self.pod_name)
            return True

        except Exception as e:
            logger.error(f"Failed to start terminal: {e}", pod=self.pod_name)
            await self.stop()
            return False

    async def stop(self):
        """Stop the terminal connection."""
        import os
        import signal

        self._running = False

        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGHUP)
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except Exception:
                    self.process.kill()
            except (ProcessLookupError, OSError):
                pass
            self.process = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self.slave_fd is not None:
            try:
                os.close(self.slave_fd)
            except OSError:
                pass
            self.slave_fd = None

        logger.info("Terminal stopped", pod=self.pod_name)

    async def write(self, data: str):
        """Write data to the terminal."""
        import os

        if not self._running or self.master_fd is None:
            return

        try:
            os.write(self.master_fd, data.encode("utf-8"))
        except OSError as e:
            logger.error(f"Error writing to terminal: {e}")
            self._running = False

    async def read(self) -> AsyncGenerator[str, None]:
        """Read output from the terminal as an async generator."""
        import os
        import select

        if self.master_fd is None:
            return

        loop = asyncio.get_event_loop()
        fd = self.master_fd

        while self._running and fd is not None:
            try:
                readable, _, _ = await loop.run_in_executor(
                    None,
                    lambda fd=fd: select.select([fd], [], [], 0.1)
                )

                if readable:
                    try:
                        data = os.read(fd, 4096)
                        if data:
                            yield data.decode("utf-8", errors="replace")
                        else:
                            break
                    except (OSError, BlockingIOError):
                        break

                if self.process and self.process.poll() is not None:
                    break

                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Error reading from terminal: {e}")
                break

    async def resize(self, cols: int, rows: int):
        """Resize the terminal."""
        if self.master_fd is None:
            return

        try:
            import struct
            import fcntl
            import termios

            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            logger.debug(f"Terminal resized to {cols}x{rows}")
        except Exception as e:
            logger.error(f"Error resizing terminal: {e}")

    @property
    def is_running(self) -> bool:
        """Check if terminal is still running."""
        if not self._running:
            return False
        if self.process and self.process.poll() is not None:
            self._running = False
            return False
        return True
