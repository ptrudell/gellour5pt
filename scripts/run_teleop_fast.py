#!/usr/bin/env python3
"""
Ultra-fast teleop launcher - minimal startup time
Skips all non-essential checks and connections
"""

import os
import sys
from pathlib import Path

# Suppress verbose output
os.environ["PYTHONUNBUFFERED"] = "1"


def main():
    """Ultra-fast launcher with minimal overhead"""
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent))

    # Import minimal required modules
    import time

    import yaml

    from hardware.ur_dynamixel_robot import DynamixelDriver

    print("⚡ FAST TELEOP - Starting in 1 second...")

    # Load config directly (could be used for parameters if needed)
    config_path = here.parent / "configs" / "teleop_dual_ur5.yaml"
    with open(config_path) as f:
        _ = yaml.safe_load(f)  # Config loaded but using defaults for speed

    # Connect to DXL only (skip UR for speed)
    left_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        baudrate=1000000,
        ids=[1, 2, 3, 4, 5, 6, 16],  # 6 joints + gripper
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    right_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        baudrate=1000000,
        ids=[1, 2, 3, 4, 5, 6, 16],  # 6 joints + gripper
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    # Quick connect
    left_ok = left_dxl.connect()
    right_ok = right_dxl.connect()

    if not (left_ok or right_ok):
        print("❌ No DXL connections!")
        return 1

    print(f"✅ Connected: LEFT={left_ok}, RIGHT={right_ok}")
    print("📍 Reading GELLO positions (Ctrl+C to exit)...")

    # Simple read loop
    try:
        while True:
            # Read positions
            left_pos = left_dxl.read_positions() if left_ok else None
            right_pos = right_dxl.read_positions() if right_ok else None

            # Display in compact format
            if left_pos is not None:
                gripper_l = left_pos[6] if len(left_pos) > 6 else 0
                print(
                    f"L: [{', '.join([f'{p:5.2f}' for p in left_pos[:6]])}] G:{gripper_l:5.2f}",
                    end="  ",
                )

            if right_pos is not None:
                gripper_r = right_pos[6] if len(right_pos) > 6 else 0
                print(
                    f"R: [{', '.join([f'{p:5.2f}' for p in right_pos[:6]])}] G:{gripper_r:5.2f}",
                    end="\r",
                )

            time.sleep(0.05)  # 20Hz update

    except KeyboardInterrupt:
        print("\n✅ Stopped")

    # Cleanup
    left_dxl.disconnect()
    right_dxl.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
