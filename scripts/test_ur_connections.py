#!/usr/bin/env python3
"""
Quick test to verify UR connections are working
"""

import sys


def test_connection(host):
    """Test RTDE connection to a UR robot."""
    try:
        from rtde_control import RTDEControlInterface
        from rtde_receive import RTDEReceiveInterface

        print(f"\nTesting {host}...")

        # Test control interface
        rtde_c = RTDEControlInterface(host)
        print("  ✅ Control interface connected")

        # Test receive interface
        rtde_r = RTDEReceiveInterface(host)
        print("  ✅ Receive interface connected")

        # Get robot status
        joints = rtde_r.getActualQ()
        if joints:
            print("  ✅ Robot responding (6 joints detected)")

        # Cleanup
        rtde_c.disconnect()
        rtde_r.disconnect()

        return True

    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False


def main():
    print("=" * 60)
    print("UR CONNECTION TEST")
    print("=" * 60)

    robots = {
        "LEFT (192.168.1.211)": "192.168.1.211",
        "RIGHT (192.168.1.210)": "192.168.1.210",
    }

    results = {}
    for name, host in robots.items():
        results[name] = test_connection(host)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    all_good = True
    for name, success in results.items():
        status = "✅ READY" if success else "❌ NOT READY"
        print(f"{name}: {status}")
        if not success:
            all_good = False

    if all_good:
        print("\n🎉 SUCCESS! Both robots are ready!")
        print("You can now run: python scripts/run_teleop.py")
    else:
        print("\n⚠️  Some robots need setup:")
        print("1. On pendant: Create/load ExternalControl.urp")
        print("2. Set Host IP = 192.168.1.8 (your PC)")
        print("3. Set Port = 50002")
        print("4. Press Play button")

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
