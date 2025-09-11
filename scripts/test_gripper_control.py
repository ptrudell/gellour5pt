#!/usr/bin/env python3
"""
Test script for gripper control via serial communication.
Tests both left and right grippers with open/close commands.
"""

import os
import subprocess
import sys
import time


def test_gripper_command(side, position, description):
    """Test a single gripper command."""
    print(f"\n{description}")
    print(f"  Side: {side.upper()}")
    print(f"  Position: {position}")

    cmd = [
        "python3",
        "/home/shared/gellour5pt/debug_tools/send_gripper_cmd.py",
        "-o",
        f"gripper_command_{side}",
        "--position",
        str(position),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print("  ✓ Command sent successfully")
            if result.stdout:
                print(f"  Output: {result.stdout.strip()}")
        else:
            print(f"  ✗ Command failed with code {result.returncode}")
            if result.stderr:
                print(f"  Error: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("  ✗ Command timed out")
        return False
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        return False


def check_ports():
    """Check if the expected USB ports exist."""
    print("\nChecking USB ports...")
    ports = {"Right gripper": "/dev/ttyUSB1", "Left gripper": "/dev/ttyUSB3"}

    all_exist = True
    for name, port in ports.items():
        if os.path.exists(port):
            print(f"  ✓ {name}: {port} exists")
        else:
            print(f"  ✗ {name}: {port} NOT FOUND")
            all_exist = False

    # List all available USB ports
    print("\nAvailable USB serial ports:")
    os.system("ls -la /dev/ttyUSB* 2>/dev/null || echo '  No USB serial ports found'")

    return all_exist


def main():
    """Main test sequence."""
    print("=" * 60)
    print("GRIPPER CONTROL TEST")
    print("=" * 60)

    # Check ports first
    if not check_ports():
        print("\n⚠️  WARNING: Not all expected ports found")
        print("Continuing anyway for testing...")

    print("\n" + "=" * 60)
    print("TESTING GRIPPER COMMANDS")
    print("=" * 60)

    # Test sequence
    tests = [
        ("left", -0.075, "Testing LEFT gripper CLOSE"),
        ("right", -0.075, "Testing RIGHT gripper CLOSE"),
        ("left", 0.25, "Testing LEFT gripper OPEN"),
        ("right", 0.25, "Testing RIGHT gripper OPEN"),
    ]

    results = []
    for side, position, description in tests:
        success = test_gripper_command(side, position, description)
        results.append((description, success))
        time.sleep(1)  # Small delay between commands

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for desc, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{status}: {desc}")
        if not success:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nTroubleshooting:")
        print("1. Check USB connections: ls -la /dev/ttyUSB*")
        print("2. Verify baud rate: 4500000 bps")
        print("3. Check gripper power and connections")
        print("4. Ensure no other programs are using the serial ports")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
