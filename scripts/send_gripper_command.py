#!/usr/bin/env python3
"""
Send gripper commands to UR robots via appropriate interface.

This script provides the interface for sending gripper commands
that the teleop system uses.

Usage:
    python scripts/send_gripper_command.py --side left --position -0.1  # Close left gripper
    python scripts/send_gripper_command.py --side left --position 0.25  # Open left gripper
    python scripts/send_gripper_command.py --side right --position -0.1  # Close right gripper
    python scripts/send_gripper_command.py --side right --position 0.25  # Open right gripper
"""

import argparse
import json
import sys
import time
from pathlib import Path


def send_gripper_command_via_topic(side: str, position: float):
    """Send gripper command via topic-based system (if available)."""
    topic_name = f"gripper_command_{side}"

    # This is a placeholder for your actual topic-based system
    # Replace with your actual implementation (e.g., ROS, ZMQ, etc.)
    print(f"[{topic_name}] Sending position: {position}")

    # If you have a specific command system, implement it here
    # For example, if using a file-based system:
    command_file = Path(f"/tmp/{topic_name}.json")
    command_data = {"timestamp": time.time(), "position": position, "side": side}

    with open(command_file, "w") as f:
        json.dump(command_data, f)

    return True


def send_gripper_command_via_rtde(host: str, position: float):
    """Send gripper command via UR RTDE interface."""
    try:
        # Import UR RTDE modules
        from rtde_control import RTDEControlInterface

        # Connect to robot
        rtde_c = RTDEControlInterface(host)

        # Map position to UR gripper range
        # UR typically uses 0-255 for gripper position
        # Our commands: -0.1 = closed, 0.25 = open
        if position < 0:
            # Closed position
            ur_position = 255  # Fully closed
        else:
            # Open position
            ur_position = 0  # Fully open

        # Send command (this depends on your specific gripper)
        # For Robotiq grippers, you might need to use Modbus
        # For UR built-in grippers, use digital outputs

        # Example using digital output (adjust pin as needed)
        gripper_pin = 0  # Adjust this for your setup
        rtde_c.setStandardDigitalOut(gripper_pin, ur_position > 127)

        print(f"[RTDE] Sent gripper position {ur_position} to {host}")

        # Disconnect
        rtde_c.disconnect()
        return True

    except Exception as e:
        print(f"[ERROR] Failed to send via RTDE: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Send gripper commands to UR robots")
    parser.add_argument(
        "--side",
        "-s",
        choices=["left", "right"],
        required=True,
        help="Which gripper to control (left or right)",
    )
    parser.add_argument(
        "--position",
        "-p",
        type=float,
        required=True,
        help="Gripper position (-0.1 for closed, 0.25 for open)",
    )
    parser.add_argument(
        "--method",
        "-m",
        choices=["topic", "rtde", "both"],
        default="topic",
        help="Communication method to use",
    )
    parser.add_argument(
        "--host", type=str, default=None, help="UR robot IP address (for RTDE method)"
    )

    args = parser.parse_args()

    # Validate position
    if args.position < -0.2 or args.position > 0.5:
        print(
            f"[WARNING] Position {args.position} is outside normal range (-0.1 to 0.25)"
        )

    # Determine robot host based on side if not provided
    if args.host is None:
        if args.side == "left":
            args.host = "192.168.1.211"  # Default left UR IP
        else:
            args.host = "192.168.1.210"  # Default right UR IP

    # Send command based on method
    success = False

    if args.method in ["topic", "both"]:
        success = send_gripper_command_via_topic(args.side, args.position)

    if args.method in ["rtde", "both"]:
        success = send_gripper_command_via_rtde(args.host, args.position) or success

    # Print result
    if success:
        state = "CLOSED" if args.position < 0 else "OPEN"
        print(
            f"✓ {args.side.upper()} gripper set to {state} (position: {args.position})"
        )
    else:
        print("✗ Failed to send gripper command")
        sys.exit(1)


if __name__ == "__main__":
    main()
