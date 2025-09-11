#!/usr/bin/env python3
"""
Start the dexgpt gripper drivers for both left and right grippers.
These drivers listen to ZCM channels and control the UR5 grippers.
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def check_gripper_driver():
    """Check if gripper driver is built"""
    dexgpt_path = Path.home() / "generalistai" / "dexgpt"
    driver_path = dexgpt_path / "build" / "gripper_driver_dynamixel"

    if not driver_path.exists():
        print(f"✗ Gripper driver not found: {driver_path}")
        print("\nTo build it:")
        print(f"  cd {dexgpt_path}")
        print("  mkdir -p build && cd build")
        print("  cmake .. && make gripper_driver_dynamixel")
        return False

    print(f"✓ Found gripper driver: {driver_path}")
    return True


def start_gripper_driver(side):
    """Start gripper driver for specified side"""
    dexgpt_path = Path.home() / "generalistai" / "dexgpt"

    # Change to dexgpt directory
    os.chdir(dexgpt_path)

    # Build command
    cmd = ["bash", "scripts/run_gripper.sh", f"--only-{side}", "--max-rate", "3"]

    print(f"\nStarting {side} gripper driver...")
    print(f"Command: {' '.join(cmd)}")

    try:
        # Start the driver in background
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(dexgpt_path),
        )

        # Give it time to start
        time.sleep(2)

        # Check if it's still running
        if proc.poll() is None:
            print(f"✓ {side.upper()} gripper driver started (PID: {proc.pid})")
            return proc
        else:
            stdout, stderr = proc.communicate()
            print(f"✗ {side.upper()} gripper driver failed to start")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")
            return None

    except Exception as e:
        print(f"✗ Failed to start {side} gripper driver: {e}")
        return None


def main():
    print("\n" + "=" * 60)
    print("STARTING DEXGPT GRIPPER DRIVERS")
    print("=" * 60)

    # Check if driver exists
    if not check_gripper_driver():
        return 1

    # Start both drivers
    left_proc = start_gripper_driver("left")
    right_proc = start_gripper_driver("right")

    if not left_proc and not right_proc:
        print("\n✗ No gripper drivers started!")
        return 1

    print("\n" + "=" * 60)
    print("GRIPPER DRIVERS RUNNING")
    print("=" * 60)

    if left_proc:
        print(f"LEFT:  PID {left_proc.pid}")
    if right_proc:
        print(f"RIGHT: PID {right_proc.pid}")

    print("\nThe drivers will listen to ZCM channels:")
    print("  - gripper_command_left")
    print("  - gripper_command_right")

    print("\nPress Ctrl+C to stop the drivers...")

    try:
        # Keep running
        while True:
            time.sleep(1)

            # Check if processes are still running
            if left_proc and left_proc.poll() is not None:
                print("\n⚠ LEFT gripper driver stopped!")
                left_proc = None
            if right_proc and right_proc.poll() is not None:
                print("\n⚠ RIGHT gripper driver stopped!")
                right_proc = None

            if not left_proc and not right_proc:
                print("\n✗ All drivers stopped!")
                break

    except KeyboardInterrupt:
        print("\n\nStopping gripper drivers...")

        # Terminate processes
        if left_proc:
            left_proc.terminate()
            left_proc.wait(timeout=5)
            print("✓ LEFT driver stopped")
        if right_proc:
            right_proc.terminate()
            right_proc.wait(timeout=5)
            print("✓ RIGHT driver stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
