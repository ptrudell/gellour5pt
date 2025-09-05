#!/usr/bin/env python3
"""
Simple teleoperation script - starts immediately without pedals
Press Ctrl+C to stop
"""

import signal
import sys
from pathlib import Path

import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from hardware.control_loop import (
    FixedRateScheduler,
    MotionProfile,
    SmoothMotionController,
)
from hardware.ur_dynamixel_robot import URDynamixelRobot

# Global flag for clean shutdown
running = True


def signal_handler(signum, frame):
    global running
    print("\n[STOP] Shutting down...")
    running = False


def main():
    # Load config
    config_path = "configs/teleop_dual_ur5.yaml"
    print(f"[CONFIG] Loading {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Create robots
    print("\n[CONNECT] Connecting to robots...")

    # LEFT robot
    left_robot = URDynamixelRobot(
        ur_host=config["left_robot"]["ur_host"],
        dxl_port=config["left_robot"]["dxl_port"],
        dxl_ids=config["left_robot"]["dxl_ids"],
        dxl_signs=config["left_robot"]["dxl_signs"],
        dxl_offsets_deg=config["left_robot"]["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    # RIGHT robot
    right_robot = URDynamixelRobot(
        ur_host=config["right_robot"]["ur_host"],
        dxl_port=config["right_robot"]["dxl_port"],
        dxl_ids=config["right_robot"]["dxl_ids"],
        dxl_signs=config["right_robot"]["dxl_signs"],
        dxl_offsets_deg=config["right_robot"]["dxl_offsets_deg"],
        dxl_baudrate=config["dynamixel"]["baudrate"],
    )

    # Connect
    left_ur_ok, left_dxl_ok = left_robot.connect()
    right_ur_ok, right_dxl_ok = right_robot.connect()

    print(
        f"LEFT:  UR={'OK' if left_ur_ok else 'FAIL'}, DXL={'OK' if left_dxl_ok else 'FAIL'}"
    )
    print(
        f"RIGHT: UR={'OK' if right_ur_ok else 'FAIL'}, DXL={'OK' if right_dxl_ok else 'FAIL'}"
    )

    if not (left_dxl_ok and right_dxl_ok):
        print("\n[ERROR] DXL servos not connected!")
        return 1

    # Create motion controllers
    profile = MotionProfile(
        velocity_max=config["control"]["velocity_max"],
        acceleration_max=config["control"]["acceleration_max"],
        deadband_rad=[0.017, 0.017, 0.017, 0.017, 0.017, 0.035, 0.017],  # ~1-2 degrees
        clamp_rad=[None, None, None, None, None, 0.8, None],  # Wrist clamp
    )

    left_controller = SmoothMotionController(6, profile, config["control"]["dt"])
    right_controller = SmoothMotionController(6, profile, config["control"]["dt"])

    # Capture baselines
    print("\n[BASELINE] Capturing current positions...")

    left_dxl = left_robot.dxl.read_positions()
    left_ur = left_robot.ur.get_joint_positions()

    right_dxl = right_robot.dxl.read_positions()
    right_ur = right_robot.ur.get_joint_positions()

    if left_dxl is not None and left_ur is not None:
        left_controller.set_baselines(left_dxl[:6], left_ur)
        print(f"LEFT:  Captured {len(left_dxl)} DXL, {len(left_ur)} UR joints")
    else:
        print("LEFT:  Failed to capture baselines!")
        return 1

    if right_dxl is not None and right_ur is not None:
        right_controller.set_baselines(right_dxl[:6], right_ur)
        print(f"RIGHT: Captured {len(right_dxl)} DXL, {len(right_ur)} UR joints")
    else:
        print("RIGHT: Failed to capture baselines!")
        return 1

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Create scheduler
    scheduler = FixedRateScheduler(config["control"]["hz"])
    scheduler.start()

    print("\n" + "=" * 60)
    print("TELEOPERATION ACTIVE")
    print("=" * 60)
    print("Move the GELLO arms to control the UR robots")
    print("Press Ctrl+C to stop")
    print("")

    error_count = {"left": 0, "right": 0}
    loop_count = 0

    # Main control loop
    while running:
        # LEFT robot
        left_dxl = left_robot.dxl.read_positions()
        left_ur = left_robot.ur.get_joint_positions()

        if left_dxl is not None and left_ur is not None:
            target, is_moving = left_controller.update(left_dxl[:6], left_ur)

            success = left_robot.ur.servo_j(
                target,
                config["control"]["velocity_max"],
                config["control"]["acceleration_max"],
                config["control"]["dt"],
                config["control"]["lookahead"],
                config["control"]["gain"],
            )

            if success:
                error_count["left"] = 0
            else:
                error_count["left"] += 1
                if error_count["left"] == 1:
                    print("\n[WARN] LEFT UR control error - check ExternalControl.urp")
                if error_count["left"] > 10:
                    print("\n[ERROR] Too many LEFT errors - stopping")
                    break

        # RIGHT robot
        right_dxl = right_robot.dxl.read_positions()
        right_ur = right_robot.ur.get_joint_positions()

        if right_dxl is not None and right_ur is not None:
            target, is_moving = right_controller.update(right_dxl[:6], right_ur)

            success = right_robot.ur.servo_j(
                target,
                config["control"]["velocity_max"],
                config["control"]["acceleration_max"],
                config["control"]["dt"],
                config["control"]["lookahead"],
                config["control"]["gain"],
            )

            if success:
                error_count["right"] = 0
            else:
                error_count["right"] += 1
                if error_count["right"] == 1:
                    print("\n[WARN] RIGHT UR control error - check ExternalControl.urp")
                if error_count["right"] > 10:
                    print("\n[ERROR] Too many RIGHT errors - stopping")
                    break

        # Wait for next tick
        scheduler.wait()

        # Print stats occasionally
        loop_count += 1
        if loop_count % 1000 == 0:
            stats = scheduler.get_stats()
            print(f"[STATS] {stats['mean_freq']:.1f}Hz, overruns: {stats['overruns']}")

    # Cleanup
    print("\n[CLEANUP] Disconnecting...")
    left_robot.disconnect()
    right_robot.disconnect()
    print("[DONE]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
