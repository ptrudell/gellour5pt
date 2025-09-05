import sys, time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
PORTS=[
"/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",
"/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",
]
BAUDS=[1_000_000, 57600, 115200]
packet=PacketHandler(2.0)
for port_name in PORTS:
    print(f"\n=== {port_name} ===")
    ph=PortHandler(port_name)
    if not ph.openPort(): print("! openPort failed"); continue
    for b in BAUDS:
        ok=ph.setBaudRate(b)
        print(f"baud {b}: set={'OK' if ok else 'FAIL'}", end="")
        if not ok: print(); continue
        found=[]
        for i in range(0, 21):
            m, r, e = packet.ping(ph, i)
            if r==COMM_SUCCESS: found.append(i)
            time.sleep(0.005)
        print(f" | IDs: {found}")
    ph.closePort()
