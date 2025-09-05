#!/usr/bin/env python3
"""
Clear stuck RTDE connections on UR robots.
Run this if you get "Another thread is already controlling the robot" errors.
"""

import socket
import sys
import time

# Try importing UR RTDE modules
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    try:
        from ur_rtde import rtde_control, rtde_receive

        RTDEControlInterface = rtde_control.RTDEControlInterface
        RTDEReceiveInterface = rtde_receive.RTDEReceiveInterface
    except ImportError:
        print("Error: UR RTDE modules not found. Install with: pip install ur_rtde")
        sys.exit(1)


def dashboard_cmd(host: str, cmd: str) -> str:
    """Send dashboard command to UR robot."""
    try:
        s = socket.create_connection((host, 29999), timeout=2.0)
        s.recv(4096)  # Welcome message
        s.send((cmd + "\n").encode())
        response = s.recv(4096).decode().strip()
        s.close()
        return response
    except Exception as e:
        return f"Error: {e}"


def clear_connections(host: str, verbose: bool = True, reload_external_control: bool = False):
    """Clear all RTDE connections for a UR robot.

    Args:
        host: IP address of the UR robot
        verbose: If True, print detailed progress
        reload_external_control: If True, reload ExternalControl.urp (requires dashboard access)

    Returns:
        bool: True if connections cleared successfully
    """
    if verbose:
        print(f"\n{'=' * 50}")
        print(f"Clearing connections for UR at {host}")
        print("=" * 50)

    success = True

    # Step 1: Try to stop any running program
    if verbose:
        print("1. Stopping any running program...")
    result = dashboard_cmd(host, "stop")
    if verbose:
        print(f"   Response: {result}")
    time.sleep(0.5)

    # Step 2: Try to create and immediately close control connections
    if verbose:
        print("2. Attempting to clear RTDE control connections...")
    for i in range(3):
        try:
            ctrl = RTDEControlInterface(host)
            if verbose:
                print(f"   Connection {i + 1}: Created successfully")
            try:
                ctrl.stopJ(2.0)  # Stop any motion
                if verbose:
                    print(f"   Connection {i + 1}: Sent stop command")
            except Exception:
                pass
            ctrl.disconnect()
            if verbose:
                print(f"   Connection {i + 1}: Disconnected")
            del ctrl
            time.sleep(0.2)
        except Exception as e:
            if verbose:
                print(f"   Connection {i + 1}: {e}")
            if "another thread" in str(e).lower():
                if verbose:
                    print("   -> Blocked by existing connection, waiting...")
                time.sleep(1.0)

    # Step 3: Optionally restart ExternalControl.urp
    if reload_external_control:
        if verbose:
            print("3. Reloading ExternalControl.urp...")
        dashboard_cmd(host, "close safety popup")
        dashboard_cmd(host, "unlock protective stop")
        dashboard_cmd(host, "power on")
        time.sleep(0.5)
        dashboard_cmd(host, "brake release")
        time.sleep(0.5)

        # Load and play ExternalControl
        result = dashboard_cmd(host, "load /programs/ExternalControl.urp")
        if verbose:
            print(f"   Load program: {result}")
        time.sleep(0.5)

        result = dashboard_cmd(host, "play")
        if verbose:
            print(f"   Play program: {result}")
        time.sleep(1.0)

    # Step 4: Test connection
    if verbose:
        print("4. Testing new connection...")
    try:
        test_ctrl = RTDEControlInterface(host)
        test_ctrl.disconnect()
        if verbose:
            print("   ✅ SUCCESS: Can create new control connections!")
    except Exception as e:
        success = False
        if verbose:
            print(f"   ❌ FAILED: {e}")
            if reload_external_control:
                print("\n   Manual fix required:")
                print("   1. On UR pendant: Stop any running program")
                print("   2. Load ExternalControl.urp")
                print("   3. Press Play button")
                print("   4. Check External Control node settings:")
                print("      - Host IP = Your PC's IP (NOT robot's IP)")
                print("      - Port = 50002")

    if verbose:
        print()

    return success


def clear_robots_quietly(hosts: list[str]) -> bool:
    """Clear connections on multiple robots quietly (for use in other scripts).

    Args:
        hosts: List of UR robot IP addresses

    Returns:
        bool: True if all robots cleared successfully
    """
    all_success = True
    for host in hosts:
        if host:  # Skip None/empty hosts
            try:
                success = clear_connections(host, verbose=False, reload_external_control=False)
                if not success:
                    all_success = False
                    print(f"[clear] {host}: Failed to clear connections")
            except Exception as e:
                all_success = False
                print(f"[clear] {host}: Error - {e}")
    return all_success


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clear stuck RTDE connections on UR robots")
    parser.add_argument(
        "--ur-left", type=str, default="192.168.1.211", help="IP address of left UR robot"
    )
    parser.add_argument(
        "--ur-right", type=str, default="192.168.1.210", help="IP address of right UR robot"
    )
    parser.add_argument("--both", action="store_true", help="Clear connections on both robots")

    args = parser.parse_args()

    if args.both:
        clear_connections(args.ur_left, verbose=True, reload_external_control=True)
        clear_connections(args.ur_right, verbose=True, reload_external_control=True)
    else:
        print("Clearing connections on left UR by default...")
        print("Use --both to clear both robots, or specify IPs with --ur-left/--ur-right")
        clear_connections(args.ur_left, verbose=True, reload_external_control=True)

    print("\n" + "=" * 50)
    print("DONE! You can now run your teleop script.")
    print("=" * 50)


if __name__ == "__main__":
    main()
