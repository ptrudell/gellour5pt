from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
PORTS = [
  "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",  # LEFT
  "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",  # RIGHT
]
BAUD = 1_000_000
PROTO = 2.0
ADDR_PRESENT_POSITION = 132  # XL-330, 4 bytes

pk = PacketHandler(PROTO)

for port in PORTS:
    ph = PortHandler(port)
    assert ph.openPort() and ph.setBaudRate(BAUD), f"open/baud failed: {port}"
    # discover IDs (0..20)
    ids=[]
    for i in range(0,21):
        _, c, _ = pk.ping(ph, i)
        if c == COMM_SUCCESS: ids.append(i)
    print(f"\n== {port} == IDs: {ids}")
    for i in ids:
        pos, c, e = pk.read4ByteTxRx(ph, i, ADDR_PRESENT_POSITION)
        ok = (c==COMM_SUCCESS and e==0)
        print(f"  ID {i}: {'OK' if ok else f'FAIL c={c} e={e}'}  pos_raw={pos if ok else '—'}")
    ph.closePort()
