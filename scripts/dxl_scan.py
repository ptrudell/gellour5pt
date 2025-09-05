# dxl_scan.py
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
import sys

if len(sys.argv) < 3:
    print("usage: python dxl_scan.py <port> <baud> [proto=2.0] [id_min=1] [id_max=30]")
    sys.exit(1)

port  = sys.argv[1]
baud  = int(sys.argv[2])
proto = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
idmin = int(sys.argv[4]) if len(sys.argv) > 4 else 1
idmax = int(sys.argv[5]) if len(sys.argv) > 5 else 30

ph = PortHandler(port); assert ph.openPort(), f"open failed: {port}"
assert ph.setBaudRate(baud), f"baud failed: {baud}"
pk = PacketHandler(proto)

found = []
for i in range(idmin, idmax+1):
    _, comm, err = pk.ping(ph, i)
    if comm == COMM_SUCCESS and err == 0:
        found.append(i)
ph.closePort()
print(f"Found IDs on {port}: {found}")

