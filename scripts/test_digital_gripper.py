#!/usr/bin/env python3
"""
Test UR5 gripper control using digital outputs.
This directly controls the gripper without ZCM or external processes.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def control_gripper_digital(robot, position, gripper_pin=0):
    """Control gripper using digital outputs

    Args:
        robot: URDynamixelRobot instance
        position: Gripper position (-0.075 for closed, 0.25 for open)
        gripper_pin: Digital output pin (0-7 for standard, 0-1 for tool)
    """
    if not robot or not robot.ur:
        print("✗ Robot not connected")
        return False

    # Normalize position to 0-1 range
    normalized = (position - (-0.075)) / (0.25 - (-0.075))
    normalized = max(0.0, min(1.0, normalized))

    # Determine digital state (adjust based on your gripper)
    # Some grippers: True = closed, False = open
    # Others: True = open, False = closed
    gripper_state = normalized < 0.5  # True = closed

    percentage = normalized * 100
    state_text = "CLOSED" if gripper_state else "OPEN"

    print(f"Setting gripper to {percentage:.0f}% open ({state_text})")
    print(f"  Position: {position:.3f}")
    print(f"  Normalized: {normalized:.3f}")
    print(f"  Digital pin {gripper_pin}: {gripper_state}")

    try:
        # Method 1: Standard digital output via control interface
        if hasattr(robot.ur, "control_interface") and robot.ur.control_interface:
            robot.ur.control_interface.setStandardDigitalOut(gripper_pin, gripper_state)
            print(f"✓ Sent via standard digital output {gripper_pin}")
            return True
        else:
            # Create temporary control interface
            from rtde_control import RTDEControlInterface

            temp_control = RTDEControlInterface(robot.ur.host)
            temp_control.setStandardDigitalOut(gripper_pin, gripper_state)
            temp_control.disconnect()
            print(f"✓ Sent via temporary control interface to pin {gripper_pin}")
            return True
    except Exception as e1:
        print(f"  Standard DO failed: {e1}")

        # Method 2: Tool digital output
        try:
            if hasattr(robot.ur, "control_interface") and robot.ur.control_interface:
                robot.ur.control_interface.setToolDigitalOut(gripper_pin, gripper_state)
                print(f"✓ Sent via tool digital output {gripper_pin}")
                return True
        except Exception as e2:
            print(f"  Tool DO failed: {e2}")
            return False


def main():
    print("\n" + "=" * 60)
    print("UR5 DIGITAL GRIPPER TEST")
    print("=" * 60)

    # Connect to UR5 robots
    print("\nConnecting to UR5 robots...")

    left_robot = URDynamixelRobot(
        ur_host="192.168.1.211",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        dxl_ids=[1, 2, 3, 4, 5, 6, 7],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0] * 7,
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    right_robot = URDynamixelRobot(
        ur_host="192.168.1.210",
        dxl_port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        dxl_ids=[10, 11, 12, 13, 14, 15, 16],
        dxl_signs=[1, 1, -1, 1, 1, 1, 1],
        dxl_offsets_deg=[0.0] * 7,
        dxl_baudrate=1000000,
        control_frequency=125,
    )

    # Connect
    left_ur_ok, left_dxl_ok = left_robot.connect()
    right_ur_ok, right_dxl_ok = right_robot.connect()

    print(f"LEFT:  UR={'✓' if left_ur_ok else '✗'}, DXL={'✓' if left_dxl_ok else '✗'}")
    print(
        f"RIGHT: UR={'✓' if right_ur_ok else '✗'}, DXL={'✓' if right_dxl_ok else '✗'}"
    )

    if not (left_ur_ok or right_ur_ok):
        print("\n✗ No UR5 robots connected!")
        return

    # Test different digital output pins
    print("\n" + "-" * 60)
    print("Testing different digital output pins...")
    print("Watch the UR5 I/O tab to see which pin controls your gripper")
    print("-" * 60)

    for pin in range(4):  # Test pins 0-3
        print(f"\n[Pin {pin}] Testing...")

        if left_ur_ok:
            print(f"  LEFT gripper CLOSE (pin {pin})...")
            control_gripper_digital(left_robot, -0.075, pin)
            time.sleep(1)

            print(f"  LEFT gripper OPEN (pin {pin})...")
            control_gripper_digital(left_robot, 0.25, pin)
            time.sleep(1)

        if right_ur_ok:
            print(f"  RIGHT gripper CLOSE (pin {pin})...")
            control_gripper_digital(right_robot, -0.075, pin)
            time.sleep(1)

            print(f"  RIGHT gripper OPEN (pin {pin})...")
            control_gripper_digital(right_robot, 0.25, pin)
            time.sleep(1)

    # Interactive test
    print("\n" + "-" * 60)
    print("INTERACTIVE TEST")
    print("-" * 60)
    print("Commands:")
    print("  lc = left close")
    print("  lo = left open")
    print("  rc = right close")
    print("  ro = right open")
    print("  l50 = left 50% open")
    print("  r75 = right 75% open")
    print("  q = quit")
    print("-" * 60)

    gripper_pin = 0  # Default pin

    while True:
        cmd = input("\nCommand: ").strip().lower()

        if cmd == "q":
            break
        elif cmd == "lc" and left_ur_ok:
            control_gripper_digital(left_robot, -0.075, gripper_pin)
        elif cmd == "lo" and left_ur_ok:
            control_gripper_digital(left_robot, 0.25, gripper_pin)
        elif cmd == "rc" and right_ur_ok:
            control_gripper_digital(right_robot, -0.075, gripper_pin)
        elif cmd == "ro" and right_ur_ok:
            control_gripper_digital(right_robot, 0.25, gripper_pin)
        elif cmd == "l50" and left_ur_ok:
            control_gripper_digital(left_robot, 0.088, gripper_pin)  # 50% open
        elif cmd == "r75" and right_ur_ok:
            control_gripper_digital(right_robot, 0.156, gripper_pin)  # 75% open
        elif cmd.startswith("pin"):
            try:
                gripper_pin = int(cmd[3:])
                print(f"Using pin {gripper_pin}")
            except Exception:
                print("Invalid pin number")
        else:
            print("Unknown command")

    # Disconnect
    if left_ur_ok or left_dxl_ok:
        left_robot.disconnect()
    if right_ur_ok or right_dxl_ok:
        right_robot.disconnect()

    print("\nDone!")


if __name__ == "__main__":
    main()
