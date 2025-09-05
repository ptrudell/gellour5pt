#!/usr/bin/env python3
"""
Create and start an RTDE control program on UR robots.
This allows teleop to work even if ExternalControl.urp doesn't exist.
"""

import socket
import time
from typing import Optional


def send_urscript_rtde_program(host: str, pc_host: str = "192.168.1.8", port: int = 30003) -> bool:
    """
    Send a URScript program that enables RTDE control directly.

    Args:
        host: UR robot IP address
        pc_host: PC IP address for RTDE connection
        port: UR primary interface port (30003)

    Returns:
        bool: True if program was sent successfully
    """

    # URScript program that keeps the robot in RTDE control mode
    urscript_program = """def rtde_control_program():
  # Enable RTDE control mode
  textmsg("Starting RTDE control mode")
  
  # Set safety parameters
  set_safety_mode_transition_hardness(1)
  
  # Keep alive loop - just maintain connection
  while True:
    # Small sleep to prevent CPU overload
    sleep(0.008)
    
    # The actual control happens via RTDE from PC
    # This script just keeps the robot ready
    sync()
  end
end

# Run the program
rtde_control_program()
"""

    try:
        # Connect to UR primary interface
        s = socket.create_connection((host, port), timeout=2)

        # Send the URScript program
        s.send(urscript_program.encode())

        # Give it a moment to start
        time.sleep(0.5)

        s.close()
        print(f"[rtde] {host}: URScript RTDE program sent successfully")
        return True

    except Exception as e:
        print(f"[rtde] {host}: Failed to send URScript - {e}")
        return False


def enable_rtde_mode(host: str, pc_host: str = "192.168.1.8") -> bool:
    """
    Enable RTDE control mode on a UR robot using direct URScript.

    Args:
        host: UR robot IP address
        pc_host: PC IP address for RTDE

    Returns:
        bool: True if RTDE mode was enabled
    """

    # First stop any running program
    try:
        dash = socket.create_connection((host, 29999), timeout=2)
        dash.recv(4096)  # Welcome

        # Stop current program
        dash.send(b"stop\n")
        time.sleep(0.2)
        dash.recv(4096)

        # Clear any popups
        dash.send(b"close safety popup\n")
        time.sleep(0.1)
        dash.recv(4096)

        dash.send(b"unlock protective stop\n")
        time.sleep(0.1)
        dash.recv(4096)

        dash.close()

    except Exception as e:
        print(f"[rtde] {host}: Dashboard error - {e}")

    # Send the URScript program
    return send_urscript_rtde_program(host, pc_host)


def check_rtde_ready(host: str, timeout: float = 2.0) -> bool:
    """
    Check if RTDE control is ready on a UR robot with timeout.

    Args:
        host: UR robot IP address
        timeout: Maximum time to wait for connection

    Returns:
        bool: True if RTDE is ready
    """
    import threading

    result = [False]  # Use list to share result with thread

    def test_connection():
        try:
            # Try to import and test RTDE
            from rtde_control import RTDEControlInterface

            ctrl = RTDEControlInterface(host)
            # Try a simple command
            try:
                ctrl.getTargetTCPSpeed()
                ctrl.disconnect()
                result[0] = True
            except:
                try:
                    ctrl.disconnect()
                except:
                    pass
                result[0] = False

        except Exception:
            result[0] = False

    # Run test in thread with timeout
    thread = threading.Thread(target=test_connection)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print(f"[rtde] {host}: Connection attempt timed out after {timeout}s")
        return False

    return result[0]


def setup_rtde_for_teleop(
    left_host: Optional[str] = None, right_host: Optional[str] = None, pc_host: str = "192.168.1.8"
) -> dict:
    """
    Setup RTDE control for teleop on one or both UR robots.

    Args:
        left_host: Left UR IP (or None to skip)
        right_host: Right UR IP (or None to skip)
        pc_host: PC IP address

    Returns:
        dict: Status for each robot
    """
    results = {}

    for name, host in [("left", left_host), ("right", right_host)]:
        if not host:
            continue

        print(f"\n[RTDE Setup] {name.upper()} UR at {host}")

        # Check if already ready
        if check_rtde_ready(host):
            print("  ✓ RTDE already ready")
            results[name] = True
            continue

        # Try to enable RTDE mode
        print("  Enabling RTDE mode via URScript...")
        if enable_rtde_mode(host, pc_host):
            time.sleep(1.0)  # Give it a moment

            # Verify it worked
            if check_rtde_ready(host):
                print("  ✓ RTDE mode enabled successfully!")
                results[name] = True
            else:
                print("  ✗ RTDE mode sent but not responding")
                results[name] = False
        else:
            print("  ✗ Failed to send RTDE program")
            results[name] = False

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup RTDE control on UR robots")
    parser.add_argument("--left", default="192.168.1.211", help="Left UR IP")
    parser.add_argument("--right", default="192.168.1.210", help="Right UR IP")
    parser.add_argument("--pc-host", default="192.168.1.8", help="PC IP address")

    args = parser.parse_args()

    print("=" * 60)
    print("UR RTDE CONTROL SETUP")
    print("=" * 60)
    print(f"PC IP: {args.pc_host}")
    print(f"Left UR: {args.left}")
    print(f"Right UR: {args.right}")

    results = setup_rtde_for_teleop(args.left, args.right, args.pc_host)

    print("\n" + "=" * 60)
    if all(results.values()):
        print("✅ ALL ROBOTS READY FOR TELEOP!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"❌ Failed to setup: {', '.join(failed)}")
        print("\nTry manual setup on pendant:")
        print("1. Create new program")
        print("2. Add External Control URCap node")
        print(f"3. Set Host IP = {args.pc_host}")
        print("4. Save as ExternalControl.urp")
        print("5. Press Play")
    print("=" * 60)
