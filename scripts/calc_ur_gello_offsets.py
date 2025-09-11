#!/usr/bin/env python3
"""
Calculate and display offsets between UR5 and GELLO positions.
Can also save calibration offsets to apply during teleoperation.

Usage:
    # Show current offsets
    python scripts/calc_ur_gello_offsets.py

    # Save offsets to config file
    python scripts/calc_ur_gello_offsets.py --save configs/offsets.json

    # Specific arm
    python scripts/calc_ur_gello_offsets.py --left
    python scripts/calc_ur_gello_offsets.py --right
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Optional

import numpy as np

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from rtde_shim import RTDEReceiveInterface
except ImportError:
    print("Error: rtde_shim not found")
    sys.exit(1)

try:
    from gello.agents.gello_agent import GelloAgent
except ImportError:
    try:
        from gello_software.gello.agents.gello_agent import GelloAgent
    except ImportError:
        print("Error: GelloAgent not found")
        sys.exit(1)


class OffsetCalculator:
    """Calculate offsets between UR5 and GELLO positions."""

    def __init__(self, ur_ip: str, gello_port: str, arm_name: str = "ARM"):
        self.ur_ip = ur_ip
        self.gello_port = gello_port
        self.arm_name = arm_name

        # Connect to devices
        print(f"\nConnecting to {arm_name}...")
        self.ur_rtde = RTDEReceiveInterface(ur_ip)
        self.gello = GelloAgent(port=gello_port)
        self.gello.connect()
        print(f"✓ {arm_name} connected")

    def get_average_positions(self, n_samples: int = 10, delay: float = 0.05):
        """Get averaged positions from both UR and GELLO."""

        ur_samples = []
        gello_samples = []

        print(f"Sampling {n_samples} readings...")
        for i in range(n_samples):
            # Get UR position
            ur_pos = self.ur_rtde.getActualQ()
            if ur_pos:
                ur_samples.append(ur_pos)

            # Get GELLO position (first 6 joints only)
            gello_pos = self.gello.get_joint_positions()
            if gello_pos:
                gello_samples.append(gello_pos[:6])

            time.sleep(delay)
            print(f"  Sample {i + 1}/{n_samples}", end="\r")

        print()

        # Average the samples
        if ur_samples and gello_samples:
            ur_avg = [sum(vals) / len(vals) for vals in zip(*ur_samples)]
            gello_avg = [sum(vals) / len(vals) for vals in zip(*gello_samples)]
            return ur_avg, gello_avg
        else:
            return None, None

    def calculate_offsets(self) -> Optional[Dict]:
        """Calculate offsets between UR and GELLO."""

        # Get averaged positions
        ur_pos, gello_pos = self.get_average_positions()

        if not ur_pos or not gello_pos:
            print(f"✗ Failed to get positions for {self.arm_name}")
            return None

        # Calculate offsets (UR - GELLO)
        offsets = [ur - gello for ur, gello in zip(ur_pos, gello_pos)]

        # Create result dictionary
        result = {
            "arm": self.arm_name,
            "timestamp": time.time(),
            "ur_positions_rad": ur_pos,
            "gello_positions_rad": gello_pos,
            "offsets_rad": offsets,
            "ur_positions_deg": [np.degrees(p) for p in ur_pos],
            "gello_positions_deg": [np.degrees(p) for p in gello_pos],
            "offsets_deg": [np.degrees(o) for o in offsets],
            "rms_error_rad": float(np.sqrt(np.mean(np.array(offsets) ** 2))),
            "rms_error_deg": float(
                np.degrees(np.sqrt(np.mean(np.array(offsets) ** 2)))
            ),
        }

        return result

    def display_offsets(self, result: Dict):
        """Display offset calculation results."""

        print(f"\n{'=' * 60}")
        print(f"{self.arm_name} ARM OFFSET CALCULATION")
        print(f"{'=' * 60}")

        print(
            f"\n{'Joint':<8} {'UR5 (deg)':<12} {'GELLO (deg)':<12} {'Offset (deg)':<12}"
        )
        print("-" * 50)

        for i in range(6):
            ur_deg = result["ur_positions_deg"][i]
            gello_deg = result["gello_positions_deg"][i]
            offset_deg = result["offsets_deg"][i]

            # Color code
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

        print("-" * 50)
        print(f"RMS Error: {result['rms_error_deg']:.2f}°")

        # Print offset arrays for easy copying
        print("\nOffset arrays for configuration:")
        print(f"Radians: {[round(o, 6) for o in result['offsets_rad']]}")
        print(f"Degrees: {[round(o, 2) for o in result['offsets_deg']]}")

    def cleanup(self):
        """Clean up connections."""
        try:
            self.ur_rtde.disconnect()
            self.gello.disconnect()
        except:
            pass


def calculate_dual_offsets(
    left_ur_ip: str, left_gello_port: str, right_ur_ip: str, right_gello_port: str
) -> Dict:
    """Calculate offsets for both arms."""

    results = {}

    # Calculate left arm offsets
    print("\n" + "=" * 60)
    print("CALCULATING LEFT ARM OFFSETS")
    print("=" * 60)

    left_calc = OffsetCalculator(left_ur_ip, left_gello_port, "LEFT")
    left_result = left_calc.calculate_offsets()
    if left_result:
        left_calc.display_offsets(left_result)
        results["left"] = left_result
    left_calc.cleanup()

    # Calculate right arm offsets
    print("\n" + "=" * 60)
    print("CALCULATING RIGHT ARM OFFSETS")
    print("=" * 60)

    right_calc = OffsetCalculator(right_ur_ip, right_gello_port, "RIGHT")
    right_result = right_calc.calculate_offsets()
    if right_result:
        right_calc.display_offsets(right_result)
        results["right"] = right_result
    right_calc.cleanup()

    # Summary
    if results:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        if "left" in results:
            print(f"LEFT  RMS Error: {results['left']['rms_error_deg']:.2f}°")
        if "right" in results:
            print(f"RIGHT RMS Error: {results['right']['rms_error_deg']:.2f}°")

        if len(results) == 2:
            avg_rms = (
                results["left"]["rms_error_deg"] + results["right"]["rms_error_deg"]
            ) / 2
            print(f"Average RMS Error: {avg_rms:.2f}°")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Calculate offsets between UR5 and GELLO positions"
    )

    # Arm selection
    parser.add_argument("--left", action="store_true", help="Calculate left arm only")
    parser.add_argument("--right", action="store_true", help="Calculate right arm only")

    # Connection parameters
    parser.add_argument(
        "--left-ur-ip", type=str, default="192.168.1.211", help="Left UR5 IP address"
    )
    parser.add_argument(
        "--right-ur-ip", type=str, default="192.168.1.210", help="Right UR5 IP address"
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

    # Output options
    parser.add_argument("--save", type=str, help="Save offsets to JSON file")
    parser.add_argument(
        "--apply-sign-correction",
        action="store_true",
        help="Apply sign correction to GELLO positions before calculating offsets",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("UR5-GELLO OFFSET CALCULATOR")
    print("=" * 60)
    print("\nThis tool calculates the offset between UR5 and GELLO positions.")
    print("Offset = UR_position - GELLO_position")
    print("\nEnsure both robots are in the same pose before running!")

    input("\nPress Enter when ready...")

    results = {}

    if args.left:
        # Left arm only
        calc = OffsetCalculator(args.left_ur_ip, args.left_gello_port, "LEFT")
        result = calc.calculate_offsets()
        if result:
            calc.display_offsets(result)
            results["left"] = result
        calc.cleanup()

    elif args.right:
        # Right arm only
        calc = OffsetCalculator(args.right_ur_ip, args.right_gello_port, "RIGHT")
        result = calc.calculate_offsets()
        if result:
            calc.display_offsets(result)
            results["right"] = result
        calc.cleanup()

    else:
        # Both arms
        results = calculate_dual_offsets(
            args.left_ur_ip,
            args.left_gello_port,
            args.right_ur_ip,
            args.right_gello_port,
        )

    # Save results if requested
    if args.save and results:
        with open(args.save, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Offsets saved to {args.save}")

    print("\nDone!")


if __name__ == "__main__":
    main()
