#!/usr/bin/env python3
"""
Send test GELLO position commands to ZCM channels.
Following the exact pattern from dexgpt's send_gripper_cmd.py for proper ZCM compatibility.
"""

import argparse
import math
import sys
import time

import zerocm

# Import the generated message type
try:
    from gello_positions_t import gello_positions_t
except ImportError:
    print("Error: gello_positions_t not found")
    print("Run: zcm-gen -p gello_positions_simple.zcm")
    sys.exit(1)


def robot_time():
    """Get current time in microseconds (matching dexgpt pattern)."""
    return int(time.time() * 1e6)


def send_position(zcm, channel, positions, gripper, arm_side, velocities=None):
    """Send a single position message."""
    msg = gello_positions_t()
    msg.timestamp = robot_time()
    msg.joint_positions = positions
    msg.gripper_position = gripper
    msg.joint_velocities = velocities if velocities else [0.0] * 6
    msg.is_valid = True
    msg.arm_side = arm_side

    zcm.publish(channel, msg)


def main():
    parser = argparse.ArgumentParser(
        description="Send test GELLO positions to ZCM channels"
    )
    parser.add_argument(
        "-l",
        "--left-channel",
        type=str,
        default="gello_positions_left",
        help="Left arm channel name",
    )
    parser.add_argument(
        "-r",
        "--right-channel",
        type=str,
        default="gello_positions_right",
        help="Right arm channel name",
    )
    parser.add_argument("--sin", action="store_true", help="Send sinusoidal positions")
    parser.add_argument(
        "--frequency",
        type=float,
        default=0.1,
        help="Frequency of sinusoidal motion (Hz)",
    )
    parser.add_argument("--static", action="store_true", help="Send static positions")
    parser.add_argument(
        "--rate", type=float, default=10.0, help="Publishing rate in Hz"
    )
    parser.add_argument(
        "--arm",
        type=str,
        choices=["left", "right", "both"],
        default="both",
        help="Which arm(s) to send",
    )

    args = parser.parse_args()

    # Initialize ZCM
    zcm = zerocm.ZCM()
    if not zcm.good():
        print("Unable to initialize ZCM")
        sys.exit(1)

    zcm.start()

    # Base positions (radians)
    left_base = [-0.785, -1.571, 0.0, -1.571, 1.571, 0.0]  # -45, -90, 0, -90, 90, 0 deg
    right_base = [
        0.785,
        -1.571,
        0.0,
        -1.571,
        -1.571,
        0.0,
    ]  # 45, -90, 0, -90, -90, 0 deg

    # Gripper ranges (from actual GELLO measurements)
    left_gripper_min = 2.5112  # closed
    left_gripper_max = 3.4316  # open
    right_gripper_min = 4.1050  # closed
    right_gripper_max = 5.0929  # open

    print(f"[ZCM] Publishing at {args.rate} Hz")
    if args.arm in ["left", "both"]:
        print(f"  LEFT:  {args.left_channel}")
    if args.arm in ["right", "both"]:
        print(f"  RIGHT: {args.right_channel}")

    if args.sin:
        print("Mode: Sinusoidal motion")
    elif args.static:
        print("Mode: Static positions")
    else:
        print("Mode: Default (sine wave)")

    print("\nPublishing... (Ctrl+C to stop)")

    start_time = robot_time()
    msg_count = 0
    sleep_time = 1.0 / args.rate

    try:
        while True:
            elapsed = (robot_time() - start_time) * 1e-6  # Convert to seconds

            if args.static:
                # Static positions
                left_positions = left_base
                right_positions = right_base
                left_gripper = (left_gripper_min + left_gripper_max) / 2
                right_gripper = (right_gripper_min + right_gripper_max) / 2

            else:  # Default to sine wave
                # Sinusoidal motion
                phase = 2 * math.pi * args.frequency * elapsed

                # Joint positions with different phases
                left_positions = [
                    left_base[i] + 0.2 * math.sin(phase + i * 0.5) for i in range(6)
                ]
                right_positions = [
                    right_base[i] + 0.2 * math.sin(phase - i * 0.5) for i in range(6)
                ]

                # Gripper oscillation
                gripper_phase = 2 * math.pi * (args.frequency * 2) * elapsed
                left_gripper = left_gripper_min + (
                    left_gripper_max - left_gripper_min
                ) * (0.5 + 0.5 * math.sin(gripper_phase))
                right_gripper = right_gripper_min + (
                    right_gripper_max - right_gripper_min
                ) * (0.5 + 0.5 * math.sin(gripper_phase + math.pi))

            # Send messages
            if args.arm in ["left", "both"]:
                send_position(
                    zcm, args.left_channel, left_positions, left_gripper, "left"
                )

            if args.arm in ["right", "both"]:
                send_position(
                    zcm, args.right_channel, right_positions, right_gripper, "right"
                )

            msg_count += 1

            # Print status every second
            if msg_count % int(args.rate) == 0:
                print(f"  Sent {msg_count} messages...")

            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print(f"\n\n[Summary] Published {msg_count} messages")
    finally:
        zcm.stop()


if __name__ == "__main__":
    main()
