import time, math
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

PORT="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0"
BAUD=1_000_000; PROTO=2.0
IDS=[10,11,12,13,14,15]  # (skip 16; it's the gripper)
ADDR_TQ=64; ADDR_GOAL=116; ADDR_POS=132
DEG=5; TPR=4096; DELTA=int((DEG/360.0)*TPR)

pk=PacketHandler(PROTO); ph=PortHandler(PORT)
assert ph.openPort() and ph.setBaudRate(BAUD), "open/baud failed"

for i in IDS:
    c,e = pk.write1ByteTxRx(ph,i,ADDR_TQ,1); assert c==COMM_SUCCESS and e==0, f"torque on fail {i}"

for i in IDS:
    pos,c,e = pk.read4ByteTxRx(ph,i,ADDR_POS); assert c==COMM_SUCCESS and e==0, f"read fail {i}"
    for tgt in (pos+DELTA, pos-DELTA, pos):
        c,e = pk.write4ByteTxRx(ph,i,ADDR_GOAL,int(tgt)%TPR); assert c==COMM_SUCCESS and e==0, f"goal fail {i}"
        time.sleep(0.5)

for i in IDS:
    c,e = pk.write1ByteTxRx(ph,i,ADDR_TQ,0); assert c==COMM_SUCCESS and e==0, f"torque off fail {i}"

ph.closePort()
print("RIGHT jog done.")
