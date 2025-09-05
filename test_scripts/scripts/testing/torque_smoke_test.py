from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

PORTS = [
    "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",  # LEFT
    "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",  # RIGHT
]
BAUD = 1_000_000
PROTO = 2.0
ADDR_TORQUE_ENABLE = 64  # XL-330
packet = PacketHandler(PROTO)

for port_name in PORTS:
    ph = PortHandler(port_name)
    assert ph.openPort() and ph.setBaudRate(BAUD), f"open/set baud failed: {port_name}"
    print(f"\n== {port_name} ==")
    ids = []
    for i in range(0, 21):
        model, comm, err = packet.ping(ph, i)
        if comm == COMM_SUCCESS:
            ids.append(i)
    print("IDs:", ids)

    for dxl_id in ids:
        for val in (0, 1, 0):  # disable, enable, disable
            comm, err = packet.write1ByteTxRx(ph, dxl_id, ADDR_TORQUE_ENABLE, val)
            ok = (comm == COMM_SUCCESS and err == 0)
            print(f"  ID {dxl_id} torque={val} -> {'OK' if ok else f'FAIL comm={comm} err={err}'}")
    ph.closePort()
