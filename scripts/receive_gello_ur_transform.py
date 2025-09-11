#!/usr/bin/env python3
"""
Receive GELLO positions and compare with UR5 positions to show offsets.
Shows:
- Left GELLO (J1-7) vs Left UR5 (192.168.1.211)
- Right GELLO (J10-16) vs Right UR5 (192.168.1.210)
"""

import sys
import time

import numpy as np
from genai_types.joint_command_t import joint_command_t
from genai_types.robot_state_t import robot_state_t

try:
    import zerocm
    from gello_positions_t import gello_positions_t
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install zerocm")
    sys.exit(1)

try:
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    print("Error: ur_rtde not installed")
    print("Install with: pip install ur_rtde")
    sys.exit(1)


class GelloURTransformReceiver:
    """Receiver that compares GELLO and UR5 positions."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.msg_count = 0

        # Last received GELLO positions
        self.last_left_gello = None
        self.last_right_gello = None
        self.last_left_time = None
        self.last_right_time = None
        self.last_left_robot_state = None
        self.last_right_robot_state = None

        # Initialize ZCM
        self.zcm = zerocm.ZCM()
        if not self.zcm.good():
            print("Unable to initialize ZCM")
            sys.exit(1)

        # Subscribe to GELLO channels
        self.zcm.subscribe(
            "gello_positions_left", gello_positions_t, self.handle_left_message
        )
        self.zcm.subscribe(
            "gello_positions_right", gello_positions_t, self.handle_right_message
        )

        self.zcm.subscribe(
            "robot_state_left", robot_state_t, self.handle_robot_state_left
        )

        self.zcm.subscribe(
            "robot_state_right", robot_state_t, self.handle_robot_state_right
        )

        print("=" * 70)
        print("GELLO-UR5 TRANSFORM RECEIVER")
        print("-" * 70)

    def handle_left_message(self, channel, msg):
        """Handle left GELLO position messages."""
        self.last_left_gello = msg
        self.last_left_time = time.time()

    def handle_right_message(self, channel, msg):
        """Handle right GELLO position messages."""
        self.last_right_gello = msg
        self.last_right_time = time.time()

    def handle_robot_state_left(self, channel, msg):
        """Handle left robot state messages."""
        self.last_left_robot_state = msg
        self.last_left_robot_state_time = time.time()

    def handle_robot_state_right(self, channel, msg):
        """Handle right robot state messages."""
        self.last_right_robot_state = msg
        self.last_right_robot_state_time = time.time()

    def calculate_and_display_offsets(self):
        """Calculate and display offsets between GELLO and UR5."""
        # Clear screen for clean display
        if not self.verbose:
            print("\033[H\033[J", end="")  # Clear screen
            print("=" * 70)
            print("GELLO-UR5 OFFSETS (GELLO - UR5)")
            print("=" * 70)

        current_time = time.time()

        left_ur_pos = None
        if self.last_left_robot_state is not None:
            left_ur_pos = self.last_left_robot_state.q[0:6]

        right_ur_pos = None
        if self.last_right_robot_state is not None:
            right_ur_pos = self.last_right_robot_state.q[0:6]

        print(self.last_left_robot_state)

        # LEFT ARM OFFSETS (J1-J7 vs UR5)
        print("\n📍 LEFT ARM:")
        if self.last_left_gello and left_ur_pos:
            age = current_time - self.last_left_time
            if age < 1.0:  # Only show if data is fresh
                print(f"  Data age: {age:.3f}s")
                print("  Joint Offsets (GELLO - UR5):")

                # Calculate offsets for joints 1-6
                for i in range(6):
                    gello_rad = self.last_left_gello.joint_positions[i]
                    ur_rad = left_ur_pos[i]
                    offset_rad = gello_rad - ur_rad
                    offset_deg = np.degrees(offset_rad)

                    # Color coding
                    abs_offset = abs(offset_deg)
                    if abs_offset > 10:
                        color = "\033[91m"  # Red
                    elif abs_offset > 5:
                        color = "\033[93m"  # Yellow
                    else:
                        color = "\033[92m"  # Green
                    reset = "\033[0m"

                    # Display as J1, J2, etc.
                    print(
                        f"    J{i + 1}: {color}{offset_deg:+8.3f}°{reset} "
                        f"(GELLO: {np.degrees(gello_rad):7.2f}° "
                        f"UR5: {np.degrees(ur_rad):7.2f}°)"
                    )

                # Gripper (J7) - no UR5 equivalent
                gripper_deg = np.degrees(self.last_left_gello.gripper_position)
                print(f"    J7 (Gripper): {gripper_deg:7.2f}° (GELLO only)")

                # Calculate RMS error for joints 1-6
                offsets = [
                    self.last_left_gello.joint_positions[i] - left_ur_pos[i]
                    for i in range(6)
                ]
                rms_rad = np.sqrt(np.mean(np.array(offsets) ** 2))
                rms_deg = np.degrees(rms_rad)

                if rms_deg > 5:
                    color = "\033[91m"  # Red
                elif rms_deg > 2:
                    color = "\033[93m"  # Yellow
                else:
                    color = "\033[92m"  # Green
                print(f"  RMS Error: {color}{rms_deg:7.3f}°{reset}")
            else:
                print("  ⚠️ GELLO data stale")
        elif self.last_left_gello and not left_ur_pos:
            print("  ✓ GELLO connected")
            print("  ✗ UR5 not connected")
        elif not self.last_left_gello and left_ur_pos:
            print("  ✗ No GELLO data")
            print("  ✓ UR5 connected")
            # Show UR5 positions
            for i in range(6):
                print(f"    UR5 J{i + 1}: {np.degrees(left_ur_pos[i]):7.2f}°")
        else:
            print("  ✗ No data")

        # RIGHT ARM OFFSETS (J10-J16 vs UR5)
        print("\n📍 RIGHT ARM:")
        if self.last_right_gello and right_ur_pos:
            age = current_time - self.last_right_time
            if age < 1.0:  # Only show if data is fresh
                print(f"  Data age: {age:.3f}s")
                print("  Joint Offsets (GELLO - UR5):")

                # Calculate offsets for joints 10-15
                for i in range(6):
                    gello_rad = self.last_right_gello.joint_positions[i]
                    ur_rad = right_ur_pos[i]
                    offset_rad = gello_rad - ur_rad
                    offset_deg = np.degrees(offset_rad)

                    # Color coding
                    abs_offset = abs(offset_deg)
                    if abs_offset > 10:
                        color = "\033[91m"  # Red
                    elif abs_offset > 5:
                        color = "\033[93m"  # Yellow
                    else:
                        color = "\033[92m"  # Green
                    reset = "\033[0m"

                    # Display as J10, J11, etc.
                    print(
                        f"    J{i + 10}: {color}{offset_deg:+8.3f}°{reset} "
                        f"(GELLO: {np.degrees(gello_rad):7.2f}° "
                        f"UR5: {np.degrees(ur_rad):7.2f}°)"
                    )

                # Gripper (J16) - no UR5 equivalent
                gripper_deg = np.degrees(self.last_right_gello.gripper_position)
                print(f"    J16 (Gripper): {gripper_deg:7.2f}° (GELLO only)")

                # Calculate RMS error for joints 10-15
                offsets = [
                    self.last_right_gello.joint_positions[i] - right_ur_pos[i]
                    for i in range(6)
                ]
                rms_rad = np.sqrt(np.mean(np.array(offsets) ** 2))
                rms_deg = np.degrees(rms_rad)

                if rms_deg > 5:
                    color = "\033[91m"  # Red
                elif rms_deg > 2:
                    color = "\033[93m"  # Yellow
                else:
                    color = "\033[92m"  # Green
                print(f"  RMS Error: {color}{rms_deg:7.3f}°{reset}")
            else:
                print("  ⚠️ GELLO data stale")
        elif self.last_right_gello and not right_ur_pos:
            print("  ✓ GELLO connected")
            print("  ✗ UR5 not connected")
        elif not self.last_right_gello and right_ur_pos:
            print("  ✗ No GELLO data")
            print("  ✓ UR5 connected")
            # Show UR5 positions
            for i in range(6):
                print(f"    UR5 J{i + 10}: {np.degrees(right_ur_pos[i]):7.2f}°")
        else:
            print("  ✗ No data")

        print("\n" + "-" * 70)
        print("Press Ctrl+C to stop")

        my_left_command = [0, 0, 0, 0, 0, 1]
        my_right_command = [0, 0, 0, 0, 0, 1]

        left_cmd_msg = joint_command_t()
        left_cmd_msg.joint_pos[0:6] = my_left_command

        right_cmd_msg = joint_command_t()
        right_cmd_msg.joint_pos[0:6] = my_right_command

        self.zcm.publish("joint_command_left_gello", left_cmd_msg)
        self.zcm.publish("joint_command_right_gello", right_cmd_msg)

    def run(self):
        """Run the receiver loop."""
        print(
            "\nReceiving GELLO positions and comparing with UR5... (Ctrl+C to stop)\n"
        )

        if not self.verbose:
            print("Tip: Use --verbose for detailed output")

        try:
            self.zcm.start()
            while True:
                # publish offsets at some rate

                self.calculate_and_display_offsets()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)

            # Show final statistics
            if self.left_ur:
                print(f"✓ LEFT UR5 ({self.left_ur_ip}) was connected")
            else:
                print(f"✗ LEFT UR5 ({self.left_ur_ip}) was not connected")

            if self.right_ur:
                print(f"✓ RIGHT UR5 ({self.right_ur_ip}) was connected")
            else:
                print(f"✗ RIGHT UR5 ({self.right_ur_ip}) was not connected")

            print("=" * 70)

            # Cleanup
            self.running = False
            self.zcm.stop()
            if self.left_ur:
                self.left_ur.disconnect()
            if self.right_ur:
                self.right_ur.disconnect()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare GELLO positions with UR5 positions"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output"
    )
    parser.add_argument(
        "--left-ur",
        type=str,
        default="192.168.1.211",
        help="Left UR5 IP address (default: 192.168.1.211)",
    )
    parser.add_argument(
        "--right-ur",
        type=str,
        default="192.168.1.210",
        help="Right UR5 IP address (default: 192.168.1.210)",
    )

    args = parser.parse_args()

    # Create and run receiver
    receiver = GelloURTransformReceiver(verbose=args.verbose)

    # Override IPs if provided
    if args.left_ur != "192.168.1.211":
        receiver.left_ur_ip = args.left_ur
        print(f"[Override] Left UR5 IP: {args.left_ur}")
    if args.right_ur != "192.168.1.210":
        receiver.right_ur_ip = args.right_ur
        print(f"[Override] Right UR5 IP: {args.right_ur}")

    receiver.run()


if __name__ == "__main__":
    main()
