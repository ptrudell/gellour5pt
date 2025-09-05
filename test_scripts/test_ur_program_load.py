#!/usr/bin/env python3
"""
Quick test to verify UR program loading and RTDE control works.
Use this to debug connection issues before running full teleop.
"""

import argparse
import socket
import sys
import time


def dash_cmd(host: str, cmd: str, timeout: float = 2.0) -> str:
    """Send a single dashboard command and return response."""
    try:
        s = socket.create_connection((host, 29999), timeout=timeout)
        s.recv(4096)  # welcome
        s.send((cmd + "\n").encode())
        resp = s.recv(4096).decode(errors="ignore").strip()
        s.close()
        return resp
    except Exception as e:
        return f"<error: {e}>"


def test_program_load(host: str, program: str = "/programs/ExternalControl.urp") -> bool:
    """Test loading and running a UR program."""
    print(f"\n{'=' * 60}")
    print(f"Testing {host} with program: {program}")
    print(f"{'=' * 60}\n")

    # Check initial state
    print("1. Checking initial state...")
    mode = dash_cmd(host, "robotmode")
    print(f"   Robot mode: {mode}")

    safety = dash_cmd(host, "safetystatus")
    print(f"   Safety status: {safety}")

    prog_state = dash_cmd(host, "programState")
    print(f"   Program state: {prog_state}")

    loaded = dash_cmd(host, "get loaded program")
    print(f"   Loaded program: {loaded}")

    # Try to load the program
    print(f"\n2. Loading {program}...")
    load_resp = dash_cmd(host, f"load {program}")
    print(f"   Response: {load_resp}")

    if "error" in load_resp.lower() or "failed" in load_resp.lower():
        # Try alternative path format
        print("   Trying without leading slash...")
        alt_path = program[1:] if program.startswith("/") else "/" + program
        load_resp = dash_cmd(host, f"load {alt_path}")
        print(f"   Response: {load_resp}")

    # Clear any popups and play
    print("\n3. Clearing popups and starting program...")
    for cmd in [
        "close popup",
        "close safety popup",
        "unlock protective stop",
        "power on",
        "brake release",
        "play",
    ]:
        resp = dash_cmd(host, cmd)
        print(f"   {cmd}: {resp}")

    # Wait and check state
    print("\n4. Waiting for program to start...")
    time.sleep(1.0)

    prog_state = dash_cmd(host, "programState")
    print(f"   Program state: {prog_state}")

    is_running = dash_cmd(host, "is program running")
    print(f"   Is running: {is_running}")

    # Test RTDE control
    print("\n5. Testing RTDE control...")
    try:
        from rtde_control import RTDEControlInterface
        from rtde_receive import RTDEReceiveInterface
    except Exception:
        try:
            from ur_rtde import rtde_control, rtde_receive

            RTDEControlInterface = rtde_control.RTDEControlInterface
            RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
        except Exception as e:
            print(f"   ✗ Cannot import RTDE: {e}")
            return False

    try:
        rcv = RTDEReceiveInterface(host)
        ctrl = RTDEControlInterface(host)

        # Try a no-op servoJ
        q = rcv.getActualQ()
        ctrl.servoJ(q, 0.1, 0.1, 0.008, 0.1, 100)
        ctrl.stopJ(0.5)

        print("   ✓ RTDE control successful!")
        return True

    except Exception as e:
        print(f"   ✗ RTDE control failed: {e}")

        if "control script is not running" in str(e).lower():
            print("\n   DIAGNOSIS:")
            print("   - Program loaded but RTDE script not accepted")
            print("   - Check External Control node settings:")
            print("     • Host IP should be THIS computer's IP")
            print("     • Port: 30001 or 30002 (default)")
            print("   - Ensure Remote Control is enabled")
            print("   - Try stopping and restarting the program")

        return False


def main():
    parser = argparse.ArgumentParser(description="Test UR program loading")
    parser.add_argument("host", help="UR robot IP")
    parser.add_argument(
        "--program", default="/programs/ExternalControl.urp", help="Path to program on robot"
    )

    args = parser.parse_args()

    success = test_program_load(args.host, args.program)

    print(f"\n{'=' * 60}")
    if success:
        print("✅ SUCCESS - Robot ready for teleop!")
    else:
        print("❌ FAILED - See errors above")
    print(f"{'=' * 60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

