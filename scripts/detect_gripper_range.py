#!/usr/bin/env python3
"""
Detect actual gripper position ranges for proper calibration.
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

from hardware.ur_dynamixel_robot import URDynamixelRobot


def main():
    """Monitor gripper positions in real-time."""
    print("=" * 60)
    print("GRIPPER POSITION MONITOR")
    print("=" * 60)
    print("\nMonitoring gripper positions...")
    print("Move the GELLO grippers to see their position values")
    print("Press Ctrl+C to stop\n")

    # Load config
    with open("configs/teleop_dual_ur5.yaml") as f:
        config = yaml.safe_load(f)

    # Create robots
    left_config = config["left_robot"]
    right_config = config["right_robot"]

    left_robot = URDynamixelRobot(
        ur_host=left_config["ur_host"],
        dxl_port=left_config["dxl_port"],
        dxl_ids=left_config["dxl_ids"],
        dxl_signs=left_config["dxl_signs"],
        dxl_offsets_deg=left_config["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    right_robot = URDynamixelRobot(
        ur_host=right_config["ur_host"],
        dxl_port=right_config["dxl_port"],
        dxl_ids=right_config["dxl_ids"],
        dxl_signs=right_config["dxl_signs"],
        dxl_offsets_deg=right_config["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    # Connect
    left_ur, left_dxl = left_robot.connect()
    right_ur, right_dxl = right_robot.connect()

    if not (left_dxl or right_dxl):
        print("No DXL connections available!")
        return 1

    # Track min/max values
    left_min = float("inf")
    left_max = float("-inf")
    right_min = float("inf")
    right_max = float("-inf")

    print("Format: LEFT: position (min-max) | RIGHT: position (min-max)")
    print("-" * 60)

    try:
        while True:
            output = []

            # Read LEFT gripper
            if left_dxl:
                positions = left_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    left_pos = positions[6]
                    left_min = min(left_min, left_pos)
                    left_max = max(left_max, left_pos)
                    output.append(
                        f"LEFT: {left_pos:6.3f} ({left_min:.3f}-{left_max:.3f})"
                    )
                else:
                    output.append("LEFT: N/A")

            # Read RIGHT gripper
            if right_dxl:
                positions = right_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    right_pos = positions[6]
                    right_min = min(right_min, right_pos)
                    right_max = max(right_max, right_pos)
                    output.append(
                        f"RIGHT: {right_pos:6.3f} ({right_min:.3f}-{right_max:.3f})"
                    )
                else:
                    output.append("RIGHT: N/A")

            # Print on same line
            print("\r" + " | ".join(output) + "  ", end="", flush=True)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("GRIPPER CALIBRATION SUMMARY")
        print("=" * 60)

        if left_min != float("inf"):
            left_threshold = (left_min + left_max) / 2
            print("\nLEFT Gripper:")
            print(f"  Range: {left_min:.3f} to {left_max:.3f} rad")
            print(f"  Threshold: {left_threshold:.3f} rad")
            print("  Update line ~874 in streamdeck_pedal_watch.py:")
            print(f"    gripper_threshold = {left_threshold:.2f}")

        if right_min != float("inf"):
            right_threshold = (right_min + right_max) / 2
            print("\nRIGHT Gripper:")
            print(f"  Range: {right_min:.3f} to {right_max:.3f} rad")
            print(f"  Threshold: {right_threshold:.3f} rad")
            print("  Update line ~959 in streamdeck_pedal_watch.py:")
            print(f"    gripper_threshold = {right_threshold:.2f}")

        print("\n" + "=" * 60)

    # Cleanup
    left_robot.disconnect()
    right_robot.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
