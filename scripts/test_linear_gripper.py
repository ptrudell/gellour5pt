#!/usr/bin/env python3
"""
Test linear (sliding scale) gripper control from GELLO to UR5.
Maps the full range of GELLO positions to the full range of UR5 commands.
This allows partial opening/closing based on exact GELLO position.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def send_ur_gripper_command(side, position):
    """Send gripper command to UR5"""
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

        result = subprocess.run(
            cmd, cwd=dexgpt_path, capture_output=True, timeout=0.5, check=False
        )

        return result.returncode == 0
    except Exception:
        return False


def map_gripper_linear(gello_pos, gello_min, gello_max, ur_min=-0.075, ur_max=0.25):
    """Map GELLO position to UR5 command using linear interpolation.

    Args:
        gello_pos: Current GELLO position
        gello_min: GELLO closed position
        gello_max: GELLO open position
        ur_min: UR5 closed command (-0.075)
        ur_max: UR5 open command (0.25)

    Returns:
        UR5 command value
    """
    if abs(gello_max - gello_min) < 0.001:
        return ur_max  # Default to open

    # Normalize to 0-1
    normalized = (gello_pos - gello_min) / (gello_max - gello_min)
    normalized = max(0.0, min(1.0, normalized))  # Clamp

    # Map to UR5 range
    ur_cmd = ur_min + normalized * (ur_max - ur_min)

    return ur_cmd


def main():
    print("\n" + "=" * 60)
    print("LINEAR GRIPPER CONTROL TEST")
    print("=" * 60)
    print("\nThis tests smooth linear mapping of GELLO to UR5 grippers")
    print("Allows partial opening (25%, 50%, 75%, etc.)")
    print("=" * 60)

    # UR5 gripper command range
    UR_CLOSED = -0.075
    UR_OPEN = 0.25

    # Connect to GELLO arms (DXL only for gripper reading)
    print("\nConnecting to GELLO grippers (DXL only)...")

    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",  # Not used
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",  # Not used
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Connect ONLY to DXL (skip UR for speed)
    left_dxl_ok = left_robot.dxl.connect()
    right_dxl_ok = right_robot.dxl.connect()

    print(f"LEFT GELLO:  {'✓ Connected' if left_dxl_ok else '✗ Not connected'}")
    print(f"RIGHT GELLO: {'✓ Connected' if right_dxl_ok else '✗ Not connected'}")

    if not (left_dxl_ok or right_dxl_ok):
        print("\n✗ No GELLO grippers connected!")
        return

    # CALIBRATION - Find min/max for linear mapping
    print("\n" + "-" * 60)
    print("CALIBRATION FOR LINEAR MAPPING")
    print("-" * 60)
    print("SQUEEZE both grippers FULLY CLOSED and press ENTER...")
    input()

    left_min = None
    right_min = None

    if left_dxl_ok:
        pos = left_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            left_min = pos[6]
            print(f"LEFT CLOSED: {left_min:.3f} rad (UR5 → -0.075)")

    if right_dxl_ok:
        pos = right_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            right_min = pos[6]
            print(f"RIGHT CLOSED: {right_min:.3f} rad (UR5 → -0.075)")

    print("\nRELEASE both grippers FULLY OPEN and press ENTER...")
    input()

    left_max = None
    right_max = None

    if left_dxl_ok:
        pos = left_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            left_max = pos[6]
            print(f"LEFT OPEN: {left_max:.3f} rad (UR5 → 0.25)")

    if right_dxl_ok:
        pos = right_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            right_max = pos[6]
            print(f"RIGHT OPEN: {right_max:.3f} rad (UR5 → 0.25)")

    # Show mapping ranges
    print("\n" + "-" * 60)
    print("LINEAR MAPPING RANGES:")
    print("-" * 60)

    if left_min is not None and left_max is not None:
        print(
            f"LEFT:  GELLO [{left_min:.3f} → {left_max:.3f}] maps to UR5 [{UR_CLOSED} → {UR_OPEN}]"
        )
        print(f"       Range: {abs(left_max - left_min):.3f} rad")

    if right_min is not None and right_max is not None:
        print(
            f"RIGHT: GELLO [{right_min:.3f} → {right_max:.3f}] maps to UR5 [{UR_CLOSED} → {UR_OPEN}]"
        )
        print(f"       Range: {abs(right_max - right_min):.3f} rad")

    print("\n" + "-" * 60)
    print("TESTING LINEAR CONTROL")
    print("-" * 60)
    print("Move GELLO grippers to any position:")
    print("• Fully closed → 0% open")
    print("• Partially open → 25%, 50%, 75%...")
    print("• Fully open → 100% open")
    print("\nPress Ctrl+C to stop")
    print("-" * 60 + "\n")

    # Track last commands to avoid spam
    last_left_cmd = None
    last_right_cmd = None
    last_print_time = 0
    print_interval = 0.5  # Print status every 500ms

    try:
        while True:
            now = time.time()
            status = []

            # LEFT gripper with linear mapping
            if left_dxl_ok and left_min is not None and left_max is not None:
                pos = left_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    gello_pos = pos[6]

                    # Update min/max dynamically for better range
                    left_min = min(left_min, gello_pos)
                    left_max = max(left_max, gello_pos)

                    # Linear mapping
                    ur_cmd = map_gripper_linear(
                        gello_pos, left_min, left_max, UR_CLOSED, UR_OPEN
                    )

                    # Calculate percentage open
                    percentage = (ur_cmd - UR_CLOSED) / (UR_OPEN - UR_CLOSED) * 100

                    status.append(f"L: {percentage:.0f}%")

                    # Send command if changed enough
                    if last_left_cmd is None or abs(ur_cmd - last_left_cmd) > 0.01:
                        if send_ur_gripper_command("left", ur_cmd):
                            if now - last_print_time > 0.2:  # Rate limit prints
                                print(
                                    f"LEFT → {percentage:.0f}% open (GELLO: {gello_pos:.3f}, UR5: {ur_cmd:.3f})"
                                )
                                last_print_time = now
                        last_left_cmd = ur_cmd

            # RIGHT gripper with linear mapping
            if right_dxl_ok and right_min is not None and right_max is not None:
                pos = right_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    gello_pos = pos[6]

                    # Update min/max dynamically for better range
                    right_min = min(right_min, gello_pos)
                    right_max = max(right_max, gello_pos)

                    # Linear mapping
                    ur_cmd = map_gripper_linear(
                        gello_pos, right_min, right_max, UR_CLOSED, UR_OPEN
                    )

                    # Calculate percentage open
                    percentage = (ur_cmd - UR_CLOSED) / (UR_OPEN - UR_CLOSED) * 100

                    status.append(f"R: {percentage:.0f}%")

                    # Send command if changed enough
                    if last_right_cmd is None or abs(ur_cmd - last_right_cmd) > 0.01:
                        if send_ur_gripper_command("right", ur_cmd):
                            if now - last_print_time > 0.2:  # Rate limit prints
                                print(
                                    f"RIGHT → {percentage:.0f}% open (GELLO: {gello_pos:.3f}, UR5: {ur_cmd:.3f})"
                                )
                                last_print_time = now
                        last_right_cmd = ur_cmd

            # Show real-time status
            if status:
                print(f"\r{' | '.join(status)} open    ", end="", flush=True)

            time.sleep(0.02)  # Faster update rate for smooth control

    except KeyboardInterrupt:
        print("\n\nTest stopped.")

    # Disconnect
    if left_dxl_ok:
        left_robot.disconnect()
    if right_dxl_ok:
        right_robot.disconnect()

    # Show final calibration for streamdeck_pedal_watch.py
    print("\n" + "=" * 60)
    print("LINEAR MAPPING CONFIG FOR streamdeck_pedal_watch.py:")
    print("=" * 60)

    if left_min is not None and left_max is not None:
        print("\nLEFT GRIPPER (Lines 712-713):")
        print(f"  self.left_gripper_min = {left_min:.3f}  # GELLO closed")
        print(f"  self.left_gripper_max = {left_max:.3f}  # GELLO open")

    if right_min is not None and right_max is not None:
        print("\nRIGHT GRIPPER (Lines 714-715):")
        print(f"  self.right_gripper_min = {right_min:.3f}  # GELLO closed")
        print(f"  self.right_gripper_max = {right_max:.3f}  # GELLO open")

    print("\n✓ Linear mapping is already implemented in streamdeck_pedal_watch.py!")
    print("✓ The script will auto-calibrate on first use and refine during operation.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
