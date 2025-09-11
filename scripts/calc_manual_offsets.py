#!/usr/bin/env python3
"""
Calculate offsets and transformations between two sets of joint angles.
Can be used to calculate UR5-to-GELLO offsets or any robot-to-robot offsets.

Usage:
    python scripts/calc_manual_offsets.py

    # Or provide angles directly:
    python scripts/calc_manual_offsets.py --ur5 "-45,-90,0,-90,90,0" --gello "-44.5,-89.8,0.1,-90.3,89.7,0.2"

    # Or load from file:
    python scripts/calc_manual_offsets.py --load-json angles.json
"""

import argparse
import json
import sys
from typing import Dict, List, Tuple

import numpy as np


def parse_angles(angle_str: str, is_degrees: bool = True) -> List[float]:
    """Parse comma-separated angle string."""
    angles = [float(x.strip()) for x in angle_str.split(",")]
    if is_degrees:
        # Convert to radians for internal calculation
        return [np.radians(a) for a in angles]
    return angles


def calculate_offsets(
    angles1: List[float],
    angles2: List[float],
    name1: str = "Robot1",
    name2: str = "Robot2",
) -> Dict:
    """
    Calculate offsets between two sets of joint angles.

    Args:
        angles1: First set of joint angles in radians
        angles2: Second set of joint angles in radians
        name1: Name of first robot
        name2: Name of second robot

    Returns:
        Dictionary with offset calculations
    """

    if len(angles1) != len(angles2):
        print(f"Error: Different number of joints ({len(angles1)} vs {len(angles2)})")
        return None

    n_joints = len(angles1)

    # Calculate offsets (angles1 - angles2)
    offsets_rad = [a1 - a2 for a1, a2 in zip(angles1, angles2)]
    offsets_deg = [np.degrees(o) for o in offsets_rad]

    # Calculate RMS error
    rms_rad = np.sqrt(np.mean(np.array(offsets_rad) ** 2))
    rms_deg = np.degrees(rms_rad)

    # Calculate max absolute offset
    max_offset_rad = max(abs(o) for o in offsets_rad)
    max_offset_deg = np.degrees(max_offset_rad)

    # Create transformation matrix for each joint
    transformations = []
    for i in range(n_joints):
        # Simple rotation transformation
        T = {
            "joint": i + 1,
            "offset_rad": offsets_rad[i],
            "offset_deg": offsets_deg[i],
            "scale": 1.0,  # No scaling by default
            "transformation": f"{name2}_J{i + 1} = {name1}_J{i + 1} - {offsets_rad[i]:.6f} rad",
        }
        transformations.append(T)

    result = {
        "robot1": name1,
        "robot2": name2,
        "n_joints": n_joints,
        "angles1_rad": angles1,
        "angles2_rad": angles2,
        "angles1_deg": [np.degrees(a) for a in angles1],
        "angles2_deg": [np.degrees(a) for a in angles2],
        "offsets_rad": offsets_rad,
        "offsets_deg": offsets_deg,
        "rms_error_rad": rms_rad,
        "rms_error_deg": rms_deg,
        "max_offset_rad": max_offset_rad,
        "max_offset_deg": max_offset_deg,
        "transformations": transformations,
    }

    return result


def display_results(result: Dict):
    """Display calculation results in a formatted way."""

    print("\n" + "=" * 70)
    print(f"OFFSET CALCULATION: {result['robot1']} → {result['robot2']}")
    print("=" * 70)

    print(f"\nOffset = {result['robot1']} - {result['robot2']}")
    print(f"Number of joints: {result['n_joints']}")

    # Display table
    print("\n" + "-" * 70)
    print(
        f"{'Joint':<8} {result['robot1'] + ' (°)':<15} {result['robot2'] + ' (°)':<15} {'Offset (°)':<15} {'Status'}"
    )
    print("-" * 70)

    for i in range(result["n_joints"]):
        a1_deg = result["angles1_deg"][i]
        a2_deg = result["angles2_deg"][i]
        offset_deg = result["offsets_deg"][i]

        # Status indicator
        abs_offset = abs(offset_deg)
        if abs_offset > 10:
            status = "⚠️  LARGE"
            color = "\033[91m"  # Red
        elif abs_offset > 5:
            status = "⚡ MEDIUM"
            color = "\033[93m"  # Yellow
        elif abs_offset > 2:
            status = "📍 SMALL"
            color = "\033[94m"  # Blue
        else:
            status = "✓  GOOD"
            color = "\033[92m"  # Green
        reset = "\033[0m"

        print(
            f"J{i + 1:<7} {a1_deg:>14.2f}° {a2_deg:>14.2f}° "
            f"{color}{offset_deg:>+14.2f}°{reset} {status}"
        )

    print("-" * 70)

    # Summary statistics
    print("\n📊 STATISTICS:")
    print(
        f"  RMS Error:     {result['rms_error_deg']:.3f}° ({result['rms_error_rad']:.6f} rad)"
    )
    print(
        f"  Max Offset:    {result['max_offset_deg']:.3f}° ({result['max_offset_rad']:.6f} rad)"
    )

    # Offset arrays
    print("\n🔧 OFFSET ARRAYS (for configuration):")
    print(f"  Radians: {[round(o, 6) for o in result['offsets_rad']]}")
    print(f"  Degrees: {[round(o, 2) for o in result['offsets_deg']]}")

    # Transformation equations
    print("\n🔄 TRANSFORMATION EQUATIONS:")
    print(f"  To convert from {result['robot1']} to {result['robot2']}:")
    for t in result["transformations"]:
        print(f"    {t['transformation']}")

    # Quality assessment
    print("\n✅ QUALITY ASSESSMENT:")
    if result["rms_error_deg"] < 2:
        print("  Excellent alignment (RMS < 2°)")
    elif result["rms_error_deg"] < 5:
        print("  Good alignment (RMS < 5°)")
    elif result["rms_error_deg"] < 10:
        print("  Moderate alignment (RMS < 10°)")
    else:
        print("  Poor alignment (RMS > 10°) - recalibration recommended")

    print("\n" + "=" * 70)


