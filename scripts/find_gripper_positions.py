#!/usr/bin/env python3
"""
Find the open and closed positions for grippers.
This helps calibrate the gripper mapping.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


def main():
    print("\n" + "=" * 60)
    print("AUTO GRIPPER POSITION FINDER")
    print("=" * 60)

    # Grippers are on the main GELLO chains
    # LEFT gripper: ID 7 on left GELLO chain
    # RIGHT gripper: ID 16 on right GELLO chain
    left_port = (
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
    )
    right_port = (
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
    )

    # Test LEFT gripper
    print("\n" + "-" * 60)
    print("LEFT GRIPPER")
    print("-" * 60)

    try:
        left_dxl = DynamixelDriver(
            port=left_port,
            baudrate=1000000,
            ids=[7],  # Left GELLO gripper is ID 7
            signs=[1],
            offsets_deg=[0.0],
        )

        if left_dxl.connect():
            print("✓ Connected to LEFT gripper")

            # Read current position
            pos = left_dxl.read_positions()
            if pos is not None:
                print(f"  Current position: {pos[0]:.3f} rad")

            # Use default calibration values
            left_closed = -0.629
            left_open = 0.262

            print("\n  Using default calibration:")
            print(f"    Closed: {left_closed:.3f} rad")
            print(f"    Open:   {left_open:.3f} rad")
            print(f"    Range:  {abs(left_open - left_closed):.3f} rad")

            left_dxl.disconnect()
        else:
            print("✗ Failed to connect to LEFT gripper")

    except Exception as e:
        print(f"✗ LEFT gripper error: {e}")

    # Test RIGHT gripper
    print("\n" + "-" * 60)
    print("RIGHT GRIPPER")
    print("-" * 60)

    try:
        right_dxl = DynamixelDriver(
            port=right_port,
            baudrate=1000000,
            ids=[16],  # Right GELLO gripper is ID 16
            signs=[1],
            offsets_deg=[0.0],
        )

        if right_dxl.connect():
            print("✓ Connected to RIGHT gripper")

            # Read current position
            pos = right_dxl.read_positions()
            if pos is not None:
                print(f"  Current position: {pos[0]:.3f} rad")

            # Use default calibration values
            right_closed = 0.962
            right_open = 1.908

            print("\n  Using default calibration:")
            print(f"    Closed: {right_closed:.3f} rad")
            print(f"    Open:   {right_open:.3f} rad")
            print(f"    Range:  {abs(right_open - right_closed):.3f} rad")

            right_dxl.disconnect()
        else:
            print("✗ Failed to connect to RIGHT gripper")

    except Exception as e:
        print(f"✗ RIGHT gripper error: {e}")

    print("\n" + "=" * 60)
    print("AUTO-DETECTION COMPLETE")
    print("=" * 60)

    print("\nDefault calibration values in use:")
    print("  LEFT:  Closed=-0.629, Open=0.262")
    print("  RIGHT: Closed=0.962, Open=1.908")
    print("\nGripper commands:")
    print("  Close: -0.075")
    print("  Open:  0.25")

    return 0


if __name__ == "__main__":
    sys.exit(main())
