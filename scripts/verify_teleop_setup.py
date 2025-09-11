#!/usr/bin/env python3
"""
Complete verification script for teleop setup
Tests all components and provides clear status
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.ur_dynamixel_robot import DynamixelDriver


def test_gello_arms():
    """Test GELLO arm connections."""
    print("\n" + "=" * 60)
    print("TESTING GELLO ARMS")
    print("=" * 60)

    results = {}

    # Test LEFT GELLO
    print("\nLEFT GELLO (IDs 1-7):")
    left_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
        baudrate=1000000,
        ids=[1, 2, 3, 4, 5, 6, 7],
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    if left_dxl.connect():
        pos = left_dxl.read_positions()
        if pos is not None and len(pos) == 7:
            print("  ✅ Connected - 6 joints + gripper (ID 7)")
            print(f"     Gripper position: {pos[6]:.3f} rad")
            results["left_gello"] = True
        else:
            print("  ❌ Connected but incomplete response")
            results["left_gello"] = False
        left_dxl.disconnect()
    else:
        print("  ❌ Failed to connect")
        results["left_gello"] = False

    # Test RIGHT GELLO
    print("\nRIGHT GELLO (IDs 10-16):")
    right_dxl = DynamixelDriver(
        port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
        baudrate=1000000,
        ids=[10, 11, 12, 13, 14, 15, 16],
        signs=[1] * 7,
        offsets_deg=[0.0] * 7,
    )

    if right_dxl.connect():
        pos = right_dxl.read_positions()
        if pos is not None and len(pos) == 7:
            print("  ✅ Connected - 6 joints + gripper (ID 16)")
            print(f"     Gripper position: {pos[6]:.3f} rad")
            results["right_gello"] = True
        else:
            print("  ❌ Connected but incomplete response")
            results["right_gello"] = False
        right_dxl.disconnect()
    else:
        print("  ❌ Failed to connect")
        results["right_gello"] = False

    return results


def test_ur_robots():
    """Test UR robot connections."""
    print("\n" + "=" * 60)
    print("TESTING UR5 ROBOTS")
    print("=" * 60)

    results = {}

    for side, host in [("LEFT", "192.168.1.211"), ("RIGHT", "192.168.1.210")]:
        print(f"\n{side} UR5 ({host}):")

        # Test ping
        import subprocess

        ping_result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host], capture_output=True
        )

        if ping_result.returncode != 0:
            print("  ❌ Not reachable (ping failed)")
            results[f"{side.lower()}_ur"] = False
            continue

        print("  ✅ Network reachable")

        # Test RTDE connection
        try:
            from rtde_control import RTDEControlInterface
            from rtde_receive import RTDEReceiveInterface

            rtde_c = RTDEControlInterface(host)
            rtde_r = RTDEReceiveInterface(host)

            joints = rtde_r.getActualQ()
            if joints and len(joints) == 6:
                print("  ✅ RTDE connected - 6 joints detected")
                print("  ✅ ExternalControl.urp is PLAYING")
                results[f"{side.lower()}_ur"] = True
            else:
                print("  ⚠️  RTDE connected but no joint data")
                results[f"{side.lower()}_ur"] = False

            rtde_c.disconnect()
            rtde_r.disconnect()

        except Exception as e:
            print(f"  ❌ RTDE connection failed: {e}")
            print("     → ExternalControl.urp not playing?")
            print("     → Wrong Host IP in External Control?")
            results[f"{side.lower()}_ur"] = False

    return results


def check_pc_network():
    """Check PC network configuration."""
    print("\n" + "=" * 60)
    print("PC NETWORK CONFIGURATION")
    print("=" * 60)

    import subprocess

    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)

    ips = result.stdout.strip().split()
    print(f"PC IP addresses: {', '.join(ips)}")

    if "192.168.1.8" in ips:
        print("✅ PC has expected IP: 192.168.1.8")
        return True
    else:
        print("⚠️  PC IP is not 192.168.1.8")
        print(
            "   Update Host IP in ExternalControl.urp to:", ips[0] if ips else "unknown"
        )
        return False


def main():
    print("\n" + "=" * 60)
    print("TELEOP SYSTEM VERIFICATION")
    print("=" * 60)
    print("\nThis will test all components of your teleop system")

    # Check network
    pc_ok = check_pc_network()

    # Test GELLO
    gello_results = test_gello_arms()

    # Test UR
    ur_results = test_ur_robots()

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_ok = True

    print("\n🔌 Network:")
    print(f"  PC IP configured: {'✅' if pc_ok else '❌ (update ExternalControl.urp)'}")

    print("\n🦾 GELLO Arms:")
    print(f"  LEFT (IDs 1-7):   {'✅' if gello_results.get('left_gello') else '❌'}")
    print(f"  RIGHT (IDs 10-16): {'✅' if gello_results.get('right_gello') else '❌'}")

    if not (gello_results.get("left_gello") and gello_results.get("right_gello")):
        all_ok = False

    print("\n🤖 UR5 Robots:")
    print(f"  LEFT (192.168.1.211):  {'✅' if ur_results.get('left_ur') else '❌'}")
    print(f"  RIGHT (192.168.1.210): {'✅' if ur_results.get('right_ur') else '❌'}")

    if not (ur_results.get("left_ur") and ur_results.get("right_ur")):
        all_ok = False

    print("\n" + "=" * 60)

    if all_ok:
        print("✅ SYSTEM READY FOR TELEOP!")
        print("\nYou can now run:")
        print("  python scripts/run_teleop.py --test-mode")
        print("\nGripper control:")
        print("  GELLO ID 7 → LEFT UR5 gripper (tool outputs)")
        print("  GELLO ID 16 → RIGHT UR5 gripper (tool outputs)")
        return 0
    else:
        print("❌ SYSTEM NOT READY")
        print("\nTroubleshooting:")

        if not gello_results.get("left_gello") or not gello_results.get("right_gello"):
            print("\n📍 GELLO Issues:")
            print("  - Check servo power is on")
            print("  - Check USB connections")
            print("  - Run: python scripts/dxl_scan.py <port> 1000000")

        if not ur_results.get("left_ur") or not ur_results.get("right_ur"):
            print("\n📍 UR5 Issues:")
            print("  - Create and run ExternalControl.urp on pendant")
            print("  - Set Host IP to your PC's IP (not robot's IP)")
            print("  - Press Play button on pendant")
            print("  - Enable Remote Control")
            print("  - See: EXTERNAL_CONTROL_SETUP.md for details")

        return 1


if __name__ == "__main__":
    sys.exit(main())
