#!/usr/bin/env python3
"""Quick diagnostic for DXL servos and UR robots."""

import sys
import time
import socket

# Test UR Dashboard connection
def test_ur_dashboard(host):
    """Test UR dashboard connection and get program state."""
    print(f"\n[UR TEST] {host}")
    print("-" * 40)
    try:
        s = socket.create_connection((host, 29999), timeout=2)
        banner = s.recv(4096).decode()
        print(f"✓ Connected to dashboard")
        
        # Get current program
        s.send(b"get loaded program\n")
        time.sleep(0.1)
        loaded = s.recv(4096).decode().strip()
        print(f"  Loaded: {loaded}")
        
        # Get program state
        s.send(b"programState\n")
        time.sleep(0.1)
        state = s.recv(4096).decode().strip()
        print(f"  State: {state}")
        
        # Get robot mode
        s.send(b"robotmode\n")
        time.sleep(0.1)
        mode = s.recv(4096).decode().strip()
        print(f"  Mode: {mode}")
        
        s.close()
        
        if "freedrive" in loaded.lower():
            print("\n⚠️  FREEDRIVE IS LOADED - Need to load ExternalControl.urp")
            print("   On pendant: File → Load Program → ExternalControl.urp")
        
        return True
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return False

# Test DXL servos
def test_dxl(port, baud, ids):
    """Test DXL servo connection."""
    print(f"\n[DXL TEST] {port}")
    print("-" * 40)
    print(f"Baud: {baud}, IDs: {ids}")
    
    try:
        from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
        
        ph = PortHandler(port)
        pk = PacketHandler(2.0)
        
        if not ph.openPort():
            print("✗ Failed to open port")
            return False
        
        if not ph.setBaudRate(baud):
            print("✗ Failed to set baud rate")
            ph.closePort()
            return False
        
        print("✓ Port opened")
        
        # Try to ping each servo
        found = []
        for servo_id in ids:
            _, result, error = pk.ping(ph, servo_id)
            if result == COMM_SUCCESS and error == 0:
                found.append(servo_id)
                print(f"  ✓ ID {servo_id}: Responding")
            else:
                print(f"  ✗ ID {servo_id}: rc={result}, err={error}")
        
        ph.closePort()
        
        if not found:
            print("\n⚠️  NO SERVOS RESPONDING")
            print("   1. Check 5V power supply")
            print("   2. Check Data+ and Data- wiring")
            print(f"   3. Try different baud: {1000000 if baud == 57600 else 57600}")
        
        return len(found) > 0
        
    except ImportError:
        print("✗ dynamixel_sdk not installed")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("QUICK SYSTEM DIAGNOSTIC")
    print("=" * 60)
    
    # Default test parameters
    ur_left = "192.168.1.211"
    ur_right = "192.168.1.210"
    left_port = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
    right_port = "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
    baud = 57600  # Try 57600 first since that's what failed in your log
    left_ids = [1, 2, 3, 4, 5, 6, 7]
    right_ids = [10, 11, 12, 13, 14, 15, 16]
    
    # Test everything
    ur_ok = 0
    if test_ur_dashboard(ur_left):
        ur_ok += 1
    if test_ur_dashboard(ur_right):
        ur_ok += 1
    
    dxl_ok = 0
    if test_dxl(left_port, baud, left_ids):
        dxl_ok += 1
    if test_dxl(right_port, baud, right_ids):
        dxl_ok += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"UR Robots: {ur_ok}/2 ready")
    print(f"DXL Arms: {dxl_ok}/2 ready")
    
    if ur_ok == 0:
        print("\n⚠️  Fix UR issues:")
        print("  1. Load ExternalControl.urp on pendants")
        print("  2. Enable Remote Control")
        print("  3. Set Host IP = your PC's IP")
    
    if dxl_ok == 0:
        print("\n⚠️  Fix DXL issues:")
        print("  1. Check 5V power (LEDs should be on)")
        print("  2. Try baud 1000000 instead of 57600")
        print("  3. Check USB adapters: ls -la /dev/serial/by-id/")
    
    sys.exit(0 if (ur_ok > 0 and dxl_ok > 0) else 1)
