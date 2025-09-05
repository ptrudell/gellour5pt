import time
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

PORT="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0"
BAUD=1_000_000; PROTO=2.0
IDS=[1,2,3,4,5,6,7]
ADDR_TORQUE_ENABLE=64
ADDR_GOAL_POSITION=116    # 4 bytes
ADDR_PRESENT_POSITION=132 # 4 bytes
DELTA=100                 # ticks

pk=PacketHandler(PROTO); ph=PortHandler(PORT)
assert ph.openPort() and ph.setBaudRate(BAUD), "open/baud failed"

# torque ON
for i in IDS:
    c,e = pk.write1ByteTxRx(ph, i, ADDR_TORQUE_ENABLE, 1)
    assert c==COMM_SUCCESS and e==0, f"torque on fail id {i}: c={c}, e={e}"

# read current, nudge +DELTA, back to start
for i in IDS:
    pos,c,e = pk.read4ByteTxRx(ph, i, ADDR_PRESENT_POSITION)
    assert c==COMM_SUCCESS and e==0, f"read fail id {i}: c={c}, e={e}"
    for tgt in (pos+DELTA, pos):
        c,e = pk.write4ByteTxRx(ph, i, ADDR_GOAL_POSITION, int(tgt)%4096)
        assert c==COMM_SUCCESS and e==0, f"write goal fail id {i}: c={c}, e={e}"
        time.sleep(0.35)

print("DONE")
ph.closePort()
