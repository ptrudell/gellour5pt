#!/usr/bin/env python3
"""
Simple GELLO test - just read and display positions
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


def main():
    print("\n" + "=" * 60)
    print("SIMPLE GELLO TEST")
    print("=" * 60)

    # Connect to GELLO arms
    left_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        baudrate=1000000,
        ids=[1, 2, 3, 4, 5, 6, 7],  # 6 joints + gripper
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    right_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        baudrate=1000000,
        ids=[10, 11, 12, 13, 14, 15, 16],  # 6 joints + gripper
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    # Connect
    left_ok = left_dxl.connect()
    right_ok = right_dxl.connect()

    if not (left_ok or right_ok):
        print("❌ No connections!")
        return 1

    print(f"\n✅ Connected: LEFT={left_ok}, RIGHT={right_ok}")
    print("\nReading GELLO positions (Ctrl+C to stop)...")
    print("-" * 60)

    try:
        while True:
            # Read positions
            if left_ok:
                left_pos = left_dxl.read_positions()
                if left_pos is not None and len(left_pos) == 7:
                    print(
                        f"LEFT:  J1-6: [{', '.join([f'{p:6.3f}' for p in left_pos[:6]])}]  Gripper: {left_pos[6]:6.3f}"
                    )

            if right_ok:
                right_pos = right_dxl.read_positions()
                if right_pos is not None and len(right_pos) == 7:
                    print(
                        f"RIGHT: J1-6: [{', '.join([f'{p:6.3f}' for p in right_pos[:6]])}]  Gripper: {right_pos[6]:6.3f}"
                    )

            print("-" * 60)
            time.sleep(0.5)  # 2Hz update

    except KeyboardInterrupt:
        print("\n✅ Test complete!")

    # Cleanup
    if left_ok:
        left_dxl.disconnect()
    if right_ok:
        right_dxl.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
