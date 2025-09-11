#!/usr/bin/env python3
"""
Receive and display arm transformation data from ZCM.
This follows the pattern from send_gripper_cmd.py for ZCM interaction.
"""

import sys
import time
import numpy as np

try:
    import zerocm
    from arm_transform_t import arm_transform_t
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install zerocm")
    print("Generate messages with: zcm-gen -p arm_transform.zcm")
    sys.exit(1)


class TransformHandler:
    """Handler for arm transform messages."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.msg_count = 0
        self.last_msg_time = None
        self.rate = 0
        
    def handle(self, channel, msg):
        """Handle incoming transform messages."""
        self.msg_count += 1
        current_time = time.time()
        
        # Calculate rate
        if self.last_msg_time:
            dt = current_time - self.last_msg_time
            self.rate = 1.0 / dt if dt > 0 else 0
        self.last_msg_time = current_time
        
        # Display transform data
        if self.verbose:
            # Detailed output
            print(f"\n[Transform #{self.msg_count}] @ {self.rate:.1f} Hz")
            print(f"  Timestamp: {msg.timestamp} µs")
            print(f"  Valid: {msg.transform_valid}")
            print(f"  Description: {msg.description}")
            print("  Joint Offsets (degrees):")
            for i, offset_rad in enumerate(msg.joint_offsets):
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
                print(f"    J{i+1}: {color}{offset_deg:+7.2f}°{reset} ({offset_rad:+.4f} rad)")
            
            gripper_deg = np.degrees(msg.gripper_offset)
            print(f"  Gripper Offset: {gripper_deg:+7.2f}° ({msg.gripper_offset:+.4f} rad)")
            
            rms_deg = np.degrees(msg.rms_error)
            print(f"  RMS Error: {rms_deg:.3f}° ({msg.rms_error:.6f} rad)")
        else:
            # Compact output (single line update)
            rms_deg = np.degrees(msg.rms_error)
            offsets_deg = [np.degrees(o) for o in msg.joint_offsets]
            offsets_str = " ".join([f"J{i+1}:{o:+5.1f}°" for i, o in enumerate(offsets_deg)])
            
            status = "✓" if msg.transform_valid else "✗"
            print(f"\r[Transform {status}] {self.rate:5.1f}Hz | {offsets_str} | RMS:{rms_deg:5.2f}° | #{self.msg_count}", end="", flush=True)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Receive arm transformation data from ZCM"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed transform information"
    )
    parser.add_argument(
        "-c", "--channel",
        type=str,
        default="arm_transform",
        help="ZCM channel to subscribe to (default: arm_transform)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="ZCM URL (e.g., ipc, udpm://239.255.76.67:7667?ttl=1)"
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
    
    # Create handler and subscribe
    handler = TransformHandler(verbose=args.verbose)
    zcm.subscribe(args.channel, arm_transform_t, handler.handle)
    
    print("=" * 60)
    print("ARM TRANSFORM RECEIVER")
    print("=" * 60)
    print(f"Listening on channel: {args.channel}")
    print(f"Verbose mode: {args.verbose}")
    print("-" * 60)
    print("\nWaiting for transform messages... (Ctrl+C to stop)\n")
    
    if not args.verbose:
        print("Tip: Use --verbose for detailed output\n")
    
    try:
        # Start ZCM
        zcm.start()
        
        # Keep running
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        print(f"\n\n[Summary] Received {handler.msg_count} transform messages")
        if handler.msg_count > 0:
            print(f"Average rate: {handler.msg_count / (time.time() - (handler.last_msg_time - handler.msg_count/handler.rate)):.1f} Hz")
        zcm.stop()


if __name__ == "__main__":
    main()

