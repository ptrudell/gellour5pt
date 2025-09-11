#!/usr/bin/env python3
"""
Diagnostic script to test gripper detection and calibration.
This will help identify why gripper commands aren't being executed.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler


def test_dxl_gripper(port: str, gripper_id: int, side: str):
    """Test if a specific gripper ID is responding."""

    PROTOCOL_VERSION = 2.0
    BAUDRATE = 1000000
    ADDR_PRESENT_POSITION = 132

    # Initialize
    portHandler = PortHandler(port)
    packetHandler = PacketHandler(PROTOCOL_VERSION)

    # Open port
    if not portHandler.openPort():
        print(f"✗ Failed to open port {port}")
        return False

    # Set baudrate
    if not portHandler.setBaudRate(BAUDRATE):
        print("✗ Failed to set baudrate")
        portHandler.closePort()
        return False

    print("\n" + "=" * 60)
    print(f"Testing {side.upper()} gripper (ID {gripper_id})")
    print(f"Port: {port}")
    print("=" * 60)

    # Try to read position
    dxl_present_position, dxl_comm_result, dxl_error = packetHandler.read4ByteTxRx(
        portHandler, gripper_id, ADDR_PRESENT_POSITION
    )

    if dxl_comm_result != COMM_SUCCESS:
        print(f"✗ Communication failed: {packetHandler.getTxRxResult(dxl_comm_result)}")
        portHandler.closePort()
        return False
    elif dxl_error != 0:
        print(f"✗ Error: {packetHandler.getRxPacketError(dxl_error)}")
        portHandler.closePort()
        return False
    else:
        # Convert to radians
        position_rad = (dxl_present_position - 2048) * 0.001533203
        print(f"✓ Gripper ID {gripper_id} responding!")
        print(f"  Position: {dxl_present_position} ticks ({position_rad:.3f} rad)")

        # Monitor for 3 seconds
        print("\n  Monitoring gripper position (squeeze/release to see changes)...")
        for i in range(30):
            dxl_pos, _, _ = packetHandler.read4ByteTxRx(
                portHandler, gripper_id, ADDR_PRESENT_POSITION
            )
            pos_rad = (dxl_pos - 2048) * 0.001533203
            print(f"  [{i + 1}/30] Position: {pos_rad:.3f} rad", end="\r")
            time.sleep(0.1)
        print()

        portHandler.closePort()
        return True


def test_robot_grippers():
    """Test both robots' gripper configurations."""

    # Configuration from teleop_dual_ur5.yaml
    left_config = {
        "port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        "ids": [1, 2, 3, 4, 5, 6, 7],
        "gripper_id": 7,
    }

    right_config = {
        "port": "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        "ids": [10, 11, 12, 13, 14, 15, 16],
        "gripper_id": 16,
    }

    print("\n" + "=" * 60)
    print("GRIPPER DIAGNOSTIC TEST")
    print("=" * 60)

    # Test left gripper
    left_ok = test_dxl_gripper(left_config["port"], left_config["gripper_id"], "left")

    # Test right gripper
    right_ok = test_dxl_gripper(
        right_config["port"], right_config["gripper_id"], "right"
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if left_ok and right_ok:
        print("✓ Both grippers detected successfully!")
        print("\nNOTE: If grippers aren't working in teleop, the issue is likely:")
        print("  1. The subprocess call to dexgpt script is failing")
        print("  2. The gripper threshold values need adjustment")
        print("  3. The hysteresis is preventing commands from being sent")
    elif left_ok and not right_ok:
        print("⚠ Only LEFT gripper detected")
        print("  Check RIGHT gripper wiring and ID configuration")
    elif not left_ok and right_ok:
        print("⚠ Only RIGHT gripper detected")
        print("  Check LEFT gripper wiring and ID configuration")
    else:
        print("✗ No grippers detected!")
        print("\nPossible issues:")
        print("  1. Gripper servos not powered")
        print("  2. Wrong servo IDs (expected: 7 for left, 16 for right)")
        print("  3. Port configuration mismatch")
        print("\nTo change servo IDs:")
        print("  1. Connect one servo at a time")
        print("  2. Use Dynamixel Wizard to scan and change ID")


if __name__ == "__main__":
    test_robot_grippers()
