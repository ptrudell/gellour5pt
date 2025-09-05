from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
PORTS=[
"/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0",  # LEFT
"/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0",  # RIGHT
]
BAUD=1_000_000
PROTO=2.0
ADDR_TORQUE_ENABLE=64
ADDR_OPERATING_MODE=11
POS_MODE=3
pk=PacketHandler(PROTO)

for port_name in PORTS:
    ph=PortHandler(port_name)
    assert ph.openPort() and ph.setBaudRate(BAUD), f"open/set baud failed: {port_name}"
    print(f"\n== {port_name} ==")
    ids=[]
    for i in range(0, 21):
        m,c,e = pk.ping(ph,i)
        if c==COMM_SUCCESS: ids.append(i)
    print("IDs:", ids)
    for i in ids:
        # disable torque
        c,e = pk.write1ByteTxRx(ph,i,ADDR_TORQUE_ENABLE,0)
        # set operating mode = position(3)
        c2,e2 = pk.write1ByteTxRx(ph,i,ADDR_OPERATING_MODE,POS_MODE)
        # re-enable torque
        c3,e3 = pk.write1ByteTxRx(ph,i,ADDR_TORQUE_ENABLE,1)
        ok = (c==COMM_SUCCESS and e==0 and c2==COMM_SUCCESS and e2==0 and c3==COMM_SUCCESS and e3==0)
        print(f"  ID {i}: set mode=3 -> {'OK' if ok else f'FAIL c={c},{c2},{c3} e={e},{e2},{e3}'}")
    ph.closePort()
