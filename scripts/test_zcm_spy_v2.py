#!/usr/bin/env python3
"""
Test script to verify zcm-spy can see the GELLO position messages.
This script publishes test messages and provides instructions for using zcm-spy.
"""

import subprocess
import sys
import time


def main():
    print("=" * 70)
    print("ZCM-SPY COMPATIBILITY TEST")
    print("=" * 70)
    print("\nThis test will help verify that zcm-spy can see GELLO messages.\n")

    print("STEP 1: Starting test publisher")
    print("-" * 40)
    print("Running: python scripts/send_gello_test.py --rate 10")

    # Start the publisher in background
    publisher = subprocess.Popen(
        ["python", "scripts/send_gello_test.py", "--rate", "10"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)  # Give it time to start

    if publisher.poll() is not None:
        print("ERROR: Publisher failed to start!")
        stdout, stderr = publisher.communicate()
        print("STDOUT:", stdout.decode())
        print("STDERR:", stderr.decode())
        return 1

    print("✓ Publisher is running (PID: {})".format(publisher.pid))

    print("\nSTEP 2: Open zcm-spy")
    print("-" * 40)
    print("In another terminal, run ONE of these commands:")
    print()
    print("  Option A (GUI):")
    print("    zcm-spy")
    print()
    print("  Option B (Command line - left channel):")
    print("    zcm-spy --channel gello_positions_left --print")
    print()
    print("  Option C (Command line - right channel):")
    print("    zcm-spy --channel gello_positions_right --print")
    print()
    print("  Option D (Command line - all channels):")
    print("    zcm-spy --print-all")
    print()

    print("WHAT YOU SHOULD SEE IN ZCM-SPY:")
    print("-" * 40)
    print("✓ Channel: gello_positions_left")
    print("✓ Channel: gello_positions_right")
    print("✓ Type: gello_positions_t")
    print("✓ Message count incrementing")
    print("✓ When you click on a message:")
    print("    - timestamp (int64)")
    print("    - joint_positions[6] (double array)")
    print("    - gripper_position (double)")
    print("    - joint_velocities[6] (double array)")
    print("    - is_valid (boolean)")
    print("    - arm_side (string)")
    print()

    print("STEP 3: Test receivers (optional)")
    print("-" * 40)
    print("You can also test with the receiver scripts:")
    print()
    print("  Left arm receiver:")
    print("    python scripts/receive_gello_left_v2.py")
    print()
    print("  Right arm receiver:")
    print("    python scripts/receive_gello_right_v2.py")
    print()
    print("  Verbose mode (see all fields):")
    print("    python scripts/receive_gello_left_v2.py -v")
    print()

    print("=" * 70)
    print("Publisher is running. Press Ctrl+C to stop the test.")
    print("=" * 70)

    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
            # Check if publisher is still running
            if publisher.poll() is not None:
                print("\nPublisher stopped unexpectedly!")
                stdout, stderr = publisher.communicate()
                if stderr:
                    print("Error:", stderr.decode())
                break

    except KeyboardInterrupt:
        print("\n\nStopping test...")
        publisher.terminate()
        time.sleep(0.5)
        if publisher.poll() is None:
            publisher.kill()
        print("Test stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
