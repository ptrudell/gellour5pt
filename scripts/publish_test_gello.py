#!/usr/bin/env python3
"""
Publish test GELLO positions to ZCM channels.
This script simulates GELLO arm movements for testing the ZCM messaging system.
"""

import argparse
import math
import sys
import time

import numpy as np

try:
    import zerocm
    from gello_msgs.gello_positions_t import gello_positions_t
except ImportError:
    print("Error: zerocm not installed")
    print("Install with: pip install zerocm")
    sys.exit(1)


class GelloTestPublisher:
    """Test publisher for GELLO arm positions."""

    def __init__(self, rate_hz=10.0):
        self.rate_hz = rate_hz
        self.left_channel = "gello_positions_left"
        self.right_channel = "gello_positions_right"

        # Initialize ZCM
        self.zcm = zerocm.ZCM()
        if not self.zcm.good():
            print("Unable to initialize ZCM")
            sys.exit(1)

        self.zcm.start()
        print(f"[ZCM] Publishing test GELLO positions at {rate_hz} Hz")
        print(f"      LEFT:  {self.left_channel}")
        print(f"      RIGHT: {self.right_channel}")
        print("-" * 60)

    def publish_positions(self, arm="both", mode="sine"):
        """Publish test positions.

        Args:
            arm: "left", "right", or "both"
            mode: "sine", "step", "static", or "random"
        """
        print(f"\nPublishing {mode} pattern to {arm} arm(s)... (Ctrl+C to stop)\n")

        msg_count = 0
        start_time = time.time()
        sleep_time = 1.0 / self.rate_hz

        # Base positions (home position in radians)
        base_left = [
            -0.785,
            -1.571,
            0.0,
            -1.571,
            1.571,
            0.0,
        ]  # -45, -90, 0, -90, 90, 0 degrees
        base_right = [
            0.785,
            -1.571,
            0.0,
            -1.571,
            -1.571,
            0.0,
        ]  # 45, -90, 0, -90, -90, 0 degrees

        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time

                # Generate positions based on mode
                if mode == "sine":
                    # Sinusoidal movement on all joints
                    left_positions = [
                        base_left[i]
                        + 0.2 * math.sin(2 * math.pi * 0.1 * elapsed + i * 0.5)
                        for i in range(6)
                    ]
                    right_positions = [
                        base_right[i]
                        + 0.2 * math.sin(2 * math.pi * 0.1 * elapsed - i * 0.5)
                        for i in range(6)
                    ]
                    # Gripper oscillates between open and closed
                    left_gripper = 2.5 + 0.5 * (
                        1 + math.sin(2 * math.pi * 0.2 * elapsed)
                    )
                    right_gripper = 4.1 + 0.5 * (
                        1 + math.sin(2 * math.pi * 0.2 * elapsed + math.pi)
                    )

                elif mode == "step":
                    # Step changes every 2 seconds
                    step = int(elapsed / 2) % 4
                    if step == 0:
                        left_positions = base_left
                        right_positions = base_right
                    elif step == 1:
                        left_positions = [p + 0.3 for p in base_left]
                        right_positions = [p - 0.3 for p in base_right]
                    elif step == 2:
                        left_positions = [p - 0.3 for p in base_left]
                        right_positions = [p + 0.3 for p in base_right]
                    else:
                        left_positions = base_left
                        right_positions = base_right

                    # Gripper toggles
                    left_gripper = 2.5 if step % 2 == 0 else 3.4
                    right_gripper = 4.1 if step % 2 == 0 else 5.0

                elif mode == "static":
                    # Static positions
                    left_positions = base_left
                    right_positions = base_right
                    left_gripper = 3.0
                    right_gripper = 4.5

                elif mode == "random":
                    # Random positions within limits
                    left_positions = [
                        base_left[i] + np.random.uniform(-0.3, 0.3) for i in range(6)
                    ]
                    right_positions = [
                        base_right[i] + np.random.uniform(-0.3, 0.3) for i in range(6)
                    ]
                    left_gripper = np.random.uniform(2.5, 3.4)
                    right_gripper = np.random.uniform(4.1, 5.0)
                else:
                    print(f"Unknown mode: {mode}")
                    return

                # Create and publish messages
                timestamp = int(current_time * 1e6)

                if arm in ["left", "both"]:
                    left_msg = gello_positions_t()
                    left_msg.timestamp = timestamp
                    left_msg.joint_positions = left_positions
                    left_msg.gripper_position = left_gripper
                    left_msg.joint_velocities = [
                        0.0
                    ] * 6  # Could calculate real velocities
                    left_msg.is_valid = True
                    left_msg.arm_side = "left"
                    self.zcm.publish(self.left_channel, left_msg)

                if arm in ["right", "both"]:
                    right_msg = gello_positions_t()
                    right_msg.timestamp = timestamp
                    right_msg.joint_positions = right_positions
                    right_msg.gripper_position = right_gripper
                    right_msg.joint_velocities = [
                        0.0
                    ] * 6  # Could calculate real velocities
                    right_msg.is_valid = True
                    right_msg.arm_side = "right"
                    self.zcm.publish(self.right_channel, right_msg)

                msg_count += 1

                # Print status every second
                if msg_count % int(self.rate_hz) == 0:
                    if arm == "both":
                        l_str = f"L:[J1:{np.degrees(left_positions[0]):.0f}° "
                        l_str += f"J2:{np.degrees(left_positions[1]):.0f}° ... "
                        l_str += f"G:{np.degrees(left_gripper):.0f}°]"
                        r_str = f"R:[J1:{np.degrees(right_positions[0]):.0f}° "
                        r_str += f"J2:{np.degrees(right_positions[1]):.0f}° ... "
                        r_str += f"G:{np.degrees(right_gripper):.0f}°]"
                        print(f"[{msg_count:5d} msgs] {l_str} {r_str}")
                    elif arm == "left":
                        print(
                            f"[{msg_count:5d} msgs] LEFT: J1:{np.degrees(left_positions[0]):.0f}° "
                            f"J2:{np.degrees(left_positions[1]):.0f}° ... "
                            f"G:{np.degrees(left_gripper):.0f}°"
                        )
                    else:
                        print(
                            f"[{msg_count:5d} msgs] RIGHT: J1:{np.degrees(right_positions[0]):.0f}° "
                            f"J2:{np.degrees(right_positions[1]):.0f}° ... "
                            f"G:{np.degrees(right_gripper):.0f}°"
                        )

                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print(f"\n\n[Summary] Published {msg_count} messages")
            self.zcm.stop()


def main():
    parser = argparse.ArgumentParser(
        description="Publish test GELLO positions to ZCM channels"
    )
    parser.add_argument(
        "-a",
        "--arm",
        type=str,
        choices=["left", "right", "both"],
        default="both",
        help="Which arm(s) to publish (default: both)",
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["sine", "step", "static", "random"],
        default="sine",
        help="Movement pattern to generate (default: sine)",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=float,
        default=10.0,
        help="Publishing rate in Hz (default: 10)",
    )

    args = parser.parse_args()

    # Create and run publisher
    publisher = GelloTestPublisher(rate_hz=args.rate)
    publisher.publish_positions(arm=args.arm, mode=args.mode)


if __name__ == "__main__":
    main()
