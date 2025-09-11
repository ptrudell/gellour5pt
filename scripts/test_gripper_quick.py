#!/usr/bin/env python3
"""
Quick gripper test - open and close both grippers
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


def quick_test():
    print("\n" + "=" * 60)
    print("QUICK GRIPPER TEST")
    print("=" * 60)

    # Gripper USB ports
    ports = {
        "left": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTA9DQQU-if00-port0",
        "right": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT9BTFWG-if00-port0",
    }

    # Command positions
    CLOSED = -0.075
    OPEN = 0.25

    for side, port in ports.items():
        print(f"\nTesting {side.upper()} gripper...")
        print(f"Port: {port}")

        try:
            # Connect
            dxl = DynamixelDriver(
                port=port, baudrate=1000000, ids=[1], signs=[1], offsets_deg=[0.0]
            )

            if dxl.connect():
                print(f"✓ Connected to {side.upper()} gripper")

                # Read current position
                pos = dxl.read_positions()
                if pos is not None:
                    print(f"  Current position: {pos[0]:.3f} rad")

                # Enable torque
                dxl.set_torque(True)
                print("  Torque ON")

                # Test movements
                print("  Closing gripper...")
                # For testing, move to a middle position
                # (we don't know the actual mapping yet)
                target = 0.0  # Middle position
                dxl.write_positions([target])
                time.sleep(1)

                print("  Opening gripper...")
                target = 1.0  # Different position
                dxl.write_positions([target])
                time.sleep(1)

                # Disable torque
                dxl.set_torque(False)
                print("  Torque OFF")

                dxl.disconnect()
                print(f"✓ {side.upper()} gripper test complete")
            else:
                print(f"✗ Failed to connect to {side.upper()} gripper")

        except Exception as e:
            print(f"✗ {side.upper()} gripper error: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nIf grippers moved, the connection is working!")
    print("Run 'python scripts/find_gripper_positions.py' to calibrate")


if __name__ == "__main__":
    quick_test()
