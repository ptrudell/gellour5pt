import time, math, threading
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS

BAUD=1_000_000; PROTO=2.0
ADDR_TQ=64; ADDR_GOAL=116; ADDR_POS=132; TPR=4096
DEG=5; DELTA=int((DEG/360.0)*TPR)

ARMS = [
  ("/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNTI-if00-port0", [1,2,3,4,5,6]),
  ("/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAAMNUF-if00-port0", [10,11,12,13,14,15]),
]

def sweep(port, ids):
    pk=PacketHandler(PROTO); ph=PortHandler(port)
    assert ph.openPort() and ph.setBaudRate(BAUD), f"open/baud failed: {port}"
    for i in ids:
        c,e=pk.write1ByteTxRx(ph,i,ADDR_TQ,1); assert c==COMM_SUCCESS and e==0
    # read starts
    starts={}
    for i in ids:
        pos,c,e=pk.read4ByteTxRx(ph,i,ADDR_POS); assert c==COMM_SUCCESS and e==0
        starts[i]=pos
    # +DELTA -> -DELTA -> back (3 passes)
    for tgt_off in (DELTA, -DELTA, 0):
        for i in ids:
            tgt=(starts[i]+tgt_off)%TPR
            c,e=pk.write4ByteTxRx(ph,i,ADDR_GOAL,int(tgt)); assert c==COMM_SUCCESS and e==0
        time.sleep(0.8)
    for i in ids:
        c,e=pk.write1ByteTxRx(ph,i,ADDR_TQ,0); assert c==COMM_SUCCESS and e==0
    ph.closePort()

threads=[threading.Thread(target=sweep, args=arm) for arm in ARMS]
[t.start() for t in threads]; [t.join() for t in threads]
print("Both arms swept ±5°.")
