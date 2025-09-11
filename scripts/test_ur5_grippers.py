#!/usr/bin/env python3
"""
Test UR5 gripper servos directly
Left gripper: /dev/ttyUSB3, ID 1
Right gripper: /dev/ttyUSB1, ID 1
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


def test_gripper(side: str, port: str):
    """Test a single UR5 gripper."""
    print(f"\n{'=' * 60}")
    print(f"{side.upper()} UR5 GRIPPER TEST")
    print(f"{'=' * 60}")
    print(f"Port: {port}")
    print("ID: 1")
    print("Baud: 1000000")

    try:
        # Connect to gripper servo
        gripper_dxl = DynamixelDriver(
            port=port,
            baudrate=1000000,
            ids=[1],  # UR5 gripper servo is ID 1
            signs=[1],
            offsets_deg=[0.0],
        )

        if not gripper_dxl.connect():
            print(f"❌ Failed to connect to {side} gripper!")
            return False

        print(f"✅ Connected to {side} gripper")

        # Read current position
        pos = gripper_dxl.read_positions()
        if pos is not None:
            print(f"📍 Current position: {pos[0]:.3f} rad")

        # Test movements
        print(f"\n🔄 Testing {side} gripper movements...")

        # Test positions (adjust these based on your gripper's range)
        test_positions = [
            ("Closed", -0.075),
            ("25% Open", 0.0),
            ("50% Open", 0.087),
            ("75% Open", 0.168),
            ("Open", 0.25),
        ]

        for desc, position in test_positions:
            print(f"  → {desc}: {position:.3f} rad...", end="")
            gripper_dxl.write_positions([position])
            time.sleep(1.0)

            # Verify position
            actual = gripper_dxl.read_positions()
            if actual is not None:
                error = abs(actual[0] - position)
                if error < 0.1:
                    print(f" ✅ (actual: {actual[0]:.3f})")
                else:
                    print(f" ⚠️  (actual: {actual[0]:.3f}, error: {error:.3f})")
            else:
                print(" ❌ (no response)")

        # Return to neutral
        print("\n🔄 Returning to neutral position...")
        gripper_dxl.write_positions([0.087])  # Middle position
        time.sleep(0.5)

        gripper_dxl.disconnect()
        print(f"✅ {side} gripper test complete")
        return True

    except Exception as e:
        print(f"❌ Error testing {side} gripper: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("UR5 GRIPPER SERVO TEST")
    print("=" * 60)
    print("\nThis tests the UR5 gripper Dynamixel servos directly")
    print("Expected configuration:")
    print("  LEFT gripper:  /dev/ttyUSB3, ID 1")
    print("  RIGHT gripper: /dev/ttyUSB1, ID 1")

    # Test both grippers
    left_ok = test_gripper("left", "/dev/ttyUSB3")
    right_ok = test_gripper("right", "/dev/ttyUSB1")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"LEFT gripper:  {'✅ PASSED' if left_ok else '❌ FAILED'}")
    print(f"RIGHT gripper: {'✅ PASSED' if right_ok else '❌ FAILED'}")

    if left_ok and right_ok:
        print("\n✅ Both UR5 grippers are working correctly!")
        print("\nYou can now use:")
        print("  python scripts/run_teleop.py")
        print("\nThe GELLO grippers (ID 7 left, ID 16 right) will control")
        print("the UR5 grippers via the Dynamixel servos.")
    else:
        print("\n❌ Some grippers are not working.")
        print("\nTroubleshooting:")
        print("1. Check USB connections")
        print("2. Verify servo power is on")
        print(
            "3. Check servo IDs with: python scripts/dxl_scan.py /dev/ttyUSBx 1000000"
        )
        print("4. Try different USB ports if needed")

    return 0 if (left_ok and right_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
