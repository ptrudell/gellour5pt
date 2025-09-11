#!/usr/bin/env python3
"""
Verify that ZCM messages are properly formatted with fingerprints.
This helps debug zcm-spy compatibility issues.
"""

import struct
import sys
import time

try:
    import zerocm
    from gello_msgs.gello_positions_t import gello_positions_t
except ImportError:
    print("Error: zerocm not installed or types not generated")
    print("Run: pip install zerocm")
    print("And: zcm-gen -p gello_positions.zcm")
    sys.exit(1)


def verify_message():
    """Create and verify a test message."""
    print("Creating test message...")

    # Create a test message
    msg = gello_positions_t()
    msg.timestamp = int(time.time() * 1e6)
    msg.joint_positions = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    msg.gripper_position = 2.5
    msg.joint_velocities = [0.0] * 6
    msg.is_valid = True
    msg.arm_side = "left"

    # Encode the message
    encoded = msg.encode()

    print("\nMessage details:")
    print(f"  Timestamp: {msg.timestamp}")
    print(f"  Arm side: {msg.arm_side}")
    print(f"  Joint positions: {msg.joint_positions}")
    print(f"  Gripper: {msg.gripper_position}")
    print(f"  Valid: {msg.is_valid}")

    print(f"\nEncoded size: {len(encoded)} bytes")

    # Check for fingerprint (first 8 bytes)
    if len(encoded) >= 8:
        fingerprint = struct.unpack(">Q", encoded[:8])[0]
        print(f"Fingerprint: 0x{fingerprint:016x}")
        print(f"Expected:    0x{gello_positions_t._get_hash_recursive([]):016x}")

        if fingerprint == gello_positions_t._get_hash_recursive([]):
            print("✅ Fingerprint matches! Message is properly formatted for zcm-spy")
        else:
            print("❌ Fingerprint mismatch! zcm-spy won't decode this properly")
            return False
    else:
        print("❌ Message too short - no fingerprint found")
        return False

    # Try to decode it back
    print("\nTesting decode...")
    try:
        decoded = gello_positions_t.decode(encoded)
        print(f"  Decoded timestamp: {decoded.timestamp}")
        print(f"  Decoded arm: {decoded.arm_side}")
        print(f"  Decoded joints: {decoded.joint_positions}")
        print("✅ Decode successful!")
        return True
    except Exception as e:
        print(f"❌ Decode failed: {e}")
        return False


def test_channel_publishing():
    """Test publishing to actual ZCM channels."""
    print("\n" + "=" * 60)
    print("Testing ZCM channel publishing...")
    print("=" * 60)

    # Initialize ZCM
    zcm = zerocm.ZCM()
    if not zcm.good():
        print("❌ Unable to initialize ZCM")
        return False

    zcm.start()

    # Create test messages
    left_msg = gello_positions_t()
    left_msg.timestamp = int(time.time() * 1e6)
    left_msg.joint_positions = [-0.785, -1.571, 0.0, -1.571, 1.571, 0.0]
    left_msg.gripper_position = 2.5
    left_msg.joint_velocities = [0.0] * 6
    left_msg.is_valid = True
    left_msg.arm_side = "left"

    right_msg = gello_positions_t()
    right_msg.timestamp = int(time.time() * 1e6)
    right_msg.joint_positions = [0.785, -1.571, 0.0, -1.571, -1.571, 0.0]
    right_msg.gripper_position = 4.1
    right_msg.joint_velocities = [0.0] * 6
    right_msg.is_valid = True
    right_msg.arm_side = "right"

    # Publish test messages
    print("\nPublishing test messages...")
    for i in range(5):
        left_msg.timestamp = int(time.time() * 1e6)
        right_msg.timestamp = int(time.time() * 1e6)

        zcm.publish("gello_positions_left", left_msg)
        zcm.publish("gello_positions_right", right_msg)

        print(f"  Published message pair {i + 1}/5")
        time.sleep(0.2)

    zcm.stop()
    print("✅ Publishing test complete!")
    return True


def main():
    print("\n" + "=" * 60)
    print("ZCM Message Verification Tool")
    print("=" * 60)

    # Test message creation and encoding
    if not verify_message():
        print("\n⚠️  Message verification failed!")
        print("Make sure you're using the generated gello_msgs package")
        sys.exit(1)

    # Test actual publishing
    if not test_channel_publishing():
        print("\n⚠️  Channel publishing test failed!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("\nYour ZCM messages are properly formatted for zcm-spy.")
    print("\nTo verify with zcm-spy:")
    print("  1. Run: zcm-spy")
    print("  2. Run: python scripts/publish_test_gello.py")
    print("  3. You should see both channels with proper decoding")
    print("=" * 60)


if __name__ == "__main__":
    main()
