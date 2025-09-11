#!/usr/bin/env python3
"""
Receive and display BOTH GELLO arm positions from ZCM channels.
This script subscribes to both 'gello_positions_left' and 'gello_positions_right'
channels and displays the joint and gripper positions in real-time.
"""

import sys
import time
from datetime import datetime
from typing import Optional

import numpy as np

try:
    import zerocm
    from arm_transform_t import arm_transform_t
    from gello_positions_t import gello_positions_t
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install zerocm")
    print("Generate messages with:")
    print("  zcm-gen -p gello_positions_simple.zcm")
    print("  zcm-gen -p arm_transform.zcm")
    sys.exit(1)


class DualGelloReceiver:
    """Receiver for both GELLO arm positions."""

    def __init__(
        self, verbose=False, display_mode="side_by_side", publish_transform=True
    ):
        self.verbose = verbose
        self.display_mode = display_mode  # "side_by_side", "stacked", "compact"
        self.publish_transform = publish_transform

        # Track messages for each arm
        self.left_msg_count = 0
        self.right_msg_count = 0
        self.left_last_msg = None
        self.right_last_msg = None
        self.left_last_time = None
        self.right_last_time = None
        self.left_rate = 0
        self.right_rate = 0

        # Transform publishing
        self.transform_count = 0
        self.transform_channel = "arm_transform"

        # Initialize ZCM
        self.zcm = zerocm.ZCM()
        if not self.zcm.good():
            print("Unable to initialize ZCM")
            sys.exit(1)

        # Subscribe to both channels
        self.zcm.subscribe(
            "gello_positions_left", gello_positions_t, self.handle_left_message
        )
        self.zcm.subscribe(
            "gello_positions_right", gello_positions_t, self.handle_right_message
        )

        print("=" * 80)
        print("DUAL GELLO ARM POSITION RECEIVER")
        print("=" * 80)
        print("Listening for messages on:")
        print("  - gello_positions_left")
        print("  - gello_positions_right")
        if self.publish_transform:
            print("Publishing transforms to:")
            print(f"  - {self.transform_channel}")
        print("-" * 80)

    def handle_left_message(self, channel, msg):
        """Handle incoming LEFT GELLO position messages."""
        self.left_msg_count += 1
        current_time = time.time()

        # Calculate message rate
        if self.left_last_time:
            dt = current_time - self.left_last_time
            self.left_rate = 1.0 / dt if dt > 0 else 0
        self.left_last_time = current_time
        self.left_last_msg = msg

        # Publish transform if both arms have data
        if self.publish_transform and self.left_last_msg and self.right_last_msg:
            self.publish_arm_transform()

        # Display update
        self.display_update()

    def handle_right_message(self, channel, msg):
        """Handle incoming RIGHT GELLO position messages."""
        self.right_msg_count += 1
        current_time = time.time()

        # Calculate message rate
        if self.right_last_time:
            dt = current_time - self.right_last_time
            self.right_rate = 1.0 / dt if dt > 0 else 0
        self.right_last_time = current_time
        self.right_last_msg = msg

        # Publish transform if both arms have data
        if self.publish_transform and self.left_last_msg and self.right_last_msg:
            self.publish_arm_transform()

        # Display update
        self.display_update()

    def format_joint_angles(
        self,
        msg: Optional[gello_positions_t],
        compact: bool = False,
        arm_side: str = "left",
    ) -> str:
        """Format joint angles for display.

        Args:
            msg: Message with joint positions
            compact: Use compact single-line format
            arm_side: 'left' or 'right' to determine joint numbering
        """
        if not msg:
            return "No data" if not compact else "---"

        joints_deg = [np.degrees(j) for j in msg.joint_positions]
        gripper_deg = np.degrees(msg.gripper_position)

        # Determine joint numbering based on arm side
        if arm_side == "left":
            joint_offset = 1  # J1-J6 for left
            gripper_num = 7  # J7 for left gripper
        else:  # right
            joint_offset = 10  # J10-J15 for right
            gripper_num = 16  # J16 for right gripper

        if compact:
            # Compact format: J1:45.2 J2:-90.1 ... or J10:45.2 J11:-90.1 ...
            joints_str = " ".join(
                [f"J{i + joint_offset}:{deg:6.1f}°" for i, deg in enumerate(joints_deg)]
            )
            return f"{joints_str} J{gripper_num}:{gripper_deg:6.1f}°"
        else:
            # Detailed format
            lines = []
            for i, deg in enumerate(joints_deg):
                rad = msg.joint_positions[i]
                # Color code based on angle
                if abs(deg) > 180:
                    color = "\033[91m"  # Red for out of range
                elif abs(deg) > 90:
                    color = "\033[93m"  # Yellow
                else:
                    color = "\033[92m"  # Green
                reset = "\033[0m"
                joint_num = i + joint_offset
                lines.append(
                    f"  J{joint_num}: {color}{deg:7.2f}°{reset} ({rad:7.4f} rad)"
                )
            lines.append(
                f"  J{gripper_num} (Gripper): {gripper_deg:7.2f}° ({msg.gripper_position:7.4f} rad)"
            )
            return "\n".join(lines)

    def publish_arm_transform(self):
        """Calculate and publish the transformation between left and right arms."""
        if not self.left_last_msg or not self.right_last_msg:
            return

        # Create transform message
        transform_msg = arm_transform_t()
        transform_msg.timestamp = int(time.time() * 1e6)  # microseconds

        # Calculate joint offsets (left - right)
        offsets = []
        for i in range(6):
            offset = (
                self.left_last_msg.joint_positions[i]
                - self.right_last_msg.joint_positions[i]
            )
            offsets.append(offset)

        transform_msg.joint_offsets = offsets

        # Calculate gripper offset
        transform_msg.gripper_offset = (
            self.left_last_msg.gripper_position - self.right_last_msg.gripper_position
        )

        # Calculate RMS error
        transform_msg.rms_error = np.sqrt(np.mean(np.array(offsets) ** 2))

        # Set validity
        transform_msg.transform_valid = (
            self.left_last_msg.is_valid and self.right_last_msg.is_valid
        )

        # Add description
        transform_msg.description = (
            f"Transform: LEFT - RIGHT (RMS: {np.degrees(transform_msg.rms_error):.2f}°)"
        )

        # Publish the transform
        self.zcm.publish(self.transform_channel, transform_msg)
        self.transform_count += 1

        # Debug output every 100 messages
        if self.transform_count % 100 == 0 and self.verbose:
            print(f"[TRANSFORM] Published {self.transform_count} transform messages")
            print(f"  Latest RMS error: {np.degrees(transform_msg.rms_error):.2f}°")

    def display_update(self):
        """Update the display with current data."""
        if self.display_mode == "side_by_side":
            self.display_side_by_side()
        elif self.display_mode == "stacked":
            self.display_stacked()
        else:  # compact
            self.display_compact()

    def display_side_by_side(self):
        """Display both arms side by side."""
        # Clear screen for clean display
        if not self.verbose:
            print("\033[2J\033[H", end="")  # Clear screen and move to top

        # Header
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n[{timestamp}] DUAL GELLO ARM POSITIONS")
        print("=" * 80)

        # Status line
        left_status = "✓" if self.left_last_msg and self.left_last_msg.is_valid else "✗"
        right_status = (
            "✓" if self.right_last_msg and self.right_last_msg.is_valid else "✗"
        )

        print(
            f"LEFT ARM {left_status}  [{self.left_rate:5.1f} Hz] #{self.left_msg_count:<6} | "
            f"RIGHT ARM {right_status} [{self.right_rate:5.1f} Hz] #{self.right_msg_count:<6}"
        )
        print("-" * 80)

        # Joint positions
        if self.left_last_msg or self.right_last_msg:
            # Get formatted strings
            left_lines = (
                self.format_joint_angles(self.left_last_msg, arm_side="left").split(
                    "\n"
                )
                if self.left_last_msg
                else ["  No data"]
            )
            right_lines = (
                self.format_joint_angles(self.right_last_msg, arm_side="right").split(
                    "\n"
                )
                if self.right_last_msg
                else ["  No data"]
            )

            # Pad to same length
            max_lines = max(len(left_lines), len(right_lines))
            left_lines += [""] * (max_lines - len(left_lines))
            right_lines += [""] * (max_lines - len(right_lines))

            # Print side by side
            for left, right in zip(left_lines, right_lines):
                print(f"{left:<38} | {right}")

        print("-" * 80)

        # Calculate offsets if both arms have data
        if self.left_last_msg and self.right_last_msg:
            print("\nOFFSET (LEFT - RIGHT):")
            offsets = []
            for i in range(6):
                offset_rad = (
                    self.left_last_msg.joint_positions[i]
                    - self.right_last_msg.joint_positions[i]
                )
                offset_deg = np.degrees(offset_rad)
                offsets.append(offset_rad)

                # Color code
                abs_offset = abs(offset_deg)
                if abs_offset > 10:
                    color = "\033[91m"  # Red
                elif abs_offset > 5:
                    color = "\033[93m"  # Yellow
                else:
                    color = "\033[92m"  # Green
                reset = "\033[0m"

                # Show offset as J1-J10, J2-J11, etc.
                left_j = i + 1
                right_j = i + 10
                print(
                    f"  J{left_j}-J{right_j}: {color}{offset_deg:+7.2f}°{reset}",
                    end="  ",
                )
                if (i + 1) % 3 == 0:
                    print()  # New line every 3 joints

            # RMS error
            rms_rad = np.sqrt(np.mean(np.array(offsets) ** 2))
            rms_deg = np.degrees(rms_rad)
            print(f"\n  RMS: {rms_deg:.2f}°")

        print("\n(Press Ctrl+C to stop)")

    def display_stacked(self):
        """Display arms in stacked format."""
        # Clear previous output
        if not self.verbose:
            print("\033[15A", end="")  # Move up 15 lines

        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] GELLO ARM POSITIONS")
        print("=" * 60)

        # LEFT ARM
        print(f"\nLEFT ARM  [{self.left_rate:5.1f} Hz] Messages: {self.left_msg_count}")
        print("-" * 40)
        if self.left_last_msg:
            print(self.format_joint_angles(self.left_last_msg, arm_side="left"))
        else:
            print("  Waiting for data...")

        # RIGHT ARM
        print(
            f"\nRIGHT ARM [{self.right_rate:5.1f} Hz] Messages: {self.right_msg_count}"
        )
        print("-" * 40)
        if self.right_last_msg:
            print(self.format_joint_angles(self.right_last_msg, arm_side="right"))
        else:
            print("  Waiting for data...")

        print("\n" + "=" * 60)

    def display_compact(self):
        """Display in compact single-line format."""
        # Build compact display string
        left_str = (
            self.format_joint_angles(self.left_last_msg, compact=True, arm_side="left")
            if self.left_last_msg
            else "Waiting..."
        )
        right_str = (
            self.format_joint_angles(
                self.right_last_msg, compact=True, arm_side="right"
            )
            if self.right_last_msg
            else "Waiting..."
        )

        # Status indicators
        left_status = "✓" if self.left_last_msg and self.left_last_msg.is_valid else "✗"
        right_status = (
            "✓" if self.right_last_msg and self.right_last_msg.is_valid else "✗"
        )

        # Print on two lines, updating in place
        print(f"\r[L {left_status}] {left_str} ({self.left_rate:4.1f}Hz)", end="")
        print(f"\n\r[R {right_status}] {right_str} ({self.right_rate:4.1f}Hz)", end="")
        print("\033[1A", end="")  # Move cursor up one line
        sys.stdout.flush()

    def run(self):
        """Run the receiver loop."""
        print("\nReceiving DUAL GELLO arm positions... (Ctrl+C to stop)\n")

        if not self.verbose:
            print(f"Display mode: {self.display_mode}")
            print("Tip: Use --verbose for detailed output\n")

        try:
            self.zcm.start()
            while True:
                time.sleep(0.01)  # Small sleep to prevent CPU spinning
        except KeyboardInterrupt:
            # Clear line and show summary
            print("\033[2K\r", end="")  # Clear current line
            print("\n\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"LEFT  ARM: Received {self.left_msg_count} messages")
            print(f"RIGHT ARM: Received {self.right_msg_count} messages")
            print(f"TOTAL:     {self.left_msg_count + self.right_msg_count} messages")
            if self.publish_transform:
                print(f"TRANSFORMS: {self.transform_count} messages published")

            # Final offset if available
            if self.left_last_msg and self.right_last_msg:
                print("\nFINAL OFFSET (LEFT - RIGHT):")
                for i in range(6):
                    offset_deg = np.degrees(
                        self.left_last_msg.joint_positions[i]
                        - self.right_last_msg.joint_positions[i]
                    )
                    print(f"  J{i + 1}: {offset_deg:+7.2f}°", end="")
                    if (i + 1) % 3 == 0:
                        print()

            print("\n" + "=" * 60)
            self.zcm.stop()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Receive BOTH GELLO arm positions from ZCM"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed message information"
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        choices=["side_by_side", "stacked", "compact"],
        default="side_by_side",
        help="Display mode (default: side_by_side)",
    )
    parser.add_argument(
        "--left-channel",
        type=str,
        default="gello_positions_left",
        help="Left arm ZCM channel (default: gello_positions_left)",
    )
    parser.add_argument(
        "--right-channel",
        type=str,
        default="gello_positions_right",
        help="Right arm ZCM channel (default: gello_positions_right)",
    )
    parser.add_argument(
        "--transform-channel",
        type=str,
        default="arm_transform",
        help="Channel to publish transform data (default: arm_transform)",
    )
    parser.add_argument(
        "--no-transform",
        action="store_true",
        help="Disable publishing transformation data",
    )

    args = parser.parse_args()

    # Create and run receiver
    receiver = DualGelloReceiver(
        verbose=args.verbose,
        display_mode=args.mode,
        publish_transform=(not args.no_transform),
    )

    # Set transform channel if specified
    if args.transform_channel:
        receiver.transform_channel = args.transform_channel

    # Override channels if specified
    if (
        args.left_channel != "gello_positions_left"
        or args.right_channel != "gello_positions_right"
    ):
        print("[Override] Channels:")
        print(f"  Left:  {args.left_channel}")
        print(f"  Right: {args.right_channel}")
        # Note: Would need to re-subscribe here if channels are different

    receiver.run()


if __name__ == "__main__":
    main()
