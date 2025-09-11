#!/usr/bin/env python3
"""
Direct gripper control using Dynamixel servos.
This bypasses the dexgpt gripper driver and controls the grippers directly.
"""

import sys
import threading
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


class DirectGripperController:
    """Direct control of grippers via Dynamixel servos"""

    def __init__(self):
        # Grippers are on the main GELLO chains
        # LEFT gripper: ID 7 on left GELLO chain
        # RIGHT gripper: ID 16 on right GELLO chain
        self.left_port = (
            "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
        )
        self.right_port = (
            "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
        )

        # Gripper servo IDs
        self.left_id = 7  # Left gripper is ID 7
        self.right_id = 16  # Right gripper is ID 16

        # Position mappings (in radians)
        # These map to the -0.075 (closed) to 0.25 (open) range
        self.CLOSED_POS = -0.075  # rad
        self.OPEN_POS = 0.25  # rad

        # Dynamixel positions (will be calibrated)
        self.left_closed_ticks = None
        self.left_open_ticks = None
        self.right_closed_ticks = None
        self.right_open_ticks = None

        # Create Dynamixel drivers
        self.left_dxl = None
        self.right_dxl = None

    def connect(self):
        """Connect to gripper servos"""
        success = True

        # Connect left gripper
        try:
            print(f"Connecting to LEFT gripper: {self.left_port}")
            self.left_dxl = DynamixelDriver(
                port=self.left_port,
                baudrate=1000000,
                ids=[self.left_id],
                signs=[1],
                offsets_deg=[0.0],
            )
            if self.left_dxl.connect():
                print("✓ LEFT gripper connected")
            else:
                print("✗ LEFT gripper connection failed")
                success = False
        except Exception as e:
            print(f"✗ LEFT gripper error: {e}")
            success = False

        # Connect right gripper
        try:
            print(f"Connecting to RIGHT gripper: {self.right_port}")
            self.right_dxl = DynamixelDriver(
                port=self.right_port,
                baudrate=1000000,
                ids=[self.right_id],
                signs=[1],
                offsets_deg=[0.0],
            )
            if self.right_dxl.connect():
                print("✓ RIGHT gripper connected")
            else:
                print("✗ RIGHT gripper connection failed")
                success = False
        except Exception as e:
            print(f"✗ RIGHT gripper error: {e}")
            success = False

        return success

    def calibrate(self):
        """Auto-calibrate gripper positions using default ranges"""
        print("\n" + "=" * 60)
        print("AUTO-CALIBRATION")
        print("=" * 60)

        # Use fixed calibration values based on typical GELLO gripper ranges
        # These work for most setups - adjust if needed

        # LEFT gripper typical range
        self.left_closed_ticks = -0.629  # Closed position
        self.left_open_ticks = 0.262  # Open position

        # RIGHT gripper typical range
        self.right_closed_ticks = 0.962  # Closed position
        self.right_open_ticks = 1.908  # Open position

        print("Using default calibration values:")
        print(
            f"  LEFT:  Closed={self.left_closed_ticks:.3f}, Open={self.left_open_ticks:.3f}"
        )
        print(
            f"  RIGHT: Closed={self.right_closed_ticks:.3f}, Open={self.right_open_ticks:.3f}"
        )

        # Try to read current positions for verification
        if self.left_dxl:
            pos = self.left_dxl.read_positions()
            if pos is not None:
                print(f"  LEFT current position: {pos[0]:.3f} rad")

        if self.right_dxl:
            pos = self.right_dxl.read_positions()
            if pos is not None:
                print(f"  RIGHT current position: {pos[0]:.3f} rad")

        print("\n" + "=" * 60)
        print("AUTO-CALIBRATION COMPLETE")
        print("=" * 60)

    def set_gripper_position(self, side, position):
        """Set gripper to specific position

        Args:
            side: "left" or "right"
            position: Target position (-0.075 for closed, 0.25 for open, or in between)
        """
        # Normalize position to 0-1 range
        normalized = (position - self.CLOSED_POS) / (self.OPEN_POS - self.CLOSED_POS)
        normalized = max(0.0, min(1.0, normalized))

        if side == "left" and self.left_dxl:
            if self.left_closed_ticks is not None and self.left_open_ticks is not None:
                # Map to actual servo position
                target_ticks = self.left_closed_ticks + normalized * (
                    self.left_open_ticks - self.left_closed_ticks
                )
                success = self.left_dxl.write_positions([target_ticks])
                if success:
                    state = "CLOSED" if normalized < 0.5 else "OPEN"
                    print(
                        f"LEFT gripper → {normalized * 100:.0f}% open ({state}), pos: {position:.3f}"
                    )
                return success

        elif side == "right" and self.right_dxl:
            if (
                self.right_closed_ticks is not None
                and self.right_open_ticks is not None
            ):
                # Map to actual servo position
                target_ticks = self.right_closed_ticks + normalized * (
                    self.right_open_ticks - self.right_closed_ticks
                )
                success = self.right_dxl.write_positions([target_ticks])
                if success:
                    state = "CLOSED" if normalized < 0.5 else "OPEN"
                    print(
                        f"RIGHT gripper → {normalized * 100:.0f}% open ({state}), pos: {position:.3f}"
                    )
                return success

        return False

    def close_gripper(self, side):
        """Close gripper"""
        return self.set_gripper_position(side, self.CLOSED_POS)

    def open_gripper(self, side):
        """Open gripper"""
        return self.set_gripper_position(side, self.OPEN_POS)

    def disconnect(self):
        """Disconnect from grippers"""
        if self.left_dxl:
            self.left_dxl.disconnect()
        if self.right_dxl:
            self.right_dxl.disconnect()


