#!/usr/bin/env python3
"""
Test script to verify gripper commands work with the dexgpt script.
"""

import os
import subprocess
import time


def test_gripper_command(side: str, position: float):
    """Test sending a gripper command."""

    # Path to the dexgpt gripper command script
    dexgpt_path = os.path.expanduser("~/generalistai/dexgpt")
    script_path = os.path.join(dexgpt_path, "debug_tools", "send_gripper_cmd.py")

    # Build the command
    cmd = [
        "python",
        script_path,
        "-o",
        f"gripper_command_{side}",
        "--position",
        str(position),
    ]

    print(f"\n{'=' * 60}")
    print(f"Testing {side.upper()} gripper command")
    print(f"Position: {position} ({'CLOSED' if position < 0 else 'OPEN'})")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        # Execute the command
        result = subprocess.run(
            cmd, cwd=dexgpt_path, capture_output=True, timeout=2.0, text=True
        )

        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        if result.stderr:
            print(f"Error: {result.stderr.strip()}")

        if result.returncode == 0:
            print("✅ Command executed successfully")
        else:
            print("⚠️ Command returned non-zero exit code")

    except subprocess.TimeoutExpired:
        print("❌ Command timed out after 2 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    print("\n" + "=" * 60)
    print("GRIPPER COMMAND TEST")
    print("=" * 60)
    print("\nThis test will send gripper commands using the dexgpt script.")
    print("Watch your robot grippers to see if they respond.")

    input("\nPress Enter to test LEFT gripper CLOSE (-0.1)...")
    test_gripper_command("left", -0.1)

    time.sleep(1)

    input("\nPress Enter to test LEFT gripper OPEN (0.25)...")
    test_gripper_command("left", 0.25)

    time.sleep(1)

    input("\nPress Enter to test RIGHT gripper CLOSE (-0.1)...")
    test_gripper_command("right", -0.1)

    time.sleep(1)

    input("\nPress Enter to test RIGHT gripper OPEN (0.25)...")
    test_gripper_command("right", 0.25)

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nIf the grippers responded correctly, the integration is working!")
    print("If not, check the dexgpt script output for errors.")


if __name__ == "__main__":
    main()
