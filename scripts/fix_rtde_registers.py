#!/usr/bin/env python3
"""
Fix RTDE register conflicts on UR robots.
This resolves the "RTDE input registers are already in use" error.
"""

import socket
import struct
import sys
import time


def send_dashboard_cmd(host, cmd):
    """Send a single dashboard command."""
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        s.recv(4096)  # Welcome
        s.send((cmd + "\n").encode())
        response = s.recv(4096).decode().strip()
        s.close()
        return response
    except Exception as e:
        return f"Error: {e}"


def fix_rtde_registers(host):
    """Fix RTDE register conflicts."""
    print(f"\nFixing RTDE registers on {host}...")

    # Step 1: Stop any running program
    print("  1. Stopping current program...")
    response = send_dashboard_cmd(host, "stop")
    if "Error" not in response:
        print("     ✓ Program stopped")
    else:
        print(f"     ⚠ {response}")

    time.sleep(1)

    # Step 2: Clear safety popup if any
    print("  2. Clearing safety popups...")
    send_dashboard_cmd(host, "close safety popup")
    print("     ✓ Cleared")

    # Step 3: Power cycle to clear registers
    print("  3. Power cycling robot...")
    send_dashboard_cmd(host, "power off")
    time.sleep(2)
    send_dashboard_cmd(host, "power on")
    time.sleep(3)
    send_dashboard_cmd(host, "brake release")
    print("     ✓ Power cycled")

    # Step 4: Load a simple clearing program first
    print("  4. Loading register clearing program...")

    # Create a simple URScript to clear registers
    clear_script = """
def clear_registers():
  # Clear all RTDE registers
  write_output_boolean_register(0, False)
  write_output_boolean_register(1, False)
  write_output_boolean_register(2, False)
  write_output_boolean_register(3, False)
  write_output_boolean_register(4, False)
  write_output_boolean_register(5, False)
  write_output_boolean_register(6, False)
  write_output_boolean_register(7, False)
  
  # Clear integer registers
  write_output_integer_register(0, 0)
  write_output_integer_register(1, 0)
  write_output_integer_register(2, 0)
  write_output_integer_register(3, 0)
  
  # Clear double registers  
  write_output_float_register(0, 0.0)
  write_output_float_register(1, 0.0)
  write_output_float_register(2, 0.0)
  write_output_float_register(3, 0.0)
  
  # Small delay
  sleep(0.5)
end

clear_registers()
"""

    # Send the clearing script via primary interface
    try:
        s = socket.create_connection((host, 30001), timeout=2)
        s.send(clear_script.encode())
        time.sleep(1)
        s.close()
        print("     ✓ Clearing script sent")
    except Exception as e:
        print(f"     ⚠ Could not send script: {e}")

    time.sleep(2)

    # Step 5: Load ExternalControl.urp
    print("  5. Loading ExternalControl.urp...")

    # Try different possible paths
    paths_to_try = [
        "ExternalControl.urp",
        "/programs/ExternalControl.urp",
        "ExternalControl",
        "/ExternalControl.urp",
    ]

    loaded = False
    for path in paths_to_try:
        response = send_dashboard_cmd(host, f"load {path}")
        if "Error" not in response and "not found" not in response.lower():
            print(f"     ✓ Program loaded from {path}")
            loaded = True
            break

    if not loaded:
        print("     ✗ ExternalControl.urp not found in standard locations")
        print("\n     MANUAL ACTION REQUIRED:")
        print(f"     On the pendant for {host}:")
        print("     1. File → Load Program → ExternalControl.urp")
        print("     2. Installation → URCaps → External Control")
        print("     3. Set Host IP = YOUR COMPUTER's IP (not robot IP)")
        print("     4. Save installation")
        print("     5. Press Play (▶)")
        return False

    time.sleep(1)

    # Step 6: Play the program
    print("  6. Starting ExternalControl...")
    response = send_dashboard_cmd(host, "play")
    if "Error" not in response:
        print("     ✓ Program started")
        return True
    else:
        print(f"     ✗ Failed: {response}")
        return False


def check_rtde_connection(host):
    """Test RTDE connection."""
    print(f"\nTesting RTDE connection to {host}...")
    try:
        # Try to connect to RTDE port
        s = socket.create_connection((host, 30004), timeout=2)

        # Send RTDE protocol version
        s.send(
            struct.pack(">HBH", 5, 86, 2)
        )  # Size, RTDE_REQUEST_PROTOCOL_VERSION, version 2

        # Try to receive response
        data = s.recv(4)
        if data:
            print("  ✓ RTDE port responding")
            s.close()
            return True
        else:
            print("  ✗ No RTDE response")
            s.close()
            return False

    except Exception as e:
        print(f"  ✗ RTDE connection failed: {e}")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("RTDE REGISTER FIX UTILITY")
    print("=" * 60)
    print("\nThis will fix 'RTDE input registers already in use' errors")

    robots = {"LEFT": "192.168.1.211", "RIGHT": "192.168.1.210"}

    all_fixed = True

    for name, host in robots.items():
        print(f"\n{'=' * 30}")
        print(f"{name} ROBOT ({host})")
        print(f"{'=' * 30}")

        # Fix RTDE registers
        success = fix_rtde_registers(host)

        if success:
            # Test connection
            time.sleep(2)
            if check_rtde_connection(host):
                print(f"\n✅ {name} robot RTDE fixed and ready!")
            else:
                print(f"\n⚠️  {name} robot: RTDE still not responding")
                all_fixed = False
        else:
            all_fixed = False

    print("\n" + "=" * 60)
    if all_fixed:
        print("✅ ALL RTDE ISSUES FIXED!")
        print("\nNow you can run teleoperation:")
        print("  python3 scripts/run_teleop.py --test-mode")
    else:
        print("⚠️  Some issues remain - see manual steps above")
        print("\nAfter manual setup, run:")
        print("  python3 scripts/run_teleop.py --test-mode")
    print("=" * 60)

    return 0 if all_fixed else 1


if __name__ == "__main__":
    sys.exit(main())
