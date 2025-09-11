#!/usr/bin/env python3
"""
Get current UR5 joint angles and display them in both radians and degrees.

Usage:
    python scripts/get_ur_angles.py                  # Default to 192.168.1.210
    python scripts/get_ur_angles.py --ip 192.168.1.211  # Specify IP
    python scripts/get_ur_angles.py --both           # Show both arms
    python scripts/get_ur_angles.py --json           # Output as JSON
    python scripts/get_ur_angles.py --continuous     # Continuous monitoring
"""

import argparse
import json
import sys
import time
from typing import List, Optional

import numpy as np

try:
    from rtde_shim import RTDEReceiveInterface
except ImportError:
    print("Error: rtde_shim not found")
    print("Try: pip install ur_rtde or check your Python path")
    sys.exit(1)


def get_ur_positions(ip: str) -> Optional[List[float]]:
    """Get current joint positions from UR5."""
    try:
        rtde = RTDEReceiveInterface(ip)
        positions = rtde.getActualQ()  # Returns list of 6 radians
        rtde.disconnect()
        return positions
    except Exception as e:
        print(f"Error connecting to {ip}: {e}")
        return None


def display_positions(
    positions: List[float], label: str = "UR5", json_output: bool = False
):
    """Display joint positions in a formatted way."""

    if json_output:
        # JSON output for scripting
        data = {
            "label": label,
            "radians": [round(p, 6) for p in positions],
            "degrees": [round(np.degrees(p), 2) for p in positions],
            "timestamp": time.time(),
        }
        print(json.dumps(data))
    else:
        # Human-readable output
        print(f"\n{label} Joint Positions:")
        print("-" * 50)
        print(f"{'Joint':<8} {'Radians':<12} {'Degrees':<12}")
        print("-" * 50)

        for i, pos in enumerate(positions):
            deg = np.degrees(pos)
            print(f"J{i + 1:<7} {pos:>11.4f}  {deg:>11.2f}°")

        print("-" * 50)

        # Also print as arrays for easy copying
        print("\nAs arrays:")
        print(f"Radians: [{', '.join([f'{p:.4f}' for p in positions])}]")
        print(f"Degrees: [{', '.join([f'{np.degrees(p):.2f}' for p in positions])}]")


def monitor_continuous(ip: str, rate_hz: float = 10.0):
    """Continuously monitor and display UR5 positions."""

    print(f"Monitoring UR5 at {ip} ({rate_hz} Hz)")
    print("Press Ctrl+C to stop\n")

    try:
        rtde = RTDEReceiveInterface(ip)

        while True:
            positions = rtde.getActualQ()

            if positions:
                # Clear previous output (8 lines)
                print("\033[8A", end="")

                # Display current positions
                print(f"[{time.strftime('%H:%M:%S')}] UR5 @ {ip}")
                print("-" * 50)

                for i, pos in enumerate(positions):
                    deg = np.degrees(pos)
                    # Add color based on position
                    if abs(deg) > 180:
                        color = "\033[91m"  # Red for extreme angles
                    elif abs(deg) > 90:
                        color = "\033[93m"  # Yellow for high angles
                    else:
                        color = "\033[92m"  # Green for normal range
                    reset = "\033[0m"

                    print(f"J{i + 1}: {color}{pos:>8.4f} rad  ({deg:>7.2f}°){reset}")

                print("-" * 50)

            time.sleep(1.0 / rate_hz)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")
    finally:
        rtde.disconnect()


def get_both_arms(left_ip: str, right_ip: str, json_output: bool = False):
    """Get positions from both UR5 arms."""

    if not json_output:
        print("\n" + "=" * 60)
        print("DUAL UR5 JOINT POSITIONS")
        print("=" * 60)

    # Get left arm
    left_pos = get_ur_positions(left_ip)
    if left_pos:
        display_positions(left_pos, f"LEFT UR5 ({left_ip})", json_output)
    else:
        if json_output:
            print(json.dumps({"error": f"Failed to connect to LEFT UR5 at {left_ip}"}))
        else:
            print(f"\n✗ Failed to connect to LEFT UR5 at {left_ip}")

    # Get right arm
    right_pos = get_ur_positions(right_ip)
    if right_pos:
        display_positions(right_pos, f"RIGHT UR5 ({right_ip})", json_output)
    else:
        if json_output:
            print(
                json.dumps({"error": f"Failed to connect to RIGHT UR5 at {right_ip}"})
            )
        else:
            print(f"\n✗ Failed to connect to RIGHT UR5 at {right_ip}")

    if not json_output:
        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Get current UR5 joint angles")
    parser.add_argument(
        "--ip",
        type=str,
        default="192.168.1.210",
        help="UR5 IP address (default: 192.168.1.210)",
    )
    parser.add_argument(
        "--left-ip",
        type=str,
        default="192.168.1.211",
        help="Left UR5 IP for dual arm mode",
    )
    parser.add_argument(
        "--right-ip",
        type=str,
        default="192.168.1.210",
        help="Right UR5 IP for dual arm mode",
    )
    parser.add_argument(
        "--both", action="store_true", help="Get positions from both arms"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--continuous", action="store_true", help="Continuously monitor positions"
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Update rate in Hz for continuous mode (default: 10)",
    )

    args = parser.parse_args()

    if args.both:
        # Get both arms
        get_both_arms(args.left_ip, args.right_ip, args.json)

    elif args.continuous:
        # Continuous monitoring
        monitor_continuous(args.ip, args.rate)

    else:
        # Single reading
        positions = get_ur_positions(args.ip)
        if positions:
            display_positions(positions, f"UR5 ({args.ip})", args.json)
        else:
            if args.json:
                print(json.dumps({"error": f"Failed to connect to {args.ip}"}))
            else:
                print(f"✗ Failed to connect to UR5 at {args.ip}")
                sys.exit(1)


if __name__ == "__main__":
    main()
