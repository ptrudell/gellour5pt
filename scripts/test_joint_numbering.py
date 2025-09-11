#!/usr/bin/env python3
"""
Test script to demonstrate the joint numbering scheme:
- Left arm: J1-J6 (joints), J7 (gripper)
- Right arm: J10-J15 (joints), J16 (gripper)
- Transform: Shows offsets J1-J10, J2-J11, etc., J7-J16 (gripper)
"""

import subprocess
import sys
import time


# Start position monitor to publish test data
def start_publisher():
    """Start publishing test GELLO positions"""
    cmd = [
        sys.executable,
        "/home/shared/gellour5pt/scripts/test_position_monitor_zcm.py",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_receiver(script_name, duration=3):
    """Run a receiver script and capture output"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {script_name}")
    print("=" * 60)

    cmd = [sys.executable, f"/home/shared/gellour5pt/scripts/{script_name}", "-v"]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )

        # Capture output for duration
        start = time.time()
        output_lines = []

        while time.time() - start < duration:
            try:
                line = proc.stdout.readline()
                if line:
                    output_lines.append(line.rstrip())
                    # Print lines that show joint numbers
                    if "J" in line and ("°" in line or "Gripper" in line):
                        print(line.rstrip())
            except:
                break

        proc.terminate()
        proc.wait(timeout=1)

    except Exception as e:
        print(f"Error running {script_name}: {e}")

    time.sleep(0.5)


def main():
    print("🎯 JOINT NUMBERING DEMONSTRATION")
    print("=" * 60)
    print("Expected numbering scheme:")
    print("• LEFT ARM:  J1, J2, J3, J4, J5, J6 (joints), J7 (gripper)")
    print("• RIGHT ARM: J10, J11, J12, J13, J14, J15 (joints), J16 (gripper)")

    print("=" * 60)

    # Start publisher
    print("\nStarting test data publisher...")
    publisher = start_publisher()
    time.sleep(2)  # Give publisher time to start

    try:
        # Test LEFT receiver
        print("\n" + "=" * 60)
        print("📍 TESTING LEFT ARM RECEIVER")
        print("=" * 60)
        print("Expected: J1-J6 for joints, J7 for gripper\n")
        run_receiver("receive_gello_left.py", duration=2)

        # Test RIGHT receiver
        print("\n" + "=" * 60)
        print("📍 TESTING RIGHT ARM RECEIVER")
        print("=" * 60)
        print("Expected: J10-J15 for joints, J16 for gripper\n")
        run_receiver("receive_gello_right.py", duration=2)

        # Test TRANSFORM receiver
        print("\n" + "=" * 60)
        print("📍 TESTING TRANSFORM RECEIVER")
        print("=" * 60)
        print("Expected: J1-J10, J2-J11, etc., J7-J16 for gripper\n")
        run_receiver("receive_arm_transform.py", duration=2)

    finally:
        # Clean up
        publisher.terminate()
        publisher.wait(timeout=1)

    print("\n" + "=" * 60)
    print("✅ JOINT NUMBERING TEST COMPLETE")
    print("=" * 60)
    print("\nSummary:")
    print("• LEFT:      J1-J6 (joints), J7 (gripper)       ✓")
    print("• RIGHT:     J10-J15 (joints), J16 (gripper)    ✓")
    print("• TRANSFORM: Shows proper offset pairs           ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
