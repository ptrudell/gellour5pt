#!/usr/bin/env python3
"""
Quick robot status check
"""

import socket
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))


def check_dashboard(host: str, name: str):
    """Check UR dashboard connection."""
    print(f"\n{name} Robot ({host}):")

    # Ping test
    import subprocess

    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", host], capture_output=True, check=False
    )

    if result.returncode == 0:
        print("  ✓ Network: Reachable")
    else:
        print("  ✗ Network: Unreachable")
        return

    # Dashboard test
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        s.recv(4096)  # Welcome message

        # Get program state
        s.send(b"get loaded program\n")
        loaded = s.recv(4096).decode().strip()
        print(f"  Program: {loaded}")

        s.send(b"programState\n")
        state = s.recv(4096).decode().strip()
        print(f"  State: {state}")

        if "PLAYING" in state.upper() and "EXTERNAL" in loaded.upper():
            print("  ✓ ExternalControl is PLAYING")
        else:
            print("  ✗ ExternalControl NOT running")
            print("  Fix: Load and play ExternalControl.urp on pendant")

        s.close()
    except Exception as e:
        print(f"  ✗ Dashboard: {e}")


def main():
    print("=" * 60)
    print("ROBOT STATUS CHECK")
    print("=" * 60)

    # Check dashboard connections
    check_dashboard("192.168.1.211", "LEFT")
    check_dashboard("192.168.1.210", "RIGHT")

    # Quick DXL test
    print("\nDynamixel Status:")

    # Try to read from LEFT DXL
    try:
        from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

        # LEFT
        port = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
        ph = PortHandler(port)
        pk = PacketHandler(2.0)

        if ph.openPort() and ph.setBaudRate(1000000):
            # Try to read from servo ID 1
            pos, result, error = pk.read4ByteTxRx(ph, 1, 132)
            if result == COMM_SUCCESS:
                print("  ✓ LEFT DXL: Servo ID 1 responding")
            else:
                print("  ✗ LEFT DXL: No response from servo ID 1")
            ph.closePort()
        else:
            print("  ✗ LEFT DXL: Can't open port")
    except Exception as e:
        print(f"  ✗ LEFT DXL: {e}")

    # RIGHT
    try:
        port = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
        ph = PortHandler(port)
        pk = PacketHandler(2.0)

        if ph.openPort() and ph.setBaudRate(1000000):
            # Try to read from servo ID 10
            pos, result, error = pk.read4ByteTxRx(ph, 10, 132)
            if result == COMM_SUCCESS:
                print("  ✓ RIGHT DXL: Servo ID 10 responding")
            else:
                print("  ✗ RIGHT DXL: No response from servo ID 10")
            ph.closePort()
        else:
            print("  ✗ RIGHT DXL: Can't open port")
    except Exception as e:
        print(f"  ✗ RIGHT DXL: {e}")

    print("\n" + "=" * 60)
    print("\nNEXT STEPS:")
    print("1. Ensure ExternalControl.urp is loaded and playing on BOTH robots")
    print("2. Once both show 'PLAYING', run:")
    print("   python scripts/simple_teleop.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
