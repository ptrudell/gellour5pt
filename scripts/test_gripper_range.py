#!/usr/bin/env python3
"""
Test script to monitor DXL gripper range of motion.
Press the GELLO grippers to see their position values.

This helps calibrate the threshold for open/closed detection.
"""

import sys
import time
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dynamixel_sdk import *


def monitor_gripper(port_path: str, gripper_id: int, side: str):
    """Monitor a single gripper's position in real-time."""

    PROTOCOL_VERSION = 2.0
    BAUDRATE = 1000000
    ADDR_PRESENT_POSITION = 132

    # Initialize
    portHandler = PortHandler(port_path)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    # Open port
    if not portHandler.openPort():
        print(f"✗ Failed to open port {port_path}")
        return

    # Set baudrate
    if not portHandler.setBaudRate(BAUDRATE):
        print("✗ Failed to set baudrate")
        portHandler.closePort()
        return

    print(f"\n{'=' * 60}")
    print(f"{side.upper()} Gripper (ID {gripper_id}) Position Monitor")
    print(f"Port: {port_path}")
    print("=" * 60)
    print("\n🎮 SQUEEZE and RELEASE the GELLO gripper to see values")
    print("📊 Watch for min/max values to determine thresholds")
    print("Press Ctrl+C to stop\n")

    min_pos = float("inf")
    max_pos = float("-inf")
    last_pos = None
    state = "UNKNOWN"

    try:
        while True:
            # Read position
            dxl_present_position, dxl_comm_result, dxl_error = (
                packetHandler.read4ByteTxRx(
                    portHandler, gripper_id, ADDR_PRESENT_POSITION
                )
            )

            if dxl_comm_result != COMM_SUCCESS:
                continue

            # Convert to signed value
            if dxl_present_position > 2147483647:
                dxl_present_position -= 4294967296

            # Convert to radians
            position_rad = dxl_present_position * 0.001534  # ticks to radians

            # Update min/max
            if position_rad < min_pos:
                min_pos = position_rad
                print(f"📉 NEW MIN: {min_pos:.4f} rad ({np.degrees(min_pos):.1f}°)")
            if position_rad > max_pos:
                max_pos = position_rad
                print(f"📈 NEW MAX: {max_pos:.4f} rad ({np.degrees(max_pos):.1f}°)")

            # Determine state change
            if last_pos is not None:
                delta = abs(position_rad - last_pos)
                if delta > 0.05:  # Significant movement
                    # Determine if opening or closing
                    if position_rad < 0:
                        new_state = "CLOSED/SQUEEZED"
                    else:
                        new_state = "OPEN/RELEASED"

                    if new_state != state:
                        state = new_state
                        print(f"\n🔄 State: {state}")
                        print(
                            f"   Position: {position_rad:.4f} rad ({np.degrees(position_rad):.1f}°)"
                        )
                        print(f"   Range so far: [{min_pos:.4f}, {max_pos:.4f}] rad")

                        # Suggest command
                        if state == "CLOSED/SQUEEZED":
                            print("   → Would send: -0.1 (closed command)")
                        else:
                            print("   → Would send: 0.25 (open command)")

            last_pos = position_rad
            time.sleep(0.05)  # 20Hz update

    except KeyboardInterrupt:
        print(f"\n\n{'=' * 60}")
        print(f"FINAL RESULTS for {side.upper()} Gripper:")
        print(f"  MIN Position: {min_pos:.4f} rad ({np.degrees(min_pos):.1f}°)")
        print(f"  MAX Position: {max_pos:.4f} rad ({np.degrees(max_pos):.1f}°)")
        print(
            f"  Range: {max_pos - min_pos:.4f} rad ({np.degrees(max_pos - min_pos):.1f}°)"
        )
        print(f"\nSuggested threshold: {(min_pos + max_pos) / 2:.4f} rad")
        print("=" * 60)

    finally:
        portHandler.closePort()


def main():
    print("\n" + "=" * 60)
    print("GELLO GRIPPER RANGE TEST")
    print("=" * 60)

    # Configuration
    LEFT_PORT = (
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
    )
    RIGHT_PORT = (
        "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
    )
    LEFT_GRIPPER_ID = 7
    RIGHT_GRIPPER_ID = 16

    print("\nWhich gripper to test?")
    print("  1. LEFT gripper (ID 7)")
    print("  2. RIGHT gripper (ID 16)")
    print("  3. BOTH (alternating)")

    choice = input("\nEnter choice (1/2/3): ").strip()

    if choice == "1":
        monitor_gripper(LEFT_PORT, LEFT_GRIPPER_ID, "left")
    elif choice == "2":
        monitor_gripper(RIGHT_PORT, RIGHT_GRIPPER_ID, "right")
    elif choice == "3":
        print("\n⚠️  Testing both grippers alternately")
        print("Press Ctrl+C to switch between grippers or exit\n")

        while True:
            try:
                print("\n>>> Testing LEFT gripper...")
                monitor_gripper(LEFT_PORT, LEFT_GRIPPER_ID, "left")
            except KeyboardInterrupt:
                pass

            try:
                print("\n>>> Testing RIGHT gripper...")
                monitor_gripper(RIGHT_PORT, RIGHT_GRIPPER_ID, "right")
            except KeyboardInterrupt:
                break
    else:
        print("Invalid choice")
        return 1

    print("\n✅ Test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
