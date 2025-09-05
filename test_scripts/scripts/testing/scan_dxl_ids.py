import sys, time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

if len(sys.argv) != 2:
    print("Usage: python3 scripts/scan_dxl_ids.py /dev/serial/by-id/<device>")
    sys.exit(1)

PORT = sys.argv[1]
BAUD = 1000000  # 1Mbps
PROTO = 2.0

print(f"Scanning {PORT} @ {BAUD} baud (protocol {PROTO}) for IDs 0..20")
port = PortHandler(PORT)
if not port.openPort():
    print("!! Failed to open port"); sys.exit(2)
if not port.setBaudRate(BAUD):
    print("!! Failed to set baud rate"); sys.exit(3)

packet = PacketHandler(2.0)
found = []
for dxl_id in range(0, 21):
    model, comm, err = packet.ping(port, dxl_id)
    if comm == COMM_SUCCESS:
        found.append(dxl_id)
        print(f"  ID {dxl_id} responds (model={model}, error={err})")
    time.sleep(0.01)

port.closePort()
print("\nFound IDs:", found)
