#!/usr/bin/env python3
"""
Clear UR robot connections and prepare for teleoperation.
This script clears RTDE connections and ensures robots are ready.
"""

import socket
import subprocess
import sys
import time


def clear_robot_connection(host):
    """Clear all connections to a UR robot."""
    print(f"\n[{host}] Clearing connections...")

    # Try to kill any existing RTDE connections
    try:
        # Connect to dashboard
        dash_sock = socket.create_connection((host, 29999), timeout=2)
        dash_sock.recv(4096)  # Welcome message

        # Send commands to reset state
        commands = [
            "stop",
            "close safety popup",
            "unlock protective stop",
            "power on",
            "brake release",
        ]

        for cmd in commands:
            dash_sock.send((cmd + "\n").encode())
            response = dash_sock.recv(4096).decode()
            if "Error" not in response:
                print(f"  ✓ {cmd}")
            time.sleep(0.1)

        dash_sock.close()
        print("  ✓ Dashboard commands sent")

    except Exception as e:
        print(f"  ✗ Dashboard error: {e}")
        return False

    # Small delay to let robot process
    time.sleep(0.5)

    # Try to clear RTDE by connecting and immediately disconnecting
    try:
        test_sock = socket.create_connection((host, 30004), timeout=1)
        test_sock.close()
        print("  ✓ RTDE port cleared")
    except:
        pass

    return True


def load_external_control(host):
    """Load and start ExternalControl.urp on the robot."""
    print(f"\n[{host}] Loading ExternalControl.urp...")

    try:
        dash_sock = socket.create_connection((host, 29999), timeout=2)
        dash_sock.recv(4096)  # Welcome

        # Load the program
        dash_sock.send(b"load /programs/ExternalControl.urp\n")
        response = dash_sock.recv(4096).decode()

        if "Error" in response or "not found" in response.lower():
            print(f"  ✗ Failed to load: {response.strip()}")
            print("  → Manual action required:")
            print("    1. On pendant: File → Load Program → ExternalControl.urp")
            print("    2. Press Play button")
            return False

        time.sleep(0.5)

        # Play the program
        dash_sock.send(b"play\n")
        response = dash_sock.recv(4096).decode()

        if "Error" not in response:
            print("  ✓ ExternalControl.urp loaded and playing")
            return True
        else:
            print(f"  ✗ Failed to play: {response.strip()}")
            return False

    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        return False


def check_program_state(host):
    """Check if ExternalControl is running."""
    try:
        dash_sock = socket.create_connection((host, 29999), timeout=2)
        dash_sock.recv(4096)  # Welcome

        # Check loaded program
        dash_sock.send(b"get loaded program\n")
        loaded = dash_sock.recv(4096).decode()

        # Check program state
        dash_sock.send(b"programState\n")
        state = dash_sock.recv(4096).decode()

        dash_sock.close()

        is_external = "ExternalControl" in loaded or "external" in loaded.lower()
        is_playing = "PLAYING" in state.upper()

        return is_external, is_playing, loaded.strip(), state.strip()

    except Exception as e:
        return False, False, str(e), ""


def kill_python_processes():
    """Kill any existing Python teleop processes."""
    print("\nKilling existing Python processes...")

    # Kill specific scripts that might be holding connections
    scripts_to_kill = [
        "streamdeck_pedal_watch.py",
        "run_teleop.py",
        "test_ur_connection.py",
    ]

    for script in scripts_to_kill:
        try:
            result = subprocess.run(
                ["pkill", "-f", script], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✓ Killed {script}")
        except:
            pass


def main():
    """Main function to clear connections and prepare robots."""
    print("=" * 60)
    print("UR ROBOT CONNECTION CLEANER")
    print("=" * 60)

    # Define robot hosts
    robots = {"LEFT": "192.168.1.211", "RIGHT": "192.168.1.210"}

    # Kill existing processes
    kill_python_processes()
    time.sleep(1)

    # Process each robot
    all_ready = True

    for name, host in robots.items():
        print(f"\n{'=' * 30}")
        print(f"{name} ROBOT ({host})")
        print(f"{'=' * 30}")

        # Clear connections
        clear_robot_connection(host)

        # Check current state
        is_external, is_playing, loaded, state = check_program_state(host)

        print("\nCurrent state:")
        print(f"  Program: {loaded}")
        print(f"  State: {state}")

        if not is_external or not is_playing:
            # Try to load ExternalControl
            if load_external_control(host):
                print(f"  ✓ {name} robot ready")
            else:
                print(f"\n⚠️  {name} robot needs manual setup:")
                print(f"  1. On pendant for {host}:")
                print("     - Stop any running program")
                print("     - File → Load Program → ExternalControl.urp")
                print("     - Press Play (▶)")
                print("     - Enable Remote Control if prompted")
                print("  2. Then run this script again")
                all_ready = False
        else:
            print("  ✓ ExternalControl already running")

    print("\n" + "=" * 60)
    if all_ready:
        print("✅ ALL ROBOTS READY FOR TELEOPERATION")
        print("\nYou can now run:")
        print("  python3 scripts/run_teleop.py")
        print("\nOr for test mode:")
        print("  python3 scripts/run_teleop.py --test-mode")
    else:
        print("⚠️  MANUAL SETUP REQUIRED")
        print("Complete the steps above, then run this script again")
    print("=" * 60)

    return 0 if all_ready else 1


if __name__ == "__main__":
    sys.exit(main())
