#!/usr/bin/env python3
"""
Receive and display GELLO LEFT arm positions from ZCM channel.
Following the exact pattern from dexgpt's send_gripper_cmd.py for proper ZCM compatibility.
"""

import argparse
import sys
import time

import numpy as np
import zerocm

# Import the generated message type
try:
    from gello_positions_t import gello_positions_t
except ImportError:
    print("Error: gello_positions_t not found")
    print("Run: zcm-gen -p gello_positions_simple.zcm")
    sys.exit(1)


class MessageHandler:
    """Handler for incoming GELLO position messages."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.msg_count = 0
        self.last_msg_time = None
        self.last_timestamp = 0

    def handle(self, channel, msg):
        """Handle incoming message on the channel."""
        self.msg_count += 1
        current_time = time.time()

        # Calculate message rate
        rate = 0.0
        if self.last_msg_time:
            dt = current_time - self.last_msg_time
            if dt > 0:
                rate = 1.0 / dt
        self.last_msg_time = current_time

        # Check for timestamp changes
        timestamp_changed = msg.timestamp != self.last_timestamp
        self.last_timestamp = msg.timestamp

        if self.verbose:
            # Detailed output
            print(f"\n[MSG #{self.msg_count}] Channel: {channel}")
            print(f"  Timestamp: {msg.timestamp} µs")
            print(f"  Rate: {rate:.1f} Hz")
            print(f"  Arm: {msg.arm_side}")
            print(f"  Valid: {msg.is_valid}")
            print("  Joint Positions (rad):")
            for i, pos in enumerate(msg.joint_positions):
                deg = np.degrees(pos)
                print(f"    J{i + 1}: {pos:+.4f} rad ({deg:+7.2f}°)")
            print(
                f"  Gripper: {msg.gripper_position:+.4f} rad ({np.degrees(msg.gripper_position):+7.2f}°)"
            )
            print("  Joint Velocities (rad/s):")
            for i, vel in enumerate(msg.joint_velocities):
                print(f"    J{i + 1}: {vel:+.4f}")
        else:
            # Compact output on single line
            if timestamp_changed:  # Only print when data actually updates
                joints_deg = [np.degrees(p) for p in msg.joint_positions]
                joints_str = " ".join(
                    [f"J{i + 1}:{d:+6.1f}°" for i, d in enumerate(joints_deg)]
                )
                gripper_deg = np.degrees(msg.gripper_position)
                valid_mark = "✓" if msg.is_valid else "✗"

                print(
                    f"\r[LEFT {valid_mark}] #{self.msg_count:5d} ({rate:5.1f}Hz) "
                    f"{joints_str} G:{gripper_deg:+6.1f}°",
                    end="",
                    flush=True,
                )


def main():
    parser = argparse.ArgumentParser(
        description="Receive GELLO LEFT arm positions from ZCM channel"
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        default="gello_positions_left",
        help="ZCM channel name (default: gello_positions_left)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--url", type=str, default="", help="ZCM URL (default: use ZCM default)"
    )

    args = parser.parse_args()

    # Initialize ZCM
    if args.url:
        zcm = zerocm.ZCM(args.url)
    else:
        zcm = zerocm.ZCM()

    if not zcm.good():
        print("Unable to initialize ZCM")
        sys.exit(1)

    # Create handler
    handler = MessageHandler(verbose=args.verbose)

    # Subscribe to channel
    zcm.subscribe(args.channel, gello_positions_t, handler.handle)

    print(f"[ZCM] Listening on channel: {args.channel}")
    if args.url:
        print(f"[ZCM] URL: {args.url}")
    print("-" * 60)
    print("Waiting for messages... (Ctrl+C to stop)")
    if not args.verbose:
        print("Tip: Use -v for detailed output\n")

    # Start receiving
    zcm.start()

    try:
        while True:
            time.sleep(0.001)  # Small sleep to prevent CPU spinning
            # Could also use zcm.handle() in a loop instead
    except KeyboardInterrupt:
        print(f"\n\n[Summary] Received {handler.msg_count} messages")
    finally:
        zcm.stop()


if __name__ == "__main__":
    main()
