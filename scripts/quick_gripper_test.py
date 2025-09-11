#!/usr/bin/env python3
"""
Quick test to find GELLO gripper open/closed positions
"""

import sys
import time
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def test_gello_grippers():
    """Quick test to find gripper positions"""

    print("\n" + "=" * 60)
    print("QUICK GELLO GRIPPER POSITION TEST")
    print("=" * 60)
    print("\nTrying to connect to GELLO arms...")

    # Left GELLO configuration
    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Right GELLO configuration
    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Try to connect
    print("\nConnecting to LEFT GELLO...")
    left_ur_ok, left_dxl_ok = left_robot.connect()

    print("Connecting to RIGHT GELLO...")
    right_ur_ok, right_dxl_ok = right_robot.connect()

    print("\n" + "-" * 60)
    print("CONNECTION STATUS:")
    print(f"LEFT:  DXL={'✓' if left_dxl_ok else '✗'}")
    print(f"RIGHT: DXL={'✓' if right_dxl_ok else '✗'}")
    print("-" * 60)

    if not (left_dxl_ok or right_dxl_ok):
        print("\n✗ No GELLO arms connected. Check connections and try again.")
        return

    print("\n📋 INSTRUCTIONS:")
    print("1. SQUEEZE the gripper CLOSED and hold for 2 seconds")
    print("2. RELEASE the gripper OPEN and hold for 2 seconds")
    print("3. Press Ctrl+C when done")
    print("\n" + "-" * 60)

    # Track min/max for each side
    left_min, left_max = float("inf"), float("-inf")
    right_min, right_max = float("inf"), float("-inf")

    try:
        print("\nMonitoring gripper positions...\n")

        while True:
            output = []

            # Read LEFT gripper
            if left_dxl_ok:
                positions = left_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    gripper_pos = positions[6]
                    if gripper_pos < left_min:
                        left_min = gripper_pos
                        print(
                            f"LEFT  NEW MIN: {left_min:.3f} rad ({np.degrees(left_min):.1f}°)"
                        )
                    if gripper_pos > left_max:
                        left_max = gripper_pos
                        print(
                            f"LEFT  NEW MAX: {left_max:.3f} rad ({np.degrees(left_max):.1f}°)"
                        )
                    output.append(f"L:{gripper_pos:.3f}")

            # Read RIGHT gripper
            if right_dxl_ok:
                positions = right_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    gripper_pos = positions[6]
                    if gripper_pos < right_min:
                        right_min = gripper_pos
                        print(
                            f"RIGHT NEW MIN: {right_min:.3f} rad ({np.degrees(right_min):.1f}°)"
                        )
                    if gripper_pos > right_max:
                        right_max = gripper_pos
                        print(
                            f"RIGHT NEW MAX: {right_max:.3f} rad ({np.degrees(right_max):.1f}°)"
                        )
                    output.append(f"R:{gripper_pos:.3f}")

            # Show current values on same line
            if output:
                print(f"\rCurrent: {' | '.join(output)} rad", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nStopped monitoring.")

    # Calculate and display results
    print("\n" + "=" * 60)
    print("RESULTS - GELLO GRIPPER POSITIONS")
    print("=" * 60)

    if left_dxl_ok and left_min < float("inf"):
        left_threshold = (left_min + left_max) / 2
        print("\nLEFT GRIPPER (ID 7):")
        print(f"  CLOSED: {left_min:.3f} rad ({np.degrees(left_min):.1f}°)")
        print(f"  OPEN:   {left_max:.3f} rad ({np.degrees(left_max):.1f}°)")
        print(f"  Range:  {left_max - left_min:.3f} rad")
        print(f"  → Suggested threshold: {left_threshold:.3f} rad")
        print("  → Current in script: 2.97 rad")

    if right_dxl_ok and right_min < float("inf"):
        right_threshold = (right_min + right_max) / 2
        print("\nRIGHT GRIPPER (ID 16):")
        print(f"  CLOSED: {right_min:.3f} rad ({np.degrees(right_min):.1f}°)")
        print(f"  OPEN:   {right_max:.3f} rad ({np.degrees(right_max):.1f}°)")
        print(f"  Range:  {right_max - right_min:.3f} rad")
        print(f"  → Suggested threshold: {right_threshold:.3f} rad")
        print("  → Current in script: 4.60 rad")

    print("\n" + "=" * 60)
    print("UPDATE streamdeck_pedal_watch.py WITH THESE VALUES:")
    print("=" * 60)

    if left_dxl_ok and left_min < float("inf"):
        print(f"\nLine 887: gripper_threshold = {left_threshold:.2f}  # LEFT")
    if right_dxl_ok and right_min < float("inf"):
        print(f"Line 972: gripper_threshold = {right_threshold:.2f}  # RIGHT")

    print("\n" + "=" * 60)

    # Disconnect
    if left_dxl_ok:
        left_robot.disconnect()
    if right_dxl_ok:
        right_robot.disconnect()

    print("Done!")


if __name__ == "__main__":
    test_gello_grippers()
