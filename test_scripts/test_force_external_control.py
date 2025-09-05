#!/usr/bin/env python3
"""
Test script to verify forcing ExternalControl.urp to load and play
when FREEDRIVE.URP is currently loaded.
"""

import argparse
import socket
import sys
import time
from contextlib import closing


def dash_exec(host: str, *cmds: str, wait: float = 0.15) -> list[str]:
    """Execute multiple dashboard commands in sequence."""
    out = []
    try:
        with closing(socket.create_connection((host, 29999), timeout=2.0)) as s:
            s.recv(4096)  # banner
            for c in cmds:
                s.sendall((c + "\n").encode())
                time.sleep(wait)
                try:
                    out.append(s.recv(4096).decode(errors="ignore").strip())
                except Exception:
                    out.append("")
    except Exception as e:
        out.append(f"[dash] {host}: error {e}")
    return out


def force_external_control(host: str, program: str = "/programs/ExternalControl.urp") -> bool:
    """Force load and play ExternalControl.urp, replacing whatever is currently loaded."""
    print(f"\n{'=' * 60}")
    print(f"Testing force-load of {program} on {host}")
    print(f"{'=' * 60}\n")

    # Check current state
    print("1. Checking current state...")
    state_before = dash_exec(host, "get loaded program", "programState")
    print(f"   Loaded program: {state_before[0]}")
    print(f"   Program state: {state_before[1]}")

    # Clear blockers and power sequence
    print("\n2. Clearing blockers and powering on...")
    dash_exec(
        host, "stop", "close safety popup", "unlock protective stop", "power on", "brake release"
    )
    print("   ✓ Cleared")

    # Check what's currently loaded
    state_lines = dash_exec(host, "get loaded program", "programState")
    loaded = "\n".join(state_lines)
    print(f"\n3. Current state after clear: {loaded}")

    # Load the requested program
    program_name = program.split("/")[-1].split("\\")[-1]
    if program_name not in loaded:
        print(f"\n4. Loading {program}...")
        load_resp = dash_exec(host, f"load {program}")
        print(f"   Response: {load_resp[0] if load_resp else 'no response'}")

        if load_resp and "error" in str(load_resp[0]).lower():
            # Try alternative path format
            alt_path = program[1:] if program.startswith("/") else "/" + program
            print(f"   Trying alternative path: {alt_path}")
            load_resp = dash_exec(host, f"load {alt_path}")
            print(f"   Response: {load_resp[0] if load_resp else 'no response'}")
    else:
        print(f"\n4. {program_name} already loaded")

    # Try to play and verify PLAYING
    print("\n5. Starting program...")
    success = False
    for i in range(1, 4):
        dash_exec(host, "play")
        time.sleep(0.6)  # Give time for program to start
        resp = "\n".join(dash_exec(host, "programState"))
        print(f"   Attempt {i}: programState → {resp}")

        if "PLAYING" in resp.upper() and program_name.upper() in resp.upper():
            print(f"   ✅ SUCCESS: {program_name} is PLAYING!")
            success = True
            break
        elif "STOPPED" in resp.upper() and "FREEDRIVE" in resp.upper():
            print(f"   ⚠️ Still showing FREEDRIVE - program may not exist at {program}")
        else:
            print("   ⚠️ Not playing yet...")

    # Test RTDE if playing
    if success:
        print("\n6. Testing RTDE control...")
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
                return success

        try:
            rcv = RTDEReceiveInterface(host)
            ctrl = RTDEControlInterface(host)
            q = rcv.getActualQ()
            ctrl.servoJ(q, 0.1, 0.1, 0.008, 0.1, 100)
            ctrl.stopJ(0.5)
            print("   ✅ RTDE control successful!")
        except Exception as e:
            print(f"   ✗ RTDE control failed: {e}")
            if "control script is not running" in str(e).lower():
                print("\n   IMPORTANT:")
                print("   - External Control node Host IP must be THIS computer's IP")
                print("   - Not the robot's IP!")
                print("   - Check the program tree on the pendant")

    return success


def main():
    parser = argparse.ArgumentParser(description="Force load ExternalControl.urp")
    parser.add_argument("host", help="UR robot IP")
    parser.add_argument(
        "--program", default="/programs/ExternalControl.urp", help="Path to program on robot"
    )

    args = parser.parse_args()

    success = force_external_control(args.host, args.program)

    print(f"\n{'=' * 60}")
    if success:
        print("✅ SUCCESS - ExternalControl.urp is PLAYING")
        print("The robot is ready for teleop!")
    else:
        print("❌ FAILED - Could not get ExternalControl.urp PLAYING")
        print("\nTroubleshooting:")
        print("1. Check the program exists at the specified path")
        print("2. Verify External Control URCap is installed")
        print("3. Enable Remote Control on the pendant")
        print("4. Clear any Protective Stops")
    print(f"{'=' * 60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

