#!/usr/bin/env python3
"""
Debug script to test gripper command execution.
Tests the full path from script to UR5 gripper.
"""

import json
import os
import subprocess
import sys
import time


def test_dexgpt_command(side, position):
    """Test sending command via dexgpt script"""
    print(f"\n{'=' * 60}")
    print(f"Testing DEXGPT command for {side} gripper at position {position}")
    print(f"{'=' * 60}")

    dexgpt_path = os.path.expanduser("~/generalistai/dexgpt")
    script_path = os.path.join(dexgpt_path, "debug_tools", "send_gripper_cmd.py")

    # Check if script exists
    if not os.path.exists(script_path):
        print(f"✗ Script not found: {script_path}")
        print("  Looking for alternatives...")

        # Try to find the script
        possible_paths = [
            "~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py",
            "~/dexgpt/debug_tools/send_gripper_cmd.py",
            "~/gellour5pt/debug_tools/send_gripper_cmd.py",
        ]

        for path in possible_paths:
            full_path = os.path.expanduser(path)
            if os.path.exists(full_path):
                print(f"  ✓ Found at: {full_path}")
                script_path = full_path
                dexgpt_path = os.path.dirname(os.path.dirname(full_path))
                break
        else:
            print("  ✗ No gripper command script found!")
            return False
    else:
        print(f"✓ Script found: {script_path}")

    # Build command
    cmd = [
        "python",
        script_path,
        "-o",
        f"gripper_command_{side}",
        "--position",
        str(position),
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Working directory: {dexgpt_path}")

    # Execute command
    try:
        result = subprocess.run(
            cmd, cwd=dexgpt_path, capture_output=True, timeout=2.0, text=True
        )

        print(f"\nReturn code: {result.returncode}")

        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("✗ Command timed out!")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_json_file(side, position):
    """Test writing to JSON file directly"""
    print(f"\n{'=' * 60}")
    print(f"Testing JSON file write for {side} gripper")
    print(f"{'=' * 60}")

    command_file = f"/tmp/gripper_command_{side}.json"
    command_data = {
        "timestamp": time.time(),
        "position": position,
        "side": side,
        "source": "debug_script",
    }

    try:
        with open(command_file, "w") as f:
            json.dump(command_data, f, indent=2)

        print(f"✓ Wrote to {command_file}")
        print(f"  Content: {json.dumps(command_data, indent=2)}")

        # Check if file exists and is readable
        if os.path.exists(command_file):
            with open(command_file, "r") as f:
                read_data = json.load(f)
            print("✓ Verified file is readable")
            print(f"  Read back: {read_data}")
            return True
        else:
            print("✗ File not created!")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def check_environment():
    """Check environment and paths"""
    print(f"\n{'=' * 60}")
    print("ENVIRONMENT CHECK")
    print(f"{'=' * 60}")

    print(f"Current directory: {os.getcwd()}")
    print(f"Python: {sys.executable}")
    print(f"Python version: {sys.version}")

    # Check for dexgpt directory
    dexgpt_paths = [
        "~/generalistai/dexgpt",
        "~/dexgpt",
        "../dexgpt",
    ]

    print("\nLooking for dexgpt directory:")
    for path in dexgpt_paths:
        full_path = os.path.expanduser(path)
        if os.path.exists(full_path):
            print(f"  ✓ Found: {full_path}")

            # Check for debug_tools
            debug_tools = os.path.join(full_path, "debug_tools")
            if os.path.exists(debug_tools):
                print("    ✓ Has debug_tools/")

                # List contents
                try:
                    files = os.listdir(debug_tools)
                    print(f"    Contents: {files[:5]}...")  # Show first 5 files
                except:
                    pass
        else:
            print(f"  ✗ Not found: {full_path}")

    # Check /tmp directory
    print("\n/tmp directory check:")
    tmp_files = [f for f in os.listdir("/tmp") if "gripper" in f.lower()]
    if tmp_files:
        print(f"  Gripper-related files: {tmp_files}")
    else:
        print("  No gripper files found")


def main():
    print("\n" + "=" * 70)
    print("GRIPPER COMMAND DEBUG TEST")
    print("=" * 70)

    # Check environment first
    check_environment()

    print("\n" + "=" * 70)
    print("TESTING GRIPPER COMMANDS")
    print("=" * 70)

    # Test positions
    test_cases = [
        ("left", -0.075, "CLOSED"),
        ("left", 0.25, "OPEN"),
        ("left", 0.088, "50% OPEN"),
        ("right", -0.075, "CLOSED"),
        ("right", 0.25, "OPEN"),
    ]

    for side, position, description in test_cases:
        print(f"\n{'=' * 70}")
        print(f"TEST: {side.upper()} gripper → {description} (position: {position})")
        print(f"{'=' * 70}")

        # Test JSON file method
        json_ok = test_json_file(side, position)

        # Test dexgpt command method
        cmd_ok = test_dexgpt_command(side, position)

        if json_ok and cmd_ok:
            print(f"\n✓ Both methods successful for {side} → {description}")
        elif json_ok:
            print(f"\n⚠ Only JSON method worked for {side} → {description}")
        elif cmd_ok:
            print(f"\n⚠ Only command method worked for {side} → {description}")
        else:
            print(f"\n✗ Both methods failed for {side} → {description}")

        time.sleep(1)  # Give time to observe

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nIf commands aren't reaching UR5:")
    print("1. Check if dexgpt script exists and is executable")
    print("2. Check if the UR5 gripper service is running")
    print("3. Check network connection to UR5")
    print("4. Check if external control is active on UR5")
    print("\nAlternative: Use direct RTDE/Dashboard commands instead of dexgpt")


if __name__ == "__main__":
    main()