def interactive_input() -> Tuple[List[float], List[float], str, str]:
    """Interactive mode to input joint angles."""

    print("\n" + "=" * 60)
    print("INTERACTIVE OFFSET CALCULATOR")
    print("=" * 60)

    # Get first robot data
    print("\n📍 FIRST ROBOT (e.g., UR5)")
    name1 = input("  Name [UR5]: ").strip() or "UR5"

    print("\n  Enter joint angles in degrees (comma-separated):")
    print("  Example: -45, -90, 0, -90, 90, 0")
    angles1_str = input("  Angles: ").strip()

    if not angles1_str:
        print("  Using default UR5 home position")
        angles1 = [-45, -90, 0, -90, 90, 0]
    else:
        angles1 = [float(x.strip()) for x in angles1_str.split(",")]

    # Get second robot data
    print("\n📍 SECOND ROBOT (e.g., GELLO)")
    name2 = input("  Name [GELLO]: ").strip() or "GELLO"

    print("\n  Enter joint angles in degrees (comma-separated):")
    angles2_str = input("  Angles: ").strip()

    if not angles2_str:
        print("  Using default GELLO position")
        angles2 = [-44.5, -89.8, 0.1, -90.3, 89.7, 0.2]
    else:
        angles2 = [float(x.strip()) for x in angles2_str.split(",")]

    # Convert to radians
    angles1_rad = [np.radians(a) for a in angles1]
    angles2_rad = [np.radians(a) for a in angles2]

    return angles1_rad, angles2_rad, name1, name2


def main():
    parser = argparse.ArgumentParser(
        description="Calculate offsets between two sets of joint angles"
    )

    # Input options
    parser.add_argument(
        "--ur5", type=str, help="UR5 angles in degrees (comma-separated)"
    )
    parser.add_argument(
        "--gello", type=str, help="GELLO angles in degrees (comma-separated)"
    )
    parser.add_argument("--robot1", type=str, help="First robot angles in degrees")
    parser.add_argument("--robot2", type=str, help="Second robot angles in degrees")
    parser.add_argument(
        "--name1", type=str, default="Robot1", help="Name of first robot"
    )
    parser.add_argument(
        "--name2", type=str, default="Robot2", help="Name of second robot"
    )
    parser.add_argument(
        "--radians",
        action="store_true",
        help="Input angles are in radians (default: degrees)",
    )

    # File I/O
    parser.add_argument("--load-json", type=str, help="Load angles from JSON file")
    parser.add_argument("--save-json", type=str, help="Save results to JSON file")

    # Example data
    parser.add_argument(
        "--example", action="store_true", help="Use example data for demonstration"
    )

    args = parser.parse_args()

    # Determine input source
    if args.example:
        # Example data
        print("Using example data...")
        angles1 = [np.radians(a) for a in [-45, -90, 0, -90, 90, 0]]
        angles2 = [np.radians(a) for a in [-44.5, -89.8, 0.1, -90.3, 89.7, 0.2]]
        name1 = "UR5"
        name2 = "GELLO"

    elif args.load_json:
        # Load from JSON
        with open(args.load_json, "r") as f:
            data = json.load(f)
        angles1 = data.get("angles1_rad", data.get("ur5_rad"))
        angles2 = data.get("angles2_rad", data.get("gello_rad"))
        name1 = data.get("name1", "Robot1")
        name2 = data.get("name2", "Robot2")

    elif args.ur5 and args.gello:
        # UR5 and GELLO specific
        angles1 = parse_angles(args.ur5, not args.radians)
        angles2 = parse_angles(args.gello, not args.radians)
        name1 = "UR5"
        name2 = "GELLO"

    elif args.robot1 and args.robot2:
        # Generic robots
        angles1 = parse_angles(args.robot1, not args.radians)
        angles2 = parse_angles(args.robot2, not args.radians)
        name1 = args.name1
        name2 = args.name2

    else:
        # Interactive mode
        angles1, angles2, name1, name2 = interactive_input()

    # Calculate offsets
    result = calculate_offsets(angles1, angles2, name1, name2)

    if result:
        # Display results
        display_results(result)

        # Save if requested
        if args.save_json:
            with open(args.save_json, "w") as f:
                json.dump(result, f, indent=2)
            print(f"\n✓ Results saved to {args.save_json}")
    else:
        print("\n❌ Calculation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
