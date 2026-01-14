#!/usr/bin/env python3
"""Test script for VM lab terminal connection."""
import asyncio
import sys
from app.services.labs.lab_manager import lab_manager
from app.services.labs.terminal_service import TerminalService
import uuid


async def test_terminal_vm():
    print("=" * 60)
    print("Testing Terminal VM Lab (minimal preset)")
    print("=" * 60)

    session_id = str(uuid.uuid4())
    user_id = "test_user"

    print(f"\n1. Starting Alphha Linux lab with minimal preset...")
    print(f"   Session ID: {session_id[:8]}...")

    result = await lab_manager.start_alphha_linux_lab(
        session_id=session_id,
        user_id=user_id,
        preset="minimal"
    )

    status = result.get('status')
    ssh_port = result.get('ssh_port')
    preset = result.get('preset')
    error = result.get('error')

    print(f"\n2. Lab start result:")
    print(f"   Status: {status}")
    print(f"   SSH Port: {ssh_port}")
    print(f"   Preset: {preset}")

    if status != "running":
        print(f"   ERROR: Lab failed to start: {error}")
        return False

    # Get container name
    containers = result.get("containers", [])
    if not containers:
        print("   ERROR: No containers started")
        return False

    container_name = containers[0].get("name")
    print(f"   Container: {container_name}")

    # Test terminal connection
    print(f"\n3. Testing terminal connection...")
    terminal = TerminalService(container_name)
    started = await terminal.start()

    if not started:
        print("   ERROR: Failed to start terminal")
        await lab_manager.stop_lab_session(session_id)
        return False

    print(f"   Terminal started successfully!")
    print(f"   Detected shell: {terminal._detected_shell}")

    # Write a test command
    print(f"\n4. Sending test commands...")
    await terminal.write("echo 'Terminal connection works!' && whoami && uname -a\n")

    # Read output
    await asyncio.sleep(1)
    output_collected = []
    async for output in terminal.read():
        output_collected.append(output)
        if len(output_collected) > 5:
            break

    full_output = "".join(output_collected)
    print(f"\n5. Output received:")
    print("-" * 40)
    output_preview = full_output[:500] if len(full_output) > 500 else full_output
    print(output_preview)
    print("-" * 40)

    # Check if output contains expected content
    success = "Terminal connection works!" in full_output or "root" in full_output

    # Cleanup
    print(f"\n6. Cleaning up...")
    await terminal.stop()
    await lab_manager.stop_lab_session(session_id)

    if success:
        print("\n✅ Terminal VM Lab test PASSED!")
    else:
        print("\n❌ Terminal VM Lab test FAILED - no expected output")

    return success


async def test_desktop_vm():
    print("\n" + "=" * 60)
    print("Testing Desktop VM Lab")
    print("=" * 60)

    session_id = str(uuid.uuid4())
    user_id = "test_user"

    print(f"\n1. Starting Alphha Linux lab with desktop preset...")
    print(f"   Session ID: {session_id[:8]}...")

    result = await lab_manager.start_alphha_linux_lab(
        session_id=session_id,
        user_id=user_id,
        preset="desktop"
    )

    status = result.get('status')
    vnc_url = result.get('vnc_url')
    vnc_port = result.get('vnc_port')
    novnc_port = result.get('novnc_port')
    preset = result.get('preset')
    error = result.get('error')

    print(f"\n2. Lab start result:")
    print(f"   Status: {status}")
    print(f"   VNC URL: {vnc_url}")
    print(f"   VNC Port: {vnc_port}")
    print(f"   noVNC Port: {novnc_port}")
    print(f"   Preset: {preset}")

    if status != "running":
        print(f"   ERROR: Lab failed to start: {error}")
        return False

    # Get container info
    containers = result.get("containers", [])
    if containers:
        container_name = containers[0].get("name")
        print(f"   Container: {container_name}")

    print(f"\n3. Desktop VM started successfully!")
    print(f"   Access URL: {vnc_url}")
    print(f"   Password: toor")

    # Give it a moment to start
    print(f"\n4. Waiting for desktop to initialize...")
    await asyncio.sleep(5)

    # Cleanup
    print(f"\n5. Cleaning up...")
    await lab_manager.stop_lab_session(session_id)

    print("\n✅ Desktop VM Lab test PASSED!")
    return True


async def main():
    terminal_success = await test_terminal_vm()
    desktop_success = await test_desktop_vm()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Terminal VM: {'✅ PASSED' if terminal_success else '❌ FAILED'}")
    print(f"Desktop VM:  {'✅ PASSED' if desktop_success else '❌ FAILED'}")

    return terminal_success and desktop_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
