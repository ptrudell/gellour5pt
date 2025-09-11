#!/usr/bin/env python3
"""
Fix wild movements and gripper control issues in teleoperation.
This script monitors gripper positions and adjusts configuration.
"""

import os
import sys

import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.ur_dynamixel_robot import URDynamixelRobot


def test_gripper_positions():
    """Test and determine actual gripper positions."""
    print("=" * 60)
    print("GRIPPER POSITION DETECTION")
    print("=" * 60)

    # Load config
    config_path = "configs/teleop_dual_ur5.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Test LEFT gripper
    print("\nTesting LEFT gripper...")
    left_config = config["left_robot"]

    left_robot = URDynamixelRobot(
        ur_host=left_config["ur_host"],
        dxl_port=left_config["dxl_port"],
        dxl_ids=left_config["dxl_ids"],
        dxl_signs=left_config["dxl_signs"],
        dxl_offsets_deg=left_config["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    ur_ok, dxl_ok = left_robot.connect()
    if dxl_ok:
        positions = left_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            gripper_pos = positions[6]
            print(f"  LEFT gripper position: {gripper_pos:.3f} rad")
            print("  → Please manually CLOSE the LEFT gripper and press Enter...")
            input()
            positions = left_robot.dxl.read_positions()
            closed_pos = (
                positions[6] if positions and len(positions) > 6 else gripper_pos
            )
            print(f"  LEFT gripper CLOSED: {closed_pos:.3f} rad")

            print("  → Please manually OPEN the LEFT gripper and press Enter...")
            input()
            positions = left_robot.dxl.read_positions()
            open_pos = positions[6] if positions and len(positions) > 6 else gripper_pos
            print(f"  LEFT gripper OPEN: {open_pos:.3f} rad")

            left_threshold = (closed_pos + open_pos) / 2
            print(f"  LEFT gripper threshold: {left_threshold:.3f} rad")
        else:
            print("  ✗ Could not read LEFT gripper")
            left_threshold = None
    else:
        print("  ✗ LEFT DXL not connected")
        left_threshold = None

    left_robot.disconnect()

    # Test RIGHT gripper
    print("\nTesting RIGHT gripper...")
    right_config = config["right_robot"]

    right_robot = URDynamixelRobot(
        ur_host=right_config["ur_host"],
        dxl_port=right_config["dxl_port"],
        dxl_ids=right_config["dxl_ids"],
        dxl_signs=right_config["dxl_signs"],
        dxl_offsets_deg=right_config["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    ur_ok, dxl_ok = right_robot.connect()
    if dxl_ok:
        positions = right_robot.dxl.read_positions()
        if positions and len(positions) > 6:
            gripper_pos = positions[6]
            print(f"  RIGHT gripper position: {gripper_pos:.3f} rad")
            print("  → Please manually CLOSE the RIGHT gripper and press Enter...")
            input()
            positions = right_robot.dxl.read_positions()
            closed_pos = (
                positions[6] if positions and len(positions) > 6 else gripper_pos
            )
            print(f"  RIGHT gripper CLOSED: {closed_pos:.3f} rad")

            print("  → Please manually OPEN the RIGHT gripper and press Enter...")
            input()
            positions = right_robot.dxl.read_positions()
            open_pos = positions[6] if positions and len(positions) > 6 else gripper_pos
            print(f"  RIGHT gripper OPEN: {open_pos:.3f} rad")

            right_threshold = (closed_pos + open_pos) / 2
            print(f"  RIGHT gripper threshold: {right_threshold:.3f} rad")
        else:
            print("  ✗ Could not read RIGHT gripper")
            right_threshold = None
    else:
        print("  ✗ RIGHT DXL not connected")
        right_threshold = None

    right_robot.disconnect()

    return left_threshold, right_threshold


def update_motion_config():
    """Update motion configuration to reduce wild movements."""
    print("\n" + "=" * 60)
    print("UPDATING MOTION CONFIGURATION")
    print("=" * 60)

    config_path = "configs/teleop_dual_ur5.yaml"

    # Load current config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Update control parameters for smoother motion
    print("\nAdjusting control parameters...")

    # Reduce velocities and accelerations for safety
    config["control"]["velocity_max"] = 0.8  # Reduced from 1.4
    config["control"]["acceleration_max"] = 2.0  # Reduced from 4.0
    config["control"]["gain"] = 200  # Reduced from 340
    config["control"]["lookahead"] = 0.10  # Reduced from 0.15

    # Increase smoothing
    config["motion_shaping"]["ema_alpha"] = 0.02  # More smoothing (was 0.03)
    config["motion_shaping"]["softstart_time"] = 0.25  # Slower start (was 0.15)

    # Increase deadbands to eliminate drift
    config["motion_shaping"]["deadband_deg"] = [1.5, 1.5, 1.5, 1.5, 1.5, 2.0, 1.5]

    # Save updated config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print("  ✓ Updated control parameters")
    print("    - Reduced velocity_max: 0.8 rad/s")
    print("    - Reduced acceleration_max: 2.0 rad/s²")
    print("    - Reduced gain: 200")
    print("    - Increased smoothing: ema_alpha=0.02")
    print("    - Increased deadbands: 1.5°")

    return config


def main():
    """Main function to fix issues."""
    print("\n🔧 TELEOPERATION FIX UTILITY")
    print("=" * 60)

    # Step 1: Update motion config
    config = update_motion_config()

    # Step 2: Test gripper positions
    print("\n📏 Testing gripper positions...")
    print("This will help calibrate gripper thresholds.")
    print("You'll need to manually move the GELLO grippers when prompted.\n")

    response = input("Do you want to calibrate grippers now? (y/n): ")

    if response.lower() == "y":
        left_threshold, right_threshold = test_gripper_positions()

        if left_threshold is not None or right_threshold is not None:
            print("\n" + "=" * 60)
            print("GRIPPER CALIBRATION RESULTS")
            print("=" * 60)

            if left_threshold is not None:
                print(f"LEFT gripper threshold: {left_threshold:.3f} rad")
            if right_threshold is not None:
                print(f"RIGHT gripper threshold: {right_threshold:.3f} rad")

            print("\nTo apply these values, update streamdeck_pedal_watch.py:")
            if left_threshold is not None:
                print(f"  Line ~875: gripper_threshold = {left_threshold:.2f}")
            if right_threshold is not None:
                print(f"  Line ~959: gripper_threshold = {right_threshold:.2f}")

    print("\n" + "=" * 60)
    print("✅ FIXES APPLIED")
    print("=" * 60)
    print("\nChanges made:")
    print("1. ✓ Reduced velocity and acceleration for smoother motion")
    print("2. ✓ Increased smoothing parameters")
    print("3. ✓ Increased deadbands to reduce drift")

    if response.lower() == "y":
        print("4. ✓ Detected gripper positions (manual update needed)")

    print("\n🚀 Ready to test:")
    print("  python3 scripts/run_teleop.py --test-mode")
    print("\n⚠️  Motion will be slower but more controlled")
    print("   Adjust parameters in configs/teleop_dual_ur5.yaml as needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
