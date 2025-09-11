#!/usr/bin/env python3
"""
Direct UR5 gripper control using RTDE.
Bypasses ZCM and directly sends gripper commands to UR5.
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import rtde_control
    import rtde_receive
except ImportError:
    print("Error: ur_rtde not installed. Install with: pip install ur_rtde")
    sys.exit(1)


class DirectGripperControl:
    """Direct control of UR5 grippers via RTDE"""

    def __init__(self, robot_ip):
        self.robot_ip = robot_ip
        self.rtde_c = None
        self.rtde_r = None

    def connect(self):
        """Connect to UR5 robot"""
        try:
            self.rtde_c = rtde_control.RTDEControlInterface(self.robot_ip)
            self.rtde_r = rtde_receive.RTDEReceiveInterface(self.robot_ip)
            print(f"✓ Connected to UR5 at {self.robot_ip}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to {self.robot_ip}: {e}")
            return False

    def send_gripper_command(self, position):
        """Send gripper position command

        Args:
            position: Gripper position (-0.075 for closed, 0.25 for open, or anything in between)
        """
        if not self.rtde_c:
            print("✗ Not connected to robot")
            return False

        try:
            # UR5 grippers typically use Tool Digital Outputs
            # Map position to gripper control
            # This depends on your specific gripper setup

            # For most UR5 setups with grippers:
            # We need to send a URScript command to control the gripper

            # Method 1: Using moveJ with gripper as 7th axis (if configured)
            # current_joints = self.rtde_r.getActualQ()
            # This would need gripper configured as external axis

            # Method 2: Send URScript directly
            # Convert position to gripper-specific command
            # Position range: -0.075 (closed) to 0.25 (open)
            # Map to 0-255 for most grippers or 0-1 for normalized

            # Normalize position to 0-1 range
            normalized = (position - (-0.075)) / (0.25 - (-0.075))
            normalized = max(0.0, min(1.0, normalized))  # Clamp to [0, 1]

            # Create URScript command
            # This format depends on your gripper driver
            # Common formats:

            # For Robotiq grippers:
            # script = f"rq_move({int(normalized * 255)})\n"

            # For OnRobot grippers:
            # script = f"set_tool_digital_out(0, {1 if normalized > 0.5 else 0})\n"

            # For generic grippers using analog output:
            script = f"""
def gripper_control():
    # Set analog output for gripper position
    set_standard_analog_out(0, {normalized})
    
    # Or use tool voltage for some grippers
    # set_tool_voltage(24 if {normalized} > 0.5 else 0)
    
    # Or use digital outputs for open/close
    if {normalized} < 0.5:
        set_tool_digital_out(0, True)   # Close
        set_tool_digital_out(1, False)
    else:
        set_tool_digital_out(0, False)  # Open
        set_tool_digital_out(1, True)
end
gripper_control()
"""

            # Send the script
            self.rtde_c.sendCustomScriptFunction("gripper_control", script)

            percentage = normalized * 100
            state = "CLOSED" if normalized < 0.5 else "OPEN"
            print(
                f"✓ Sent gripper command: {percentage:.0f}% open ({state}), raw: {position:.3f}"
            )

            return True

        except Exception as e:
            print(f"✗ Failed to send gripper command: {e}")
            return False

    def disconnect(self):
        """Disconnect from robot"""
        if self.rtde_c:
            self.rtde_c.disconnect()
        if self.rtde_r:
            self.rtde_r.disconnect()
        print(f"Disconnected from {self.robot_ip}")


def main():
    parser = argparse.ArgumentParser(description="Direct UR5 gripper control")
    parser.add_argument("--ip", type=str, required=True, help="Robot IP address")
    parser.add_argument(
        "--position",
        type=float,
        required=True,
        help="Gripper position (-0.075 for closed, 0.25 for open)",
    )
    parser.add_argument(
        "--side",
        type=str,
        choices=["left", "right"],
        help="Which gripper (for logging)",
    )

    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print("DIRECT UR5 GRIPPER CONTROL")
    print(f"{'=' * 60}")
    print(f"Robot: {args.ip}")
    print(f"Position: {args.position}")
    if args.side:
        print(f"Side: {args.side}")

    # Create controller
    controller = DirectGripperControl(args.ip)

    # Connect
    if not controller.connect():
        print("Failed to connect!")
        return 1

    # Send command
    success = controller.send_gripper_command(args.position)

    # Keep connection briefly to ensure command is processed
    time.sleep(0.5)

    # Disconnect
    controller.disconnect()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
