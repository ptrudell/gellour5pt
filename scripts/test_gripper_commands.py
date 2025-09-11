#!/usr/bin/env python3
"""
Test gripper commands directly using the dexgpt script.
"""

import argparse
import os
import subprocess
import time


def send_gripper_command(side: str, position: float, verbose: bool = True):
    """Send a gripper command using the dexgpt script."""
    try:
        dexgpt_path = os.path.expanduser("~/generalistai/dexgpt")
        script_path = os.path.join(dexgpt_path, "debug_tools", "send_gripper_cmd.py")

        cmd = [
            "python",
            script_path,
            "-o",
            f"gripper_command_{side}",
            "--position",
            str(position),
        ]

        if verbose:
            print(f"Sending {side} gripper to position {position}...")
            print(f"Command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, cwd=dexgpt_path, capture_output=True, timeout=2.0, check=False
        )

        if result.returncode == 0:
            if verbose:
                print(f"✓ {side} gripper command sent successfully")
            return True
        else:
            print(f"✗ {side} gripper command failed:")
            if result.stderr:
                print(f"  Error: {result.stderr.decode()}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ {side} gripper command timed out")
        return False
    except Exception as e:
        print(f"✗ Error sending {side} gripper command: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test gripper commands")
    parser.add_argument(
        "--side",
        choices=["left", "right", "both"],
        default="both",
        help="Which gripper(s) to test",
    )
    parser.add_argument(
        "--position",
        type=float,
        default=None,
        help="Custom position to test (overrides default test sequence)",
    )
    parser.add_argument(
        "--cycle",
        action="store_true",
        help="Continuously cycle between open and closed",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("GRIPPER COMMAND TEST")
    print("=" * 60)
    print("\nDefault positions:")
    print("  CLOSED: -0.075")
    print("  OPEN:   0.25")
    print("=" * 60 + "\n")

    sides = ["left", "right"] if args.side == "both" else [args.side]

    if args.position is not None:
        # Test custom position
        for side in sides:
            send_gripper_command(side, args.position)

    elif args.cycle:
        # Cycle between open and closed
        print("Cycling grippers (Ctrl+C to stop)...")
        try:
            while True:
                # Close grippers
                print("\n--- CLOSING GRIPPERS ---")
                for side in sides:
                    send_gripper_command(side, -0.075)
                time.sleep(2)

                # Open grippers
                print("\n--- OPENING GRIPPERS ---")
                for side in sides:
                    send_gripper_command(side, 0.25)
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n\nStopped cycling")

    else:
        # Default test sequence
        print("Testing gripper commands...\n")

        # Test close
        print("--- CLOSING GRIPPERS ---")
        for side in sides:
            send_gripper_command(side, -0.075)
            time.sleep(0.5)

        print("\nWaiting 2 seconds...")
        time.sleep(2)

        # Test open
        print("\n--- OPENING GRIPPERS ---")
        for side in sides:
            send_gripper_command(side, 0.25)
            time.sleep(0.5)

        print("\nWaiting 2 seconds...")
        time.sleep(2)

        # Test close again
        print("\n--- CLOSING GRIPPERS AGAIN ---")
        for side in sides:
            send_gripper_command(side, -0.075)
            time.sleep(0.5)

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
