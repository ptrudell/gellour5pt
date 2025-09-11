#!/usr/bin/env python3
"""
Display real-time offset between UR5 and GELLO positions.
Shows the difference between current UR5 joint angles and GELLO joint angles.

Usage:
    python scripts/show_ur_gello_offset.py         # Both arms
    python scripts/show_ur_gello_offset.py --left  # Left arm only
    python scripts/show_ur_gello_offset.py --right # Right arm only
"""

import argparse
import os
import sys
import time
from typing import List, Optional

import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import UR RTDE interface
try:
    from rtde_shim import RTDEReceiveInterface
except ImportError:
    print("Error: rtde_shim not found. Make sure it's in your path.")
    sys.exit(1)

# Import GELLO agent
try:
    from gello.agents.gello_agent import GelloAgent
except ImportError:
    try:
        from gello_software.gello.agents.gello_agent import GelloAgent
    except ImportError:
        print("Error: GelloAgent not found")
        sys.exit(1)


class URGelloOffsetMonitor:
    """Monitor and display offsets between UR5 and GELLO positions."""

    def __init__(self, ur_ip: str, gello_port: str, arm_name: str = "ARM"):
        """
        Args:
            ur_ip: IP address of UR5 robot
            gello_port: Serial port for GELLO (e.g., /dev/ttyUSB0)
            arm_name: Name for display (LEFT/RIGHT)
        """
        self.ur_ip = ur_ip
        self.gello_port = gello_port
        self.arm_name = arm_name

        # Connect to UR
        print(f"Connecting to UR5 at {ur_ip}...")
        self.ur_rtde = RTDEReceiveInterface(ur_ip)

        # Connect to GELLO
        print(f"Connecting to GELLO on {gello_port}...")
        self.gello = GelloAgent(port=gello_port)
        self.gello.connect()

        print(f"✓ {arm_name} connections established\n")

    def get_ur_positions(self) -> Optional[List[float]]:
        """Get current UR5 joint positions in radians."""
        try:
            return self.ur_rtde.getActualQ()  # Returns list of 6 floats
        except Exception as e:
            print(f"Error reading UR5: {e}")
            return None

    def get_gello_positions(self) -> Optional[List[float]]:
        """Get current GELLO joint positions in radians."""
        try:
            # GELLO returns 7 joints (6 arm + 1 gripper)
            positions = self.gello.get_joint_positions()
            return (
                positions[:6] if positions else None
            )  # Return only first 6 for UR comparison
        except Exception as e:
            print(f"Error reading GELLO: {e}")
            return None

    def display_offsets(self, continuous: bool = True):
        """Display the offsets between UR and GELLO positions."""

        print(f"{'=' * 70}")
        print(f"UR5-GELLO OFFSET MONITOR - {self.arm_name}")
        print(f"{'=' * 70}")
        print("Showing: OFFSET = UR_POSITION - GELLO_POSITION")
        print("(Positive offset means UR is ahead of GELLO)\n")

        if continuous:
            print("Press Ctrl+C to stop\n")

        try:
            while True:
                ur_pos = self.get_ur_positions()
                gello_pos = self.get_gello_positions()

                if ur_pos and gello_pos:
                    # Calculate offsets
                    offsets = [ur - gello for ur, gello in zip(ur_pos, gello_pos)]

                    # Clear previous lines (move cursor up)
                    if continuous:
                        print("\033[9A", end="")  # Move up 9 lines

                    # Display header
                    print(f"\n[{time.strftime('%H:%M:%S')}] {self.arm_name} ARM")
                    print("-" * 50)

                    # Display positions and offsets
                    print(
                        f"{'Joint':<8} {'UR5 (deg)':<12} {'GELLO (deg)':<12} {'Offset (deg)':<12}"
                    )
                    print("-" * 50)

                    for i in range(6):
                        ur_deg = np.degrees(ur_pos[i])
                        gello_deg = np.degrees(gello_pos[i])
                        offset_deg = np.degrees(offsets[i])

                        # Color code the offset (red if > 5 degrees, yellow if > 2, green otherwise)
                        abs_offset = abs(offset_deg)
                        if abs_offset > 5:
                            color = "\033[91m"  # Red
                        elif abs_offset > 2:
                            color = "\033[93m"  # Yellow
                        else:
                            color = "\033[92m"  # Green
                        reset = "\033[0m"

                        print(
                            f"J{i + 1:<7} {ur_deg:>11.2f}° {gello_deg:>11.2f}° "
                            f"{color}{offset_deg:>+11.2f}°{reset}"
                        )

                    # Calculate and display RMS error
                    rms_error = np.sqrt(np.mean(np.array(offsets) ** 2))
                    rms_deg = np.degrees(rms_error)

                    print("-" * 50)
                    print(f"RMS Error: {rms_deg:.2f}°")

                else:
                    print("\nWaiting for data...")

                if not continuous:
                    break

                time.sleep(0.1)  # 10Hz update rate

        except KeyboardInterrupt:
            print("\n\nStopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up connections."""
        try:
            self.ur_rtde.disconnect()
            self.gello.disconnect()
            print(f"\n✓ {self.arm_name} connections closed")
        except:
            pass


def monitor_dual_arms(
    left_ur_ip: str, left_gello_port: str, right_ur_ip: str, right_gello_port: str
):
    """Monitor both arms simultaneously."""

    # Connect to both arms
    left_monitor = URGelloOffsetMonitor(left_ur_ip, left_gello_port, "LEFT")
    right_monitor = URGelloOffsetMonitor(right_ur_ip, right_gello_port, "RIGHT")

    print(f"{'=' * 70}")
    print("DUAL ARM UR5-GELLO OFFSET MONITOR")
    print(f"{'=' * 70}")
    print("Showing: OFFSET = UR_POSITION - GELLO_POSITION")
    print("(Positive offset means UR is ahead of GELLO)\n")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Get positions from both arms
            left_ur = left_monitor.get_ur_positions()
            left_gello = left_monitor.get_gello_positions()
            right_ur = right_monitor.get_ur_positions()
            right_gello = right_monitor.get_gello_positions()

            # Clear screen for clean display
            print("\033[2J\033[H", end="")  # Clear screen and move to top

            # Display timestamp
            print(f"[{time.strftime('%H:%M:%S')}] DUAL ARM MONITORING\n")

            # Display LEFT arm
            print("LEFT ARM:")
            print("-" * 60)
            if left_ur and left_gello:
                print(
                    f"{'Joint':<6} {'UR5':<10} {'GELLO':<10} {'Offset':<10} {'Status'}"
                )
                for i in range(6):
                    ur_deg = np.degrees(left_ur[i])
                    gello_deg = np.degrees(left_gello[i])
                    offset_deg = np.degrees(left_ur[i] - left_gello[i])

                    # Status indicator
                    abs_offset = abs(offset_deg)
                    if abs_offset > 5:
                        status = "⚠️  LARGE"
                    elif abs_offset > 2:
                        status = "⚡ MEDIUM"
                    else:
                        status = "✓  GOOD"

                    print(
                        f"J{i + 1:<5} {ur_deg:>9.1f}° {gello_deg:>9.1f}° "
                        f"{offset_deg:>+9.1f}° {status}"
                    )

                # RMS error
                left_offsets = [ur - g for ur, g in zip(left_ur, left_gello)]
                left_rms = np.degrees(np.sqrt(np.mean(np.array(left_offsets) ** 2)))
                print(f"RMS Error: {left_rms:.2f}°")
            else:
                print("No data available")

            print()

            # Display RIGHT arm
            print("RIGHT ARM:")
            print("-" * 60)
            if right_ur and right_gello:
                print(
                    f"{'Joint':<6} {'UR5':<10} {'GELLO':<10} {'Offset':<10} {'Status'}"
                )
                for i in range(6):
                    ur_deg = np.degrees(right_ur[i])
                    gello_deg = np.degrees(right_gello[i])
                    offset_deg = np.degrees(right_ur[i] - right_gello[i])

                    # Status indicator
                    abs_offset = abs(offset_deg)
                    if abs_offset > 5:
                        status = "⚠️  LARGE"
                    elif abs_offset > 2:
                        status = "⚡ MEDIUM"
                    else:
                        status = "✓  GOOD"

                    print(
                        f"J{i + 1:<5} {ur_deg:>9.1f}° {gello_deg:>9.1f}° "
                        f"{offset_deg:>+9.1f}° {status}"
                    )

                # RMS error
                right_offsets = [ur - g for ur, g in zip(right_ur, right_gello)]
                right_rms = np.degrees(np.sqrt(np.mean(np.array(right_offsets) ** 2)))
                print(f"RMS Error: {right_rms:.2f}°")
            else:
                print("No data available")

            time.sleep(0.1)  # 10Hz update

    except KeyboardInterrupt:
        print("\n\nStopped by user")
    finally:
        left_monitor.cleanup()
        right_monitor.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor offsets between UR5 and GELLO positions"
    )
    parser.add_argument("--left", action="store_true", help="Monitor left arm only")
    parser.add_argument("--right", action="store_true", help="Monitor right arm only")
    parser.add_argument(
        "--left-ur-ip",
        type=str,
        default="192.168.1.211",
        help="Left UR5 IP address (default: 192.168.1.211)",
    )
    parser.add_argument(
        "--right-ur-ip",
        type=str,
        default="192.168.1.210",
        help="Right UR5 IP address (default: 192.168.1.210)",
    )
    parser.add_argument(
        "--left-gello-port",
        type=str,
        default="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7WBEIA-if00-port0",
        help="Left GELLO serial port",
    )
    parser.add_argument(
        "--right-gello-port",
        type=str,
        default="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT8J0XJV-if00-port0",
        help="Right GELLO serial port",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Display once and exit (no continuous monitoring)",
    )

    args = parser.parse_args()

    # Determine which arms to monitor
    if args.left:
        # Monitor left arm only
        monitor = URGelloOffsetMonitor(args.left_ur_ip, args.left_gello_port, "LEFT")
        monitor.display_offsets(continuous=not args.once)

    elif args.right:
        # Monitor right arm only
        monitor = URGelloOffsetMonitor(args.right_ur_ip, args.right_gello_port, "RIGHT")
        monitor.display_offsets(continuous=not args.once)

    else:
        # Monitor both arms
        monitor_dual_arms(
            args.left_ur_ip,
            args.left_gello_port,
            args.right_ur_ip,
            args.right_gello_port,
        )


if __name__ == "__main__":
    main()
