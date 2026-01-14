import asyncio
import os
import pty
import select
import subprocess
import signal
from typing import AsyncGenerator, Optional
import structlog

logger = structlog.get_logger()


class TerminalService:
    """Service to manage PTY terminal connections to Docker containers."""

    def __init__(self, container_name: str, shell: str = "/bin/sh"):
        self.container_name = container_name
        self.shell = shell
        self.process: Optional[subprocess.Popen] = None
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self._running = False
        self._read_task: Optional[asyncio.Task] = None
        self._detected_shell: Optional[str] = None

    async def _detect_shell(self) -> str:
        """Detect available shell in the container."""
        # Try bash first, then sh
        for shell in ["/bin/bash", "/bin/sh"]:
            check = await asyncio.create_subprocess_exec(
                "docker", "exec", self.container_name, "test", "-x", shell,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await check.communicate()
            if check.returncode == 0:
                logger.debug(f"Detected shell: {shell}", container=self.container_name)
                return shell
        return "/bin/sh"  # Default fallback

    async def start(self) -> bool:
        """Start the terminal connection to the container."""
        try:
            # Check if container is running
            check_result = await asyncio.create_subprocess_exec(
                "docker", "inspect", "-f", "{{.State.Running}}", self.container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await check_result.communicate()

            if check_result.returncode != 0 or stdout.decode().strip() != "true":
                logger.error(
                    "Container not running",
                    container=self.container_name,
                    error=stderr.decode() if stderr else "Not running",
                )
                return False

            # Detect available shell
            self._detected_shell = await self._detect_shell()

            # Create PTY
            self.master_fd, self.slave_fd = pty.openpty()

            # Build exec command based on detected shell
            # Use -i for interactive mode only, since we're handling TTY ourselves via PTY
            # The -t flag would allocate a second TTY which conflicts with our PTY setup
            exec_cmd = [
                "docker", "exec", "-i",
                "-e", "TERM=xterm-256color",
                "-e", "PS1=\\u@\\h:\\w\\$ ",
                self.container_name,
            ]

            # Add shell with appropriate flags
            if self._detected_shell == "/bin/bash":
                exec_cmd.extend([self._detected_shell, "--login"])
            else:
                # For sh/ash, just start interactive shell
                exec_cmd.append(self._detected_shell)

            self.process = subprocess.Popen(
                exec_cmd,
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                preexec_fn=os.setsid,
                close_fds=True,
            )

            # Close slave in parent process
            os.close(self.slave_fd)
            self.slave_fd = None

            # Set non-blocking mode on master
            import fcntl
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            self._running = True
            logger.info("Terminal started", container=self.container_name)
            return True

        except Exception as e:
            logger.error(f"Failed to start terminal: {e}", container=self.container_name)
            await self.stop()
            return False

    async def stop(self):
        """Stop the terminal connection."""
        self._running = False

        if self.process:
            try:
                # Send SIGHUP to terminal
                os.killpg(os.getpgid(self.process.pid), signal.SIGHUP)
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
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

        logger.info("Terminal stopped", container=self.container_name)

    async def write(self, data: str):
        """Write data to the terminal."""
        if not self._running or self.master_fd is None:
            return

        try:
            os.write(self.master_fd, data.encode("utf-8"))
        except OSError as e:
            logger.error(f"Error writing to terminal: {e}")
            self._running = False

    async def read(self) -> AsyncGenerator[str, None]:
        """Read output from the terminal as an async generator."""
        if self.master_fd is None:
            return

        loop = asyncio.get_event_loop()
        fd = self.master_fd  # Capture the file descriptor

        while self._running and fd is not None:
            try:
                # Use select to wait for data with timeout
                # Capture fd in lambda to avoid closure issues
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
                            # EOF
                            break
                    except (OSError, BlockingIOError):
                        break

                # Check if process is still running
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

            # Set terminal size
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
