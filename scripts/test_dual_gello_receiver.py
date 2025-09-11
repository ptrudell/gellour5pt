#!/usr/bin/env python3
"""
Test script for the dual GELLO receiver.
This script demonstrates how to use receive_gello_both.py

Usage:
    # Terminal 1: Start the receiver
    python scripts/receive_gello_both.py

    # Terminal 2: Send test messages
    python scripts/test_dual_gello_receiver.py
"""

import subprocess
import time


def main():
    print("=" * 60)
    print("DUAL GELLO RECEIVER TEST")
    print("=" * 60)
    print("\nThis test will demonstrate the dual GELLO receiver.")
    print("\nSTEP 1: Start the receiver in another terminal:")
    print("  python scripts/receive_gello_both.py")
    print("\nSTEP 2: Send test messages (starting in 3 seconds)...")

    time.sleep(3)

    print("\n" + "-" * 60)
    print("Starting test message sender...")
    print("-" * 60)

    # Start the test message sender
    try:
        # Run the send_gello_test script to send messages to both arms
        cmd = [
            "python",
            "scripts/send_gello_test.py",
            "--arm",
            "both",
            "--sin",
            "--rate",
            "20",
        ]
        print(f"\nRunning: {' '.join(cmd)}")
        print("\nSending sine wave patterns to both arms...")
        print("Press Ctrl+C to stop\n")

        process = subprocess.Popen(cmd)
        process.wait()

    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except FileNotFoundError:
        print("\nError: send_gello_test.py not found")
        print("Make sure you're in the gellour5pt directory")
    except Exception as e:
        print(f"\nError: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nThe receiver should have displayed:")
    print("  - Real-time joint positions for both arms")
    print("  - Update rates (Hz) for each arm")
    print("  - Offset calculations between left and right arms")
    print("  - Color-coded status indicators")

    print("\nDisplay Modes:")
    print("  --mode side_by_side : Shows both arms side by side (default)")
    print("  --mode stacked      : Shows arms stacked vertically")
    print("  --mode compact      : Compact single-line display")

    print("\nExample Commands:")
    print("  python scripts/receive_gello_both.py")
    print("  python scripts/receive_gello_both.py --mode compact")
    print("  python scripts/receive_gello_both.py --verbose")


if __name__ == "__main__":
    main()
