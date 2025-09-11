#!/usr/bin/env python3
"""
FAST gripper test - connects only to DXL, skips UR connection for speed.
Just reads GELLO positions and sends UR gripper commands.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler
except ImportError:
    print("Error: dynamixel_sdk not installed")
    sys.exit(1)


class FastDXLReader:
    """Fast Dynamixel reader - no UR connection needed"""

    def __init__(self, port, ids, baudrate=1000000):
        self.port_name = port
        self.ids = ids
        self.baudrate = baudrate
        self.port = None
        self.ph = None

    def connect(self):
        """Quick connect to DXL only"""
        try:
            self.port = PortHandler(self.port_name)
            self.ph = PacketHandler(2.0)  # Protocol 2.0

            if not self.port.openPort():
                print(f"  ✗ Failed to open port {self.port_name}")
                return False

            if not self.port.setBaudRate(self.baudrate):
                print("  ✗ Failed to set baudrate")
                return False

            # Quick ping test on first servo only
            result, error = self.ph.ping(self.port, self.ids[0])
            if result != COMM_SUCCESS:
                print(f"  ✗ No response from servo ID {self.ids[0]}")
                return False

            return True
        except Exception as e:
            print(f"  ✗ Connection error: {e}")
            return False

    def read_gripper(self):
        """Read just the gripper position (ID 7 or 16)"""
        if not self.port or not self.ph:
            return None

        # Gripper is last ID in the list
        gripper_id = self.ids[-1]

        # Read present position (address 132 for XL330)
        result, error = self.ph.read4ByteTxRx(self.port, gripper_id, 132)
        if result != COMM_SUCCESS:
            return None

        # Convert to radians
        raw_value = self.ph.read4ByteTxRx(self.port, gripper_id, 132)[1]
        position = (raw_value - 2048) * 0.001533981  # Convert to radians

        return position

    def disconnect(self):
        """Quick disconnect"""
        if self.port:
            self.port.closePort()


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
            cmd,
            cwd=dexgpt_path,
            capture_output=True,
            timeout=0.3,  # Faster timeout
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def main():
    print("\n" + "=" * 60)
    print("FAST GRIPPER TEST (DXL-only connection)")
    print("=" * 60)

    # UR5 gripper commands
    UR_CLOSED = -0.075
    UR_OPEN = 0.25

    # Quick connect to GELLO DXLs only
    print("\nConnecting to GELLO grippers (DXL only)...")

    # Left GELLO
    left_dxl = FastDXLReader(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        ids=[1, 2, 3, 4, 5, 6, 7],  # ID 7 is gripper
        baudrate=1000000,
    )

    # Right GELLO
    right_dxl = FastDXLReader(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        ids=[10, 11, 12, 13, 14, 15, 16],  # ID 16 is gripper
        baudrate=1000000,
    )

    # Fast parallel-ish connection
    left_ok = left_dxl.connect()
    right_ok = right_dxl.connect()

    print(f"LEFT:  {'✓ Connected' if left_ok else '✗ Not connected'}")
    print(f"RIGHT: {'✓ Connected' if right_ok else '✗ Not connected'}")

    if not (left_ok or right_ok):
        print("\n✗ No grippers found!")
        return

    # Quick calibration
    print("\n" + "-" * 60)
    print("CALIBRATION (10 seconds)")
    print("-" * 60)
    print("1. SQUEEZE grippers CLOSED (3 sec)...")
    time.sleep(3)

    left_min = left_dxl.read_gripper() if left_ok else None
    right_min = right_dxl.read_gripper() if right_ok else None

    if left_min:
        print(f"   LEFT CLOSED: {left_min:.3f} rad")
    if right_min:
        print(f"   RIGHT CLOSED: {right_min:.3f} rad")

    print("\n2. RELEASE grippers OPEN (3 sec)...")
    time.sleep(3)

    left_max = left_dxl.read_gripper() if left_ok else None
    right_max = right_dxl.read_gripper() if right_ok else None

    if left_max:
        print(f"   LEFT OPEN: {left_max:.3f} rad")
    if right_max:
        print(f"   RIGHT OPEN: {right_max:.3f} rad")

    # Calculate thresholds
    left_threshold = (left_min + left_max) / 2 if left_min and left_max else None
    right_threshold = (right_min + right_max) / 2 if right_min and right_max else None

    if left_threshold:
        print(f"\n   LEFT threshold: {left_threshold:.3f} rad")
    if right_threshold:
        print(f"   RIGHT threshold: {right_threshold:.3f} rad")

    # Quick test
    print("\n" + "-" * 60)
    print("TESTING - Move grippers to control UR5")
    print("Press Ctrl+C to stop")
    print("-" * 60 + "\n")

    last_left_state = None
    last_right_state = None

    try:
        while True:
            status = []

            # LEFT
            if left_ok and left_threshold:
                pos = left_dxl.read_gripper()
                if pos:
                    state = "CLOSED" if pos < left_threshold else "OPEN"
                    ur_cmd = UR_CLOSED if state == "CLOSED" else UR_OPEN

                    status.append(f"L:{state}")

                    if state != last_left_state:
                        if send_ur_gripper_command("left", ur_cmd):
                            print(f"LEFT → {state}")
                        last_left_state = state

            # RIGHT
            if right_ok and right_threshold:
                pos = right_dxl.read_gripper()
                if pos:
                    state = "CLOSED" if pos < right_threshold else "OPEN"
                    ur_cmd = UR_CLOSED if state == "CLOSED" else UR_OPEN

                    status.append(f"R:{state}")

                    if state != last_right_state:
                        if send_ur_gripper_command("right", ur_cmd):
                            print(f"RIGHT → {state}")
                        last_right_state = state

            if status:
                print(f"\r{' | '.join(status)}  ", end="", flush=True)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n\nStopped.")

    # Disconnect
    if left_ok:
        left_dxl.disconnect()
    if right_ok:
        right_dxl.disconnect()

    # Results
    print("\n" + "=" * 60)
    print("RESULTS FOR streamdeck_pedal_watch.py:")
    print("=" * 60)

    if left_threshold:
        print(f"\nLine 887: gripper_threshold = {left_threshold:.2f}  # LEFT")
    if right_threshold:
        print(f"Line 972: gripper_threshold = {right_threshold:.2f}  # RIGHT")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
