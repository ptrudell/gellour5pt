#!/usr/bin/env python3
"""
Quick utility to unlock (turn off torque) on all DXL motors.
Useful when GELLO arms are locked up after a teleop session.
"""

from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

# Serial ports for left and right GELLO arms
PORTS = [
    "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",  # LEFT
    "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",  # RIGHT
]

# Dynamixel settings
BAUD = 1_000_000
PROTO = 2.0
ADDR_TORQUE_ENABLE = 64

# Motor IDs to check (covers both arms including grippers)
IDS = list(range(1, 17))  # 1-16; non-existing IDs are ignored

# Create packet handler
pk = PacketHandler(PROTO)

print("[unlock] Attempting to turn OFF DXL torque on specified ports...")

for port in PORTS:
    ph = PortHandler(port)
    if ph.openPort() and ph.setBaudRate(BAUD):
        print(f"[unlock] Opened {port}")
        for motor_id in IDS:
            try:
                # Write torque OFF (0) to each motor
                rc, er = pk.write1ByteTxRx(ph, motor_id, ADDR_TORQUE_ENABLE, 0)
                if rc == COMM_SUCCESS and er == 0:
                    print(f"  ID {motor_id}: torque OFF ✓")
                else:
                    # Only show if motor exists but command failed
                    if rc != COMM_SUCCESS:
                        pass  # Motor doesn't exist, skip silently
                    else:
                        print(f"  ID {motor_id}: torque OFF failed (rc={rc}, er={er})")
            except Exception:
                # Usually means motor doesn't exist on this port
                pass
        ph.closePort()
        print(f"[unlock] Closed {port}")
    else:
        print(f"[unlock] Failed to open or set baud for {port}")

print("\n[unlock] DXL torque OFF requested on both ports.")
print("Your GELLO arms should now move freely.")
print("If arms are still stiff, check:")
print("  1. USB connections")
print("  2. Power to DXL motors")
print("  3. Correct port names in PORTS list")
