#!/usr/bin/env python3
"""
Test script to demonstrate GELLO arm position monitoring.
This shows what the continuous position display will look like.
"""

import time

import numpy as np


def demo_position_display():
    """Demonstrate what the position monitoring output looks like."""

    print("\n" + "=" * 80)
    print("GELLO ARM POSITION MONITOR - DEMO")
    print("=" * 80)
    print("\nThis shows what you'll see when the position monitor is running:")
    print("- Updates at 10Hz (10 times per second)")
    print("- Shows all 6 joints + gripper for each arm")
    print("- Displays positions in degrees for easy reading")
    print("\n" + "-" * 80 + "\n")

    # Simulate position updates
    for i in range(50):  # Run for 5 seconds
        timestamp = time.strftime("%H:%M:%S")

        # Simulate some joint positions (in degrees)
        left_j1 = -45.2 + np.sin(i * 0.1) * 5
        left_j2 = -90.5 + np.cos(i * 0.1) * 3
        left_j3 = 0.0 + np.sin(i * 0.15) * 2
        left_j4 = -90.0 + np.cos(i * 0.12) * 4
        left_j5 = 90.0 + np.sin(i * 0.08) * 3
        left_j6 = 0.0 + np.cos(i * 0.1) * 10
        left_grip = 143.5 if i % 20 < 10 else 196.4  # Toggle gripper

        right_j1 = 45.2 + np.sin(i * 0.11) * 5
        right_j2 = -90.5 + np.cos(i * 0.09) * 3
        right_j3 = 0.0 + np.sin(i * 0.14) * 2
        right_j4 = -90.0 + np.cos(i * 0.13) * 4
        right_j5 = -90.0 + np.sin(i * 0.07) * 3
        right_j6 = 0.0 + np.cos(i * 0.11) * 10
        right_grip = 235.1 if i % 20 < 10 else 291.6  # Toggle gripper

        # Format the output exactly as the real monitor does
        left_str = f"J1:{left_j1:6.1f}° J2:{left_j2:6.1f}° J3:{left_j3:6.1f}° J4:{left_j4:6.1f}° J5:{left_j5:6.1f}° J6:{left_j6:6.1f}° G:{left_grip:6.1f}°"
        right_str = f"J1:{right_j1:6.1f}° J2:{right_j2:6.1f}° J3:{right_j3:6.1f}° J4:{right_j4:6.1f}° J5:{right_j5:6.1f}° J6:{right_j6:6.1f}° G:{right_grip:6.1f}°"

        # Print with cursor control for updating display
        print(f"\r[{timestamp}] GELLO LEFT:  {left_str}", end="")
        print(f"\n           GELLO RIGHT: {right_str}", end="", flush=True)

        # Move cursor up for next update (creates updating display)
        if i < 49:  # Don't move up on last iteration
            print("\033[1A", end="")

        time.sleep(0.1)  # 10Hz update rate

    print("\n\n" + "-" * 80)
    print("DEMO COMPLETE")
    print("-" * 80)
    print("\nIn the actual teleop script, this runs continuously in the background")
    print("and shows the real-time positions of your GELLO arms.")
    print("\nKey features:")
    print("  ✓ Runs at all times, regardless of teleop state")
    print("  ✓ Shows 'DISCONNECTED' when robots are not connected")
    print("  ✓ Updates even when teleop is stopped")
    print("  ✓ Helps with debugging and monitoring arm positions")
    print("  ✓ Gripper position shown as 'G' value\n")


if __name__ == "__main__":
    demo_position_display()
