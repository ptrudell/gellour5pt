#!/usr/bin/env python3
"""
UR Connection Debug Tool
Tests UR connectivity, dashboard commands, and RTDE control.
"""

import argparse
import socket
import sys
import time


def test_dashboard(host: str, verbose: bool = False) -> bool:
    """Test dashboard connection and get robot state."""
    print(f"\n{'=' * 60}")
    print(f"Testing Dashboard on {host}:29999")
    print(f"{'=' * 60}")

    try:
        s = socket.create_connection((host, 29999), timeout=2)
        welcome = s.recv(4096).decode().strip()
        print(f"✓ Connected: {welcome}")

        # Test various status commands
        test_commands = [
            ("robotmode", "Robot mode"),
            ("programState", "Program state"),
            ("is program running", "Program running?"),
            ("get loaded program", "Loaded program"),
            ("safetystatus", "Safety status"),
            ("running", "Controller status"),
        ]

        for cmd, desc in test_commands:
            s.send((cmd + "\n").encode())
            response = s.recv(4096).decode().strip()
            print(f"  {desc}: {response}")
            if verbose:
                print(f"    (raw: {repr(response)})")

        s.close()
        return True

    except Exception as e:
        print(f"✗ Dashboard error: {e}")
        return False


def test_rtde_receive(host: str) -> bool:
    """Test RTDE receive interface."""
    print(f"\n{'=' * 60}")
    print(f"Testing RTDE Receive on {host}")
    print(f"{'=' * 60}")

    try:
        from rtde_receive import RTDEReceiveInterface
    except Exception:
        try:
            from ur_rtde import rtde_receive

            RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
        except Exception as e:
            print(f"✗ Cannot import RTDE: {e}")
            return False

    try:
        rcv = RTDEReceiveInterface(host)
        print("✓ RTDE Receive connected")

        # Read some basic info
        q = rcv.getActualQ()
        print(f"  Joint positions: {[f'{v:.3f}' for v in q]}")

        tcp = rcv.getActualTCPPose()
        print(f"  TCP pose: {[f'{v:.3f}' for v in tcp[:3]]} (xyz)")

        mode = rcv.getRobotMode()
        print(f"  Robot mode: {mode}")

        return True

    except Exception as e:
        print(f"✗ RTDE Receive error: {e}")
        return False


def test_rtde_control(host: str) -> bool:
    """Test RTDE control interface."""
    print(f"\n{'=' * 60}")
    print(f"Testing RTDE Control on {host}")
    print(f"{'=' * 60}")

    try:
        from rtde_control import RTDEControlInterface
    except Exception:
        try:
            from ur_rtde import rtde_control

            RTDEControlInterface = rtde_control.RTDEControlInterface
        except Exception as e:
            print(f"✗ Cannot import RTDE: {e}")
            return False

    try:
        ctrl = RTDEControlInterface(host)
        print("✓ RTDE Control connected")

        # Try to get the current position and send a no-op command
        # This tests if external control is actually running
        try:
            from rtde_receive import RTDEReceiveInterface
        except Exception:
            from ur_rtde import rtde_receive

            RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface

        rcv = RTDEReceiveInterface(host)
        current_q = rcv.getActualQ()

        # Try a minimal servoJ command (no actual movement)
        ctrl.servoJ(current_q, 0.1, 0.1, 0.008, 0.1, 100)
        print("✓ servoJ test command successful - External Control is running!")

        # Clean stop
        ctrl.stopJ(0.5)

        return True

    except Exception as e:
        error_msg = str(e)
        print(f"✗ RTDE Control error: {error_msg}")

        if "control script is not running" in error_msg.lower():
            print("\n⚠️  SOLUTION:")
            print("  1. On the UR pendant touchscreen:")
            print("     a. Tap menu (≡) → Run Program")
            print("     b. Load 'ExternalControl.urp' (or your RTDE program)")
            print("     c. Press green Play button (▶)")
            print("  2. Ensure status shows 'Program Running'")
            print("  3. Enable Remote Control in settings if not already")

        return False


def attempt_program_load(host: str, program: str) -> bool:
    """Attempt to load and play a program via dashboard."""
    print(f"\n{'=' * 60}")
    print(f"Attempting to load '{program}' on {host}")
    print(f"{'=' * 60}")

    try:
        s = socket.create_connection((host, 29999), timeout=2)
        s.recv(4096)  # Welcome

        commands = [
            "stop",
            "close safety popup",
            "unlock protective stop",
            "power on",
            "brake release",
            f"load {program}",
            "play",
        ]

        for cmd in commands:
            print(f"  Sending: {cmd}")
            s.send((cmd + "\n").encode())
            response = s.recv(4096).decode().strip()

            if "Error" in response or "File not found" in response:
                print(f"    ⚠️ Response: {response}")
            else:
                print(f"    ✓ Response: {response}")

        s.close()

        # Wait for program to start
        print("\n  Waiting 2 seconds for program to start...")
        time.sleep(2)

        # Check if it worked
        return test_rtde_control(host)

    except Exception as e:
        print(f"✗ Load program error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Debug UR robot connections")
    parser.add_argument("host", help="UR robot IP address")
    parser.add_argument(
        "--program",
        default="ExternalControl.urp",
        help="Program to load (default: ExternalControl.urp)",
    )
    parser.add_argument(
        "--auto-load",
        action="store_true",
        help="Automatically try to load the program if control fails",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("\nUR Connection Debugger")
    print(f"Testing robot at: {args.host}")

    # Test dashboard
    dash_ok = test_dashboard(args.host, args.verbose)

    # Test RTDE receive
    rcv_ok = test_rtde_receive(args.host)

    # Test RTDE control
    ctrl_ok = test_rtde_control(args.host)

    # Auto-load if requested and control failed
    if args.auto_load and not ctrl_ok and dash_ok:
        print(f"\nAuto-load enabled, attempting to load '{args.program}'...")
        ctrl_ok = attempt_program_load(args.host, args.program)

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Dashboard:     {'✓ OK' if dash_ok else '✗ FAILED'}")
    print(f"RTDE Receive:  {'✓ OK' if rcv_ok else '✗ FAILED'}")
    print(f"RTDE Control:  {'✓ OK' if ctrl_ok else '✗ FAILED'}")

    if ctrl_ok:
        print("\n✅ Robot is ready for teleop!")
    else:
        print("\n❌ Robot is NOT ready for teleop - see errors above")

    return 0 if ctrl_ok else 1


if __name__ == "__main__":
    sys.exit(main())
