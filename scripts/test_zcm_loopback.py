#!/usr/bin/env python3
"""
Test ZCM publishing and receiving in the same process (loopback test).
"""

import time

try:
    import zerocm
    from gello_positions_t import gello_positions_t

    print("✓ Imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)


class TestReceiver:
    def __init__(self):
        self.msg_count = 0

    def handle(self, channel, msg):
        self.msg_count += 1
        print(f"  ✓ Received message #{self.msg_count} on channel '{channel}'")
        print(f"    Arm: {msg.arm_side}, Valid: {msg.is_valid}")
        print(f"    J1: {msg.joint_positions[0]:.3f} rad")


def main():
    print("\n" + "=" * 60)
    print("ZCM LOOPBACK TEST")
    print("=" * 60)

    # Create ZCM instance
    print("\n1. Creating ZCM instance...")
    zcm = zerocm.ZCM()

    if not zcm.good():
        print("✗ Failed to create ZCM")
        return
    print("✓ ZCM created")

    # Create receiver
    print("\n2. Setting up receiver...")
    receiver = TestReceiver()
    zcm.subscribe("gello_positions_left", gello_positions_t, receiver.handle)
    print("✓ Subscribed to 'gello_positions_left'")

    # Start ZCM in thread
    print("\n3. Starting ZCM...")
    zcm.start()
    print("✓ ZCM started")

    # Give it a moment
    time.sleep(0.1)

    # Publish test messages
    print("\n4. Publishing test messages...")
    for i in range(3):
        msg = gello_positions_t()
        msg.timestamp = int(time.time() * 1e6)
        msg.arm_side = "left"
        msg.joint_positions = [-0.785, -1.571, 0.0, -1.571, 1.571, 0.0]
        msg.gripper_position = 0.5
        msg.joint_velocities = [0.0] * 6
        msg.is_valid = True

        print(f"\n  Publishing message {i + 1}...")
        zcm.publish("gello_positions_left", msg)
        time.sleep(0.2)  # Give time to receive

    # Check results
    print("\n5. Results:")
    if receiver.msg_count > 0:
        print(f"✅ SUCCESS! Received {receiver.msg_count} messages")
        print("   ZCM is working correctly!")
    else:
        print("❌ FAILED! No messages received")
        print("\nPossible issues:")
        print("  - ZCM transport configuration")
        print("  - Message format mismatch")
        print("  - Threading issues")

    # Cleanup
    zcm.stop()
    print("\n✓ ZCM stopped")


if __name__ == "__main__":
    main()
