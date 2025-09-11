#!/usr/bin/env python3
"""
Map GELLO gripper positions to UR5 gripper commands.
This script will:
1. Find GELLO gripper open/closed positions
2. Map them to UR5 gripper commands
3. Test the mapping in real-time
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


class GripperMapper:
    """Maps GELLO gripper positions to UR5 commands"""

    # UR5 gripper command values (known)
    UR_GRIPPER_CLOSED = -0.075
    UR_GRIPPER_OPEN = 0.25

    def __init__(self):
        self.left_gello_min = None
        self.left_gello_max = None
        self.right_gello_min = None
        self.right_gello_max = None

        # Store last sent commands to avoid spamming
        self.last_left_cmd = None
        self.last_right_cmd = None
        self.min_cmd_interval = 0.2  # Minimum time between commands
        self.last_left_time = 0
        self.last_right_time = 0

    def map_gello_to_ur(self, gello_pos, gello_min, gello_max):
        """
        Map GELLO position to UR5 gripper command.
        Linear interpolation between closed and open.
        """
        if gello_min is None or gello_max is None:
            return None

        # Normalize GELLO position to 0-1 range
        normalized = (gello_pos - gello_min) / (gello_max - gello_min)
        normalized = max(0, min(1, normalized))  # Clamp to [0, 1]

        # Map to UR5 command range
        ur_cmd = self.UR_GRIPPER_CLOSED + normalized * (
            self.UR_GRIPPER_OPEN - self.UR_GRIPPER_CLOSED
        )

        return ur_cmd

    def send_gripper_command(self, side, position):
        """Send gripper command to UR5"""
        now = time.time()

        # Check if enough time has passed
        if side == "left":
            if now - self.last_left_time < self.min_cmd_interval:
                return False
            if (
                self.last_left_cmd is not None
                and abs(position - self.last_left_cmd) < 0.01
            ):
                return False  # Position hasn't changed enough
            self.last_left_cmd = position
            self.last_left_time = now
        else:
            if now - self.last_right_time < self.min_cmd_interval:
                return False
            if (
                self.last_right_cmd is not None
                and abs(position - self.last_right_cmd) < 0.01
            ):
                return False
            self.last_right_cmd = position
            self.last_right_time = now

        try:
            dexgpt_path = os.path.expanduser("~/generalistai/dexgpt")
            script_path = os.path.join(
                dexgpt_path, "debug_tools", "send_gripper_cmd.py"
            )

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


def calibrate_grippers(mapper):
    """Calibrate GELLO gripper min/max positions"""

    print("\n" + "=" * 70)
    print("GELLO GRIPPER CALIBRATION")
    print("=" * 70)

    # Connect to GELLO arms
    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    print("\nConnecting to GELLO arms...")
    left_ur_ok, left_dxl_ok = left_robot.connect()
    right_ur_ok, right_dxl_ok = right_robot.connect()

    if not (left_dxl_ok or right_dxl_ok):
        print("✗ No GELLO arms connected!")
        return False

    print(f"LEFT:  {'✓ Connected' if left_dxl_ok else '✗ Not connected'}")
    print(f"RIGHT: {'✓ Connected' if right_dxl_ok else '✗ Not connected'}")

    print("\n" + "-" * 70)
    print("CALIBRATION INSTRUCTIONS:")
    print("1. SQUEEZE each gripper FULLY CLOSED")
    print("2. Press ENTER when both are closed")
    print("-" * 70)

    input("\nPress ENTER when grippers are CLOSED...")

    # Read closed positions
    if left_dxl_ok:
        positions = left_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            mapper.left_gello_min = positions[6]
            print(
                f"LEFT CLOSED:  {mapper.left_gello_min:.3f} rad ({np.degrees(mapper.left_gello_min):.1f}°)"
            )

    if right_dxl_ok:
        positions = right_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            mapper.right_gello_min = positions[6]
            print(
                f"RIGHT CLOSED: {mapper.right_gello_min:.3f} rad ({np.degrees(mapper.right_gello_min):.1f}°)"
            )

    print("\n" + "-" * 70)
    print("3. Now RELEASE grippers FULLY OPEN")
    print("4. Press ENTER when both are open")
    print("-" * 70)

    input("\nPress ENTER when grippers are OPEN...")

    # Read open positions
    if left_dxl_ok:
        positions = left_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            mapper.left_gello_max = positions[6]
            print(
                f"LEFT OPEN:  {mapper.left_gello_max:.3f} rad ({np.degrees(mapper.left_gello_max):.1f}°)"
            )

    if right_dxl_ok:
        positions = right_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            mapper.right_gello_max = positions[6]
            print(
                f"RIGHT OPEN: {mapper.right_gello_max:.3f} rad ({np.degrees(mapper.right_gello_max):.1f}°)"
            )

    # Save calibration
    calibration = {
        "left_gello_min": mapper.left_gello_min,
        "left_gello_max": mapper.left_gello_max,
        "right_gello_min": mapper.right_gello_min,
        "right_gello_max": mapper.right_gello_max,
    }

    with open("/tmp/gello_gripper_calibration.json", "w") as f:
        json.dump(calibration, f, indent=2)

    print("\n" + "=" * 70)
    print("CALIBRATION COMPLETE!")
    print("=" * 70)

    if mapper.left_gello_min and mapper.left_gello_max:
        left_range = mapper.left_gello_max - mapper.left_gello_min
        print("\nLEFT GRIPPER:")
        print(f"  Range: {left_range:.3f} rad ({np.degrees(left_range):.1f}°)")
        print(f"  GELLO: {mapper.left_gello_min:.3f} → {mapper.left_gello_max:.3f} rad")
        print(f"  UR5:   {mapper.UR_GRIPPER_CLOSED} → {mapper.UR_GRIPPER_OPEN}")

    if mapper.right_gello_min and mapper.right_gello_max:
        right_range = mapper.right_gello_max - mapper.right_gello_min
        print("\nRIGHT GRIPPER:")
        print(f"  Range: {right_range:.3f} rad ({np.degrees(right_range):.1f}°)")
        print(
            f"  GELLO: {mapper.right_gello_min:.3f} → {mapper.right_gello_max:.3f} rad"
        )
        print(f"  UR5:   {mapper.UR_GRIPPER_CLOSED} → {mapper.UR_GRIPPER_OPEN}")

    print("\nCalibration saved to /tmp/gello_gripper_calibration.json")

    # Disconnect
    if left_dxl_ok:
        left_robot.disconnect()
    if right_dxl_ok:
        right_robot.disconnect()

    return True


def test_mapping(mapper):
    """Test the gripper mapping in real-time"""

    print("\n" + "=" * 70)
    print("GRIPPER MAPPING TEST")
    print("=" * 70)
    print("\nMove GELLO grippers to control UR5 grippers")
    print("Press Ctrl+C to stop\n")
    print("-" * 70)

    # Connect to GELLO arms
    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    left_ur_ok, left_dxl_ok = left_robot.connect()
    right_ur_ok, right_dxl_ok = right_robot.connect()

    if not (left_dxl_ok or right_dxl_ok):
        print("✗ No GELLO arms connected!")
        return

    try:
        while True:
            output = []

            # Process LEFT gripper
            if left_dxl_ok and mapper.left_gello_min is not None:
                positions = left_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    gello_pos = positions[6]
                    ur_cmd = mapper.map_gello_to_ur(
                        gello_pos, mapper.left_gello_min, mapper.left_gello_max
                    )

                    if ur_cmd is not None:
                        # Determine state
                        if (
                            ur_cmd
                            < (mapper.UR_GRIPPER_CLOSED + mapper.UR_GRIPPER_OPEN) / 2
                        ):
                            state = "CLOSED"
                        else:
                            state = "OPEN"

                        output.append(
                            f"L: GELLO={gello_pos:.3f} → UR={ur_cmd:.3f} ({state})"
                        )

                        # Send command
                        if mapper.send_gripper_command("left", ur_cmd):
                            output.append("✓")

            # Process RIGHT gripper
            if right_dxl_ok and mapper.right_gello_min is not None:
                positions = right_robot.dxl.read_positions()
                if positions and len(positions) > 6:
                    gello_pos = positions[6]
                    ur_cmd = mapper.map_gello_to_ur(
                        gello_pos, mapper.right_gello_min, mapper.right_gello_max
                    )

                    if ur_cmd is not None:
                        # Determine state
                        if (
                            ur_cmd
                            < (mapper.UR_GRIPPER_CLOSED + mapper.UR_GRIPPER_OPEN) / 2
                        ):
                            state = "CLOSED"
                        else:
                            state = "OPEN"

                        output.append(
                            f"R: GELLO={gello_pos:.3f} → UR={ur_cmd:.3f} ({state})"
                        )

                        # Send command
                        if mapper.send_gripper_command("right", ur_cmd):
                            output.append("✓")

            # Display
            if output:
                print("\r" + " | ".join(output) + "    ", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nTest stopped.")

    # Disconnect
    if left_dxl_ok:
        left_robot.disconnect()
    if right_dxl_ok:
        right_robot.disconnect()


def main():
    """Main function"""

    print("\n" + "=" * 70)
    print("GELLO TO UR5 GRIPPER MAPPER")
    print("=" * 70)

    mapper = GripperMapper()

    # Try to load existing calibration
    try:
        with open("/tmp/gello_gripper_calibration.json", "r") as f:
            cal = json.load(f)
            mapper.left_gello_min = cal.get("left_gello_min")
            mapper.left_gello_max = cal.get("left_gello_max")
            mapper.right_gello_min = cal.get("right_gello_min")
            mapper.right_gello_max = cal.get("right_gello_max")
            print("\n✓ Loaded existing calibration")
            print("  Press 'r' to recalibrate or ENTER to test")
    except:
        print("\n✗ No calibration found")
        print("  Press ENTER to calibrate")

    choice = input("\nYour choice: ").lower()

    if choice == "r" or mapper.left_gello_min is None:
        if not calibrate_grippers(mapper):
            print("Calibration failed!")
            return

    # Test the mapping
    test_mapping(mapper)

    # Show recommended values for streamdeck_pedal_watch.py
    print("\n" + "=" * 70)
    print("RECOMMENDED CHANGES FOR streamdeck_pedal_watch.py:")
    print("=" * 70)

    if mapper.left_gello_min and mapper.left_gello_max:
        left_threshold = (mapper.left_gello_min + mapper.left_gello_max) / 2
        print("\nLEFT (Line 887):")
        print(f"  gripper_threshold = {left_threshold:.2f}")
        print(f"  # Min: {mapper.left_gello_min:.3f}, Max: {mapper.left_gello_max:.3f}")

    if mapper.right_gello_min and mapper.right_gello_max:
        right_threshold = (mapper.right_gello_min + mapper.right_gello_max) / 2
        print("\nRIGHT (Line 972):")
        print(f"  gripper_threshold = {right_threshold:.2f}")
        print(
            f"  # Min: {mapper.right_gello_min:.3f}, Max: {mapper.right_gello_max:.3f}"
        )

    print("\n" + "=" * 70)
    print("Done!")


if __name__ == "__main__":
    main()
