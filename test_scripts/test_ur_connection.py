#!/usr/bin/env python3
"""
Test UR robot connectivity and control readiness.
This helps diagnose why teleop might not be working.
"""

import socket
import sys
import time

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except Exception:
    try:
        from ur_rtde import rtde_control, rtde_receive

        RTDEControlInterface = rtde_control.RTDEControlInterface
        RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
    except Exception as e:
        print(f"[ERROR] Could not import UR RTDE modules: {e}")
        sys.exit(1)


def test_ping(host):
    """Test basic network connectivity."""
    import subprocess

    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host], capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def test_dashboard(host):
    """Test dashboard connection and send play command."""
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        welcome = s.recv(4096).decode()
        print(f"     Dashboard welcome: {welcome.strip()}")

        # Try to get robot mode
        s.send(b"robotmode\n")
        response = s.recv(4096).decode()
        print(f"     Robot mode: {response.strip()}")

        # Send play command
        s.send(b"play\n")
        response = s.recv(4096).decode()
        print(f"     Play command response: {response.strip()}")

        s.close()
        return True
    except Exception as e:
        print(f"     Dashboard error: {e}")
        return False


def test_ur(host):
    """Test complete UR connectivity."""
    print(f"\n{'=' * 50}")
    print(f"Testing UR at {host}")
    print("=" * 50)

    # 1. Network connectivity
    print("\n1. Network connectivity:")
    if test_ping(host):
        print("   ✓ Ping successful")
    else:
        print(f"   ✗ Cannot ping {host}")
        print("   → Check network cable and IP address")
        return False

    # 2. Dashboard connection
    print("\n2. Dashboard connection (port 29999):")
    if test_dashboard(host):
        print("   ✓ Dashboard accessible")
    else:
        print("   ✗ Dashboard not accessible")
        return False

    # 3. RTDE Receive Interface
    print("\n3. RTDE Receive Interface (port 30004):")
    try:
        rcv = RTDEReceiveInterface(host)
        print("   ✓ Receive interface created")

        # Try to read joint positions
        q = rcv.getActualQ()
        if q:
            print("   ✓ Can read joint positions")
            print(f"     Current joints: {[f'{x:.3f}' for x in q]}")
        else:
            print("   ✗ Cannot read joint positions")
    except Exception as e:
        print(f"   ✗ Receive interface failed: {e}")
        return False

    # 4. RTDE Control Interface
    print("\n4. RTDE Control Interface (port 30003):")
    try:
        ctrl = RTDEControlInterface(host)
        print("   ✓ Control interface created")

        # Test control with a no-op move
        current_q = rcv.getActualQ()
        if current_q:
            ctrl.servoJ(current_q, 0.1, 0.1, 0.008, 0.1, 100)
            print("   ✓ Control test successful (servoJ)")
        else:
            print("   ✗ Cannot test control (no position)")

    except Exception as e:
        error_msg = str(e).lower()
        if "control script is not running" in error_msg:
            print("   ✗ Control script not running!")
            print("   ")
            print("   SOLUTION:")
            print("   1. On UR pendant: Menu → Run Program")
            print("   2. Load 'ExternalControl.urp' or your control program")
            print("   3. Press green Play button (▶)")
            print("   4. Status should show 'Program Running'")
        else:
            print(f"   ✗ Control interface failed: {e}")
        return False

    print(f"\n✅ UR at {host} is READY for teleop!")
    return True


def main():
    print("\nUR ROBOT CONNECTIVITY TEST")
    print("=" * 50)

    if len(sys.argv) < 2:
        print("Usage: python test_ur_connection.py <UR_IP> [UR_IP2]")
        print("Example: python test_ur_connection.py 192.168.1.211 192.168.1.210")
        sys.exit(1)

    all_ready = True
    for host in sys.argv[1:]:
        if not test_ur(host):
            all_ready = False

    print("\n" + "=" * 50)
    if all_ready:
        print("✅ ALL UR ROBOTS READY FOR TELEOP")
    else:
        print("⚠️  SOME UR ROBOTS NOT READY")
        print("Fix the issues above before running teleop")
    print("=" * 50)

    return 0 if all_ready else 1


if __name__ == "__main__":
    sys.exit(main())

