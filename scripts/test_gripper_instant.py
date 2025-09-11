#!/usr/bin/env python3
"""
INSTANT gripper test - Ultra-fast connection with cached values.
Connects in < 1 second and uses saved calibration if available.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def load_calibration():
    """Load saved calibration if available"""
    try:
        with open("/tmp/gello_gripper_calibration.json", "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_calibration(left_min, left_max, right_min, right_max):
    """Save calibration for next time"""
    cal = {
        "left_gello_min": left_min,
        "left_gello_max": left_max,
        "right_gello_min": right_min,
        "right_gello_max": right_max,
        "timestamp": time.time(),
    }
    with open("/tmp/gello_gripper_calibration.json", "w") as f:
        json.dump(cal, f, indent=2)


def send_cmd(side, pos):
    """Quick gripper command"""
    try:
        cmd = [
            "python",
            os.path.expanduser("~/generalistai/dexgpt/debug_tools/send_gripper_cmd.py"),
            "-o",
            f"gripper_command_{side}",
            "--position",
            str(pos),
        ]
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=0.2,
            cwd=os.path.expanduser("~/generalistai/dexgpt"),
        )
        return True
    except Exception:
        return False


def main():
    print("\n" + "=" * 60)
    print("⚡ INSTANT GRIPPER TEST")
    print("=" * 60)

    # Try to load saved calibration
    cal = load_calibration()

    if cal and (time.time() - cal.get("timestamp", 0)) < 3600:  # Use if < 1 hour old
        print("✓ Using saved calibration (< 1 hour old)")
        left_min = cal.get("left_gello_min")
        left_max = cal.get("left_gello_max")
        right_min = cal.get("right_gello_min")
        right_max = cal.get("right_gello_max")

        print(f"  LEFT:  {left_min:.3f} → {left_max:.3f} rad")
        print(f"  RIGHT: {right_min:.3f} → {right_max:.3f} rad")

        skip_calibration = True
    else:
        print("⚠ No recent calibration - will do quick calibration")
        skip_calibration = False

    # Fast connect - DXL only
    print("\n⚡ Fast connecting...")

    left_robot = URDynamixelRobot(
        ur_host="127.0.0.1",  # Dummy - not used
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0] * 7,
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="127.0.0.1",  # Dummy - not used
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0] * 7,
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Connect DXL only
    left_ok = left_robot.dxl.connect()
    right_ok = right_robot.dxl.connect()

    print(f"LEFT:  {'✓' if left_ok else '✗'}")
    print(f"RIGHT: {'✓' if right_ok else '✗'}")

    if not (left_ok or right_ok):
        print("\n✗ No grippers!")
        return

    # Quick calibration if needed
    if not skip_calibration:
        print("\n⚡ QUICK CALIBRATION (5 seconds total)")
        print("Close grippers NOW...")
        time.sleep(2)

        if left_ok:
            pos = left_robot.dxl.read_positions()
            left_min = pos[6] if pos is not None and len(pos) > 6 else None

        if right_ok:
            pos = right_robot.dxl.read_positions()
            right_min = pos[6] if pos is not None and len(pos) > 6 else None

        print("Open grippers NOW...")
        time.sleep(2)

        if left_ok:
            pos = left_robot.dxl.read_positions()
            left_max = pos[6] if pos is not None and len(pos) > 6 else None

        if right_ok:
            pos = right_robot.dxl.read_positions()
            right_max = pos[6] if pos is not None and len(pos) > 6 else None

        # Save for next time
        if left_min and left_max and right_min and right_max:
            save_calibration(left_min, left_max, right_min, right_max)
            print("✓ Calibration saved!")

    # Calculate thresholds
    left_thresh = (left_min + left_max) / 2 if left_min and left_max else None
    right_thresh = (right_min + right_max) / 2 if right_min and right_max else None

    # Test loop
    print("\n⚡ TESTING - Move grippers! (Ctrl+C to stop)")
    print("-" * 60)

    last_l = None
    last_r = None

    try:
        while True:
            # LEFT
            if left_ok and left_thresh:
                pos = left_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    state = "C" if pos[6] < left_thresh else "O"
                    if state != last_l:
                        cmd = -0.075 if state == "C" else 0.25
                        if send_cmd("left", cmd):
                            print(f"L→{state}", end=" ")
                        last_l = state

            # RIGHT
            if right_ok and right_thresh:
                pos = right_robot.dxl.read_positions()
                if pos is not None and len(pos) > 6:
                    state = "C" if pos[6] < right_thresh else "O"
                    if state != last_r:
                        cmd = -0.075 if state == "C" else 0.25
                        if send_cmd("right", cmd):
                            print(f"R→{state}", end=" ")
                        last_r = state

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass

    # Results
    print("\n\n" + "=" * 60)
    print("UPDATE streamdeck_pedal_watch.py:")
    print("=" * 60)

    if left_thresh:
        print(f"Line 887: gripper_threshold = {left_thresh:.2f}  # LEFT")
    if right_thresh:
        print(f"Line 972: gripper_threshold = {right_thresh:.2f}  # RIGHT")

    print("=" * 60)

    # Disconnect
    if left_ok:
        left_robot.dxl.disconnect()
    if right_ok:
        right_robot.dxl.disconnect()


if __name__ == "__main__":
    main()
