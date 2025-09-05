#!/usr/bin/env python3
"""
Prepare UR robots for teleoperation by sending dashboard commands.
This automates the setup process as much as possible.
"""

import socket
import sys
import time


def send_dashboard_commands(host, commands):
    """Send a series of commands to UR dashboard."""
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        welcome = s.recv(4096).decode()
        print(f"Connected to {host}")

        for cmd in commands:
            print(f"  Sending: {cmd}")
            s.send((cmd + "\n").encode())
            response = s.recv(4096).decode().strip()
            print(f"    Response: {response}")
            time.sleep(0.5)

        s.close()
        return True
    except Exception as e:
        print(f"Error with {host}: {e}")
        return False


def prepare_ur(host):
    """Prepare a single UR robot for teleop."""
    print(f"\n{'=' * 50}")
    print(f"Preparing UR at {host}")
    print("=" * 50)

    commands = [
        "stop",  # Stop any running program
        "close safety popup",  # Clear safety popups
        "close popup",  # Clear any other popups
        "unlock protective stop",  # Clear protective stops
        "power on",  # Power on robot
        "brake release",  # Release brakes
        "load /programs/ExternalControl.urp",  # Try to load external control
        "play",  # Start the program
        "robotmode",  # Check robot mode
        "running",  # Check if running
    ]

    success = send_dashboard_commands(host, commands)

    if success:
        print(f"✓ Commands sent to {host}")
        print("  Note: If ExternalControl.urp doesn't exist, manually load a program")
    else:
        print(f"✗ Failed to prepare {host}")

    return success


def main():
    print("\nUR ROBOT PREPARATION TOOL")
    print("=" * 50)
    print("This will attempt to automatically prepare UR robots for teleop")
    print("")

    # Default IPs if none provided
    hosts = sys.argv[1:] if len(sys.argv) > 1 else ["192.168.1.211", "192.168.1.210"]

    print(f"Preparing robots at: {hosts}")

    for host in hosts:
        prepare_ur(host)

    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("1. Check each UR pendant - should show 'Program Running'")
    print("2. If not, manually load and run ExternalControl.urp")
    print("3. Enable Remote Control in Settings → System → Remote Control")
    print("4. Run: python gello/test_scripts/test_ur_connection.py", " ".join(hosts))
    print("5. Once test passes, run teleop")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())

