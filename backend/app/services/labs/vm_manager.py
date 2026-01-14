"""
Alphha Linux VM Manager
Manages QEMU/KVM virtual machines for cybersecurity labs.
Supports both Docker containers and full VMs.
"""

import asyncio
import json
import os
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def utcnow():
    """Get current UTC time with timezone awareness."""
    return datetime.now(timezone.utc)


class VMManager:
    """Manage QEMU/KVM virtual machines for cybersecurity labs."""

    def __init__(self):
        self.active_vms: Dict[str, Dict[str, Any]] = {}
        self._qemu_available: Optional[bool] = None
        self._libvirt_available: Optional[bool] = None

        # VM storage paths (configured via settings)
        self.vm_base_path = Path(settings.LAB_VM_PATH)
        self.template_path = Path(settings.LAB_TEMPLATE_PATH)

        # Default VM settings
        self.default_memory = "512M"
        self.default_cpus = 1
        self.default_disk_size = "4G"

    async def _run_command(self, *args, timeout: int = 60) -> tuple[str, str, int]:
        """Run a shell command asynchronously."""
        cmd = list(args)
        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                return stdout.decode(), stderr.decode(), process.returncode
            except asyncio.TimeoutError:
                process.kill()
                return "", "Command timed out", 1

        except FileNotFoundError as e:
            logger.error(f"Command not found: {cmd[0]}")
            return "", f"Command not found: {cmd[0]}", 1
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return "", str(e), 1

    async def check_qemu_available(self) -> bool:
        """Check if QEMU is available on the system."""
        if self._qemu_available is not None:
            return self._qemu_available

        try:
            stdout, stderr, returncode = await self._run_command("qemu-system-x86_64", "--version")
            if returncode == 0:
                logger.info(f"QEMU available: {stdout.strip().split(chr(10))[0]}")
                self._qemu_available = True
                return True
            logger.warning(f"QEMU check failed: {stderr}")
            self._qemu_available = False
            return False
        except Exception as e:
            logger.error(f"QEMU not available: {e}")
            self._qemu_available = False
            return False

    async def check_kvm_available(self) -> bool:
        """Check if KVM acceleration is available."""
        try:
            # Check if /dev/kvm exists and is accessible
            if os.path.exists("/dev/kvm"):
                stdout, stderr, returncode = await self._run_command("ls", "-la", "/dev/kvm")
                if returncode == 0:
                    logger.info("KVM acceleration available")
                    return True
            logger.info("KVM acceleration not available, will use TCG")
            return False
        except Exception as e:
            logger.warning(f"KVM check failed: {e}")
            return False

    async def check_libvirt_available(self) -> bool:
        """Check if libvirt is available."""
        if self._libvirt_available is not None:
            return self._libvirt_available

        try:
            stdout, stderr, returncode = await self._run_command("virsh", "--version")
            if returncode == 0:
                logger.info(f"Libvirt available: {stdout.strip()}")
                self._libvirt_available = True
                return True
            self._libvirt_available = False
            return False
        except Exception as e:
            logger.warning(f"Libvirt not available: {e}")
            self._libvirt_available = False
            return False

    async def list_available_templates(self) -> List[Dict[str, Any]]:
        """List available VM templates."""
        templates = []

        # Check for QCOW2 images in template directory
        vm_dir = self.template_path / "output" / "vm"
        if vm_dir.exists():
            for qcow2_file in vm_dir.glob("*.qcow2"):
                templates.append({
                    "name": qcow2_file.stem,
                    "path": str(qcow2_file),
                    "type": "qcow2",
                    "size": qcow2_file.stat().st_size,
                })

        # Check for presets that can be built
        presets_dir = self.template_path / "config" / "presets"
        if presets_dir.exists():
            for preset_file in presets_dir.glob("*.conf"):
                templates.append({
                    "name": preset_file.stem,
                    "path": str(preset_file),
                    "type": "preset",
                    "buildable": True,
                })

        return templates

    async def create_vm_from_template(
        self,
        session_id: str,
        template_name: str,
        vm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new VM instance from a template."""

        config = vm_config or {}
        memory = config.get("memory", self.default_memory)
        cpus = config.get("cpus", self.default_cpus)

        result = {
            "session_id": session_id,
            "status": "creating",
            "vm_name": f"cyberx_vm_{session_id[:8]}",
            "template": template_name,
            "error": None,
        }

        # Create VM directory
        vm_dir = self.vm_base_path / session_id
        try:
            vm_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Failed to create VM directory: {e}"
            return result

        # Find template
        template_path = self.template_path / "output" / "vm" / f"{template_name}.qcow2"
        if not template_path.exists():
            # Try finding any available template
            alt_template = self.template_path / "output" / "vm" / "alphha-linux.qcow2"
            if alt_template.exists():
                template_path = alt_template
            else:
                result["status"] = "failed"
                result["error"] = f"Template not found: {template_name}"
                return result

        # Create overlay disk (copy-on-write)
        vm_disk = vm_dir / f"{result['vm_name']}.qcow2"
        try:
            stdout, stderr, returncode = await self._run_command(
                "qemu-img", "create",
                "-f", "qcow2",
                "-b", str(template_path),
                "-F", "qcow2",
                str(vm_disk)
            )
            if returncode != 0:
                result["status"] = "failed"
                result["error"] = f"Failed to create disk: {stderr}"
                return result
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Failed to create disk: {e}"
            return result

        result["disk_path"] = str(vm_disk)
        result["status"] = "created"

        return result

    async def start_vm(
        self,
        session_id: str,
        user_id: str,
        vm_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Start a VM for a lab session."""

        result = {
            "session_id": session_id,
            "status": "starting",
            "vm_info": {},
            "access_info": {},
            "error": None,
        }

        # Check QEMU availability
        if not await self.check_qemu_available():
            result["status"] = "failed"
            result["error"] = "QEMU not available on this system"
            return result

        # Check KVM availability
        use_kvm = await self.check_kvm_available()

        # Get VM configuration
        template = vm_spec.get("template", "alphha-linux")
        memory = vm_spec.get("memory", self.default_memory)
        cpus = vm_spec.get("cpus", self.default_cpus)
        ssh_port = vm_spec.get("ssh_port", 2222 + hash(session_id) % 1000)
        vnc_port = vm_spec.get("vnc_port", 5900 + hash(session_id) % 100)

        # Create VM from template
        vm_result = await self.create_vm_from_template(session_id, template, vm_spec)
        if vm_result["status"] == "failed":
            return vm_result

        vm_name = vm_result["vm_name"]
        disk_path = vm_result["disk_path"]

        # Build QEMU command
        qemu_cmd = [
            "qemu-system-x86_64",
            "-name", vm_name,
            "-m", memory,
            "-smp", str(cpus),
            "-drive", f"file={disk_path},if=virtio,format=qcow2",
            "-netdev", f"user,id=net0,hostfwd=tcp::{ssh_port}-:22",
            "-device", "virtio-net-pci,netdev=net0",
            "-vnc", f":{vnc_port - 5900}",
            "-daemonize",
            "-pidfile", f"{self.vm_base_path}/{session_id}/{vm_name}.pid",
        ]

        # Add KVM acceleration if available
        if use_kvm:
            qemu_cmd.extend(["-enable-kvm", "-cpu", "host"])
        else:
            qemu_cmd.extend(["-cpu", "qemu64"])

        # Add UEFI if available
        ovmf_path = "/usr/share/OVMF/OVMF_CODE.fd"
        if os.path.exists(ovmf_path):
            qemu_cmd.extend(["-bios", ovmf_path])

        # Start VM
        try:
            stdout, stderr, returncode = await self._run_command(*qemu_cmd, timeout=30)
            if returncode != 0:
                result["status"] = "failed"
                result["error"] = f"Failed to start VM: {stderr}"
                return result
        except Exception as e:
            result["status"] = "failed"
            result["error"] = f"Failed to start VM: {e}"
            return result

        # Store session info
        self.active_vms[session_id] = {
            "user_id": user_id,
            "vm_name": vm_name,
            "disk_path": disk_path,
            "pid_file": f"{self.vm_base_path}/{session_id}/{vm_name}.pid",
            "ssh_port": ssh_port,
            "vnc_port": vnc_port,
            "started_at": utcnow(),
            "expires_at": utcnow() + timedelta(minutes=settings.LAB_TIMEOUT_MINUTES),
        }

        result["status"] = "running"
        result["vm_info"] = {
            "name": vm_name,
            "memory": memory,
            "cpus": cpus,
            "kvm_enabled": use_kvm,
        }
        result["access_info"] = {
            "ssh": f"ssh -p {ssh_port} alphha@localhost",
            "ssh_port": ssh_port,
            "vnc_port": vnc_port,
            "username": "alphha",
            "password": "alphha",
        }
        result["expires_at"] = self.active_vms[session_id]["expires_at"].isoformat()

        logger.info(f"VM started: {vm_name}", session_id=session_id, ssh_port=ssh_port)

        return result

    async def stop_vm(self, session_id: str) -> bool:
        """Stop a VM and cleanup resources."""
        session = self.active_vms.get(session_id)

        if not session:
            logger.warning(f"VM session not found: {session_id}")
            return False

        try:
            # Read PID and kill process
            pid_file = session.get("pid_file")
            if pid_file and os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Try graceful shutdown first
                await self._run_command("kill", "-TERM", str(pid))
                await asyncio.sleep(2)

                # Force kill if still running
                await self._run_command("kill", "-9", str(pid))

            # Cleanup VM directory
            vm_dir = self.vm_base_path / session_id
            if vm_dir.exists():
                shutil.rmtree(vm_dir, ignore_errors=True)

            # Remove from active VMs
            del self.active_vms[session_id]

            logger.info(f"VM stopped: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping VM: {e}")
            return False

    async def get_vm_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a VM."""
        session = self.active_vms.get(session_id)

        if not session:
            return {"status": "not_found", "session_id": session_id}

        # Check if VM is still running
        pid_file = session.get("pid_file")
        is_running = False

        if pid_file and os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process exists
                os.kill(pid, 0)
                is_running = True
            except (OSError, ValueError):
                is_running = False

        is_expired = utcnow() > session["expires_at"]

        return {
            "session_id": session_id,
            "status": "expired" if is_expired else ("running" if is_running else "stopped"),
            "vm_name": session["vm_name"],
            "started_at": session["started_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat(),
            "ssh_port": session["ssh_port"],
            "vnc_port": session["vnc_port"],
        }

    async def cleanup_expired_vms(self) -> int:
        """Cleanup all expired VMs."""
        cleaned = 0
        now = utcnow()

        expired_sessions = [
            sid for sid, session in self.active_vms.items()
            if now > session["expires_at"]
        ]

        for session_id in expired_sessions:
            if await self.stop_vm(session_id):
                cleaned += 1

        if cleaned:
            logger.info(f"Cleaned up {cleaned} expired VMs")

        return cleaned

    async def list_active_vms(self) -> List[Dict[str, Any]]:
        """List all active VM sessions."""
        vms = []
        for session_id, session in self.active_vms.items():
            vms.append({
                "session_id": session_id,
                "user_id": session["user_id"],
                "vm_name": session["vm_name"],
                "started_at": session["started_at"].isoformat(),
                "expires_at": session["expires_at"].isoformat(),
                "ssh_port": session["ssh_port"],
            })
        return vms


# Singleton instance
vm_manager = VMManager()
