#!/usr/bin/env python3
"""
Test ZCM publishing directly to verify it's working.
This simulates what streamdeck_pedal_watch.py should be doing.
"""

import sys
import time

try:
    import zerocm
    from gello_positions_t import gello_positions_t

    print("✓ ZCM and gello_positions_t imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure you're in the scripts directory and gello_positions_t.py exists")
    sys.exit(1)


def test_publishing():
    """Test publishing GELLO positions to ZCM."""

    # Initialize ZCM
    print("\nInitializing ZCM...")
    zcm = zerocm.ZCM()

    if not zcm.good():
        print("✗ Failed to initialize ZCM")
        return False

    print("✓ ZCM initialized")

    # Start ZCM
    zcm.start()
    print("✓ ZCM started")

    # Create test messages
    left_channel = "gello_positions_left"
    right_channel = "gello_positions_right"

    print("\nPublishing to channels:")
    print(f"  - {left_channel}")
    print(f"  - {right_channel}")
    print("\nSending 10 test messages...")

    for i in range(10):
        # Create LEFT message
        left_msg = gello_positions_t()
        left_msg.timestamp = int(time.time() * 1e6)
        left_msg.arm_side = "left"
        # Simple test positions
        left_msg.joint_positions = [
            -0.785,  # J1: -45 degrees
            -1.571,  # J2: -90 degrees
            0.0,  # J3: 0 degrees
            -1.571,  # J4: -90 degrees
            1.571,  # J5: 90 degrees
            0.0,  # J6: 0 degrees
        ]
        left_msg.gripper_position = 0.5
        left_msg.joint_velocities = [0.0] * 6
        left_msg.is_valid = True

        # Create RIGHT message
        right_msg = gello_positions_t()
        right_msg.timestamp = int(time.time() * 1e6)
        right_msg.arm_side = "right"
        # Slightly different positions
        right_msg.joint_positions = [
            -0.790,  # J1: -45.3 degrees
            -1.570,  # J2: -89.9 degrees
            0.001,  # J3: 0.06 degrees
            -1.572,  # J4: -90.1 degrees
            1.570,  # J5: 89.9 degrees
            0.001,  # J6: 0.06 degrees
        ]
        right_msg.gripper_position = 0.6
        right_msg.joint_velocities = [0.0] * 6
        right_msg.is_valid = True

        # Publish messages
        zcm.publish(left_channel, left_msg)
        zcm.publish(right_channel, right_msg)

        print(f"  [{i + 1}/10] Published messages (timestamp: {left_msg.timestamp})")
        time.sleep(0.1)  # 10Hz

    print("\n✓ Test complete!")
    print("\nTo verify messages are being received:")
    print("  1. In another terminal: python scripts/receive_gello_both.py")
    print("  2. Or: python scripts/receive_gello_left.py")
    print("  3. Or: python scripts/receive_gello_right.py")

    # Keep publishing for a bit longer
    print("\nContinuing to publish for 10 more seconds...")
    print("Press Ctrl+C to stop")

    try:
        for i in range(100):  # 10 seconds at 10Hz
            # Update timestamps
            left_msg.timestamp = int(time.time() * 1e6)
            right_msg.timestamp = int(time.time() * 1e6)

            # Vary positions slightly to show movement
            import math

            phase = i * 0.1
            left_msg.joint_positions[0] = -0.785 + 0.1 * math.sin(phase)
            right_msg.joint_positions[0] = -0.790 + 0.1 * math.sin(phase + 0.5)

            zcm.publish(left_channel, left_msg)
            zcm.publish(right_channel, right_msg)

            if i % 10 == 0:
                print(f"  Publishing... ({i // 10 + 1}/10 seconds)")

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by user")

    # Cleanup
    zcm.stop()
    print("\n✓ ZCM stopped")
    return True


def main():
    print("=" * 60)
    print("ZCM PUBLISHING TEST")
    print("=" * 60)

    success = test_publishing()

    if success:
        print("\n✅ Publishing test successful!")
    else:
        print("\n❌ Publishing test failed")
        print("\nTroubleshooting:")
        print("  1. Check that zerocm is installed: pip install zerocm")
        print("  2. Check that gello_positions_t.py exists in scripts/")
        print("  3. Try regenerating: zcm-gen -p gello_positions_simple.zcm")


if __name__ == "__main__":
    main()
