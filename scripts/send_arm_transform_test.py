#!/usr/bin/env python3
"""
Test publisher for arm transformation messages.
Follows the pattern from send_gripper_cmd.py for ZCM compatibility.
"""

import argparse
import math
import sys
import time

import numpy as np

try:
    import zerocm
    from arm_transform_t import arm_transform_t
except ImportError as e:
    print(f"Error: {e}")
    sys.exit(1)


def robot_time():
    """Return current time in microseconds."""
    return int(time.time() * 1e6)


def send_transform(zcm, channel, offsets, rms_error):
    """Send a transform message."""
    msg = arm_transform_t()
    msg.timestamp = robot_time()
    msg.joint_offsets = offsets
    msg.gripper_offset = 0.1  # Example gripper offset
    msg.rms_error = rms_error
    msg.transform_valid = True
    msg.description = f"Transform at {time.strftime('%H:%M:%S')}"

    zcm.publish(channel, msg)


def main():
    parser = argparse.ArgumentParser(
        description="Send arm transformation test messages"
    )
    parser.add_argument(
        "-o",
        "--output_channel",
        type=str,
        default="arm_transform",
        help="Output ZCM channel (default: arm_transform)",
    )
    parser.add_argument(
        "--static", action="store_true", help="Send static transform values"
    )
    parser.add_argument(
        "--sin", action="store_true", help="Send sinusoidal transform values"
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=0.2,
        help="Frequency for sinusoidal mode (Hz)",
    )

    args = parser.parse_args()

    # Initialize ZCM
    zcm = zerocm.ZCM()
    if not zcm.good():
        print("Unable to initialize ZCM")
        sys.exit(1)

    zcm.start()

    print(f"Publishing arm transforms to channel: {args.output_channel}")

    if args.static:
        print("Sending static transform values...")
        # Static offsets (small values in radians)
        offsets = [
            0.02,  # J1: ~1.1 degrees
            -0.01,  # J2: ~-0.6 degrees
            0.03,  # J3: ~1.7 degrees
            -0.02,  # J4: ~-1.1 degrees
            0.01,  # J5: ~0.6 degrees
            -0.005,  # J6: ~-0.3 degrees
        ]
        rms_error = np.sqrt(np.mean(np.array(offsets) ** 2))

        while True:
            send_transform(zcm, args.output_channel, offsets, rms_error)
            time.sleep(0.1)  # 10Hz

    elif args.sin:
        print(f"Sending sinusoidal transforms at {args.frequency} Hz...")
        start_time = robot_time()

        while True:
            elapsed = (robot_time() - start_time) * 1e-6  # Convert to seconds
            phase = 2 * math.pi * args.frequency * elapsed

            # Create varying offsets
            offsets = [
                0.05 * math.sin(phase),  # J1
                0.03 * math.cos(phase),  # J2
                0.02 * math.sin(phase * 2),  # J3
                0.04 * math.cos(phase * 1.5),  # J4
                0.03 * math.sin(phase * 0.5),  # J5
                0.02 * math.cos(phase * 3),  # J6
            ]

            rms_error = np.sqrt(np.mean(np.array(offsets) ** 2))
            send_transform(zcm, args.output_channel, offsets, rms_error)

            # Display periodically
            if int(elapsed * 10) % 10 == 0 and int(elapsed * 10) != int(
                (elapsed - 0.1) * 10
            ):
                rms_deg = np.degrees(rms_error)
                print(f"  t={elapsed:.1f}s, RMS={rms_deg:.2f}°")

            time.sleep(0.05)  # 20Hz
    else:
        # Send a single test message
        print("Sending single test transform...")
        offsets = [0.01, -0.02, 0.015, -0.01, 0.02, -0.005]
        rms_error = np.sqrt(np.mean(np.array(offsets) ** 2))

        send_transform(zcm, args.output_channel, offsets, rms_error)
        print(f"  Sent transform with RMS error: {np.degrees(rms_error):.2f}°")
        time.sleep(0.1)

        print("\nUse --static or --sin for continuous publishing")


if __name__ == "__main__":
    main()
