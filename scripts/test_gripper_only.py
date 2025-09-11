#!/usr/bin/env python3
"""
Test ONLY the gripper control from GELLO to UR5.
Simple standalone script for gripper testing.
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


def main():
    print("\n" + "=" * 60)
    print("GRIPPER-ONLY TEST")
    print("=" * 60)
    print("\nThis tests ONLY gripper control (no arm movement)")
    print("=" * 60)

    # UR5 gripper commands
    UR_CLOSED = -0.075
    UR_OPEN = 0.25

    # Connect to GELLO arms (DXL only for gripper reading)
    print("\nConnecting to GELLO grippers (DXL only, skipping UR)...")

    # Create robots but skip UR connection for speed
    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",  # Not used but required
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",  # Not used but required
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Connect ONLY to DXL (skip UR for speed)
    # Manually connect just DXL to avoid UR connection delay
    left_dxl_ok = left_robot.dxl.connect()

    right_dxl_ok = right_robot.dxl.connect()

    print(f"LEFT GELLO:  {'✓ Connected' if left_dxl_ok else '✗ Not connected'}")
    print(f"RIGHT GELLO: {'✓ Connected' if right_dxl_ok else '✗ Not connected'}")

    if not (left_dxl_ok or right_dxl_ok):
        print("\n✗ No GELLO grippers connected!")
        return

    # Find min/max for each gripper
    print("\n" + "-" * 60)
    print("STEP 1: CALIBRATION")
    print("-" * 60)
    print("SQUEEZE both grippers CLOSED and press ENTER...")
    input()

    left_min = None
    right_min = None

    if left_dxl_ok:
        pos = left_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            left_min = pos[6]
            print(f"LEFT CLOSED: {left_min:.3f} rad")

    if right_dxl_ok:
        pos = right_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            right_min = pos[6]
            print(f"RIGHT CLOSED: {right_min:.3f} rad")

    print("\nRELEASE both grippers OPEN and press ENTER...")
    input()

    left_max = None
    right_max = None

    if left_dxl_ok:
        pos = left_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            left_max = pos[6]
            print(f"LEFT OPEN: {left_max:.3f} rad")

    if right_dxl_ok:
        pos = right_robot.dxl.read_positions()
        if pos is not None and len(pos) > 6:
            right_max = pos[6]
            print(f"RIGHT OPEN: {right_max:.3f} rad")

    # Calculate thresholds
    left_threshold = None
    right_threshold = None

    if left_min is not None and left_max is not None:
        left_threshold = (left_min + left_max) / 2
        print(f"\nLEFT threshold: {left_threshold:.3f} rad")

    if right_min is not None and right_max is not None:
        right_threshold = (right_min + right_max) / 2
        print(f"RIGHT threshold: {right_threshold:.3f} rad")

    print("\n" + "-" * 60)
    print("STEP 2: TESTING")
    print("-" * 60)
    print("Move GELLO grippers to control UR5 grippers")
    print("Press Ctrl+C to stop")
    print("-" * 60 + "\n")

    # Track last commands to avoid spam
    last_left_cmd = None
    last_right_cmd = None
    last_left_time = 0
    last_right_time = 0
    min_interval = 0.3  # Minimum time between commands

    try:
        while True:
            now = time.time()
            status = []

            # LEFT gripper
            if left_dxl_ok and left_threshold is not None:
                pos = left_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    gello_pos = pos[6]

                    # Simple threshold-based control
                    if gello_pos < left_threshold:
                        ur_cmd = UR_CLOSED
                        state = "CLOSED"
                    else:
                        ur_cmd = UR_OPEN
                        state = "OPEN"

                    status.append(f"L: {gello_pos:.2f}→{state}")

                    # Send command if changed and enough time passed
                    if last_left_cmd != ur_cmd and now - last_left_time > min_interval:
                        if send_ur_gripper_command("left", ur_cmd):
                            print(f"LEFT → {state} (cmd: {ur_cmd})")
                            last_left_cmd = ur_cmd
                            last_left_time = now

            # RIGHT gripper
            if right_dxl_ok and right_threshold is not None:
                pos = right_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    gello_pos = pos[6]

                    # Simple threshold-based control
                    if gello_pos < right_threshold:
                        ur_cmd = UR_CLOSED
                        state = "CLOSED"
                    else:
                        ur_cmd = UR_OPEN
                        state = "OPEN"

                    status.append(f"R: {gello_pos:.2f}→{state}")

                    # Send command if changed and enough time passed
                    if (
                        last_right_cmd != ur_cmd
                        and now - last_right_time > min_interval
                    ):
                        if send_ur_gripper_command("right", ur_cmd):
                            print(f"RIGHT → {state} (cmd: {ur_cmd})")
                            last_right_cmd = ur_cmd
                            last_right_time = now

            # Show status
            if status:
                print(f"\r{' | '.join(status)}    ", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nTest stopped.")

    # Disconnect
    if left_dxl_ok:
        left_robot.disconnect()
    if right_dxl_ok:
        right_robot.disconnect()

    # Show results
    print("\n" + "=" * 60)
    print("TEST COMPLETE - RESULTS:")
    print("=" * 60)

    if left_threshold is not None:
        print("\nLEFT GRIPPER:")
        print(f"  GELLO range: {left_min:.3f} to {left_max:.3f} rad")
        print(f"  Threshold: {left_threshold:.3f} rad")
        print(f"  UR5 commands: {UR_CLOSED} (closed) to {UR_OPEN} (open)")

    if right_threshold is not None:
        print("\nRIGHT GRIPPER:")
        print(f"  GELLO range: {right_min:.3f} to {right_max:.3f} rad")
        print(f"  Threshold: {right_threshold:.3f} rad")
        print(f"  UR5 commands: {UR_CLOSED} (closed) to {UR_OPEN} (open)")

    print("\n" + "=" * 60)
    print("UPDATE streamdeck_pedal_watch.py:")
    print("=" * 60)

    if left_threshold is not None:
        print(f"\nLine 887: gripper_threshold = {left_threshold:.2f}  # LEFT")
    if right_threshold is not None:
        print(f"Line 972: gripper_threshold = {right_threshold:.2f}  # RIGHT")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
