#!/usr/bin/env python3
"""
Test Dynamixel XL330 connection and diagnose rc=-3001 errors.
"""

import argparse
import sys
import time

try:
    from dynamixel_sdk import (
        COMM_SUCCESS,
        GroupBulkRead,
        PacketHandler,
        PortHandler,
    )
except ImportError as e:
    print(f"Error importing dynamixel_sdk: {e}")
    print("Install with: pip install dynamixel_sdk")
    sys.exit(1)


def test_single_servo(port: str, baud: int, servo_id: int, protocol: float = 2.0):
    """Test a single servo connection."""
    ADDR_TORQUE_ENABLE = 64
    ADDR_PRESENT_POSITION = 132

    print(f"\nTesting servo ID {servo_id} on {port} @ {baud} baud")
    print("=" * 60)

    ph = PortHandler(port)
    pk = PacketHandler(protocol)

    # Open port
    if not ph.openPort():
        print(f"✗ Failed to open port {port}")
        print("  Check: USB cable connected? Port path correct?")
        return False
    print(f"✓ Port opened: {port}")

    # Set baud rate
    if not ph.setBaudRate(baud):
        print(f"✗ Failed to set baud rate to {baud}")
        ph.closePort()
        return False
    print(f"✓ Baud rate set: {baud}")

    # Try to read position
    print(f"\nReading position from servo ID {servo_id}...")
    pos, rc, er = pk.read4ByteTxRx(ph, servo_id, ADDR_PRESENT_POSITION)

    if rc == COMM_SUCCESS and er == 0:
        print(f"✓ SUCCESS! Position = {pos} (0x{pos:04x})")
        angle = ((pos - 2048) / 4096.0) * 360.0
        print(f"  Angle: {angle:.1f}°")
        success = True
    else:
        print(f"✗ FAILED! rc={rc}, error={er}")

        # Diagnose error codes
        if rc == -3001:
            print("\n  DIAGNOSIS: Timeout (rc=-3001)")
            print("  Possible causes:")
            print("  • Wrong servo ID (servo not responding)")
            print("  • Wrong baud rate (try 57600 or 1000000)")
            print("  • Servo not powered (check 5V supply)")
            print("  • Wiring issue (check data lines)")
            print("  • Protocol mismatch (XL330 uses protocol 2.0)")
        elif rc == -3002:
            print("\n  DIAGNOSIS: Checksum error")
            print("  • Electrical noise or bad connection")
        elif rc == -1:
            print("\n  DIAGNOSIS: Port error")
            print("  • Port may be in use by another process")
        success = False

    # Try to ping the servo
    if not success:
        print(f"\nPinging servo ID {servo_id}...")
        model, rc, er = pk.ping(ph, servo_id)
        if rc == COMM_SUCCESS:
            print(f"✓ Servo responded to ping! Model number: {model}")
        else:
            print(f"✗ No response to ping (rc={rc}, er={er})")

    ph.closePort()
    return success


def scan_for_servos(port: str, baud: int, id_range: range = range(1, 25), protocol: float = 2.0):
    """Scan for any responding servos."""
    print(f"\nScanning for servos on {port} @ {baud} baud")
    print("=" * 60)

    ph = PortHandler(port)
    pk = PacketHandler(protocol)

    if not ph.openPort() or not ph.setBaudRate(baud):
        print(f"✗ Failed to open {port} @ {baud}")
        return []

    found = []
    print(f"Scanning IDs {id_range.start} to {id_range.stop - 1}...")

    for servo_id in id_range:
        model, rc, er = pk.ping(ph, servo_id)
        if rc == COMM_SUCCESS:
            found.append(servo_id)
            print(f"  ✓ Found servo at ID {servo_id} (model: {model})")
        else:
            print(f"  · ID {servo_id}: no response", end="\r")

    print(" " * 50, end="\r")  # Clear line

    if found:
        print(f"\n✓ Found {len(found)} servo(s): {found}")
    else:
        print("\n✗ No servos found")
        print("\nTroubleshooting:")
        print("1. Check servo power (5V for XL330)")
        print("2. Try different baud rates: 57600, 1000000")
        print("3. Verify wiring (data lines connected?)")
        print("4. Check servo IDs with Dynamixel Wizard")

    ph.closePort()
    return found


def test_bulk_read(port: str, baud: int, ids: list, protocol: float = 2.0):
    """Test bulk read performance."""
    ADDR_PRESENT_POSITION = 132

    print(f"\nTesting bulk read for IDs {ids} on {port}")
    print("=" * 60)

    ph = PortHandler(port)
    pk = PacketHandler(protocol)

    if not ph.openPort() or not ph.setBaudRate(baud):
        print(f"✗ Failed to open {port} @ {baud}")
        return

    # Setup bulk read
    bulk = GroupBulkRead(ph, pk)
    for servo_id in ids:
        if not bulk.addParam(servo_id, ADDR_PRESENT_POSITION, 4):
            print(f"✗ Failed to add ID {servo_id} to bulk read")

    # Try bulk read
    print("\nBulk read test...")
    if bulk.txRxPacket():
        print("✓ Bulk read packet sent/received")
        for servo_id in ids:
            if bulk.isAvailable(servo_id, ADDR_PRESENT_POSITION, 4):
                pos = bulk.getData(servo_id, ADDR_PRESENT_POSITION, 4)
                print(f"  ID {servo_id}: position = {pos}")
            else:
                print(f"  ID {servo_id}: data not available")
    else:
        print("✗ Bulk read failed - falling back to individual reads recommended")

    ph.closePort()


def main():
    parser = argparse.ArgumentParser(description="Test Dynamixel connection")
    parser.add_argument("port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate (default: 1000000)")
    parser.add_argument("--id", type=int, default=1, help="Servo ID to test (default: 1)")
    parser.add_argument("--scan", action="store_true", help="Scan for all servos")
    parser.add_argument(
        "--bulk", type=str, help="Test bulk read with comma-separated IDs (e.g., 1,2,3,4,5,6)"
    )
    parser.add_argument(
        "--protocol", type=float, default=2.0, help="Dynamixel protocol version (default: 2.0)"
    )

    args = parser.parse_args()

    # Try different baud rates if the default fails
    baud_rates = [args.baud]
    if args.baud != 57600:
        baud_rates.append(57600)
    if args.baud != 1000000:
        baud_rates.append(1000000)

    success = False

    # Test single servo
    if not args.scan and not args.bulk:
        for baud in baud_rates:
            if test_single_servo(args.port, baud, args.id, args.protocol):
                success = True
                break
            if baud != baud_rates[-1]:
                print("\nTrying different baud rate...")

    # Scan mode
    if args.scan:
        for baud in baud_rates:
            found = scan_for_servos(args.port, baud, protocol=args.protocol)
            if found:
                success = True
                break

    # Bulk read test
    if args.bulk:
        ids = [int(x) for x in args.bulk.split(",")]
        test_bulk_read(args.port, args.baud, ids, args.protocol)

    if not success and not args.bulk:
        print("\n" + "=" * 60)
        print("CONNECTION FAILED")
        print("=" * 60)
        print("\nQuick fixes to try:")
        print("1. Check power: XL330 needs 5V (3.7-6V range)")
        print("2. Verify USB adapter: ls -la /dev/serial/by-id/")
        print("3. Try scanning: python", sys.argv[0], args.port, "--scan")
        print("4. Use Dynamixel Wizard to verify servo IDs and baud rate")
        print("5. Check permissions: sudo chmod 666", args.port)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

