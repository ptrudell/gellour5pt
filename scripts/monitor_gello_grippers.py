#!/usr/bin/env python3
"""
Monitor GELLO gripper positions in real-time to help find optimal thresholds.
Shows current position and whether it would trigger open/closed commands.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def monitor_grippers(duration: int = 30, update_rate: float = 0.1):
    """Monitor both GELLO grippers and show their positions."""

    # Configuration
    left_config = {
        "ur_host": "192.168.1.211",
        "dxl_port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        "dxl_ids": [1, 2, 3, 4, 5, 6, 7],
        "dxl_baudrate": 1000000,
    }

    right_config = {
        "ur_host": "192.168.1.210",
        "dxl_port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        "dxl_ids": [10, 11, 12, 13, 14, 15, 16],
        "dxl_baudrate": 1000000,
    }

    # Current thresholds from the script
    LEFT_THRESHOLD = 2.97
    RIGHT_THRESHOLD = 4.60

    robots = {}

    # Connect to robots
    for side, config in [("LEFT", left_config), ("RIGHT", right_config)]:
        try:
            robot = URDynamixelRobot(
                ur_host=config["ur_host"],
                dxl_port=config["dxl_port"],
                dxl_ids=config["dxl_ids"],
                dxl_signs=[1, 1, -1, 1, 1, 1, 1],  # Standard UR signs
                dxl_offsets_deg=[
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ],  # No offsets needed for monitoring
                dxl_baudrate=config["dxl_baudrate"],
                control_frequency=125,
            )

            ur_ok, dxl_ok = robot.connect()

            if dxl_ok:
                robots[side] = robot
                print(f"✓ Connected to {side} GELLO")
            else:
                print(f"✗ Could not connect to {side} DXL servos")

        except Exception as e:
            print(f"✗ Error connecting to {side}: {e}")

    if not robots:
        print("No robots connected. Exiting.")
        return

    print("\n" + "=" * 70)
    print("GELLO GRIPPER MONITOR")
    print("=" * 70)
    print("Press Ctrl+C to stop\n")
    print("Current thresholds:")
    print(f"  LEFT:  {LEFT_THRESHOLD:.3f} rad")
    print(f"  RIGHT: {RIGHT_THRESHOLD:.3f} rad")
    print("\n" + "-" * 70)

    # Track statistics
    stats = {
        "LEFT": {"min": float("inf"), "max": float("-inf"), "readings": []},
        "RIGHT": {"min": float("inf"), "max": float("-inf"), "readings": []},
    }

    try:
        start_time = time.time()
        while time.time() - start_time < duration:
            output = []

            for side, robot in robots.items():
                positions = robot.dxl.read_positions()

                if positions and len(positions) > 6:
                    gripper_pos = positions[6]

                    # Update statistics
                    if gripper_pos < stats[side]["min"]:
                        stats[side]["min"] = gripper_pos
                    if gripper_pos > stats[side]["max"]:
                        stats[side]["max"] = gripper_pos
                    stats[side]["readings"].append(gripper_pos)

                    # Determine state based on threshold
                    threshold = LEFT_THRESHOLD if side == "LEFT" else RIGHT_THRESHOLD
                    state = "CLOSED" if gripper_pos < threshold else "OPEN"

                    # Format output
                    output.append(
                        f"{side}: {gripper_pos:6.3f} rad ({np.degrees(gripper_pos):6.1f}°) → {state:6s}"
                    )

            # Print on same line
            if output:
                print("\r" + " | ".join(output), end="", flush=True)

            time.sleep(update_rate)

    except KeyboardInterrupt:
        pass

    # Print statistics
    print("\n\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)

    for side in ["LEFT", "RIGHT"]:
        if side in stats and stats[side]["readings"]:
            readings = stats[side]["readings"]
            min_val = stats[side]["min"]
            max_val = stats[side]["max"]
            mean_val = np.mean(readings)
            std_val = np.std(readings)

            print(f"\n{side} GRIPPER:")
            print(f"  Range: {min_val:.4f} to {max_val:.4f} rad")
            print(
                f"         ({np.degrees(min_val):.1f}° to {np.degrees(max_val):.1f}°)"
            )
            print(f"  Mean:  {mean_val:.4f} rad ({np.degrees(mean_val):.1f}°)")
            print(f"  Std:   {std_val:.4f} rad ({np.degrees(std_val):.1f}°)")

            # Suggest threshold
            suggested = (min_val + max_val) / 2
            current = LEFT_THRESHOLD if side == "LEFT" else RIGHT_THRESHOLD
            print(f"  Current threshold: {current:.4f} rad")
            print(f"  Suggested threshold: {suggested:.4f} rad")

            if abs(suggested - current) > 0.1:
                print(f"  ⚠️  Consider updating threshold to {suggested:.3f}")

    # Disconnect
    for robot in robots.values():
        robot.disconnect()

    print("\n" + "=" * 70)
    print("Done!")


def main():
    parser = argparse.ArgumentParser(description="Monitor GELLO gripper positions")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Monitoring duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--rate", type=float, default=0.1, help="Update rate in seconds (default: 0.1)"
    )
    args = parser.parse_args()

    monitor_grippers(args.duration, args.rate)


if __name__ == "__main__":
    main()