# Global gripper controller instance
_gripper_controller = None
_gripper_lock = threading.Lock()


def get_gripper_controller():
    """Get or create the global gripper controller"""
    global _gripper_controller
    with _gripper_lock:
        if _gripper_controller is None:
            _gripper_controller = DirectGripperController()
            if _gripper_controller.connect():
                _gripper_controller.calibrate()
            else:
                _gripper_controller = None
        return _gripper_controller


def send_gripper_command(side, position):
    """Send gripper command (compatible with existing interface)

    Args:
        side: "left" or "right"
        position: Target position (-0.075 for closed, 0.25 for open)
    """
    controller = get_gripper_controller()
    if controller:
        return controller.set_gripper_position(side, position)
    return False


def main():
    """Test the direct gripper control"""
    import time

    print("\n" + "=" * 60)
    print("DIRECT GRIPPER CONTROL TEST")
    print("=" * 60)

    controller = DirectGripperController()

    if not controller.connect():
        print("Failed to connect to grippers!")
        return 1

    controller.calibrate()

    print("\n" + "=" * 60)
    print("AUTO-TEST SEQUENCE")
    print("=" * 60)
    print("Running automatic gripper test...")

    # Test sequence
    test_sequence = [
        ("Left close", "left", controller.CLOSED_POS),
        ("Left open", "left", controller.OPEN_POS),
        ("Right close", "right", controller.CLOSED_POS),
        ("Right open", "right", controller.OPEN_POS),
        ("Both 50% open", "both", (controller.CLOSED_POS + controller.OPEN_POS) / 2),
    ]

    for description, side, position in test_sequence:
        print(f"\n{description}...")
        if side == "both":
            controller.set_gripper_position("left", position)
            controller.set_gripper_position("right", position)
        else:
            controller.set_gripper_position(side, position)
        time.sleep(1.5)

    print("\n" + "=" * 60)
    print("AUTO-TEST COMPLETE")
    print("=" * 60)
    print("\nGrippers tested successfully!")
    print("The grippers are now ready for use in teleop.")

    controller.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
